import structlog
from fastapi import APIRouter, HTTPException
from firstknock.api.schemas import SkillsResponse, SkillItem
from firstknock.pipeline.graph.client import get_driver
from firstknock.pipeline.graph.queries import GET_ALL_SKILLS

router = APIRouter(tags=["skills"])
logger = structlog.get_logger()


@router.get("/skills/{user_id}", response_model=SkillsResponse)
async def get_skills(user_id: str):
    try:
        driver = await get_driver()
        async with driver.session(database="memgraph") as session:
            r = await session.run(GET_ALL_SKILLS, person_id=user_id)
            rows = await r.values()
    except Exception as exc:
        logger.warning("skills_fetch_failed", user_id=user_id, error=str(exc))
        raise HTTPException(status_code=503, detail="Graph database unavailable")

    if not rows:
        raise HTTPException(status_code=404, detail="No skills found — user may not exist or graph not built")

    explicit: list[SkillItem] = []
    inferred: list[SkillItem] = []

    for row in rows:
        name, category, source, confidence, inferred_by, reason = row
        item = SkillItem(
            name=name or "",
            category=category or "concept",
            source=source or "explicit",
            confidence=float(confidence) if confidence is not None else 1.0,
            inferred_by=inferred_by,
            reason=reason,
        )
        if source == "explicit":
            explicit.append(item)
        else:
            inferred.append(item)

    return SkillsResponse(
        user_id=user_id,
        explicit=explicit,
        inferred=inferred,
        total=len(explicit) + len(inferred),
    )
