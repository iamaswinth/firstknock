import structlog
from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from firstknock.api.schemas import ResumeStatusResponse, ProfileResponse
from firstknock.pipeline.persistence.db import get_session
from firstknock.pipeline.persistence.models import Resume, User
from firstknock.pipeline.graph.client import get_driver
from firstknock.pipeline.graph.queries import GET_PERSON_NODE
import uuid

router = APIRouter(tags=["profile"])
logger = structlog.get_logger()


@router.get("/resume/{resume_id}", response_model=ResumeStatusResponse)
async def get_resume(resume_id: str):
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
async def get_profile(user_id: str):
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
    try:
        driver = await get_driver()
        async with driver.session(database="memgraph") as s:
            r = await s.run(GET_PERSON_NODE, person_id=user_id)
            node_row = await r.single()
        if node_row:
            seniority = node_row["seniority"]
            total_months = node_row["total_months"]
            github_followers = node_row["github_followers"]
            public_repos = node_row["public_repos"]
    except Exception as exc:
        logger.warning("profile_graph_fetch_failed", user_id=user_id, error=str(exc))

    # ── Skills summary ────────────────────────────────────────────────────────
    skills = extracted.get("skills", {})
    explicit_count = sum(len(v) for v in skills.values() if isinstance(v, list))

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
        experience=extracted.get("experience", []),
        projects=extracted.get("projects", []),
        education=extracted.get("education", []),
        skills_summary={
            "explicit_count": explicit_count,
            "inferred_count": 0,  # filled in by /skills endpoint
            "total": explicit_count,
        },
    )
