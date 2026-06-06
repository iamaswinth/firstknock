import uuid
from datetime import datetime, timezone


def _now() -> datetime:
    # Column is TIMESTAMP WITHOUT TIME ZONE — strip tz before assigning
    return datetime.now(timezone.utc).replace(tzinfo=None)
from sqlalchemy import select, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .db import get_session
from .models import User, Resume


async def get_or_create_user(email: str) -> uuid.UUID:
    async with get_session() as session:
        stmt = pg_insert(User).values(
            user_id=uuid.uuid4(),
            email=email,
        ).on_conflict_do_update(
            index_elements=["email"],
            set_={"email": email},
        ).returning(User.user_id)
        result = await session.execute(stmt)
        return result.scalar_one()


async def create_resume_stub(user_email: str, source_type: str) -> tuple[uuid.UUID, uuid.UUID]:
    """Create User (upsert) + Resume with status='queued'. Returns (user_id, resume_id)."""
    user_id = await get_or_create_user(user_email)
    async with get_session() as session:
        resume = Resume(
            resume_id=uuid.uuid4(),
            user_id=user_id,
            source_type=source_type,
            status="queued",
        )
        session.add(resume)
        await session.flush()
        return user_id, resume.resume_id


async def save_extracted_resume(
    user_email: str,
    source_type: str,
    raw_text: str,
    extracted_json: dict,
    resume_id: uuid.UUID | None = None,
) -> tuple[uuid.UUID, uuid.UUID]:
    user_id = await get_or_create_user(user_email)
    async with get_session() as session:
        if resume_id is not None:
            result = await session.execute(select(Resume).where(Resume.resume_id == resume_id))
            resume = result.scalar_one()
            resume.raw_text = raw_text
            resume.extracted_json = extracted_json
            resume.status = "extracted"
            resume.updated_at = _now()
            return resume.user_id, resume.resume_id
        resume = Resume(
            resume_id=uuid.uuid4(),
            user_id=user_id,
            source_type=source_type,
            raw_text=raw_text,
            extracted_json=extracted_json,
            status="extracted",
        )
        session.add(resume)
        await session.flush()
        return user_id, resume.resume_id


async def update_resume_status(
    resume_id: uuid.UUID,
    status: str,
    error_message: str | None = None,
) -> None:
    async with get_session() as session:
        result = await session.execute(select(Resume).where(Resume.resume_id == resume_id))
        resume = result.scalar_one()
        resume.status = status
        resume.updated_at = _now()
        if error_message is not None:
            resume.error_message = error_message


async def save_inferred_data(resume_id: uuid.UUID, inferred_json: dict) -> None:
    async with get_session() as session:
        result = await session.execute(select(Resume).where(Resume.resume_id == resume_id))
        resume = result.scalar_one()
        resume.inferred_json = inferred_json
        resume.updated_at = _now()


async def get_resume_by_id(resume_id: uuid.UUID) -> Resume:
    async with get_session() as session:
        result = await session.execute(select(Resume).where(Resume.resume_id == resume_id))
        return result.scalar_one()


async def save_compiled_profile(resume_id: uuid.UUID, compiled_json: dict) -> None:
    async with get_session() as session:
        result = await session.execute(select(Resume).where(Resume.resume_id == resume_id))
        resume = result.scalar_one()
        resume.compiled_json = compiled_json
        resume.updated_at = _now()


async def save_enrichment_data(resume_id: uuid.UUID, enriched_json: dict) -> None:
    async with get_session() as session:
        result = await session.execute(select(Resume).where(Resume.resume_id == resume_id))
        resume = result.scalar_one()
        resume.enriched_json = enriched_json
        resume.status = "enriched"
        resume.updated_at = _now()


async def mark_graph_built(resume_id: uuid.UUID) -> None:
    async with get_session() as session:
        result = await session.execute(select(Resume).where(Resume.resume_id == resume_id))
        resume = result.scalar_one()
        resume.graph_built = True
        resume.updated_at = _now()


async def save_person_embedding(user_id: str, embedding: list[float]) -> None:
    async with get_session() as session:
        result = await session.execute(select(User).where(User.user_id == uuid.UUID(user_id)))
        user = result.scalar_one()
        user.embedding = embedding


async def get_latest_resume_for_user(email: str) -> Resume:
    async with get_session() as session:
        stmt = (
            select(Resume)
            .join(User, Resume.user_id == User.user_id)
            .where(User.email == email)
            .order_by(Resume.ingested_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one()
