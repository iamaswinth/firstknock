import json
import structlog
import httpx
from pydantic import BaseModel
from firstknock.config import settings

logger = structlog.get_logger()

PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"


class CompanyData(BaseModel):
    stage: str | None = None        # seed|series-a|series-b|series-c|public|private|unknown
    industry: str | None = None
    headcount: int | None = None
    founded: int | None = None
    headquarters: str | None = None


COMPANY_PROMPT = """Find information about the company "{name}".

Return JSON only — no explanation, no markdown:
{{"stage": "seed|series-a|series-b|series-c|public|private|unknown",
  "industry": "string or null",
  "headcount": "integer or null",
  "founded": "integer year or null",
  "headquarters": "City, Country or null"}}

Rules:
- stage must be one of the exact strings listed above
- If you cannot find reliable data for any field, use null
- Do NOT guess or fabricate data
- headcount should be approximate (e.g. 50, 200, 1000)"""


async def _query_perplexity(company_name: str) -> CompanyData:
    if not settings.perplexity_api_key:
        logger.warning("perplexity_api_key_missing")
        return CompanyData()

    prompt = COMPANY_PROMPT.format(name=company_name)

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
                    "max_tokens": 256,
                    "temperature": 0.1,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()

            # Strip markdown fences if present
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            raw = json.loads(content)
            return CompanyData(
                stage=raw.get("stage") or None,
                industry=raw.get("industry") or None,
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
    Enrich a list of company names using Perplexity AI.
    Returns {company_name: {stage, industry, headcount, founded, headquarters}}
    """
    results: dict[str, dict] = {}
    for name in company_names:
        if not name:
            continue
        data = await _query_perplexity(name)
        results[name] = data.model_dump()
        logger.info("company_enriched", company=name, stage=data.stage, industry=data.industry)

    return results
