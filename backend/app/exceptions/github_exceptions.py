"""
github_exceptions.py
====================
Custom exception classes raised by GitHub authentication and API integration layers.

Author : AI Code Review Bot
"""

from __future__ import annotations

from typing import Optional


class GitHubAuthError(Exception):
    """Raised when GitHub App / PAT authentication fails."""


class GitHubAPIError(Exception):
    """Base exception for GitHub REST API interactions.

    Attributes:
        status_code  : HTTP response status code (e.g. 404, 422, 429).
        response_body: Raw text body returned by the API.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class GitHubNotFoundError(GitHubAPIError):
    """Raised when a requested GitHub resource (PR, repo, commit) returns 404."""


class GitHubRateLimitError(GitHubAPIError):
    """Raised when GitHub API rate limits (primary or secondary) are exceeded."""


class GitHubValidationError(GitHubAPIError):
    """Raised when GitHub returns 422 Unprocessable Entity (e.g. invalid diff position)."""
