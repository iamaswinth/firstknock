import redis.asyncio as aioredis
from firstknock.config import settings


async def store_file(resume_id: str, file_bytes: bytes) -> None:
    async with aioredis.from_url(settings.redis_url) as client:
        key = f"{settings.redis_file_key_prefix}{resume_id}"
        await client.set(key, file_bytes, ex=settings.redis_file_ttl_seconds)


async def fetch_file(resume_id: str) -> bytes:
    async with aioredis.from_url(settings.redis_url) as client:
        key = f"{settings.redis_file_key_prefix}{resume_id}"
        data = await client.get(key)
    if data is None:
        raise RuntimeError(f"File bytes expired or missing for resume {resume_id}")
    return data


async def delete_file(resume_id: str) -> None:
    async with aioredis.from_url(settings.redis_url) as client:
        key = f"{settings.redis_file_key_prefix}{resume_id}"
        await client.delete(key)
