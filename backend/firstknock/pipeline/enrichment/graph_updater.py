import structlog
from firstknock.pipeline.graph.client import get_driver
from firstknock.pipeline.graph.queries import (
    SET_PROJECT_ENRICHMENT,
    MERGE_PINNED_PROJECT,
    MERGE_PROJECT_TOPIC_SKILL,
    SET_COMPANY_ENRICHMENT,
    SET_INSTITUTION_TIER,
    SET_PERSON_GITHUB_STATS,
)

logger = structlog.get_logger()

_SKILL_CATEGORY_HINTS = {
    "language": {"python", "typescript", "javascript", "go", "rust", "java", "c++", "c#", "ruby", "swift", "kotlin"},
    "framework": {"react", "nextjs", "fastapi", "django", "express", "vue", "angular", "flask", "spring"},
    "tool": {"docker", "kubernetes", "redis", "postgresql", "mongodb", "aws", "gcp", "azure"},
}


def _guess_category(skill_name: str) -> str:
    lower = skill_name.lower()
    for category, keywords in _SKILL_CATEGORY_HINTS.items():
        if any(kw in lower for kw in keywords):
            return category
    return "concept"


async def update_graph(person_id: str, enriched: dict) -> None:
    """
    Write all enriched data back to Memgraph.
    enriched = merged output of all 4 enrichers.
    """
    driver = await get_driver()
    async with driver.session(database="memgraph") as session:

        # ── GitHub: person profile ────────────────────────────────────────────
        github = enriched.get("github", {})
        profile = github.get("profile", {})
        if profile.get("followers") is not None or profile.get("public_repos") is not None:
            await session.run(
                SET_PERSON_GITHUB_STATS,
                person_id=person_id,
                followers=profile.get("followers", 0),
                public_repos=profile.get("public_repos", 0),
            )

        # ── GitHub: pinned repos ──────────────────────────────────────────────
        for repo in github.get("pinned_repos", []):
            project_id = repo["matched_project_id"]
            is_new = repo.get("is_new", False)

            description = repo.get("readme_summary") or repo.get("description") or ""

            if is_new:
                # Create new project node discovered from GitHub pins
                r = await session.run(
                    MERGE_PINNED_PROJECT,
                    project_id=project_id,
                    person_id=person_id,
                    name=repo["name"],
                    description=description,
                    github_url=repo["github_url"],
                    stars=repo.get("stars", 0),
                    forks=repo.get("forks", 0),
                    primary_language=repo.get("primary_language", ""),
                )
                await r.consume()
            else:
                # Enrich existing project node
                r = await session.run(
                    SET_PROJECT_ENRICHMENT,
                    project_id=project_id,
                    stars=repo.get("stars", 0),
                    forks=repo.get("forks", 0),
                    primary_language=repo.get("primary_language", ""),
                    last_pushed=repo.get("last_pushed", ""),
                    description=description,
                )
                await r.consume()

            # Write primary language as a Skill
            if repo.get("primary_language"):
                r = await session.run(
                    MERGE_PROJECT_TOPIC_SKILL,
                    project_id=project_id,
                    name=repo["primary_language"],
                    category="language",
                )
                await r.consume()

            # Write topics as Skills
            for topic in repo.get("topics", []):
                skill_name = topic.replace("-", " ").title()
                r = await session.run(
                    MERGE_PROJECT_TOPIC_SKILL,
                    project_id=project_id,
                    name=skill_name,
                    category=_guess_category(skill_name),
                )
                await r.consume()

            # Write README-extracted skills as Skills on this project
            for skill_name in repo.get("extracted_skills", []):
                if skill_name:
                    r = await session.run(
                        MERGE_PROJECT_TOPIC_SKILL,
                        project_id=project_id,
                        name=skill_name.strip(),
                        category=_guess_category(skill_name),
                    )
                    await r.consume()

        # ── Company enrichment ────────────────────────────────────────────────
        for company_name, data in enriched.get("companies", {}).items():
            if any(v is not None for v in data.values()):
                r = await session.run(
                    SET_COMPANY_ENRICHMENT,
                    name=company_name,
                    stage=data.get("stage"),
                    industry=data.get("industry"),
                    headcount=data.get("headcount"),
                    founded=data.get("founded"),
                    headquarters=data.get("headquarters"),
                )
                await r.consume()

        # ── Institution enrichment ────────────────────────────────────────────
        for inst_name, data in enriched.get("institutions", {}).items():
            r = await session.run(
                SET_INSTITUTION_TIER,
                name=inst_name,
                ranking_tier=data.get("ranking_tier", "other"),
            )
            await r.consume()

    logger.info("graph_update_complete", person_id=person_id)
