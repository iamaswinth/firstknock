import asyncio
import json
from pathlib import Path
from urllib.parse import urlencode, unquote

import httpx

from config import (
    ALGOLIA_APP_ID,
    ALGOLIA_INDEX,
    ALGOLIA_HITS_PER_PAGE,
    WAAS_BASE_URL,
    WAAS_FETCH_URL,
    FETCH_BATCH_SIZE,
    RATE_DELAY_SECONDS,
    COOKIES_FILE,
    ALGOLIA_KEY_FILE,
)

_BROWSER_HEADERS = {
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "accept-language": "en-US,en;q=0.9",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "cors",
    "sec-fetch-dest": "empty",
    "x-requested-with": "XMLHttpRequest",
}


def _load_cookies() -> dict[str, str]:
    data = json.loads(Path(COOKIES_FILE).read_text(encoding="utf-8"))
    return {c["name"]: c["value"] for c in data}


def _load_algolia_key() -> str:
    return Path(ALGOLIA_KEY_FILE).read_text(encoding="utf-8").strip()


class SessionExpiredError(RuntimeError):
    """Raised when the server signals our session is no longer valid."""


class WaaSClient:
    """Async context manager that handles auth, CSRF, and rate limiting."""

    def __init__(self) -> None:
        self._cookies = _load_cookies()
        self._algolia_key = _load_algolia_key()
        self._csrf: str | None = None
        self._http: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "WaaSClient":
        self._http = httpx.AsyncClient(
            cookies=self._cookies,
            headers={**_BROWSER_HEADERS, "accept": "application/json"},
            follow_redirects=False,  # detect session expiry via redirects
            timeout=30.0,
        )
        await self._refresh_csrf()
        return self

    async def __aexit__(self, *_) -> None:
        if self._http:
            await self._http.aclose()

    # ── CSRF ──────────────────────────────────────────────────────────────────

    async def _refresh_csrf(self) -> None:
        resp = await self._http.get(
            f"{WAAS_BASE_URL}/companies",
            headers={"accept": "text/html,application/xhtml+xml"},
        )
        if resp.status_code in (301, 302, 303):
            raise SessionExpiredError(
                "Session expired (got redirect). Re-run auth.py to log in again."
            )

        # Multiple XSRF-TOKEN cookies can exist (different domains); pick the WaaS one.
        csrf = self._http.cookies.get("XSRF-TOKEN", domain="www.workatastartup.com")
        if not csrf:
            for cookie in self._http.cookies.jar:
                if cookie.name == "XSRF-TOKEN":
                    csrf = unquote(cookie.value)
                    break

        if not csrf:
            raise SessionExpiredError(
                "Could not read XSRF-TOKEN — session may have expired. Re-run auth.py."
            )

        self._csrf = csrf

    # ── Algolia ───────────────────────────────────────────────────────────────

    _ALGOLIA_URL = (
        f"https://{ALGOLIA_APP_ID.lower()}-dsn.algolia.net/1/indexes/*/queries"
    )
    _ALGOLIA_HEADERS = {
        "x-algolia-agent": "Algolia for JavaScript (3.35.1); Browser",
        "x-algolia-application-id": ALGOLIA_APP_ID,
        "origin": WAAS_BASE_URL,
        "referer": f"{WAAS_BASE_URL}/",
    }

    async def _algolia_post(self, payload: dict) -> list[dict]:
        headers = {**self._ALGOLIA_HEADERS, "x-algolia-api-key": self._algolia_key}
        resp = await self._http.post(self._ALGOLIA_URL, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()["results"]

    def _algolia_params(self, page: int) -> str:
        return urlencode({
            "query": "",
            "page": page,
            "attributesToRetrieve": json.dumps(["company_id"]),
            "attributesToHighlight": json.dumps([]),
            "attributesToSnippet": json.dumps([]),
            "hitsPerPage": ALGOLIA_HITS_PER_PAGE,
            "distinct": "true",
        })

    async def _algolia_query(self, page: int) -> dict:
        payload = {
            "requests": [{"indexName": ALGOLIA_INDEX, "params": self._algolia_params(page)}]
        }
        return (await self._algolia_post(payload))[0]

    async def get_all_company_ids(self) -> list[int]:
        """
        Return IDs for all actively-hiring YC companies visible in Algolia.
        The secured API key limits results to the 1000 most-recently-active companies.
        """
        seen: set[int] = set()
        company_ids: list[int] = []
        page = 0

        while True:
            result = await self._algolia_query(page)
            nb_pages = result.get("nbPages", 1)
            nb_hits = result.get("nbHits", 0)
            for hit in result.get("hits", []):
                cid = hit.get("company_id")
                if cid and cid not in seen:
                    seen.add(cid)
                    company_ids.append(cid)
            print(f"  [algolia] page {page + 1}/{nb_pages} — {len(company_ids)}/{nb_hits} IDs")
            if page + 1 >= nb_pages:
                break
            page += 1
            await asyncio.sleep(0.2)

        return company_ids

    # ── /companies/fetch ──────────────────────────────────────────────────────

    async def _fetch_batch(self, ids: list[int]) -> list[dict]:
        resp = await self._http.post(
            WAAS_FETCH_URL,
            json={"ids": ids},
            headers={
                "content-type": "application/json",
                "x-csrf-token": self._csrf,
                "referer": f"{WAAS_BASE_URL}/companies",
            },
        )
        if resp.status_code in (301, 302, 303):
            raise SessionExpiredError(
                "Redirect on /companies/fetch — session expired, re-run auth.py."
            )
        if resp.status_code in (401, 403):
            raise SessionExpiredError(
                f"HTTP {resp.status_code} on /companies/fetch — re-run auth.py."
            )
        resp.raise_for_status()
        return resp.json().get("companies", [])

    async def fetch_all_companies(self, ids: list[int]) -> list[dict]:
        """Batch-fetch full company+job+founder details for all given IDs."""
        all_companies: list[dict] = []
        total = len(ids)

        for start in range(0, total, FETCH_BATCH_SIZE):
            chunk = ids[start : start + FETCH_BATCH_SIZE]
            all_companies.extend(await self._fetch_batch(chunk))
            done = min(start + FETCH_BATCH_SIZE, total)
            print(f"  [fetch] {done}/{total} companies fetched")
            if done < total:
                await asyncio.sleep(RATE_DELAY_SECONDS)

        return all_companies
