import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from firstknock.api.auth import verify_clerk_token
from firstknock.api.schemas import DeleteResumeResponse, IngestResponse
from firstknock.pipeline.graph.client import get_driver
from firstknock.pipeline.graph.queries import DELETE_PERSON_AND_RELS
from firstknock.pipeline.orchestrator import run_sync_ingestion
from firstknock.pipeline.persistence.db import get_session
from firstknock.pipeline.persistence.models import Resume, User

router = APIRouter()
logger = structlog.get_logger()

_SUPPORTED_TYPES = {"pdf", "docx"}


@router.post("/ingest", response_model=IngestResponse)
async def ingest_resume(
    file: UploadFile = File(...),
    current_user: dict = Depends(verify_clerk_token),
) -> IngestResponse:
    email: str = current_user["email"]
    if not email:
        raise HTTPException(status_code=400, detail="Could not resolve email from Clerk token")

    suffix = file.filename.rsplit(".", 1)[-1].lower() if file.filename else "pdf"
    if suffix not in _SUPPORTED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: .{suffix}")

    file_bytes = await file.read()
    result = await run_sync_ingestion(file_bytes, suffix, email)

    stages_complete = ["parse", "normalize", "extract", "resolve", "persist"]
    stages_pending = ["enrichment", "inference", "embedding"]
    if result.get("graph_written"):
        stages_complete.append("graph")
    else:
        stages_pending.insert(0, "graph")

    return IngestResponse(
        resume_id=str(result["resume_id"]),
        user_id=str(result["user_id"]),
        status=result["status"],
        stages_complete=stages_complete,
        stages_pending=stages_pending,
    )


async def _delete_resume_and_graph(resume: Resume) -> None:
    person_id = str(resume.user_id)
    try:
        driver = await get_driver()
        async with driver.session(database="memgraph") as s:
            await s.run(DELETE_PERSON_AND_RELS, person_id=person_id)
    except Exception as exc:
        logger.warning("graph_delete_failed", person_id=person_id, error=str(exc))

    async with get_session() as session:
        db_resume = await session.get(Resume, resume.resume_id)
        if db_resume:
            await session.delete(db_resume)
            await session.commit()


@router.delete("/resume/{resume_id}", response_model=DeleteResumeResponse)
async def delete_resume(
    resume_id: str,
    current_user: dict = Depends(verify_clerk_token),
) -> DeleteResumeResponse:
    email: str = current_user["email"]

    async with get_session() as session:
        result = await session.execute(
            select(Resume, User)
            .join(User, Resume.user_id == User.user_id)
            .where(Resume.resume_id == resume_id)
        )
        row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Resume not found")

    resume, user = row
    if user.email != email:
        raise HTTPException(status_code=403, detail="Not authorized to delete this resume")

    user_id = str(resume.user_id)
    await _delete_resume_and_graph(resume)

    return DeleteResumeResponse(resume_id=resume_id, user_id=user_id, deleted=True)


@router.post("/resume/{resume_id}/reingest", response_model=IngestResponse)
async def reingest_resume(
    resume_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(verify_clerk_token),
) -> IngestResponse:
    email: str = current_user["email"]
    if not email:
        raise HTTPException(status_code=400, detail="Could not resolve email from Clerk token")

    suffix = file.filename.rsplit(".", 1)[-1].lower() if file.filename else "pdf"
    if suffix not in _SUPPORTED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: .{suffix}")

    async with get_session() as session:
        result = await session.execute(
            select(Resume, User)
            .join(User, Resume.user_id == User.user_id)
            .where(Resume.resume_id == resume_id)
        )
        row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Resume not found")

    resume, user = row
    if user.email != email:
        raise HTTPException(status_code=403, detail="Not authorized to reingest this resume")

    await _delete_resume_and_graph(resume)

    file_bytes = await file.read()
    result = await run_sync_ingestion(file_bytes, suffix, email)

    stages_complete = ["parse", "normalize", "extract", "resolve", "persist"]
    stages_pending = ["enrichment", "inference", "embedding"]
    if result.get("graph_written"):
        stages_complete.append("graph")
    else:
        stages_pending.insert(0, "graph")

    return IngestResponse(
        resume_id=str(result["resume_id"]),
        user_id=str(result["user_id"]),
        status=result["status"],
        stages_complete=stages_complete,
        stages_pending=stages_pending,
    )
