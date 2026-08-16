"""
persistence_models.py
======================
Pydantic data models for MongoDB persistence (Phase 7).

Defines the database schema for storing code reviews, issues, and metadata.
Includes helpers for deterministic review_key generation and mapping from
Phase 6 FinalReview payloads.

Author : AI Code Review Bot — Phase 7 (Stage 7.1)
"""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.agent_models import AgentReview, FinalReview
from app.models.review_models import Issue


class ReviewStatus(str, Enum):
    """Lifecycle status of a persisted code review."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


def generate_review_key(
    owner: str,
    repo_name: str,
    pull_request_number: int,
    commit_sha: Optional[str] = None,
) -> str:
    """Generate a deterministic review key for idempotency.

    Format: ``{owner}/{repo_name}#PR-{pull_request_number}@{commit_sha or 'head'}``
    """
    clean_owner = owner.strip().lower()
    clean_repo = repo_name.strip().lower()
    sha_part = (commit_sha or "head").strip().lower()
    return f"{clean_owner}/{clean_repo}#{pull_request_number}@{sha_part}"


class PersistedReview(BaseModel):
    """MongoDB document representation of an AI code review.

    Combines Phase 6 ``FinalReview`` analysis with GitHub PR metadata for
    analytics and dashboard querying.
    """

    id: Optional[str] = Field(
        default=None,
        alias="_id",
        description="MongoDB BSON ObjectId (hex string).",
    )
    review_key: str = Field(
        ...,
        min_length=3,
        description="Deterministic key for idempotency (owner/repo#PR@sha).",
    )
    repository: str = Field(
        ...,
        description="Full repository slug e.g. 'owner/repo'.",
    )
    repository_id: Optional[str] = Field(
        default=None,
        description="GitHub numeric or string repository ID.",
    )
    repository_url: Optional[str] = Field(
        default=None,
        description="GitHub web URL for repository.",
    )
    owner: str = Field(
        ...,
        description="Repository owner/organization.",
    )
    repo_name: str = Field(
        ...,
        description="Repository name.",
    )
    pull_request_number: int = Field(
        ...,
        ge=1,
        description="Target PR number.",
    )
    pull_request_url: Optional[str] = Field(
        default=None,
        description="GitHub web URL for PR.",
    )
    pull_request_title: str = Field(
        default="",
        description="PR title.",
    )
    pull_request_state: str = Field(
        default="open",
        description="PR state ('open', 'closed', 'merged').",
    )
    author: str = Field(
        default="unknown",
        description="PR author GitHub handle.",
    )
    base_branch: Optional[str] = Field(
        default=None,
        description="Target base branch e.g. 'main'.",
    )
    head_branch: Optional[str] = Field(
        default=None,
        description="Source head branch.",
    )
    commit_sha: Optional[str] = Field(
        default=None,
        description="Head commit SHA evaluated.",
    )
    files_changed: int = Field(
        default=0,
        ge=0,
        description="Number of files changed in diff.",
    )
    additions: int = Field(
        default=0,
        ge=0,
        description="Total lines added.",
    )
    deletions: int = Field(
        default=0,
        ge=0,
        description="Total lines deleted.",
    )
    overall_score: int = Field(
        default=-1,
        ge=-1,
        le=100,
        description="0-100 quality score.",
    )
    summary: str = Field(
        default="",
        description="Overall narrative summary.",
    )
    total_issues: int = Field(
        default=0,
        ge=0,
        description="Total deduplicated issue count.",
    )
    severity_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Count of issues by severity.",
    )
    category_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Count of issues by category.",
    )
    agent_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Count of findings per agent.",
    )
    issues: list[Issue] = Field(
        default_factory=list,
        description="Deduplicated list of findings.",
    )
    agent_results: list[AgentReview] = Field(
        default_factory=list,
        description="Individual agent reviews.",
    )
    review_duration_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Total execution time in milliseconds.",
    )
    review_status: ReviewStatus = Field(
        default=ReviewStatus.COMPLETED,
        description="Lifecycle status.",
    )
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="Record creation timestamp.",
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="Record update timestamp.",
    )

    @field_validator("review_status", mode="before")
    @classmethod
    def normalise_status(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    model_config = {
        "use_enum_values": True,
        "populate_by_name": True,
    }

    @classmethod
    def from_final_review(
        cls,
        final_review: FinalReview,
        owner: str,
        repo_name: str,
        pull_request_number: int,
        commit_sha: Optional[str] = None,
        author: str = "unknown",
        pull_request_title: Optional[str] = None,
        pull_request_url: Optional[str] = None,
        base_branch: Optional[str] = None,
        head_branch: Optional[str] = None,
        files_changed: int = 1,
        additions: int = 0,
        deletions: int = 0,
    ) -> PersistedReview:
        """Factory method mapping a Phase 6 FinalReview into a PersistedReview."""
        review_key = generate_review_key(
            owner=owner,
            repo_name=repo_name,
            pull_request_number=pull_request_number,
            commit_sha=commit_sha,
        )

        agent_counts: dict[str, int] = {}
        for agent_res in final_review.agent_results:
            agent_counts[agent_res.agent_name] = len(agent_res.issues)

        # Status determination: if all failed -> FAILED, if any failed -> PARTIAL, else COMPLETED
        if final_review.failed_agents and not final_review.successful_agents:
            status = ReviewStatus.FAILED
        elif final_review.failed_agents:
            status = ReviewStatus.PARTIAL
        else:
            status = ReviewStatus.COMPLETED

        return cls(
            review_key=review_key,
            repository=f"{owner}/{repo_name}",
            repository_id=f"{owner}/{repo_name}",
            repository_url=f"https://github.com/{owner}/{repo_name}",
            owner=owner,
            repo_name=repo_name,
            pull_request_number=pull_request_number,
            pull_request_url=pull_request_url or f"https://github.com/{owner}/{repo_name}/pull/{pull_request_number}",
            pull_request_title=pull_request_title or "",
            author=author,
            base_branch=base_branch,
            head_branch=head_branch,
            commit_sha=commit_sha,
            files_changed=files_changed,
            additions=additions,
            deletions=deletions,
            overall_score=final_review.overall_score,
            summary=final_review.summary,
            total_issues=final_review.total_issues,
            severity_counts=final_review.issues_by_severity,
            category_counts=final_review.issues_by_category,
            agent_counts=agent_counts,
            issues=final_review.issues,
            agent_results=final_review.agent_results,
            review_duration_ms=final_review.execution_time_ms,
            review_status=status,
        )
