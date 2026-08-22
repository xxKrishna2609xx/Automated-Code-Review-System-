"""
models.py  (app.fixes)
======================
Pydantic domain models for Phase 8 — AI Code Fix & Auto-Remediation.

Defines the complete fix lifecycle:

    FixStatus     — 14-state enum representing every stage of the fix pipeline.
    FixRequest    — Trigger record created from a stored Phase 6/7 finding.
    FixPatch      — Structured AI-generated minimal patch for one file.
    FixResult     — Final outcome record (branch, commit, PR, resolution flags).

Design rules (from Phase 8 safety spec):
    - FixRequest stores only trusted identifiers (review_id / issue_id).
    - File paths are validated against path-traversal patterns.
    - No Gemini calls, no GitHub mutations, no MongoDB in this module.
    - All models are independently testable with no external services.

Author : AI Code Review Bot — Phase 8 (Stage 8.1)
"""

from __future__ import annotations

import datetime
import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Repository slug helpers
# ---------------------------------------------------------------------------

_REPO_SLUG_RE = re.compile(r"^[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+$")

# Path-traversal patterns that must never appear in a file path
_UNSAFE_PATH_FRAGMENTS = ("../", "..\\", "\x00")


def _validate_repo_slug(value: str) -> str:
    """Raise ValueError when value is not a valid 'owner/repo' slug."""
    stripped = value.strip()
    if not stripped:
        raise ValueError("Repository slug must not be empty.")
    if not _REPO_SLUG_RE.match(stripped):
        raise ValueError(
            f"Repository slug '{stripped}' is not a valid 'owner/repo' identifier. "
            "Only alphanumeric characters, hyphens, underscores, and dots are allowed."
        )
    return stripped


def _validate_file_path(value: str) -> str:
    """Reject empty, absolute, and path-traversal file paths."""
    stripped = value.strip()
    if not stripped:
        raise ValueError("File path must not be empty.")
    for fragment in _UNSAFE_PATH_FRAGMENTS:
        if fragment in stripped:
            raise ValueError(
                f"File path contains unsafe traversal sequence '{fragment}'. "
                "Only relative repository paths are permitted."
            )
    if stripped.startswith("/") or (len(stripped) >= 2 and stripped[1] == ":"):
        raise ValueError(
            "Absolute file paths are not permitted. "
            "Provide a path relative to the repository root."
        )
    return stripped


# ---------------------------------------------------------------------------
# FixStatus — 14-state lifecycle enum
# ---------------------------------------------------------------------------


class FixStatus(str, Enum):
    """Lifecycle states for a fix request.

    Ordering reflects the happy-path pipeline:

        REQUESTED → GENERATING → GENERATED → VALIDATING → READY_FOR_APPROVAL
        → APPROVED → APPLYING → COMMITTED → PR_CREATED → REVIEWING → COMPLETED

    Terminal failure / rejection states:
        REJECTED — developer explicitly rejected the proposed fix.
        FAILED   — a pipeline stage failed non-recoverably (see FixResult.error_code).
        STALE    — base commit drifted; fix can no longer be safely applied.
    """

    REQUESTED = "REQUESTED"
    GENERATING = "GENERATING"
    GENERATED = "GENERATED"
    VALIDATING = "VALIDATING"
    READY_FOR_APPROVAL = "READY_FOR_APPROVAL"
    APPROVED = "APPROVED"
    APPLYING = "APPLYING"
    COMMITTED = "COMMITTED"
    PR_CREATED = "PR_CREATED"
    REVIEWING = "REVIEWING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    STALE = "STALE"


# ---------------------------------------------------------------------------
# FixRequest — trigger record
# ---------------------------------------------------------------------------


class FixRequest(BaseModel):
    """Trigger record created when a developer requests an AI-generated fix.

    Populated server-side from a stored Phase 7 PersistedReview document and
    the specific Issue within it.  The client supplies ONLY:
        - review_id   (MongoDB ObjectId hex string of the PersistedReview)
        - issue_id    (deterministic issue identifier within the review)

    All other fields are loaded server-side to prevent client-side injection
    of arbitrary file paths, source code, or repository context.

    Attributes:
        id                   : Unique fix request identifier (UUID hex string).
                               Set by the service layer, not the client.
        review_id            : ID of the Phase 7 PersistedReview this fix targets.
        issue_id             : Stable identifier of the specific Issue within
                               the review (format: '<category>-<index>' or hash).
        repository_id        : Opaque repository identifier (GitHub numeric ID
                               or 'owner/repo' slug).
        repository           : 'owner/repo' slug — loaded from the stored review.
        pull_request_number  : PR number — loaded from the stored review.
        base_commit_sha      : HEAD commit SHA at the time of review — loaded
                               from stored review for staleness detection.
        file_path            : Target file path relative to repository root.
        line                 : Optional 1-based line number of the issue.
        issue_title          : Human-readable title of the original finding.
        issue_description    : Full description loaded from the stored issue.
        suggestion           : Original AI suggestion from the Phase 6 review.
        status               : Current lifecycle state (default: REQUESTED).
        created_by           : GitHub handle / user identifier of the requester.
        created_at           : UTC timestamp of request creation.
        updated_at           : UTC timestamp of last status change.
    """

    id: Optional[str] = Field(
        default=None,
        description="Unique fix request identifier (UUID hex string, set by service layer).",
    )
    review_id: str = Field(
        ...,
        min_length=1,
        description="Phase 7 PersistedReview document ID this fix targets.",
    )
    issue_id: str = Field(
        ...,
        min_length=1,
        description="Stable identifier of the specific Issue within the review.",
    )
    repository_id: Optional[str] = Field(
        default=None,
        description="Opaque GitHub repository identifier.",
    )
    repository: str = Field(
        ...,
        description="Full repository slug 'owner/repo' — loaded from stored review.",
    )
    pull_request_number: int = Field(
        ...,
        ge=1,
        description="Pull Request number — loaded from stored review.",
    )
    base_commit_sha: str = Field(
        ...,
        min_length=7,
        max_length=40,
        description="HEAD commit SHA at review time — used for staleness detection.",
    )
    file_path: str = Field(
        ...,
        description="Target file path relative to repository root.",
    )
    line: Optional[int] = Field(
        default=None,
        ge=1,
        description="1-based line number of the issue in the file (nullable).",
    )
    issue_title: str = Field(
        ...,
        min_length=3,
        max_length=120,
        description="Human-readable title of the original finding.",
    )
    issue_description: str = Field(
        ...,
        min_length=10,
        description="Full description of the original finding.",
    )
    suggestion: str = Field(
        default="",
        description="Original AI suggestion from the Phase 6 review.",
    )
    status: FixStatus = Field(
        default=FixStatus.REQUESTED,
        description="Current lifecycle state.",
    )
    created_by: str = Field(
        default="system",
        description="GitHub handle or user identifier of the requester.",
    )
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="UTC timestamp of request creation.",
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="UTC timestamp of last status change.",
    )

    @field_validator("repository", mode="before")
    @classmethod
    def validate_repository(cls, value: str) -> str:
        return _validate_repo_slug(value)

    @field_validator("file_path", mode="before")
    @classmethod
    def validate_file_path(cls, value: str) -> str:
        return _validate_file_path(value)

    @field_validator("base_commit_sha", mode="before")
    @classmethod
    def validate_sha(cls, value: str) -> str:
        stripped = value.strip()
        if not re.match(r"^[0-9a-fA-F]{7,40}$", stripped):
            raise ValueError(
                f"base_commit_sha '{stripped}' is not a valid Git commit SHA "
                "(7–40 hex characters)."
            )
        return stripped.lower()

    model_config = {
        "use_enum_values": True,
        "populate_by_name": True,
    }


# ---------------------------------------------------------------------------
# FixPatch — AI-generated minimal patch
# ---------------------------------------------------------------------------


class FixPatch(BaseModel):
    """Structured minimal patch generated by the AI Fix Generator.

    Contains exactly what will be applied to the target file.  The
    ``original_content_hash`` allows the Patch Validator (Stage 8.6) to
    confirm the file has not drifted since the patch was generated.

    Attributes:
        file_path             : Target file path relative to repository root.
        original_content_hash : SHA-256 hex digest of the original file content
                                at ``base_commit_sha``.
        patch                 : Unified diff patch string (standard GNU format).
        changed_lines         : 1-based line numbers that the patch modifies.
        explanation           : Plain-English explanation of what was changed
                                and why, produced by the AI generator.
    """

    file_path: str = Field(
        ...,
        description="Target file path relative to repository root.",
    )
    original_content_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="SHA-256 hex digest of the original file content.",
    )
    patch: str = Field(
        ...,
        min_length=1,
        description="Unified diff patch string in standard GNU format.",
    )
    changed_lines: list[int] = Field(
        default_factory=list,
        description="1-based line numbers modified by this patch.",
    )
    explanation: str = Field(
        ...,
        min_length=10,
        description="Plain-English explanation of what changed and why.",
    )

    @field_validator("file_path", mode="before")
    @classmethod
    def validate_file_path(cls, value: str) -> str:
        return _validate_file_path(value)

    @field_validator("original_content_hash", mode="before")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        stripped = value.strip().lower()
        if not re.match(r"^[0-9a-f]{64}$", stripped):
            raise ValueError(
                "original_content_hash must be a 64-character lowercase hex SHA-256 digest."
            )
        return stripped

    @field_validator("changed_lines", mode="before")
    @classmethod
    def validate_changed_lines(cls, value: list) -> list:
        for ln in value:
            if not isinstance(ln, int) or ln < 1:
                raise ValueError(
                    f"changed_lines must contain positive integers (1-based line numbers), got {ln!r}."
                )
        return value

    model_config = {"use_enum_values": True}


# ---------------------------------------------------------------------------
# FixResult — final outcome record
# ---------------------------------------------------------------------------


class FixResult(BaseModel):
    """Outcome of the complete fix pipeline, persisted to the fix_requests collection.

    Populated progressively as the pipeline advances.  All fields are nullable
    so that a partial result can be stored on failure at any stage.

    Attributes:
        fix_request_id        : References the parent FixRequest.id.
        status                : Final lifecycle status at the time of recording.
        validation_results    : Dictionary of validator names → pass/fail/message.
        branch_name           : Created fix branch name (e.g. 'ai-fix/abc123').
        commit_sha            : SHA of the commit that applied the patch.
        pr_number             : Number of the fix Pull Request created on GitHub.
        pr_url                : Web URL of the fix Pull Request.
        post_fix_review_id    : Phase 7 PersistedReview ID of the re-review run
                                on the fix PR (populated in Stage 8.15).
        original_issue_resolved : True  — Phase 6 re-review no longer finds the issue.
                                  False — Issue persists in the re-review.
                                  None  — Verification not yet run / inconclusive.
        new_issues_detected   : True if Phase 6 re-review found NEW issues that
                                were not in the original review.
        error_code            : Stable machine-readable error identifier when
                                status is FAILED (e.g. 'PATCH_VALIDATION_FAILED').
        created_at            : UTC timestamp of result record creation.
        updated_at            : UTC timestamp of last update.
    """

    fix_request_id: str = Field(
        ...,
        min_length=1,
        description="References the parent FixRequest.id.",
    )
    status: FixStatus = Field(
        ...,
        description="Final lifecycle status at time of recording.",
    )
    validation_results: dict[str, str] = Field(
        default_factory=dict,
        description="Validator name → 'passed' | 'failed: <reason>'.",
    )
    branch_name: Optional[str] = Field(
        default=None,
        description="Created fix branch name (e.g. 'ai-fix/abc123').",
    )
    commit_sha: Optional[str] = Field(
        default=None,
        description="Git SHA of the commit that applied the patch.",
    )
    pr_number: Optional[int] = Field(
        default=None,
        ge=1,
        description="Fix Pull Request number on GitHub.",
    )
    pr_url: Optional[str] = Field(
        default=None,
        description="Web URL of the fix Pull Request.",
    )
    post_fix_review_id: Optional[str] = Field(
        default=None,
        description="Phase 7 PersistedReview ID of the re-review on the fix PR.",
    )
    original_issue_resolved: Optional[bool] = Field(
        default=None,
        description=(
            "True=resolved, False=still present, None=not yet verified/inconclusive."
        ),
    )
    new_issues_detected: bool = Field(
        default=False,
        description="True if the re-review found regressions not in the original.",
    )
    error_code: Optional[str] = Field(
        default=None,
        description="Stable machine-readable error code when status=FAILED.",
    )
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="UTC timestamp of record creation.",
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="UTC timestamp of last update.",
    )

    model_config = {
        "use_enum_values": True,
        "populate_by_name": True,
    }
