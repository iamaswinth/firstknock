import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from firstknock.api.auth import verify_clerk_token
from firstknock.api.schemas import DeleteResumeResponse, IngestQueuedResponse
from firstknock.pipeline.graph.client import get_driver
from firstknock.pipeline.graph.queries import DELETE_PERSON_AND_RELS
from firstknock.pipeline.persistence.db import get_session
from firstknock.pipeline.persistence.models import Resume, User

router = APIRouter()
logger = structlog.get_logger()

_SUPPORTED_TYPES = {"pdf", "docx"}


@router.post("/ingest", status_code=202, response_model=IngestQueuedResponse)
async def ingest_resume(
    file: UploadFile = File(...),
    current_user: dict = Depends(verify_clerk_token),
) -> IngestQueuedResponse:
    email: str = current_user["email"]
    if not email:
        raise HTTPException(status_code=400, detail="Could not resolve email from Clerk token")

    suffix = file.filename.rsplit(".", 1)[-1].lower() if file.filename else "pdf"
    if suffix not in _SUPPORTED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: .{suffix}")

    file_bytes = await file.read()

    from firstknock.pipeline.persistence.postgres_writer import create_resume_stub
    from firstknock.pipeline.ingestion.file_store import store_file
    from firstknock.pipeline.ingestion.task import process_ingestion

    user_id, resume_id = await create_resume_stub(email, suffix)
    await store_file(str(resume_id), file_bytes)
    process_ingestion.apply_async(args=[str(resume_id), email, suffix], queue="ingestion")

    logger.info("ingest_queued", resume_id=str(resume_id), email=email)
    return IngestQueuedResponse(
        resume_id=str(resume_id),
        user_id=str(user_id),
        status="queued",
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


@router.post("/resume/{resume_id}/reingest", status_code=202, response_model=IngestQueuedResponse)
async def reingest_resume(
    resume_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(verify_clerk_token),
) -> IngestQueuedResponse:
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

    from firstknock.pipeline.persistence.postgres_writer import create_resume_stub
    from firstknock.pipeline.ingestion.file_store import store_file
    from firstknock.pipeline.ingestion.task import process_ingestion

    user_id, new_resume_id = await create_resume_stub(email, suffix)
    await store_file(str(new_resume_id), file_bytes)
    process_ingestion.apply_async(args=[str(new_resume_id), email, suffix], queue="ingestion")

    logger.info("reingest_queued", resume_id=str(new_resume_id), email=email)
    return IngestQueuedResponse(
        resume_id=str(new_resume_id),
        user_id=str(user_id),
        status="queued",
    )
