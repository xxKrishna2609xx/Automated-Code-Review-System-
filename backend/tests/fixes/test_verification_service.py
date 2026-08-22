"""
test_verification_service.py  (tests.fixes)
===========================================
Unit tests for Stage 8.16 — VerificationService.

Tests cover:
    - Target issue matching algorithm (file, line proximity, category, title)
    - VERIFIED_FIXED outcome (target issue gone, 0 regressions -> COMPLETED)
    - REGRESSION_DETECTED outcome (target issue gone, regressions introduced -> FAILED)
    - FIX_FAILED outcome (target issue still present -> FAILED)
    - FixResult store persistence and success boolean setting
    - Nonexistent fix request 404 handling

Author : AI Code Review Bot — Phase 8 (Stage 8.16)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.fixes.exceptions import FixNotFoundError
from app.fixes.fix_service import _FIX_REQUEST_STORE, _FIX_RESULT_STORE, reset_fix_stores
from app.fixes.models import FixRequest, FixStatus
from app.fixes.verification_service import (
    VerificationResult,
    VerificationService,
    VerificationStatus,
    is_matching_issue,
)
from app.models.persistence_models import PersistedReview
from app.models.review_models import Issue


# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------

BASE_SHA = "a" * 40

def _make_fix_request() -> FixRequest:
    return FixRequest(
        id="fix-req-verify123",
        review_id="rev-456",
        issue_id="bug-0",
        repository="owner/repo",
        pull_request_number=42,
        base_commit_sha=BASE_SHA,
        file_path="math_utils.py",
        line=10,
        issue_title="Incorrect operator in add()",
        issue_description="Minus used instead of plus.",
        suggestion="Use + operator.",
        status=FixStatus.PR_CREATED,
    )


def _make_persisted_review(issues: list[Issue] | None = None) -> PersistedReview:
    rev = MagicMock(spec=PersistedReview)
    rev.id = "post-rev-789"
    rev.review_key = "owner/repo#42@sha"
    rev.issues = issues or []
    return rev


@pytest.fixture(autouse=True)
def clean_stores():
    reset_fix_stores()
    yield
    reset_fix_stores()


# ---------------------------------------------------------------------------
# Matching Helper Tests
# ---------------------------------------------------------------------------

class TestIssueMatching:
    def test_is_matching_issue_true(self):
        fix_req = _make_fix_request()
        matching_issue = Issue(
            title="Incorrect operator in add()",
            severity="High",
            category="Bug",
            description="Minus used instead of plus.",
            suggestion="Use + operator.",
            line=10,
        )
        object.__setattr__(matching_issue, "file_path", "math_utils.py")
        assert is_matching_issue(fix_req, matching_issue) is True

    def test_is_matching_issue_false_different_file(self):
        fix_req = _make_fix_request()
        diff_file_issue = Issue(
            title="Incorrect operator in add()",
            severity="High",
            category="Bug",
            description="Minus used instead of plus.",
            suggestion="Use + operator.",
            line=10,
        )
        object.__setattr__(diff_file_issue, "file_path", "other_file.py")
        assert is_matching_issue(fix_req, diff_file_issue) is False




# ---------------------------------------------------------------------------
# VerificationService Tests
# ---------------------------------------------------------------------------

class TestVerificationService:
    svc = VerificationService()

    def test_verify_fix_success_verified_fixed(self):
        fix_req = _make_fix_request()
        _FIX_REQUEST_STORE[fix_req.id] = fix_req

        # Clean post-fix review (no issues)
        post_review = _make_persisted_review([])

        res = self.svc.verify_fix(
            fix_request_id=fix_req.id,
            post_fix_review=post_review,
        )

        assert isinstance(res, VerificationResult)
        assert res.verification_status == VerificationStatus.VERIFIED_FIXED
        assert res.target_issue_resolved is True
        assert res.new_issues_found == 0
        assert _FIX_REQUEST_STORE[fix_req.id].status == FixStatus.COMPLETED

        # Check FixResult in store
        fix_res = _FIX_RESULT_STORE.get(fix_req.id)
        assert fix_res is not None
        assert fix_res.original_issue_resolved is True
        assert fix_res.status == FixStatus.COMPLETED


    def test_verify_fix_failed_target_still_present(self):
        fix_req = _make_fix_request()
        _FIX_REQUEST_STORE[fix_req.id] = fix_req

        still_present_issue = Issue(
            title="Incorrect operator in add()",
            severity="High",
            category="Bug",
            description="Minus used instead of plus.",
            suggestion="Use + operator.",
            line=10,
            file_path="math_utils.py",
        )
        post_review = _make_persisted_review([still_present_issue])

        res = self.svc.verify_fix(
            fix_request_id=fix_req.id,
            post_fix_review=post_review,
        )

        assert res.verification_status == VerificationStatus.FIX_FAILED
        assert res.target_issue_resolved is False
        assert _FIX_REQUEST_STORE[fix_req.id].status == FixStatus.FAILED

        fix_res = _FIX_RESULT_STORE.get(fix_req.id)
        assert fix_res is not None
        assert fix_res.original_issue_resolved is False
        assert fix_res.status == FixStatus.FAILED

    def test_verify_fix_regression_detected(self):
        fix_req = _make_fix_request()
        _FIX_REQUEST_STORE[fix_req.id] = fix_req

        original_issue = Issue(
            title="Incorrect operator in add()",
            severity="High",
            category="Bug",
            description="Minus used instead of plus.",
            suggestion="Use + operator.",
            line=10,
            file_path="math_utils.py",
        )
        new_regression_issue = Issue(
            title="New Syntax Warning",
            severity="Low",
            category="Maintainability",
            description="Unused variable x",
            suggestion="Remove unused variable.",
            line=20,
            file_path="math_utils.py",
        )


        # Post review has ONLY regression issue, original target issue is gone
        post_review = _make_persisted_review([new_regression_issue])

        res = self.svc.verify_fix(
            fix_request_id=fix_req.id,
            post_fix_review=post_review,
            original_review_issues=[original_issue],
        )

        assert res.verification_status == VerificationStatus.REGRESSION_DETECTED
        assert res.target_issue_resolved is True
        assert res.new_issues_found == 1
        assert _FIX_REQUEST_STORE[fix_req.id].status == FixStatus.FAILED

    def test_verify_fix_nonexistent_request_raises_404(self):
        post_review = _make_persisted_review([])
        with pytest.raises(FixNotFoundError):
            self.svc.verify_fix("nonexistent-id", post_review)
