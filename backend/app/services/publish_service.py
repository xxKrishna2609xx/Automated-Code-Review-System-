"""
publish_service.py
==================
High-level service orchestrator connecting the AI Review Engine with the
GitHub Review Publisher.

Workflow:
1. Receive ReviewRequest DTO and GitHub PR parameters (owner, repo, pull_number).
2. Execute AI Review via ReviewService.
3. Fetch PR head commit SHA and file metadata via GitHubClient.
4. Format ReviewResponse into GitHubReviewPayload using ReviewFormatter.
5. Publish review with inline comments and summary via ReviewPublisher.
6. Emit structured audit logs and return GitHubPublishResult.

Author : AI Code Review Bot — Phase 5
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from app.github import GitHubClient, ReviewFormatter, ReviewPublisher
from app.models.github_models import GitHubPublishResult
from app.models.review_models import ReviewRequest, ReviewResponse
from app.services.review_service import ReviewService

logger = logging.getLogger(__name__)


class PublishService:
    """Orchestrates end-to-end AI review generation and GitHub publishing."""

    def __init__(
        self,
        review_service: ReviewService,
        github_client: Optional[GitHubClient] = None,
        formatter: Optional[ReviewFormatter] = None,
        publisher: Optional[ReviewPublisher] = None,
    ) -> None:
        self._review_service = review_service
        self._client = github_client or GitHubClient()
        self._formatter = formatter or ReviewFormatter()
        self._publisher = publisher or ReviewPublisher(github_client=self._client)

    async def review_and_publish(
        self,
        request: ReviewRequest,
        owner: str,
        repo: str,
        pull_number: int,
    ) -> GitHubPublishResult:
        """Run AI code review on the supplied request and publish results directly to GitHub PR.

        Args:
            request    : Incoming ``ReviewRequest`` DTO.
            owner      : Repository owner / organisation.
            repo       : Repository name.
            pull_number: Target Pull Request number.

        Returns:
            ``GitHubPublishResult`` containing publish status and review details.
        """
        start_ts = time.monotonic()
        logger.info("PublishService starting review and publish pipeline — owner=%s repo=%s pr=%d", owner, repo, pull_number)

        # ── Step 1: AI Code Review ──────────────────────────────────────
        review_response: ReviewResponse = await self._review_service.review(request)
        ai_duration = time.monotonic() - start_ts

        # ── Step 2: Fetch GitHub PR Metadata ────────────────────────────
        commit_sha: Optional[str] = None
        files_reviewed_count = 1
        try:
            commit_sha = await self._client.get_latest_commit_sha(owner, repo, pull_number)
            files = await self._client.get_pull_request_files(owner, repo, pull_number)
            files_reviewed_count = len(files) if files else 1
        except Exception as exc:
            logger.warning("Could not fetch PR metadata from GitHub API: %s. Continuing with default commit_sha.", exc)

        # ── Step 3: Format Review Payload ───────────────────────────────
        payload = self._formatter.format_review(
            response=review_response,
            diff_text=request.diff,
            commit_sha=commit_sha,
            pr_number=pull_number,
            files_reviewed_count=files_reviewed_count,
            review_duration_seconds=ai_duration,
        )

        # ── Step 4: Publish Review to GitHub ────────────────────────────
        publish_result = await self._publisher.publish(
            owner=owner,
            repo=repo,
            pull_number=pull_number,
            payload=payload,
        )

        logger.info(
            "PublishService pipeline complete — status=%s event=%s comments=%d total_time=%.2fs",
            publish_result.status,
            publish_result.event.value,
            publish_result.comments_published,
            time.monotonic() - start_ts,
        )

        return publish_result
