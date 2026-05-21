from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from firstknock.api.schemas import IngestResponse
from firstknock.pipeline.orchestrator import run_sync_ingestion

router = APIRouter()

_SUPPORTED_TYPES = {"pdf", "docx"}


@router.post("/ingest", response_model=IngestResponse)
async def ingest_resume(
    file: UploadFile = File(...),
    email: str = Form(...),
) -> IngestResponse:
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
