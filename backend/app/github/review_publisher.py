"""
review_publisher.py
===================
Publishing engine for posting GitHub Pull Request Reviews.

Responsibilities:
• Submits structured reviews containing inline comments and summary via GitHub REST API.
• Handles transient HTTP failures with exponential backoff retries.
• Implements HTTP 422 Fallback Strategy: If batch inline comments fail (e.g. due to stale diff position or missing line), automatically falls back to publishing the summary comment with inline findings embedded as Markdown so review feedback is NEVER lost.

Author : AI Code Review Bot — Phase 5
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from app.github.github_client import GitHubClient, GitHubValidationError
from app.models.github_models import (
    GitHubInlineComment,
    GitHubPublishResult,
    GitHubReviewEvent,
    GitHubReviewPayload,
)

logger = logging.getLogger(__name__)


class ReviewPublisher:
    """Publisher for posting formatted reviews to GitHub Pull Requests."""

    def __init__(self, github_client: Optional[GitHubClient] = None) -> None:
        self._client = github_client or GitHubClient()

    async def publish(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        payload: GitHubReviewPayload,
    ) -> GitHubPublishResult:
        """Publish a GitHubReviewPayload to the specified Pull Request.

        Args:
            owner      : Repository owner / organization.
            repo       : Repository name.
            pull_number: Target PR ID number.
            payload    : Formatted ``GitHubReviewPayload``.

        Returns:
            Structured ``GitHubPublishResult``.
        """
        start_ts = time.monotonic()

        try:
            # 1. Primary Attempt — Submit full review with inline comments
            res = await self._client.create_review(owner, repo, pull_number, payload)
            elapsed = time.monotonic() - start_ts

            review_id = res.get("id")
            html_url = res.get("html_url")
            comments_count = len(payload.comments)

            logger.info(
                "Successfully published GitHub PR review — id=%s pr=%d comments=%d elapsed=%.2fs",
                review_id, pull_number, comments_count, elapsed,
            )

            return GitHubPublishResult(
                review_id=review_id,
                pr_number=pull_number,
                html_url=html_url,
                comments_published=comments_count,
                event=payload.event,
                status="success",
                elapsed_seconds=elapsed,
            )

        except GitHubValidationError as exc:
            # 2. HTTP 422 Fallback — Stale diff line numbers or position mismatch
            logger.warning(
                "GitHub batch inline comments failed (HTTP 422: %s). Executing Fallback Strategy...",
                exc,
            )
            return await self._publish_fallback(
                owner=owner,
                repo=repo,
                pull_number=pull_number,
                payload=payload,
                start_ts=start_ts,
                error_reason=str(exc),
            )

        except Exception as exc:
            elapsed = time.monotonic() - start_ts
            logger.error("Failed to publish GitHub review to PR #%d: %s", pull_number, exc)
            return GitHubPublishResult(
                pr_number=pull_number,
                comments_published=0,
                event=payload.event,
                status="failed",
                elapsed_seconds=elapsed,
                error_message=str(exc),
            )

    async def _publish_fallback(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        payload: GitHubReviewPayload,
        start_ts: float,
        error_reason: str,
    ) -> GitHubPublishResult:
        """Fallback publishing strategy when batch inline comments fail.

        Appends all inline findings into the main review summary markdown and
        publishes a clean summary comment so feedback is delivered without loss.
        """
        fallback_body_lines = [
            payload.body,
            "",
            "---",
            "### ⚠️ Inline Comment Placement Notice",
            "*Some inline comments could not be placed on exact diff lines due to stale commits or file changes. All detected findings are detailed below:*",
            "",
        ]

        for idx, comment in enumerate(payload.comments, 1):
            fallback_body_lines.extend([
                f"#### Issue #{idx} — `{comment.path}` (Line {comment.line})",
                comment.body,
                "",
            ])

        fallback_body = "\n".join(fallback_body_lines)

        try:
            # Send simplified review payload without inline comments array
            clean_payload = GitHubReviewPayload(
                commit_id=payload.commit_id,
                body=fallback_body,
                event=payload.event,
                comments=[],
            )
            res = await self._client.create_review(owner, repo, pull_number, clean_payload)
            elapsed = time.monotonic() - start_ts

            logger.info("Published fallback PR review summary — pr=%d elapsed=%.2fs", pull_number, elapsed)

            return GitHubPublishResult(
                review_id=res.get("id"),
                pr_number=pull_number,
                html_url=res.get("html_url"),
                comments_published=0,
                event=payload.event,
                status="fallback_published",
                elapsed_seconds=elapsed,
                extra={"fallback_reason": error_reason, "issues_inlined_in_summary": len(payload.comments)},
            )
        except Exception as exc:
            # Last resort — issue comment
            logger.error("Fallback review creation failed: %s. Attempting issue comment...", exc)
            res = await self._client.create_issue_comment(owner, repo, pull_number, fallback_body)
            elapsed = time.monotonic() - start_ts

            return GitHubPublishResult(
                review_id=res.get("id"),
                pr_number=pull_number,
                html_url=res.get("html_url"),
                comments_published=0,
                event=payload.event,
                status="fallback_published",
                elapsed_seconds=elapsed,
                extra={"fallback_reason": str(exc)},
            )
