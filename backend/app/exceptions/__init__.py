"""
exceptions
==========
Centralized exports for all custom domain exceptions.

Author : AI Code Review Bot
"""

from app.exceptions.gemini_exceptions import (
    EmptyDiffError,
    GeminiAuthError,
    GeminiParseError,
    GeminiRateLimitError,
    GeminiServiceError,
    GeminiTimeoutError,
)
from app.exceptions.github_exceptions import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubValidationError,
)
from app.exceptions.review_exceptions import ReviewServiceError

__all__ = [
    "GeminiServiceError",
    "GeminiAuthError",
    "GeminiRateLimitError",
    "GeminiTimeoutError",
    "GeminiParseError",
    "EmptyDiffError",
    "GitHubAuthError",
    "GitHubAPIError",
    "GitHubNotFoundError",
    "GitHubRateLimitError",
    "GitHubValidationError",
    "ReviewServiceError",
]
