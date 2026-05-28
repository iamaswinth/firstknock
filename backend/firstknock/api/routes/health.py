import time
import structlog
from fastapi import APIRouter
from firstknock.api.schemas import DeepHealthResponse, ServiceStatus

router = APIRouter(tags=["health"])
logger = structlog.get_logger()


@router.get("/health/deep", response_model=DeepHealthResponse)
async def deep_health():
    services: list[ServiceStatus] = []

    # ── NeonDB ────────────────────────────────────────────────────────────────
    try:
        from firstknock.pipeline.persistence.db import engine
        t0 = time.monotonic()
        async with engine.connect() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
        latency = round((time.monotonic() - t0) * 1000, 1)
        services.append(ServiceStatus(name="neondb", status="ok", latency_ms=latency))
    except Exception as exc:
        services.append(ServiceStatus(name="neondb", status="error", detail=str(exc)))

    # ── Memgraph ──────────────────────────────────────────────────────────────
    try:
        from firstknock.pipeline.graph.client import get_driver
        t0 = time.monotonic()
        driver = await get_driver()
        async with driver.session(database="memgraph") as s:
            await s.run("RETURN 1")
        latency = round((time.monotonic() - t0) * 1000, 1)
        services.append(ServiceStatus(name="memgraph", status="ok", latency_ms=latency))
    except Exception as exc:
        services.append(ServiceStatus(name="memgraph", status="error", detail=str(exc)))

    # ── Redis ─────────────────────────────────────────────────────────────────
    try:
        import redis.asyncio as aioredis
        from firstknock.config import settings
        t0 = time.monotonic()
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        latency = round((time.monotonic() - t0) * 1000, 1)
        services.append(ServiceStatus(name="redis", status="ok", latency_ms=latency))
    except Exception as exc:
        services.append(ServiceStatus(name="redis", status="error", detail=str(exc)))

    error_count = sum(1 for s in services if s.status == "error")
    overall = "ok" if error_count == 0 else ("degraded" if error_count < len(services) else "error")

    return DeepHealthResponse(overall=overall, services=services)
