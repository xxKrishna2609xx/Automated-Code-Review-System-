"""
main.py
=======
FastAPI application entry point for the AI Code Review Backend.

Registers:
    • Application-wide lifespan (startup / shutdown hooks)
    • Global exception handlers
    • API routers (Phase 4 review router)
    • Middleware (CORS, structured logging, request-id injection)

Author : AI Code Review Bot — Phase 4
"""

from __future__ import annotations

import logging
import sys
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.review_router import router as review_router
from app.config import settings

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and graceful shutdown."""
    from app.db.mongodb import close_mongo_connection, connect_to_mongo

    logger.info(
        "AI Code Review Bot starting — environment=%s model=%s",
        settings.environment,
        settings.gemini_model,
    )
    try:
        await connect_to_mongo()
    except Exception as exc:
        logger.warning("MongoDB initial connection deferred or failed: %s", exc)

    yield

    logger.info("AI Code Review Bot shutting down.")
    close_mongo_connection()


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """Build and configure the FastAPI application.

    Returns:
        Fully configured ``FastAPI`` instance.
    """
    app = FastAPI(
        title="AI Code Review Bot",
        description=(
            "Production-grade automated Pull Request review engine powered by "
            "Google Gemini.  Phase 4 — AI Review Layer."
        ),
        version="4.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.environment == "development" else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request-ID middleware ────────────────────────────────────────────
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # ── Global exception handlers ────────────────────────────────────────
    from app.utils import register_exception_handlers

    register_exception_handlers(app)

    # ── Routers ──────────────────────────────────────────────────────────
    from app.api.analytics_router import router as analytics_router
    from app.api.dashboard_router import router as dashboard_router
    from app.api.export_router import router as export_router
    from app.api.fixes_router import router as fixes_router
    from app.api.history_router import router as history_router
    from app.api.repository_router import router as repository_router

    app.include_router(review_router, prefix="/api/v1", tags=["Review"])
    app.include_router(history_router, prefix="/api/v1", tags=["Review History"])
    app.include_router(history_router, prefix="/api", tags=["Review History"])
    app.include_router(dashboard_router, prefix="/api/v1", tags=["Dashboard"])
    app.include_router(dashboard_router, prefix="/api", tags=["Dashboard"])
    app.include_router(repository_router, prefix="/api/v1", tags=["Repositories"])
    app.include_router(repository_router, prefix="/api", tags=["Repositories"])
    app.include_router(analytics_router, prefix="/api/v1", tags=["Analytics"])
    app.include_router(analytics_router, prefix="/api", tags=["Analytics"])
    app.include_router(export_router, prefix="/api/v1", tags=["Export"])
    app.include_router(export_router, prefix="/api", tags=["Export"])
    app.include_router(fixes_router, prefix="/api/v1", tags=["Fixes"])
    app.include_router(fixes_router, prefix="/api", tags=["Fixes"])


    # ── Health check ─────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "environment": settings.environment,
            "model": settings.gemini_model,
        }

    return app


# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------

app: FastAPI = create_app()


# ---------------------------------------------------------------------------
# Dev entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower(),
    )
