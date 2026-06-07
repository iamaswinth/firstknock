import structlog
from firstknock.pipeline.graph.client import get_driver, close_driver
from firstknock.pipeline.graph.queries import (
    SET_PERSON_EMBEDDING,
    SET_PROJECT_EMBEDDING,
    GET_PERSON_PROJECTS,
)
from firstknock.pipeline.persistence.postgres_writer import save_person_embedding
from firstknock.pipeline.persistence.db import dispose_engine
from .embedder import build_person_text, build_project_text, embed_text, embed_batch

logger = structlog.get_logger()


async def embed_and_write(user_id: str, resume_id: str, extracted_json: dict) -> dict:
    """
    Generates and writes embeddings for a person and their projects.
    Person embedding → NeonDB (source of truth) + Memgraph Person node.
    Project embeddings → Memgraph Project nodes only (cheap to regen).
    Returns: {"person": bool, "projects": int}
    """
    result = {"person": False, "projects": 0}

    # ── Person embedding ──────────────────────────────────────────────────────
    person_text = build_person_text(extracted_json)
    if person_text:
        try:
            vector = await embed_text(person_text)
            if vector:
                await save_person_embedding(user_id, vector)

                driver = await get_driver()
                async with driver.session(database="memgraph") as session:
                    r = await session.run(
                        SET_PERSON_EMBEDDING, person_id=user_id, embedding=vector
                    )
                    await r.consume()

                result["person"] = True
                logger.info("person_embedded", person_id=user_id)
        except Exception as exc:
            logger.warning("person_embed_failed", person_id=user_id, error=str(exc))

    # ── Project embeddings ────────────────────────────────────────────────────
    try:
        driver = await get_driver()
        async with driver.session(database="memgraph") as session:
            r = await session.run(GET_PERSON_PROJECTS, person_id=user_id)
            project_rows = await r.values()

        projects = [
            {"project_id": row[0], "name": row[1], "description": row[2]}
            for row in project_rows
        ]

        # Merge readme_summary from extracted_json if available
        proj_map = {
            (p.get("name") or "").lower(): p
            for p in extracted_json.get("projects", [])
        }
        for proj in projects:
            resume_proj = proj_map.get((proj.get("name") or "").lower(), {})
            proj["readme_summary"] = resume_proj.get("readme_summary", "")

        texts = [build_project_text(p) for p in projects]
        vectors = await embed_batch(texts)

        driver = await get_driver()
        async with driver.session(database="memgraph") as session:
            for proj, vector in zip(projects, vectors):
                if vector:
                    r = await session.run(
                        SET_PROJECT_EMBEDDING,
                        project_id=proj["project_id"],
                        embedding=vector,
                    )
                    await r.consume()
                    result["projects"] += 1

        logger.info("projects_embedded", person_id=user_id, count=result["projects"])
    except Exception as exc:
        logger.warning("project_embed_failed", person_id=user_id, error=str(exc))

    await close_driver()
    await dispose_engine()
    return result
