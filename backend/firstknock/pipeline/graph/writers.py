import uuid
import structlog
from itertools import combinations

from .client import get_driver
from .queries import (
    MERGE_PERSON,
    DELETE_STALE_EXPLICIT_SKILLS,
    MERGE_SKILL_AND_HAS_SKILL,
    MERGE_COMPANY_AND_WORKED_AT,
    MERGE_COMPANY_USED_SKILL,
    MERGE_PROJECT_AND_BUILT,
    MERGE_PROJECT_USES_SKILL,
    MERGE_INSTITUTION_AND_STUDIED_AT,
    MERGE_CO_OCCURS_BATCH,
    COUNT_PERSON_RELS,
)

logger = structlog.get_logger()

_CATEGORY_MAP = {
    "languages": "language",
    "frameworks": "framework",
    "ai_ml": "tool",
    "databases": "tool",
    "devops": "tool",
    "other": "concept",
}


def _collect_skills(extracted: dict) -> list[tuple[str, str]]:
    seen: set[str] = set()
    result: list[tuple[str, str]] = []

    # Main skills block — has category info, takes priority
    for cat_key, names in extracted.get("skills", {}).items():
        if isinstance(names, list):
            category = _CATEGORY_MAP.get(cat_key, "concept")
            for name in names:
                if name and name not in seen:
                    seen.add(name)
                    result.append((name, category))

    # Experience tech_stack — skills used on the job, often not in the main block
    for exp in extracted.get("experience", []):
        for name in exp.get("tech_stack", []):
            if name and name not in seen:
                seen.add(name)
                result.append((name, "tool"))

    return result


async def _write_tx(tx, user_id: str, data: dict) -> None:
    identity = data.get("identity", {})

    # 1. Person — write all identity fields
    r = await tx.run(
        MERGE_PERSON,
        person_id=user_id,
        name=identity.get("name", ""),
        email=identity.get("email"),
        headline=identity.get("headline"),
        github_url=identity.get("github_url"),
        linkedin_url=identity.get("linkedin_url"),
        location=identity.get("location"),
    )
    await r.consume()

    # Delete stale explicit skills before re-writing — prevents ghost skills
    # from accumulating across re-ingestions of the same person
    r = await tx.run(DELETE_STALE_EXPLICIT_SKILLS, person_id=user_id)
    await r.consume()

    # 2. Skills → HAS_SKILL
    all_skills = _collect_skills(data)
    for name, category in all_skills:
        r = await tx.run(
            MERGE_SKILL_AND_HAS_SKILL,
            person_id=user_id,
            name=name,
            category=category,
        )
        await r.consume()

    # 3. Experience → Company + WORKED_AT + Company→Skill edges
    for exp in data.get("experience", []):
        r = await tx.run(
            MERGE_COMPANY_AND_WORKED_AT,
            person_id=user_id,
            company=exp.get("company", ""),
            title=exp.get("title", ""),
            start_date=exp.get("start_date"),
            end_date=exp.get("end_date"),
            months=exp.get("months"),
            is_current=exp.get("is_current", False),
            location=exp.get("location"),
            description=exp.get("description", []),
            skills_used=exp.get("tech_stack", []),
        )
        await r.consume()
        for skill_name in exp.get("tech_stack", []):
            if skill_name:
                r = await tx.run(
                    MERGE_COMPANY_USED_SKILL,
                    company=exp.get("company", ""),
                    skill_name=skill_name,
                    category="tool",
                )
                await r.consume()

    # 4. Projects → BUILT + USES
    for proj in data.get("projects", []):
        project_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{user_id}:{proj['name']}"))
        r = await tx.run(
            MERGE_PROJECT_AND_BUILT,
            project_id=project_id,
            person_id=user_id,
            name=proj["name"],
            description=proj.get("description", ""),
            url=proj.get("url"),
            github_url=proj.get("github_url"),
        )
        await r.consume()
        for skill_name in proj.get("tech_stack", []):
            if skill_name:
                r = await tx.run(
                    MERGE_PROJECT_USES_SKILL,
                    project_id=project_id,
                    name=skill_name,
                    category="tool",
                )
                await r.consume()

    # 5. Education → Institution + STUDIED_AT
    for edu in data.get("education", []):
        r = await tx.run(
            MERGE_INSTITUTION_AND_STUDIED_AT,
            person_id=user_id,
            institution=edu.get("institution", ""),
            degree=edu.get("degree", ""),
            field=edu.get("field", ""),
            start_year=edu.get("start_year"),
            end_year=edu.get("end_year"),
        )
        await r.consume()

    # 6. CO_OCCURS_WITH — sorted pairs to avoid A→B and B→A duplicates
    skill_names = sorted({name for name, _ in all_skills})
    pairs = [[s1, s2] for s1, s2 in combinations(skill_names, 2)]
    if pairs:
        r = await tx.run(MERGE_CO_OCCURS_BATCH, pairs=pairs)
        await r.consume()


async def write_resume_graph(user_id: str, extracted_json: dict) -> None:
    driver = await get_driver()

    async with driver.session(database="memgraph") as session:
        await session.execute_write(_write_tx, user_id, extracted_json)

    # 7. Health check — runs outside transaction as a read
    async with driver.session(database="memgraph") as session:
        result = await session.run(COUNT_PERSON_RELS, person_id=user_id)
        record = await result.single()
        if record and record["rel_count"] == 0:
            logger.warning("person_node_isolated", person_id=user_id)
        else:
            rel_count = record["rel_count"] if record else 0
            logger.info("graph_write_complete", person_id=user_id, relationships=rel_count)
