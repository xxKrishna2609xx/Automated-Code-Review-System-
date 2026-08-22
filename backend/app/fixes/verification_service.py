"""
verification_service.py  (app.fixes)
=====================================
Stage 8.16 — Original Issue Verification Service.

Compares post-fix Phase 6 review findings against the original review issue
to verify whether the target finding was resolved and detect regression issues.

Design principles (Phase 8 spec §19):
    1. "Do not claim a fix worked until Phase 6 re-reviews it."
    2. Deterministic issue matching:
       - Match by target file_path + line proximity (±5 lines) + category + title text similarity.
    3. Verification Outcomes:
       - VERIFIED_FIXED: Original issue is resolved AND zero new regressions introduced -> FixStatus.COMPLETED.
       - REGRESSION_DETECTED: Original issue is resolved BUT new issues introduced -> FixStatus.FAILED.
       - FIX_FAILED: Original issue is STILL PRESENT in post-fix review -> FixStatus.FAILED.
    4. Produces a comprehensive FixResult audit payload.

Author : AI Code Review Bot — Phase 8 (Stage 8.16)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from app.fixes.exceptions import FixNotFoundError, FixStateError
from app.fixes.fix_service import _FIX_REQUEST_STORE, _FIX_RESULT_STORE
from app.fixes.models import FixRequest, FixResult, FixStatus
from app.models.persistence_models import PersistedReview
from app.models.review_models import Issue

logger = logging.getLogger(__name__)


class VerificationStatus(str, Enum):
    """Outcome status of post-fix issue verification."""

    VERIFIED_FIXED = "VERIFIED_FIXED"
    REGRESSION_DETECTED = "REGRESSION_DETECTED"
    FIX_FAILED = "FIX_FAILED"


@dataclass(frozen=True)
class VerificationResult:
    """Detailed result of issue verification comparing pre-fix and post-fix reviews.

    Attributes:
        fix_request_id       : Target FixRequest ID.
        verification_status  : Outcome enum (VERIFIED_FIXED, REGRESSION_DETECTED, FIX_FAILED).
        target_issue_resolved: True if target issue is no longer present in post-fix review.
        original_issue_id    : Target issue ID.
        new_issues_found     : Count of new findings in post-fix review.
        regressions          : List of new Issue objects raised in post-fix review.
        summary_message      : Readable summary message.
    """

    fix_request_id: str
    verification_status: VerificationStatus
    target_issue_resolved: bool
    original_issue_id: str
    new_issues_found: int = 0
    regressions: list[Issue] = field(default_factory=list)
    summary_message: str = ""


# ---------------------------------------------------------------------------
# Matching Helper Functions
# ---------------------------------------------------------------------------


def is_matching_issue(original_req: FixRequest, post_fix_issue: Issue) -> bool:
    """Determine if a post-fix issue matches the target original FixRequest finding.

    Matching criteria:
        1. File path match (exact or suffix match).
        2. Line proximity check: target line ± 5 lines (if line is present).
        3. Category or title match (case-insensitive substring overlap).
    """
    # File path match
    orig_path = (original_req.file_path or "").lower().strip()
    issue_path = (getattr(post_fix_issue, "file_path", None) or getattr(post_fix_issue, "path", None) or "").lower().strip()
    if orig_path and issue_path:
        if orig_path != issue_path and not orig_path.endswith(issue_path) and not issue_path.endswith(orig_path):
            return False


    # Line proximity check
    if original_req.line is not None and post_fix_issue.line is not None:
        if abs(original_req.line - post_fix_issue.line) > 5:
            return False

    # Title / Category similarity check
    orig_title = (original_req.issue_title or "").lower().strip()
    issue_title = (post_fix_issue.title or "").lower().strip()

    orig_category = (original_req.issue_id or "").split("-")[0].lower()
    issue_category = (post_fix_issue.category or "").lower().replace(" ", "")

    title_overlap = orig_title in issue_title or issue_title in orig_title
    category_overlap = orig_category in issue_category or issue_category in orig_category

    return title_overlap or category_overlap


# ---------------------------------------------------------------------------
# VerificationService
# ---------------------------------------------------------------------------


class VerificationService:
    """Verifies that an AI fix resolved the original issue without introducing regressions."""

    def verify_fix(
        self,
        fix_request_id: str,
        post_fix_review: PersistedReview,
        original_review_issues: Optional[list[Issue]] = None,
    ) -> VerificationResult:
        """Compare post-fix review against original FixRequest finding.

        Args:
            fix_request_id         : Unique FixRequest ID.
            post_fix_review        : PersistedReview object from Stage 8.15 post-fix review.
            original_review_issues : Optional list of original review issues for regression detection.

        Returns:
            VerificationResult detailing resolution status and regressions.

        Raises:
            FixNotFoundError : If FixRequest is not in store.
        """
        logger.info("Verifying fix resolution for fix request %s", fix_request_id)

        fix_req = _FIX_REQUEST_STORE.get(fix_request_id)
        if not fix_req:
            raise FixNotFoundError(f"Fix request '{fix_request_id}' was not found.")

        post_issues = post_fix_review.issues or []

        # ── 1. Check if target issue is still present ─────────────────
        matching_issues = [i for i in post_issues if is_matching_issue(fix_req, i)]
        target_resolved = len(matching_issues) == 0

        # ── 2. Identify new regression issues ─────────────────────────
        regressions: list[Issue] = []
        if original_review_issues:
            orig_titles = {(i.title or "").lower().strip() for i in original_review_issues}
            for post_issue in post_issues:
                if (post_issue.title or "").lower().strip() not in orig_titles and not is_matching_issue(fix_req, post_issue):
                    regressions.append(post_issue)
        elif not target_resolved:
            regressions = [i for i in post_issues if not is_matching_issue(fix_req, i)]

        # ── 3. Determine Final Verification Outcome ───────────────────
        if target_resolved and len(regressions) == 0:
            outcome = VerificationStatus.VERIFIED_FIXED
            new_status = FixStatus.COMPLETED
            msg = f"Fix request '{fix_request_id}' successfully verified. Target issue resolved with 0 regressions."
        elif target_resolved and len(regressions) > 0:
            outcome = VerificationStatus.REGRESSION_DETECTED
            new_status = FixStatus.FAILED
            msg = f"Fix request '{fix_request_id}' resolved target issue, but introduced {len(regressions)} new regression(s)."
        else:
            outcome = VerificationStatus.FIX_FAILED
            new_status = FixStatus.FAILED
            msg = f"Fix request '{fix_request_id}' failed verification. Target issue was still detected in post-fix review."

        # Update status in store
        fix_req.status = new_status
        _FIX_REQUEST_STORE[fix_req.id] = fix_req

        # Store FixResult DTO
        fix_res = FixResult(
            fix_request_id=fix_req.id,
            status=new_status,
            original_issue_resolved=target_resolved,
            new_issues_detected=(len(regressions) > 0),
            post_fix_review_id=getattr(post_fix_review, "id", None) or post_fix_review.review_key,
        )
        _FIX_RESULT_STORE[fix_req.id] = fix_res


        logger.info("Fix verification complete for %s: outcome=%s, status=%s", fix_req.id, outcome.value, new_status.value)

        return VerificationResult(
            fix_request_id=fix_req.id,
            verification_status=outcome,
            target_issue_resolved=target_resolved,
            original_issue_id=fix_req.issue_id,
            new_issues_found=len(regressions),
            regressions=regressions,
            summary_message=msg,
        )
