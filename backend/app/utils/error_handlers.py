"""
error_handlers.py
=================
FastAPI exception handler helpers for Gemini AI and GitHub API exceptions.
"""

from __future__ import annotations

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register application-wide custom exception handlers on the FastAPI app instance."""
    from app.ai.gemini_service import (
        EmptyDiffError,
        GeminiAuthError,
        GeminiParseError,
        GeminiRateLimitError,
        GeminiServiceError,
        GeminiTimeoutError,
    )
    from app.github import GitHubAPIError, GitHubAuthError

    @app.exception_handler(EmptyDiffError)
    async def empty_diff_handler(request: Request, exc: EmptyDiffError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(GeminiAuthError)
    async def auth_error_handler(request: Request, exc: GeminiAuthError):
        logger.error("Gemini Authentication Error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Gemini authentication failed. Check GEMINI_API_KEY."},
        )

    @app.exception_handler(GeminiRateLimitError)
    async def rate_limit_handler(request: Request, exc: GeminiRateLimitError):
        logger.warning("Gemini Rate Limit Exceeded: %s", exc)
        return JSONResponse(
            status_code=429,
            content={"detail": "Gemini API quota exhausted. Please retry later."},
        )

    @app.exception_handler(GeminiTimeoutError)
    async def timeout_handler(request: Request, exc: GeminiTimeoutError):
        logger.warning("Gemini Request Timeout: %s", exc)
        return JSONResponse(
            status_code=504,
            content={"detail": "Gemini API timed out. Please retry."},
        )

    @app.exception_handler(GeminiParseError)
    async def parse_error_handler(request: Request, exc: GeminiParseError):
        logger.error("Gemini Response Parse Error: %s", exc)
        return JSONResponse(
            status_code=502,
            content={"detail": f"Failed to parse Gemini response: {exc}"},
        )

    @app.exception_handler(GeminiServiceError)
    async def gemini_service_error_handler(request: Request, exc: GeminiServiceError):
        logger.error("Gemini Service Error: %s", exc)
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(GitHubAuthError)
    async def github_auth_error_handler(request: Request, exc: GitHubAuthError):
        logger.error("GitHub Authentication Error: %s", exc)
        return JSONResponse(
            status_code=401,
            content={"detail": f"GitHub authentication failed: {exc}"},
        )

    @app.exception_handler(GitHubAPIError)
    async def github_api_error_handler(request: Request, exc: GitHubAPIError):
        logger.error("GitHub API Error: %s", exc)
        return JSONResponse(
            status_code=502,
            content={"detail": f"GitHub API error: {exc}"},
        )
