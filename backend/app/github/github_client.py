"""
github_client.py
================
Async, resilient HTTP client wrapper around the GitHub REST API v3.

Encapsulates GitHub REST endpoints for Pull Requests, Changed Files,
Inline Comments, and Pull Request Reviews with built-in retry logic,
exponential backoff, error categorization, and typed Pydantic responses.

Author : AI Code Review Bot — Phase 5
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

import httpx

from app.config import Settings, get_settings
from app.github.github_auth import GitHubAuth, PATAuth
from app.models.github_models import (
    GitHubFile,
    GitHubInlineComment,
    GitHubPullRequest,
    GitHubReviewPayload,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------


class GitHubAPIError(Exception):
    """Base exception for GitHub REST API failures."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class GitHubNotFoundError(GitHubAPIError):
    """Raised on HTTP 404 (PR or Repo not found)."""


class GitHubRateLimitError(GitHubAPIError):
    """Raised on HTTP 429 / 403 Rate Limit Exhaustion."""


class GitHubValidationError(GitHubAPIError):
    """Raised on HTTP 422 (Unprocessable Entity / stale diff position)."""


# ---------------------------------------------------------------------------
# GitHubClient
# ---------------------------------------------------------------------------


class GitHubClient:
    """Async GitHub REST API client.

    Args:
        auth    : ``GitHubAuth`` authentication provider (defaults to PATAuth).
        settings: Application ``Settings`` instance.
    """

    def __init__(
        self,
        auth: Optional[GitHubAuth] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._auth = auth or PATAuth(settings=self._settings)
        self._base_url = self._settings.github_api_url.rstrip("/")
        self._timeout = self._settings.github_timeout_seconds

    # ------------------------------------------------------------------
    # Public API Methods
    # ------------------------------------------------------------------

    async def get_pull_request(self, owner: str, repo: str, pull_number: int) -> GitHubPullRequest:
        """Fetch Pull Request metadata from GitHub API.

        GET /repos/{owner}/{repo}/pulls/{pull_number}
        """
        endpoint = f"/repos/{owner}/{repo}/pulls/{pull_number}"
        data = await self._request("GET", endpoint)

        return GitHubPullRequest(
            number=data["number"],
            title=data.get("title", ""),
            body=data.get("body") or "",
            state=data.get("state", "open"),
            head_sha=data["head"]["sha"],
            base_sha=data["base"]["sha"],
            html_url=data.get("html_url", ""),
            owner=owner,
            repo=repo,
            user=data.get("user", {}).get("login"),
        )

    async def get_pull_request_files(self, owner: str, repo: str, pull_number: int) -> list[GitHubFile]:
        """Fetch list of changed files with diff patches for a Pull Request.

        GET /repos/{owner}/{repo}/pulls/{pull_number}/files
        """
        endpoint = f"/repos/{owner}/{repo}/pulls/{pull_number}/files"
        data = await self._request("GET", endpoint, params={"per_page": 100})

        files: list[GitHubFile] = []
        for item in data:
            files.append(
                GitHubFile(
                    filename=item["filename"],
                    status=item.get("status", "modified"),
                    additions=item.get("additions", 0),
                    deletions=item.get("deletions", 0),
                    changes=item.get("changes", 0),
                    patch=item.get("patch"),
                    sha=item.get("sha"),
                    blob_url=item.get("blob_url"),
                    raw_url=item.get("raw_url"),
                )
            )
        return files

    async def get_latest_commit_sha(self, owner: str, repo: str, pull_number: int) -> str:
        """Fetch the head commit SHA for a Pull Request."""
        pr = await self.get_pull_request(owner, repo, pull_number)
        return pr.head_sha

    async def create_review(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        payload: GitHubReviewPayload,
    ) -> dict[str, Any]:
        """Publish a full Pull Request Review with summary and inline comments.

        POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews
        """
        endpoint = f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews"

        body_dict: dict[str, Any] = {
            "body": payload.body,
            "event": payload.event.value,
        }
        if payload.commit_id:
            body_dict["commit_id"] = payload.commit_id

        if payload.comments:
            comments_payload = []
            for c in payload.comments:
                c_dict: dict[str, Any] = {
                    "path": c.path,
                    "line": c.line,
                    "side": c.side,
                    "body": c.body,
                }
                if c.position:
                    c_dict["position"] = c.position
                if c.start_line:
                    c_dict["start_line"] = c.start_line
                    c_dict["start_side"] = c.start_side or c.side
                comments_payload.append(c_dict)

            body_dict["comments"] = comments_payload

        logger.info(
            "Submitting PR review — owner=%s repo=%s pr=%d event=%s comments=%d",
            owner, repo, pull_number, payload.event.value, len(payload.comments),
        )

        return await self._request("POST", endpoint, json_data=body_dict)

    async def create_review_comment(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        comment: GitHubInlineComment,
        commit_id: str,
    ) -> dict[str, Any]:
        """Publish a single inline review comment on a Pull Request.

        POST /repos/{owner}/{repo}/pulls/{pull_number}/comments
        """
        endpoint = f"/repos/{owner}/{repo}/pulls/{pull_number}/comments"
        payload = {
            "body": comment.body,
            "commit_id": commit_id,
            "path": comment.path,
            "line": comment.line,
            "side": comment.side,
        }
        return await self._request("POST", endpoint, json_data=payload)

    async def create_issue_comment(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        body: str,
    ) -> dict[str, Any]:
        """Publish a top-level issue/PR comment (used for fallback summary).

        POST /repos/{owner}/{repo}/issues/{pull_number}/comments
        """
        endpoint = f"/repos/{owner}/{repo}/issues/{pull_number}/comments"
        return await self._request("POST", endpoint, json_data={"body": body})

    # ------------------------------------------------------------------
    # Private Helper Methods & Retry Logic
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
    ) -> Any:
        url = f"{self._base_url}{endpoint}"
        headers = await self._auth.get_headers()

        max_retries = self._settings.review_max_retries
        retry_delay = self._settings.review_retry_delay

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(1, max_retries + 1):
                try:
                    logger.debug("GitHub API %s %s (attempt %d/%d)", method, endpoint, attempt, max_retries)
                    response = await client.request(
                        method,
                        url,
                        headers=headers,
                        params=params,
                        json=json_data,
                    )

                    if response.status_code in (200, 201):
                        return response.json()

                    # Error handling by HTTP status code
                    if response.status_code == 404:
                        raise GitHubNotFoundError(
                            f"GitHub resource not found: {endpoint}",
                            status_code=404,
                            response_body=response.text,
                        )
                    if response.status_code == 422:
                        raise GitHubValidationError(
                            f"GitHub validation failed (422): {response.text}",
                            status_code=422,
                            response_body=response.text,
                        )
                    if response.status_code in (429, 403) and "rate limit" in response.text.lower():
                        if attempt < max_retries:
                            wait_time = retry_delay * (2 ** (attempt - 1))
                            logger.warning("GitHub Rate Limit hit. Retrying in %.1fs...", wait_time)
                            await asyncio.sleep(wait_time)
                            continue
                        raise GitHubRateLimitError(
                            "GitHub API Rate Limit exceeded.",
                            status_code=response.status_code,
                            response_body=response.text,
                        )

                    # Transient server errors (502, 503, 504) -> retry
                    if response.status_code in (502, 503, 504):
                        if attempt < max_retries:
                            wait_time = retry_delay * (2 ** (attempt - 1))
                            logger.warning("GitHub transient server error %d. Retrying in %.1fs...", response.status_code, wait_time)
                            await asyncio.sleep(wait_time)
                            continue

                    raise GitHubAPIError(
                        f"GitHub API error HTTP {response.status_code}: {response.text}",
                        status_code=response.status_code,
                        response_body=response.text,
                    )

                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    if attempt < max_retries:
                        wait_time = retry_delay * (2 ** (attempt - 1))
                        logger.warning("GitHub network/timeout error: %s. Retrying in %.1fs...", exc, wait_time)
                        await asyncio.sleep(wait_time)
                        continue
                    raise GitHubAPIError(f"GitHub connection failed after {max_retries} attempts: {exc}")

        raise GitHubAPIError(f"GitHub API request to {endpoint} failed.")
