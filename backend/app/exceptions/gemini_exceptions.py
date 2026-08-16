"""
gemini_exceptions.py
====================
Custom exception classes raised by the Gemini AI integration layer.

Author : AI Code Review Bot
"""

from __future__ import annotations


class GeminiServiceError(Exception):
    """Base class for all errors raised by GeminiService."""


class GeminiAuthError(GeminiServiceError):
    """Raised when the API key is invalid or missing."""


class GeminiRateLimitError(GeminiServiceError):
    """Raised when the API quota is exhausted (HTTP 429)."""


class GeminiTimeoutError(GeminiServiceError):
    """Raised when an API call exceeds the configured timeout."""


class GeminiParseError(GeminiServiceError):
    """Raised when the model response cannot be parsed as ReviewResponse JSON."""


class EmptyDiffError(GeminiServiceError):
    """Raised when the supplied diff is empty after normalisation."""
