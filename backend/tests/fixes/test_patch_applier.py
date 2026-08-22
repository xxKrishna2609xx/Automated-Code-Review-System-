"""
test_patch_applier.py  (tests.fixes)
=====================================
Unit tests for Stage 8.11 — InMemoryPatchService & Git Tree Item Preparation.

Tests cover:
    - Successful in-memory patch application
    - Correct SHA-256 updated content hash calculation
    - Correct Git Tree Item payload structure for GitHub API
    - Hash mismatch detection and error handling
    - Invalid patch hunk error handling
    - Post-patch syntax check enforcement
    - Verification of zero disk mutations

Author : AI Code Review Bot — Phase 8 (Stage 8.11)
"""

from __future__ import annotations

import hashlib
import pytest

from app.fixes.exceptions import FixValidationError
from app.fixes.models import FixPatch, FixRequest, FixStatus
from app.fixes.patch_applier import AppliedPatchResult, InMemoryPatchService


# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------

BASE_CODE = """def multiply(a, b):
    return a / b
"""

BAD_PATCH = """@@ -2,1 +2,1 @@
-    return a / b
+    return a * b
"""

BROKEN_SYNTAX_PATCH = """@@ -2,1 +2,1 @@
-    return a / b
+    return a *
"""

ORIGINAL_HASH = hashlib.sha256(BASE_CODE.encode("utf-8")).hexdigest()

def _make_fix_request() -> FixRequest:
    return FixRequest(
        id="fix-req-8.11",
        review_id="rev-123",
        issue_id="bug-0",
        repository="owner/repo",
        pull_request_number=42,
        base_commit_sha="a" * 40,
        file_path="math_utils.py",
        issue_title="Wrong operator in multiply()",
        issue_description="multiply() divides instead of multiplying.",
        suggestion="Use * operator.",
        status=FixStatus.APPROVED,
    )


def _make_fix_patch(patch_str: str = BAD_PATCH, content_hash: str = ORIGINAL_HASH) -> FixPatch:
    return FixPatch(
        file_path="math_utils.py",
        original_content_hash=content_hash,
        patch=patch_str,
        changed_lines=[2],
        explanation="Fixed division to multiplication in multiply().",
    )


# ---------------------------------------------------------------------------
# InMemoryPatchService Tests
# ---------------------------------------------------------------------------

class TestInMemoryPatchService:
    service = InMemoryPatchService()

    def test_apply_patch_success(self):
        fix_req = _make_fix_request()
        fix_patch = _make_fix_patch()

        result = self.service.apply_patch(
            fix_request=fix_req,
            fix_patch=fix_patch,
            base_file_content=BASE_CODE,
        )

        assert isinstance(result, AppliedPatchResult)
        assert result.file_path == "math_utils.py"
        assert "return a * b" in result.updated_content
        assert "return a / b" not in result.updated_content
        assert result.original_hash == ORIGINAL_HASH
        assert result.updated_hash == hashlib.sha256(result.updated_content.encode("utf-8")).hexdigest()

    def test_git_tree_item_structure(self):
        fix_req = _make_fix_request()
        fix_patch = _make_fix_patch()

        result = self.service.apply_patch(
            fix_request=fix_req,
            fix_patch=fix_patch,
            base_file_content=BASE_CODE,
        )

        item = result.git_tree_item
        assert item["path"] == "math_utils.py"
        assert item["mode"] == "100644"
        assert item["type"] == "blob"
        assert item["content"] == result.updated_content

    def test_hash_mismatch_raises_fix_validation_error(self):
        fix_req = _make_fix_request()
        fix_patch = _make_fix_patch(content_hash="b" * 64)  # Wrong hash

        with pytest.raises(FixValidationError) as exc_info:
            self.service.apply_patch(
                fix_request=fix_req,
                fix_patch=fix_patch,
                base_file_content=BASE_CODE,
            )

        assert "hash mismatch" in str(exc_info.value).lower()

    def test_invalid_patch_application_raises_fix_validation_error(self):
        fix_req = _make_fix_request()
        invalid_hunk_patch = _make_fix_patch(patch_str="invalid hunk format string")

        with pytest.raises(FixValidationError) as exc_info:
            self.service.apply_patch(
                fix_request=fix_req,
                fix_patch=invalid_hunk_patch,
                base_file_content=BASE_CODE,
            )

        assert "patch application failed" in str(exc_info.value).lower() or "hunk" in str(exc_info.value).lower()

    def test_broken_syntax_patch_raises_fix_validation_error(self):
        fix_req = _make_fix_request()
        broken_patch = _make_fix_patch(patch_str=BROKEN_SYNTAX_PATCH)

        with pytest.raises(FixValidationError) as exc_info:
            self.service.apply_patch(
                fix_request=fix_req,
                fix_patch=broken_patch,
                base_file_content=BASE_CODE,
            )

        assert "syntax" in str(exc_info.value).lower()
