import asyncio
import re
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
# Roles that signal a founder-run or personally-owned company with no guaranteed web presence.
# If the hint contains one of these roles AND has no website URL, skip Perplexity enrichment
# entirely — it will hallucinate data from an unrelated company with a similar name.
_FOUNDER_ROLES = {"founder", "co-founder", "cofounder", "owner", "proprietor", "co founder"}

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


def _names_match(queried: str, found: str | None) -> bool:
    """Return True if found_name is plausibly the same company as queried.

    Strips all non-alphanumeric characters so 'Marketing Benz' and 'MarketingBenz'
    both normalise to 'marketingbenz'. A mismatch like 'marketingbenz' vs
    'marketingintelligenceio' returns False and causes the enrichment to be discarded.
    """
    if not found:
        return True  # Perplexity didn't echo a name — give it the benefit of the doubt
    q = re.sub(r'[^a-z0-9]', '', queried.lower())
    f = re.sub(r'[^a-z0-9]', '', found.lower())
    if not q or not f:
        return True
    return q in f or f in q


class CompanyData(BaseModel):
    # Identity
    website: str | None = None
    linkedin_url: str | None = None

    # Context
    description: str | None = None
    business_model: str | None = None   # B2B SaaS | B2C | marketplace | enterprise | etc.
    industry: str | None = None

    # Classification
    domain: str | None = None           # HR Tech | FinTech | DevTools | HealthTech | etc.
    customer_type: str | None = None    # B2B | B2C | B2B2C | Enterprise | Developer | Government | Consumer
    company_size: str | None = None     # 1-10 | 11-50 | 51-200 | 201-500 | 501-1000 | 1001-5000 | 5000+
    tags: list[str] = []                # ["AI/ML", "SaaS", "Open Source", ...]

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

IMPORTANT — identification rules:
- The context (role, what the company does) is the most reliable identifier; trust it above all else.
- If a website is provided, use it only if its content is consistent with the context. \
  If the site belongs to a different company with the same name, ignore it.
- Do NOT return data for a different company that happens to share the same name or domain.

Return JSON only — no explanation, no markdown fences.
Fields are grouped by category; each group is clearly labelled in comments:

{{
  "found_name": "exact company name you found data for, or null",

  "identity": {{
    "website": "string or null",
    "linkedin_url": "string or null",
    "founded": "integer year or null",
    "headquarters": "City, Country or null"
  }},

  "context": {{
    "description": "2-3 sentence summary of what the company does and its business model, or null",
    "business_model": "one of: B2B SaaS | B2C | marketplace | enterprise | developer tools | other — or null",
    "industry": "broad industry string (e.g. Software, Financial Services, Healthcare) or null"
  }},

  "classification": {{
    "domain": "specific tech vertical — one of: HR Tech | FinTech | EdTech | DevTools | HealthTech | LegalTech | ClimateTech | AdTech | MarTech | E-commerce | Logistics | Cybersecurity | Data & Analytics | PropTech | AgriTech | SpaceTech | Mobility | Gaming | Media & Entertainment | InsurTech | BioTech | Manufacturing Tech | GovTech | Consumer | other — or null",
    "customer_type": "primary buyer — one of: B2B | B2C | B2B2C | Enterprise | Developer | Government | Consumer — or null",
    "company_size": "headcount bucket — one of: 1-10 | 11-50 | 51-200 | 201-500 | 501-1000 | 1001-5000 | 5000+ — must match headcount, or null",
    "tags": ["3-8 short labels such as: AI/ML, Open Source, API-first, PLG, SaaS, Marketplace, Platform, Mobile-first, Cloud-native, No-code, Real-time, Deep Tech — empty array if unknown"]
  }},

  "funding": {{
    "stage": "one of: seed | series-a | series-b | series-c | public | private | unknown",
    "total_funding_usd": "integer in USD or null",
    "last_round_type": "e.g. Series B, Seed, IPO — or null",
    "last_round_amount_usd": "integer in USD or null",
    "last_round_date": "integer year e.g. 2023 or null",
    "key_investors": ["notable VC or fund names — empty array if unknown"]
  }},

  "people": {{
    "founders": ["founder full names — empty array if unknown"],
    "ceo": "current CEO full name or null"
  }},

  "size": {{
    "headcount": "approximate integer or null"
  }}
}}

Rules:
- found_name: the actual name you retrieved data for; null if the company cannot be identified or \
  you are forced to return data for a similarly-named company
- stage must be one of the exact strings listed
- domain and customer_type must be one of the exact strings listed
- company_size must align with headcount (e.g. headcount 40 → "11-50")
- Use null for any field you cannot find reliable data for
- If the context describes a small/new company you cannot verify online, return null for funding \
  fields and unknown for stage — do NOT substitute data from a different company with the same name
- Do NOT guess or fabricate funding numbers, investor names, or people
- headcount and funding figures must be raw integers (no commas, no $, no strings)"""

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

    # Format hint as a clearly labelled block so the model treats it as authoritative context,
    # not just a parenthetical note.
    if hint:
        context_hint = f"\nKnown context: {hint}"
    else:
        context_hint = ""
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
                    "max_tokens": 900,
                    "temperature": 0.1,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()

            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            raw = json.loads(content)

            # Reject if Perplexity found a different company with a similar name
            found_name = raw.get("found_name") or None
            if not _names_match(company_name, found_name):
                logger.warning(
                    "company_enrichment_rejected_name_mismatch",
                    queried=company_name,
                    found=found_name,
                )
                return CompanyData()

            identity = raw.get("identity") or {}
            context = raw.get("context") or {}
            classification = raw.get("classification") or {}
            funding = raw.get("funding") or {}
            people = raw.get("people") or {}
            size = raw.get("size") or {}

            raw_website = identity.get("website") or None
            if not _is_valid_company_website(raw_website):
                if raw_website:
                    logger.warning("company_website_rejected", company=company_name, url=raw_website)
                raw_website = None
            return CompanyData(
                website=raw_website,
                linkedin_url=identity.get("linkedin_url") or None,
                founded=int(identity["founded"]) if identity.get("founded") else None,
                headquarters=identity.get("headquarters") or None,
                description=context.get("description") or None,
                business_model=context.get("business_model") or None,
                industry=context.get("industry") or None,
                domain=classification.get("domain") or None,
                customer_type=classification.get("customer_type") or None,
                company_size=classification.get("company_size") or None,
                tags=classification.get("tags") or [],
                stage=funding.get("stage") or None,
                total_funding_usd=int(funding["total_funding_usd"]) if funding.get("total_funding_usd") else None,
                last_round_type=funding.get("last_round_type") or None,
                last_round_amount_usd=int(funding["last_round_amount_usd"]) if funding.get("last_round_amount_usd") else None,
                last_round_date=int(funding["last_round_date"]) if funding.get("last_round_date") else None,
                key_investors=funding.get("key_investors") or [],
                founders=people.get("founders") or [],
                ceo=people.get("ceo") or None,
                headcount=int(size["headcount"]) if size.get("headcount") else None,
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


_PERPLEXITY_SEM = asyncio.Semaphore(5)


async def _enrich_one(name: str, hint: str) -> tuple[str, dict]:
    """Enrich a single company; returns (name, data_dict). Always succeeds."""
    hint_lower = hint.lower()
    has_website_hint = "website:" in hint_lower
    is_founder_role = any(f"role: {r}" in hint_lower for r in _FOUNDER_ROLES)
    if is_founder_role and not has_website_hint:
        logger.info("company_enrichment_skipped_founder", company=name)
        return name, CompanyData().model_dump()

    async with _PERPLEXITY_SEM:
        data = await _query_perplexity(name, hint)

    if not data.founders and (data.website or data.total_funding_usd):
        logger.info("company_founders_retry", company=name)
        retry_hint = hint or data.website or data.industry or ""
        founders, ceo = await _query_founders_only(name, retry_hint)
        if founders:
            data.founders = founders
        if not data.ceo and ceo:
            data.ceo = ceo

    logger.info(
        "company_enriched",
        company=name,
        stage=data.stage,
        total_funding_usd=data.total_funding_usd,
        founders=data.founders,
    )
    return name, data.model_dump()


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

    valid_names = [name for name in company_names if name]
    tasks = [_enrich_one(name, hints.get(name, "")) for name in valid_names]
    pairs = await asyncio.gather(*tasks, return_exceptions=True)

    for item in pairs:
        if isinstance(item, Exception):
            logger.warning("company_enrich_failed", error=str(item))
            continue
        name, data = item
        results[name] = data

    return results
