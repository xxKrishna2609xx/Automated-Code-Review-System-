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
    logger.info(
        "AI Code Review Bot starting — environment=%s model=%s",
        settings.environment,
        settings.gemini_model,
    )
    yield
    logger.info("AI Code Review Bot shutting down.")


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
    from app.ai.gemini_service import (
        EmptyDiffError,
        GeminiAuthError,
        GeminiParseError,
        GeminiRateLimitError,
        GeminiServiceError,
        GeminiTimeoutError,
    )

    @app.exception_handler(EmptyDiffError)
    async def empty_diff_handler(request: Request, exc: EmptyDiffError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(GeminiAuthError)
    async def auth_error_handler(request: Request, exc: GeminiAuthError):
        return JSONResponse(status_code=500, content={"detail": "Gemini authentication failed.  Check GEMINI_API_KEY."})

    @app.exception_handler(GeminiRateLimitError)
    async def rate_limit_handler(request: Request, exc: GeminiRateLimitError):
        return JSONResponse(status_code=429, content={"detail": "Gemini API quota exhausted.  Please retry later."})

    @app.exception_handler(GeminiTimeoutError)
    async def timeout_handler(request: Request, exc: GeminiTimeoutError):
        return JSONResponse(status_code=504, content={"detail": "Gemini API timed out.  Please retry."})

    @app.exception_handler(GeminiParseError)
    async def parse_error_handler(request: Request, exc: GeminiParseError):
        return JSONResponse(status_code=502, content={"detail": f"Failed to parse Gemini response: {exc}"})

    @app.exception_handler(GeminiServiceError)
    async def gemini_service_error_handler(request: Request, exc: GeminiServiceError):
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    # ── Routers ──────────────────────────────────────────────────────────
    app.include_router(review_router, prefix="/api/v1", tags=["Review"])

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
