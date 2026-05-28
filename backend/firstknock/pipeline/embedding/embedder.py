import structlog
from openai import AsyncOpenAI
from firstknock.config import settings

logger = structlog.get_logger()


def build_person_text(extracted_json: dict) -> str:
    """
    Builds a rich text representation of a person for embedding.
    Captures headline + skills + experience + projects in one string.
    """
    identity = extracted_json.get("identity", {})
    headline = identity.get("headline", "")

    skills = extracted_json.get("skills", {})
    all_skills: list[str] = []
    for cat in ("languages", "frameworks", "ai_ml", "databases", "devops", "other"):
        all_skills.extend(skills.get(cat, []))

    experience = extracted_json.get("experience", [])
    exp_parts = [
        f"{e['title']} at {e['company']}"
        for e in experience[:4]
        if e.get("title") and e.get("company")
    ]

    project_names = [
        p["name"] for p in extracted_json.get("projects", [])[:5] if p.get("name")
    ]

    parts: list[str] = []
    if headline:
        parts.append(headline)
    if all_skills:
        parts.append(f"Skills: {', '.join(all_skills[:15])}")
    if exp_parts:
        parts.append(f"Experience: {'; '.join(exp_parts)}")
    if project_names:
        parts.append(f"Projects: {', '.join(project_names)}")

    return ". ".join(parts)


def build_project_text(project: dict) -> str:
    """
    Prefers readme_summary (enriched by GitHub worker), falls back to description.
    Returns empty string if neither is set.
    """
    text = project.get("readme_summary", "") or project.get("description", "")
    name = project.get("name", "")
    if not text and not name:
        return ""
    if not text:
        return name
    return f"{name}: {text}"


async def embed_text(text: str) -> list[float]:
    """Single text → 1536-float vector via OpenAI."""
    if not text.strip():
        return []
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.embeddings.create(
        model=settings.embedding_model,
        input=text,
    )
    return resp.data[0].embedding


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Batch embed — one API call for multiple texts.
    Empty strings are skipped and return [] in output.
    """
    if not texts:
        return []

    non_empty = [(i, t) for i, t in enumerate(texts) if t.strip()]
    if not non_empty:
        return [[] for _ in texts]

    indices, non_empty_texts = zip(*non_empty)
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.embeddings.create(
        model=settings.embedding_model,
        input=list(non_empty_texts),
    )

    result: list[list[float]] = [[] for _ in texts]
    for (original_idx, _), embedding_obj in zip(non_empty, resp.data):
        result[original_idx] = embedding_obj.embedding
    return result
