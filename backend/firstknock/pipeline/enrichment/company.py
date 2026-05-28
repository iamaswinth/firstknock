import json
import structlog
import httpx
from pydantic import BaseModel
from firstknock.config import settings

logger = structlog.get_logger()

PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"


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


COMPANY_PROMPT = """Find company intelligence data for "{name}".

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


async def _query_perplexity(company_name: str) -> CompanyData:
    if not settings.perplexity_api_key:
        logger.warning("perplexity_api_key_missing")
        return CompanyData()

    prompt = COMPANY_PROMPT.format(name=company_name)

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
            return CompanyData(
                website=raw.get("website") or None,
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


async def enrich_companies(company_names: list[str]) -> dict[str, dict]:
    """
    Enrich a list of company names with company intelligence via Perplexity AI.
    Returns {company_name: CompanyData dict}
    """
    results: dict[str, dict] = {}
    for name in company_names:
        if not name:
            continue
        data = await _query_perplexity(name)
        results[name] = data.model_dump()
        logger.info(
            "company_enriched",
            company=name,
            stage=data.stage,
            total_funding_usd=data.total_funding_usd,
            founders=data.founders,
        )

    return results
