"""
github_auth.py
==============
Authentication provider for GitHub REST API calls.

Supports Personal Access Tokens (PAT) and establishes an abstract interface
so migrating to GitHub App Installation Tokens (JWT/installation token flow)
in the future requires zero changes to API callers.

Author : AI Code Review Bot — Phase 5
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class GitHubAuthError(Exception):
    """Raised when GitHub authentication fails or credentials are missing."""


class GitHubAuth(ABC):
    """Abstract authentication interface for GitHub API authorization headers."""

    @abstractmethod
    async def get_headers(self) -> dict[str, str]:
        """Return HTTP authorization headers required for GitHub REST API.

        Returns:
            Dict containing Authorization and GitHub API version headers.
        """
        ...


class PATAuth(GitHubAuth):
    """Personal Access Token (PAT) authentication provider.

    Reads GitHub Personal Access Token from application settings or environment.
    """

    def __init__(self, token: Optional[str] = None, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._token = token or self._settings.github_token

        if not self._token or not self._token.strip():
            logger.warning("No GITHUB_TOKEN configured. Authenticated API calls will fail.")

    async def get_headers(self) -> dict[str, str]:
        """Return Bearer token headers for GitHub REST API v3."""
        token = self._token or self._settings.github_token
        if not token or not token.strip():
            raise GitHubAuthError(
                "Missing GitHub Access Token. Provide GITHUB_TOKEN environment variable "
                "or pass a token to PATAuth."
            )

        clean_token = token.strip()
        auth_value = f"Bearer {clean_token}" if clean_token.startswith("ghp_") or clean_token.startswith("github_pat_") else f"token {clean_token}"

        return {
            "Authorization": auth_value,
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "AI-Code-Review-Bot/1.0",
        }
