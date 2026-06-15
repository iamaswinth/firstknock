"""
Run this once (or whenever the session expires) to capture your login cookies
and the Algolia API key that the site generates per-session.

Usage:
    python auth.py

A headed browser will open. Log in with your YC magic link, then the script
navigates to the companies page automatically and captures everything.
"""

import asyncio
import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from playwright.async_api import async_playwright

from config import COOKIES_FILE, ALGOLIA_KEY_FILE, WAAS_BASE_URL

# Use the full filter URL — this is what triggers the Algolia search on load
COMPANIES_URL = (
    f"{WAAS_BASE_URL}/companies"
    "?demographic=any&hasEquity=any&hasSalary=any&industry=any"
    "&interviewProcess=any&jobType=any&layout=list-compact"
    "&sortBy=created_desc&tab=any&usVisaNotRequired=any"
)

LOGIN_URL = (
    "https://account.ycombinator.com/magic"
    "?continue=https%3A%2F%2Fwww.workatastartup.com%2F"
)


async def login_and_capture() -> None:
    algolia_key: str | None = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        # SYNC handler — async handlers have timing issues with Playwright events
        def on_request(request):
            nonlocal algolia_key
            if "algolia.net" not in request.url:
                return
            # Try request headers first
            key = request.headers.get("x-algolia-api-key")
            # Fallback: key is also in the URL query params
            if not key:
                params = parse_qs(urlparse(request.url).query)
                key_list = params.get("x-algolia-api-key")
                key = key_list[0] if key_list else None
            if key and not algolia_key:
                algolia_key = key
                print(f"  [auth] Algolia key captured ({len(key)} chars)")

        page.on("request", on_request)

        # Step 1: login
        print("Opening YC login page — enter your email to receive the magic link...")
        await page.goto(LOGIN_URL, wait_until="networkidle")

        print("Waiting for you to click the magic link in your email...")
        await page.wait_for_url(
            lambda url: "workatastartup.com" in url and "account.ycombinator" not in url,
            timeout=300_000,  # 5 minutes
        )
        print("  Login detected!")

        # Step 2: navigate to the companies page with full filter params
        print("Loading companies page (this triggers the Algolia request)...")
        await page.goto(COMPANIES_URL, wait_until="domcontentloaded")

        # Wait up to 30s for the Algolia XHR to fire naturally
        for _ in range(30):
            if algolia_key:
                break
            await asyncio.sleep(1)

        # If still no key, try interacting with the page to trigger Algolia
        if not algolia_key:
            print("  Algolia request not detected yet — trying page interaction...")
            try:
                # Change the sortBy dropdown to force a new search
                await page.wait_for_selector("select", timeout=5_000)
                await page.select_option("select", index=1)
                await asyncio.sleep(3)
                await page.select_option("select", index=0)
                await asyncio.sleep(3)
            except Exception:
                pass

            # Final wait
            for _ in range(10):
                if algolia_key:
                    break
                await asyncio.sleep(1)

        if not algolia_key:
            raise RuntimeError(
                "Could not capture the Algolia key.\n"
                "Try manually changing a filter on the companies page "
                "while this browser window is open, then re-run auth.py."
            )

        # Step 3: save cookies + key
        cookies = await context.cookies()
        Path(COOKIES_FILE).write_text(
            json.dumps(cookies, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"  [auth] {len(cookies)} cookies saved → {COOKIES_FILE}")

        Path(ALGOLIA_KEY_FILE).write_text(algolia_key, encoding="utf-8")
        print(f"  [auth] Algolia key saved → {ALGOLIA_KEY_FILE}")

        await browser.close()

    print("\nDone. Run  python main.py  for daily scraping.")


if __name__ == "__main__":
    asyncio.run(login_and_capture())
