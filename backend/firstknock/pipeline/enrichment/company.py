import json
import structlog
import httpx
from pydantic import BaseModel
from firstknock.config import settings

logger = structlog.get_logger()

PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"

# Domains that are never a company's own website — blog/social platforms Perplexity
# sometimes returns for small startups that have more web presence there than on
# their actual domain.
_NON_COMPANY_DOMAINS = {
    "hashnode.dev", "hashnode.com",
    "medium.com",
    "substack.com",
    "wordpress.com", "wordpress.org",
    "blogspot.com",
    "notion.so", "notion.site",
    "github.com", "github.io",
    "linkedin.com",
    "twitter.com", "x.com",
    "facebook.com",
    "instagram.com",
    "crunchbase.com",
    "angel.co", "angellist.com",
    "producthunt.com",
    "dev.to",
    "beehiiv.com",
    "carrd.co",
    "wix.com",
    "squarespace.com",
    "webflow.io",
    "sites.google.com",
}


def _is_valid_company_website(url: str | None) -> bool:
    """Return False if the URL points to a blog/social platform instead of a real company site."""
    if not url:
        return False
    # Normalise: strip scheme
    clean = url.lower().removeprefix("https://").removeprefix("http://").removeprefix("www.")
    domain = clean.split("/")[0]
    # Check if any blocked domain appears as a suffix (catches *.hashnode.dev etc.)
    return not any(domain == bd or domain.endswith("." + bd) for bd in _NON_COMPANY_DOMAINS)


class CompanyData(BaseModel):
    # Identity
    website: str | None = None
    linkedin_url: str | None = None

    # Context
    description: str | None = None
    business_model: str | None = None   # B2B SaaS | B2C | marketplace | enterprise | etc.
    industry: str | None = None

    # Funding trajectory
    stage: str | None = None            # seed|series-a|series-b|series-c|public|private|unknown
    total_funding_usd: int | None = None
    last_round_type: str | None = None  # "Series B", "Seed", "IPO", etc.
    last_round_amount_usd: int | None = None
    last_round_date: int | None = None  # year, e.g. 2023

    # Key investors
    key_investors: list[str] = []

    # People
    founders: list[str] = []
    ceo: str | None = None

    # Size & location
    headcount: int | None = None
    founded: int | None = None
    headquarters: str | None = None


COMPANY_PROMPT = """Find company intelligence data for "{name}"{context_hint}.

Return JSON only — no explanation, no markdown fences:
{{
  "website": "string or null",
  "linkedin_url": "string or null",
  "description": "2-3 sentence summary of what the company does and its business model, or null",
  "business_model": "one of: B2B SaaS | B2C | marketplace | enterprise | developer tools | fintech | healthtech | other — or null",
  "industry": "string or null",
  "stage": "one of: seed | series-a | series-b | series-c | public | private | unknown",
  "total_funding_usd": "integer in USD or null",
  "last_round_type": "e.g. Series B, Seed, IPO — or null",
  "last_round_amount_usd": "integer in USD or null",
  "last_round_date": "integer year e.g. 2023 or null",
  "key_investors": ["list of notable VC or fund names, empty array if unknown"],
  "founders": ["list of founder full names, empty array if unknown"],
  "ceo": "current CEO full name or null",
  "headcount": "approximate integer or null",
  "founded": "integer year or null",
  "headquarters": "City, Country or null"
}}

Rules:
- stage must be one of the exact strings listed
- Use null for any field you cannot find reliable data for
- Do NOT guess or fabricate funding numbers, investor names, or people
- headcount and funding figures should be approximate (e.g. 500, 1000000)
- total_funding_usd and last_round_amount_usd must be raw integers (no commas, no $)"""

FOUNDERS_PROMPT = """Who are the founders and current CEO of "{name}"{context_hint}?

Return JSON only — no explanation, no markdown fences:
{{
  "founders": ["list of founder full names"],
  "ceo": "current CEO full name or null"
}}

Rules:
- Only include founders you are confident about from reliable sources
- Return empty array for founders if you cannot find reliable data
- Do NOT fabricate or guess names"""


async def _query_perplexity(company_name: str, hint: str = "") -> CompanyData:
    if not settings.perplexity_api_key:
        logger.warning("perplexity_api_key_missing")
        return CompanyData()

    context_hint = f" (context: {hint})" if hint else ""
    prompt = COMPANY_PROMPT.format(name=company_name, context_hint=context_hint)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                PERPLEXITY_URL,
                headers={
                    "Authorization": f"Bearer {settings.perplexity_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "sonar",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 512,
                    "temperature": 0.1,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()

            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            raw = json.loads(content)
            raw_website = raw.get("website") or None
            if not _is_valid_company_website(raw_website):
                if raw_website:
                    logger.warning("company_website_rejected", company=company_name, url=raw_website)
                raw_website = None
            return CompanyData(
                website=raw_website,
                linkedin_url=raw.get("linkedin_url") or None,
                description=raw.get("description") or None,
                business_model=raw.get("business_model") or None,
                industry=raw.get("industry") or None,
                stage=raw.get("stage") or None,
                total_funding_usd=int(raw["total_funding_usd"]) if raw.get("total_funding_usd") else None,
                last_round_type=raw.get("last_round_type") or None,
                last_round_amount_usd=int(raw["last_round_amount_usd"]) if raw.get("last_round_amount_usd") else None,
                last_round_date=int(raw["last_round_date"]) if raw.get("last_round_date") else None,
                key_investors=raw.get("key_investors") or [],
                founders=raw.get("founders") or [],
                ceo=raw.get("ceo") or None,
                headcount=int(raw["headcount"]) if raw.get("headcount") else None,
                founded=int(raw["founded"]) if raw.get("founded") else None,
                headquarters=raw.get("headquarters") or None,
            )

    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        logger.warning("perplexity_parse_failed", company=company_name, error=str(exc))
        return CompanyData()
    except Exception as exc:
        logger.warning("perplexity_request_failed", company=company_name, error=str(exc))
        return CompanyData()


async def _query_founders_only(company_name: str, hint: str = "") -> tuple[list[str], str | None]:
    """Targeted retry to fetch founders/CEO when the main call returned empty."""
    if not settings.perplexity_api_key:
        return [], None

    context_hint = f" (context: {hint})" if hint else ""
    prompt = FOUNDERS_PROMPT.format(name=company_name, context_hint=context_hint)

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                PERPLEXITY_URL,
                headers={
                    "Authorization": f"Bearer {settings.perplexity_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "sonar",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 128,
                    "temperature": 0.1,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()

            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            raw = json.loads(content)
            founders = [f for f in (raw.get("founders") or []) if f]
            ceo = raw.get("ceo") or None
            return founders, ceo

    except Exception as exc:
        logger.warning("perplexity_founders_retry_failed", company=company_name, error=str(exc))
        return [], None


async def enrich_companies(
    company_names: list[str],
    hints: dict[str, str] | None = None,
) -> dict[str, dict]:
    """
    Enrich a list of company names with company intelligence via Perplexity AI.
    Returns {company_name: CompanyData dict}.

    hints: optional {company_name: "industry, location or website"} to disambiguate
           companies that share a common name.
    """
    hints = hints or {}
    results: dict[str, dict] = {}

    for name in company_names:
        if not name:
            continue

        hint = hints.get(name, "")
        data = await _query_perplexity(name, hint)

        # Retry founders specifically when the main call returned empty but the
        # company appears real (has a website or funding data).
        if not data.founders and (data.website or data.total_funding_usd):
            logger.info("company_founders_retry", company=name)
            retry_hint = hint or data.website or data.industry or ""
            founders, ceo = await _query_founders_only(name, retry_hint)
            if founders:
                data.founders = founders
            if not data.ceo and ceo:
                data.ceo = ceo

        results[name] = data.model_dump()
        logger.info(
            "company_enriched",
            company=name,
            stage=data.stage,
            total_funding_usd=data.total_funding_usd,
            founders=data.founders,
        )

    return results
