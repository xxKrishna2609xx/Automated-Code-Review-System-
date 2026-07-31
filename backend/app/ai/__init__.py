"""
app/ai/__init__.py
==================
Public re-exports for the AI package.
"""
from app.ai.gemini_service import (
    EmptyDiffError,
    GeminiAuthError,
    GeminiParseError,
    GeminiRateLimitError,
    GeminiService,
    GeminiServiceError,
    GeminiTimeoutError,
    get_gemini_service,
)

__all__ = [
    "GeminiService",
    "GeminiServiceError",
    "GeminiAuthError",
    "GeminiRateLimitError",
    "GeminiTimeoutError",
    "GeminiParseError",
    "EmptyDiffError",
    "get_gemini_service",
]
