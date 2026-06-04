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
    DELETE_STALE_INFERRED_SKILLS,
    MERGE_INFERRED_HAS_SKILL,
    SET_PERSON_SENIORITY,
    SET_PERSON_GITHUB_STATS,
    MERGE_PINNED_PROJECT,
    SET_PROJECT_ENRICHMENT,
    MERGE_PROJECT_TOPIC_SKILL,
    SET_COMPANY_ENRICHMENT,
    SET_INSTITUTION_TIER,
    UPDATE_RESUME_EDGE_WITH_LINKEDIN,
    CREATE_LINKEDIN_WORKED_AT,
    SET_PERSON_LINKEDIN_STATS,
    MERGE_LINKEDIN_STUDIED_AT,
    UPDATE_WORKED_AT_JOB_SKILLS,
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
                name = name.strip() if name else ""
                if name and name not in seen:
                    seen.add(name)
                    result.append((name, category))

    # Experience tech_stack — skills used on the job, often not in the main block
    for exp in extracted.get("experience", []):
        for name in exp.get("tech_stack", []):
            name = name.strip() if name else ""
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
    # Convert years to int — EducationEntry stores them as strings ("2019"), LinkedIn as int.
    for edu in data.get("education", []):
        def _year_int(v) -> int | None:
            try:
                return int(v) if v is not None else None
            except (ValueError, TypeError):
                return None

        r = await tx.run(
            MERGE_INSTITUTION_AND_STUDIED_AT,
            person_id=user_id,
            institution=edu.get("institution", ""),
            degree=edu.get("degree", ""),
            field=edu.get("field", ""),
            start_year=_year_int(edu.get("start_year")),
            end_year=_year_int(edu.get("end_year")),
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


# ── Final layer: inferred skills + enrichment ─────────────────────────────────

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


async def _write_inferred_tx(tx, user_id: str, inferred_json: dict) -> None:
    r = await tx.run(DELETE_STALE_INFERRED_SKILLS, person_id=user_id)
    await r.consume()
    for skill in inferred_json.get("skills", []):
        r = await tx.run(
            MERGE_INFERRED_HAS_SKILL,
            person_id=user_id,
            name=skill["name"],
            category=skill["category"],
            confidence=skill["confidence"],
            inferred_by=skill.get("inferred_by", ""),
            reason=skill.get("reason", ""),
        )
        await r.consume()
    seniority = inferred_json.get("seniority")
    total_months = inferred_json.get("total_experience_months", 0)
    if seniority:
        r = await tx.run(
            SET_PERSON_SENIORITY,
            person_id=user_id,
            seniority=seniority,
            total_months=total_months,
        )
        await r.consume()


async def _write_enrichment(driver, user_id: str, enriched_json: dict, explicit_skills: set[str]) -> None:
    async with driver.session(database="memgraph") as session:
        github = enriched_json.get("github", {})
        profile = github.get("profile", {})
        if profile.get("followers") is not None or profile.get("public_repos") is not None:
            r = await session.run(
                SET_PERSON_GITHUB_STATS,
                person_id=user_id,
                followers=profile.get("followers", 0),
                public_repos=profile.get("public_repos", 0),
            )
            await r.consume()

        for repo in github.get("pinned_repos", []):
            project_id = repo["matched_project_id"]
            description = repo.get("readme_summary") or repo.get("description") or ""
            if repo.get("is_new", False):
                r = await session.run(
                    MERGE_PINNED_PROJECT,
                    project_id=project_id,
                    person_id=user_id,
                    name=repo["name"],
                    description=description,
                    github_url=repo["github_url"],
                    stars=repo.get("stars", 0),
                    forks=repo.get("forks", 0),
                    primary_language=repo.get("primary_language", ""),
                )
                await r.consume()
            else:
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

            if repo.get("primary_language"):
                r = await session.run(
                    MERGE_PROJECT_TOPIC_SKILL,
                    project_id=project_id,
                    name=repo["primary_language"],
                    category="language",
                )
                await r.consume()

            for topic in repo.get("topics", []):
                skill_name = topic.replace("-", " ").title()
                r = await session.run(
                    MERGE_PROJECT_TOPIC_SKILL,
                    project_id=project_id,
                    name=skill_name,
                    category=_guess_category(skill_name),
                )
                await r.consume()

            for skill_name in repo.get("extracted_skills", []):
                if skill_name:
                    r = await session.run(
                        MERGE_PROJECT_TOPIC_SKILL,
                        project_id=project_id,
                        name=skill_name.strip(),
                        category=_guess_category(skill_name),
                    )
                    await r.consume()

        for company_name, data in enriched_json.get("companies", {}).items():
            if any(v is not None and v != [] for v in data.values()):
                r = await session.run(
                    SET_COMPANY_ENRICHMENT,
                    name=company_name,
                    stage=data.get("stage"),
                    industry=data.get("industry"),
                    headcount=data.get("headcount"),
                    founded=data.get("founded"),
                    headquarters=data.get("headquarters"),
                    website=data.get("website"),
                    linkedin_url=data.get("linkedin_url"),
                    description=data.get("description"),
                    business_model=data.get("business_model"),
                    total_funding_usd=data.get("total_funding_usd"),
                    last_round_type=data.get("last_round_type"),
                    last_round_amount_usd=data.get("last_round_amount_usd"),
                    last_round_date=data.get("last_round_date"),
                    key_investors=data.get("key_investors") or [],
                    founders=data.get("founders") or [],
                    ceo=data.get("ceo"),
                )
                await r.consume()

        # ── LinkedIn ──────────────────────────────────────────────────────────
        # enriched_json["linkedin"] is the flat model_dump() of LinkedInProfileData
        linkedin = enriched_json.get("linkedin", {})

        # Profile stats on Person node
        if any(linkedin.get(k) is not None for k in ("headline", "connections", "followers", "linkedin_id")):
            r = await session.run(
                SET_PERSON_LINKEDIN_STATS,
                person_id=user_id,
                linkedin_id=linkedin.get("linkedin_id"),
                headline=linkedin.get("headline"),
                connections=linkedin.get("connections"),
                followers=linkedin.get("followers"),
                summary=linkedin.get("summary"),
                open_to_work=bool(linkedin.get("open_to_work", False)),
                hiring=bool(linkedin.get("hiring", False)),
                verified=bool(linkedin.get("verified", False)),
                current_company=linkedin.get("current_company"),
            )
            await r.consume()

        # LinkedIn-sourced WORKED_AT edges
        # Strategy: try to update an existing resume edge at the same company
        # (within ±2 months of the LinkedIn start date) rather than creating a
        # duplicate. Only fall back to a new LinkedIn edge when no resume edge exists.
        from firstknock.pipeline.resolution.date_normalizer import normalize_date as _norm_date

        def _month_offset(ym: str | None, delta: int) -> str | None:
            """Shift a YYYY-MM string by delta months, return YYYY-MM."""
            if not ym or len(ym) < 7:
                return ym
            try:
                y, m = int(ym[:4]), int(ym[5:7])
                m += delta
                while m > 12:
                    m -= 12; y += 1
                while m < 1:
                    m += 12; y -= 1
                return f"{y:04d}-{m:02d}"
            except (ValueError, IndexError):
                return ym

        for exp in linkedin.get("experience", []):
            if not exp.get("company") or not exp.get("title"):
                continue

            company_raw = exp["company"]
            norm_start  = _norm_date(exp.get("start_date"))
            norm_end    = _norm_date(exp.get("end_date"))
            description = exp.get("description", "")
            job_skills  = exp.get("job_skills") or []

            # Step 1: try to merge into existing resume edge (±2 months)
            lower = _month_offset(norm_start, -2) or ""
            upper = _month_offset(norm_start,  2) or "9999-99"
            result = await session.run(
                UPDATE_RESUME_EDGE_WITH_LINKEDIN,
                person_id=user_id,
                company=company_raw,
                title=exp["title"],
                li_start_date=norm_start,
                start_lower=lower,
                start_upper=upper,
                description=description,
            )
            record = await result.single()
            updated = record["updated"] if record else 0

            # Stamp per-job skills onto the matched edge
            if updated and job_skills:
                r = await session.run(
                    UPDATE_WORKED_AT_JOB_SKILLS,
                    person_id=user_id,
                    company=company_raw,
                    start_lower=lower,
                    start_upper=upper,
                    job_skills=job_skills,
                )
                await r.consume()

            # Step 2: no resume edge found — create a dedicated LinkedIn edge
            if not updated:
                r = await session.run(
                    CREATE_LINKEDIN_WORKED_AT,
                    person_id=user_id,
                    company=company_raw,
                    title=exp["title"],
                    start_date=norm_start,
                    end_date=norm_end,
                    is_current=exp.get("is_current", False),
                    description=description,
                )
                await r.consume()

        # LinkedIn education → STUDIED_AT (only when no resume edge exists at that school)
        for edu in linkedin.get("education", []):
            school = edu.get("school_name") or ""
            if not school:
                continue
            r = await session.run(
                MERGE_LINKEDIN_STUDIED_AT,
                person_id=user_id,
                institution=school,
                degree=edu.get("degree") or "",
                field=edu.get("field_of_study") or "",
                start_year=edu.get("start_year"),
                end_year=edu.get("end_year"),
            )
            await r.consume()

        # Languages → HAS_SKILL with category='language'
        for lang in linkedin.get("languages", []):
            name = lang.get("name") or ""
            if not name:
                continue
            r = await session.run(
                MERGE_SKILL_AND_HAS_SKILL,
                person_id=user_id,
                name=name,
                category="language",
            )
            await r.consume()

        for inst_name, data in enriched_json.get("institutions", {}).items():
            r = await session.run(
                SET_INSTITUTION_TIER,
                name=inst_name,
                ranking_tier=data.get("ranking_tier", "other"),
            )
            await r.consume()


async def write_graph_final_layer(
    user_id: str,
    inferred_json: dict | None,
    enriched_json: dict | None,
    explicit_skills: set[str] | None = None,
) -> None:
    """Write inferred skills + enrichment to Memgraph in one pass. Called by finalize_enrichment or the fallback path."""
    driver = await get_driver()

    if inferred_json:
        async with driver.session(database="memgraph") as session:
            await session.execute_write(_write_inferred_tx, user_id, inferred_json)
        logger.info(
            "graph_final_layer_inferred",
            person_id=user_id,
            skills=len(inferred_json.get("skills", [])),
            seniority=inferred_json.get("seniority"),
        )

    if enriched_json:
        await _write_enrichment(driver, user_id, enriched_json, explicit_skills or set())
        logger.info("graph_final_layer_enriched", person_id=user_id)
