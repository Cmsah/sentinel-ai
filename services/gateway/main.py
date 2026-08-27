"""FastAPI application — main entry point for the Sentinel AI Gateway.

Features:
- CORS middleware for frontend access
- Request ID middleware for distributed tracing
- Structured logging with structlog
- Lifespan management for DB, Redis, Kafka connections
- OpenAPI documentation at /docs
"""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from services.gateway.routes import analysis, deployments, health, incidents, webhooks
from services.shared.config import get_settings
from services.shared.database import init_db, close_db
from services.shared.exceptions import SentinelError
from services.shared.redis import close_redis

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown."""
    settings = get_settings()
    logger.info(
        "sentinel_ai_starting",
        env=settings.app_env,
        debug=settings.app_debug,
        llm_provider=settings.llm.provider,
    )

    # Initialize database (create tables in dev, use migrations in prod)
    if not settings.is_production:
        await init_db()

    yield

    # Shutdown
    logger.info("sentinel_ai_shutting_down")
    await close_db()
    await close_redis()


# ---------------------------------------------------------------------------
# Application Factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Sentinel AI — Autonomous Cloud Operations Platform",
        description=(
            "AI-powered SRE that monitors cloud infrastructure, "
            "investigates incidents, explains failures, and proposes fixes."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # --- CORS ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app_debug else ["https://sentinel.example.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Request ID + Timing Middleware ---
    @app.middleware("http")
    async def request_middleware(request: Request, call_next) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start_time = time.perf_counter()

        # Bind request context to structlog for this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms:.1f}ms"

        logger.info(
            "request_completed",
            status=response.status_code,
            duration_ms=round(duration_ms, 1),
        )
        return response

    # --- Global Exception Handler ---
    @app.exception_handler(SentinelError)
    async def sentinel_error_handler(request: Request, exc: SentinelError) -> JSONResponse:
        logger.error("sentinel_error", code=exc.code, message=exc.message, details=exc.details)
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}},
        )

    # --- Include Routers ---
    app.include_router(health.router, tags=["Health"])
    app.include_router(incidents.router, prefix="/api/v1", tags=["Incidents"])
    app.include_router(deployments.router, prefix="/api/v1", tags=["Deployments"])
    app.include_router(analysis.router, prefix="/api/v1", tags=["AI Analysis"])
    app.include_router(webhooks.router, tags=["Webhooks"])

    return app


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

app = create_app()
