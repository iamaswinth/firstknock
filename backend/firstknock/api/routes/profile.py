import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from firstknock.api.auth import verify_clerk_token
from firstknock.api.schemas import ResumeStatusResponse, ProfileResponse, ProfileCompletenessResponse, RoleFitResponse, RoleMatch
from firstknock.pipeline.completeness import calculate_completeness
from firstknock.pipeline.persistence.db import get_session
from firstknock.pipeline.persistence.models import Resume, User
from firstknock.pipeline.graph.client import get_driver
from firstknock.pipeline.graph.queries import GET_PERSON_NODE, GET_PERSON_PROJECTS_ENRICHED
import uuid

router = APIRouter(tags=["profile"])
logger = structlog.get_logger()


@router.get("/resume/{resume_id}", response_model=ResumeStatusResponse)
async def get_resume(resume_id: str, _: dict = Depends(verify_clerk_token)):
    try:
        rid = uuid.UUID(resume_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid resume_id format")

    async with get_session() as session:
        result = await session.execute(
            select(Resume, User)
            .join(User, Resume.user_id == User.user_id)
            .where(Resume.resume_id == rid)
        )
        row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Resume not found")

    resume, user = row
    extracted = resume.extracted_json or {}
    identity = extracted.get("identity", {})

    return ResumeStatusResponse(
        resume_id=str(resume.resume_id),
        user_id=str(resume.user_id),
        status=resume.status,
        graph_built=resume.graph_built,
        ingested_at=resume.ingested_at.isoformat(),
        updated_at=resume.updated_at.isoformat(),
        identity=identity,
        experience=extracted.get("experience", []),
        projects=extracted.get("projects", []),
        skills=extracted.get("skills", {}),
        education=extracted.get("education", []),
        certifications=extracted.get("certifications", []),
        enriched=resume.enriched_json,
    )


@router.get("/profile/{user_id}", response_model=ProfileResponse)
async def get_profile(user_id: str, _: dict = Depends(verify_clerk_token)):
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    # ── Postgres: latest resume ───────────────────────────────────────────────
    async with get_session() as session:
        result = await session.execute(
            select(Resume, User)
            .join(User, Resume.user_id == User.user_id)
            .where(Resume.user_id == uid)
            .order_by(Resume.ingested_at.desc())
            .limit(1)
        )
        row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    resume, user = row
    extracted = resume.extracted_json or {}
    identity = extracted.get("identity", {})

    # ── Memgraph: graph properties ────────────────────────────────────────────
    seniority = total_months = github_followers = public_repos = None
    enriched_projects: list[dict] = []
    try:
        driver = await get_driver()
        async with driver.session(database="memgraph") as s:
            r = await s.run(GET_PERSON_NODE, person_id=user_id)
            node_row = await r.single()
            proj_r = await s.run(GET_PERSON_PROJECTS_ENRICHED, person_id=user_id)
            proj_rows = await proj_r.data()
        if node_row:
            seniority = node_row["seniority"]
            total_months = node_row["total_months"]
            github_followers = node_row["github_followers"]
            public_repos = node_row["public_repos"]
        enriched_projects = [dict(row) for row in proj_rows]
    except Exception as exc:
        logger.warning("profile_graph_fetch_failed", user_id=user_id, error=str(exc))

    # ── Merge enriched project data from Memgraph ────────────────────────────
    # Build lookup by name (lower) and github_url so we can match regardless of source
    _enrich_by_name: dict[str, dict] = {}
    _enrich_by_gh: dict[str, dict] = {}
    for ep in enriched_projects:
        if ep.get("name"):
            _enrich_by_name[ep["name"].lower()] = ep
        if ep.get("github_url"):
            _enrich_by_gh[ep["github_url"]] = ep

    _enriched_fields = (
        "stars", "forks", "primary_language", "last_pushed",
        "category", "domain", "use_case", "problem_solved",
        "customer_type", "similar_companies", "transferable_job_relevance",
    )

    base_projects = extracted.get("projects", [])
    merged: list[dict] = []
    seen_names: set[str] = set()
    for p in base_projects:
        ep = _enrich_by_gh.get(p.get("github_url") or "") or _enrich_by_name.get((p.get("name") or "").lower())
        merged_p = dict(p)
        if ep:
            for f in _enriched_fields:
                if ep.get(f) is not None:
                    merged_p[f] = ep[f]
        merged.append(merged_p)
        seen_names.add((p.get("name") or "").lower())

    # Append any Memgraph-only projects (e.g. GitHub pinned repos not on resume)
    for ep in enriched_projects:
        if (ep.get("name") or "").lower() not in seen_names:
            merged.append({
                "name": ep.get("name", ""),
                "description": ep.get("description", ""),
                "tech_stack": [],
                "url": ep.get("url"),
                "github_url": ep.get("github_url"),
                **{f: ep.get(f) for f in _enriched_fields},
            })

    # ── Skills summary ────────────────────────────────────────────────────────
    skills = extracted.get("skills", {})
    explicit_count = sum(len(v) for v in skills.values() if isinstance(v, list))

    enriched = resume.enriched_json or {}
    profile_picture_url = (enriched.get("linkedin") or {}).get("profile_picture_url") or None

    return ProfileResponse(
        user_id=user_id,
        name=identity.get("name", ""),
        email=user.email,
        headline=identity.get("headline"),
        github_url=identity.get("github_url"),
        linkedin_url=identity.get("linkedin_url"),
        location=identity.get("location"),
        seniority=seniority,
        total_experience_months=total_months,
        github_followers=github_followers,
        public_repos=public_repos,
        profile_picture_url=profile_picture_url,
        experience=extracted.get("experience", []),
        projects=merged,
        education=extracted.get("education", []),
        skills_summary={
            "explicit_count": explicit_count,
            "inferred_count": 0,  # filled in by /skills endpoint
            "total": explicit_count,
        },
    )


@router.get("/profile/{user_id}/roles", response_model=RoleFitResponse)
async def get_role_fit(user_id: str, _: dict = Depends(verify_clerk_token)):
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    async with get_session() as session:
        result = await session.execute(
            select(Resume)
            .where(Resume.user_id == uid)
            .order_by(Resume.ingested_at.desc())
            .limit(1)
        )
        resume = result.scalar_one_or_none()

    if not resume:
        raise HTTPException(status_code=404, detail="User not found")

    roles_raw = (resume.extracted_json or {}).get("role_recommendations", [])
    roles = [RoleMatch(**r) for r in roles_raw if isinstance(r, dict)]
    return RoleFitResponse(user_id=user_id, roles=roles)


@router.get("/profile/{user_id}/completeness", response_model=ProfileCompletenessResponse)
async def get_profile_completeness(user_id: str, _: dict = Depends(verify_clerk_token)):
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    async with get_session() as session:
        result = await session.execute(
            select(Resume)
            .where(Resume.user_id == uid)
            .order_by(Resume.ingested_at.desc())
            .limit(1)
        )
        resume = result.scalar_one_or_none()

    if not resume:
        raise HTTPException(status_code=404, detail="User not found")

    data = calculate_completeness(resume.extracted_json or {}, resume.enriched_json)

    return ProfileCompletenessResponse(user_id=user_id, **data)
