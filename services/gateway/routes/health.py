"""Health check routes — liveness and readiness probes.

Kubernetes uses these endpoints to determine pod health.
- /health — Liveness: is the process alive?
- /ready — Readiness: can it accept traffic?
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class ReadyResponse(BaseModel):
    status: str
    checks: dict[str, str]


@router.get("/health", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    """Liveness probe — returns 200 if the process is alive."""
    return HealthResponse(
        status="healthy",
        service="sentinel-ai",
        version="0.1.0",
    )


@router.get("/ready", response_model=ReadyResponse)
async def readiness() -> ReadyResponse:
    """Readiness probe — checks dependencies are available."""
    checks = {}

    # Database
    try:
        from services.shared.database import get_engine
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # Redis
    try:
        from services.shared.redis import get_redis
        redis = await get_redis()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return ReadyResponse(
        status="ready" if all_ok else "degraded",
        checks=checks,
    )
