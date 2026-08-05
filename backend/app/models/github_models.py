"""
github_models.py
================
Strict Pydantic schemas representing GitHub PRs, Files, Inline Comments,
Review Payloads, and Publishing Results for the GitHub REST API v3.

Author : AI Code Review Bot — Phase 5
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class GitHubReviewEvent(str, Enum):
    """Action event types for GitHub Pull Request Reviews."""

    COMMENT = "COMMENT"
    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"


class GitHubInlineComment(BaseModel):
    """Individual inline comment placed on a specific line of a file diff.

    Attributes:
        path       : Relative file path in the repository (e.g. "app/main.py").
        line       : Line number in the target file (1-indexed).
        side       : Diff side — "RIGHT" (new file) or "LEFT" (old file). Default "RIGHT".
        body       : Markdown formatted comment body.
        start_line : Optional start line for multi-line comments.
        start_side : Optional start side for multi-line comments.
        position   : Classic 1-based diff hunk position index.
    """

    path: str = Field(..., min_length=1, description="Relative file path in repository.")
    line: int = Field(..., ge=1, description="1-indexed line number in the file.")
    side: str = Field(default="RIGHT", description="Diff side: RIGHT (added/modified) or LEFT (deleted).")
    body: str = Field(..., min_length=1, description="Markdown formatted inline comment content.")
    start_line: Optional[int] = Field(default=None, ge=1, description="Start line for multi-line comment.")
    start_side: Optional[str] = Field(default=None, description="Start side for multi-line comment.")
    position: Optional[int] = Field(default=None, ge=1, description="Legacy 1-based diff position index.")

    @field_validator("side", "start_side", mode="before")
    @classmethod
    def normalise_side(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            return v.upper().strip()
        return v


class GitHubReviewPayload(BaseModel):
    """Payload sent to GitHub POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews."""

    commit_id: Optional[str] = Field(default=None, description="SHA of the commit to review.")
    body: str = Field(..., min_length=1, description="Overall Markdown review summary.")
    event: GitHubReviewEvent = Field(default=GitHubReviewEvent.COMMENT, description="Review action event.")
    comments: list[GitHubInlineComment] = Field(default_factory=list, description="Inline review comments.")


class GitHubFile(BaseModel):
    """A changed file within a GitHub Pull Request."""

    filename: str = Field(..., description="File path relative to repo root.")
    status: str = Field(default="modified", description="added | modified | removed | renamed.")
    additions: int = Field(default=0, ge=0, description="Lines added.")
    deletions: int = Field(default=0, ge=0, description="Lines deleted.")
    changes: int = Field(default=0, ge=0, description="Total changes.")
    patch: Optional[str] = Field(default=None, description="Unified patch string for this file.")
    sha: Optional[str] = Field(default=None, description="Blob SHA.")
    blob_url: Optional[str] = Field(default=None, description="GitHub Web URL for the blob.")
    raw_url: Optional[str] = Field(default=None, description="GitHub Raw URL.")


class GitHubPullRequest(BaseModel):
    """Metadata representing a GitHub Pull Request."""

    number: int = Field(..., ge=1, description="Pull Request ID number.")
    title: str = Field(..., description="PR title.")
    body: Optional[str] = Field(default="", description="PR description body.")
    state: str = Field(default="open", description="open | closed.")
    head_sha: str = Field(..., description="Head commit SHA.")
    base_sha: str = Field(..., description="Base commit SHA.")
    html_url: str = Field(default="", description="Web URL for the pull request.")
    owner: str = Field(..., description="Repository owner / organization.")
    repo: str = Field(..., description="Repository name.")
    user: Optional[str] = Field(default=None, description="Author username.")


class GitHubPublishResult(BaseModel):
    """Result of publishing a review to GitHub."""

    review_id: Optional[int] = Field(default=None, description="Created GitHub Review ID.")
    pr_number: int = Field(..., ge=1, description="Target PR number.")
    html_url: Optional[str] = Field(default=None, description="Web URL of published review.")
    comments_published: int = Field(default=0, ge=0, description="Count of inline comments created.")
    event: GitHubReviewEvent = Field(..., description="Action event published.")
    status: str = Field(..., description="success | partial_success | failed | fallback_published.")
    elapsed_seconds: float = Field(..., ge=0.0, description="Publish duration in seconds.")
    error_message: Optional[str] = Field(default=None, description="Error detail if failed.")
    extra: dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary.")
