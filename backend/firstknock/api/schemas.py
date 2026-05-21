from pydantic import BaseModel


class IngestResponse(BaseModel):
    resume_id: str
    user_id: str
    status: str
    stages_complete: list[str]
    stages_pending: list[str]
