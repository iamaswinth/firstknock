import redis.asyncio as aioredis
from firstknock.config import settings

# Do NOT use a module-level async client singleton: aioredis connections are bound
# to the event loop they first connect on. Celery solo workers create a new event
# loop per task, so a singleton created on task N's loop raises "Event loop is closed"
# on task N+1. Creating a fresh client per call is the correct pattern here.


def _make_client() -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, decode_responses=False)


async def store_file(resume_id: str, file_bytes: bytes) -> None:
    key = f"{settings.redis_file_key_prefix}{resume_id}"
    client = _make_client()
    try:
        await client.set(key, file_bytes, ex=settings.redis_file_ttl_seconds)
    finally:
        await client.aclose()


async def fetch_file(resume_id: str) -> bytes:
    key = f"{settings.redis_file_key_prefix}{resume_id}"
    client = _make_client()
    try:
        data = await client.get(key)
    finally:
        await client.aclose()
    if data is None:
        raise RuntimeError(f"File bytes expired or missing for resume {resume_id}")
    return data


async def delete_file(resume_id: str) -> None:
    key = f"{settings.redis_file_key_prefix}{resume_id}"
    client = _make_client()
    try:
        await client.delete(key)
    finally:
        await client.aclose()
