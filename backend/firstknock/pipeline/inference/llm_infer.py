import json
import structlog
import anthropic
from firstknock.config import settings

logger = structlog.get_logger()

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


async def infer_skills_from_llm(
    explicit_skills: list[str],
    skip: set[str] | None = None,
) -> list[dict]:
    """
    Sends explicit skill names to Claude Haiku and returns inferred implied skills.
    Returns list of {name, category, confidence, reason, inferred_from} dicts.
    Works for any technology stack — no hardcoded rules.

    skip: skill names already covered by graph_implies (excluded from prompt + results).
    """
    if not explicit_skills:
        return []

    skip = skip or set()
    client = _get_client()

    skill_list = "\n".join(f"- {s}" for s in sorted(explicit_skills))
    skip_note = (
        f"\nSkip these — already inferred via graph: {', '.join(sorted(skip))}\n"
        if skip else ""
    )
    prompt = f"""You are a technical skill inference engine for resume analysis.

Given these EXPLICIT skills from a software engineer's resume:
{skill_list}
{skip_note}
Return a JSON array of skills they almost certainly also know based on strong technical implications.

Rules:
- Only include skills with technically strong implications (e.g. asyncpg implies PostgreSQL because asyncpg IS the PostgreSQL async driver)
- Do NOT include any skill already listed above
- Do NOT include soft skills, vague concepts, or anything not technically specific
- Each object must have exactly these keys: name, category, confidence, reason, inferred_from
- category must be one of: language, framework, tool, concept
- confidence must be a float between 0.5 and 0.9 (never 1.0 — that is reserved for explicit skills)
  - 0.85-0.9: near-certain (asyncpg → PostgreSQL)
  - 0.70-0.84: very likely (Next.js → React)
  - 0.50-0.69: likely (Docker → Linux administration)
- reason must be at most 10 words — ultra short technical justification
- inferred_from: the single skill from the list above that most directly implies this skill
- Capitalize skill names exactly as they appear on professional resumes
  (e.g. 'Prompt Engineering' not 'prompt engineering', 'REST APIs' not 'rest apis')
  Keep intentionally lowercase tools as-is (npm, pip, curl, git)
- Every skill MUST have a non-empty inferred_from — if you cannot identify the source skill, skip it
- Return at most 20 inferred skills, prioritising the highest confidence ones

Return ONLY a valid JSON array. No markdown, no explanation, no code fences."""

    response = await client.messages.create(
        model=settings.inference_model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if model wrapped the JSON
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0].strip()

    try:
        inferred = json.loads(raw)
        # Filter out explicit and already-graph-implied skills; validate structure
        explicit_set = {s.lower() for s in explicit_skills}
        skip_lower = {s.lower() for s in skip}
        valid = []
        for item in inferred:
            if not isinstance(item, dict):
                continue
            name = item.get("name", "").strip()
            inferred_from = item.get("inferred_from", "").strip()
            if not name or not inferred_from:
                continue
            if name.lower() in explicit_set or name.lower() in skip_lower:
                continue
            confidence = float(item.get("confidence", 0.5))
            if confidence >= 1.0:
                confidence = 0.9
            valid.append({
                "name": name,
                "category": item.get("category", "concept"),
                "confidence": round(confidence, 2),
                "reason": item.get("reason", ""),
                "inferred_from": inferred_from,
            })
        logger.info("llm_inference_complete", explicit_count=len(explicit_skills), inferred_count=len(valid))
        return valid
    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning("llm_inference_parse_failed", error=str(exc), raw=raw[:200])
        return []
