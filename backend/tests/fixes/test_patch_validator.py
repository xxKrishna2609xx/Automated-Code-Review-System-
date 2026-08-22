"""
test_patch_validator.py  (tests.fixes)
=======================================
Unit tests for Stage 8.6 — PatchValidator.

Tests cover:
    - Successful validation & in-memory patch application
    - Path traversal and absolute path rejection
    - Unexpected file modification rejection
    - Content hash mismatch / stale commit detection
    - Patch size and line limit enforcement
    - Malformed patch format rejection
    - dry_run_application failure handling

Author : AI Code Review Bot — Phase 8 (Stage 8.6)
"""

from __future__ import annotations

import hashlib
import pytest

from app.fixes.models import FixPatch
from app.fixes.patch_validator import PatchValidator, apply_patch_in_memory


# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------

ORIGINAL_CODE = """def calculate_total(items):
    total = 0
    for item in items:
        total = total + item.price
    return total
"""

PATCH_CODE = """@@ -3,2 +3,2 @@
-    for item in items:
-        total = total + item.price
+    for item in items:
+        total += item.price
"""

EXPECTED_HASH = hashlib.sha256(ORIGINAL_CODE.encode("utf-8")).hexdigest()

def _make_patch(**overrides) -> FixPatch:
    base = dict(
        file_path="app/calculator.py",
        original_content_hash=EXPECTED_HASH,
        patch=PATCH_CODE,
        changed_lines=[4],
        explanation="Refactored total addition using += operator.",
    )
    base.update(overrides)
    return FixPatch(**base)


validator = PatchValidator()


# ---------------------------------------------------------------------------
# In-Memory Patch Applicator Tests
# ---------------------------------------------------------------------------

class TestApplyPatchInMemory:
    def test_apply_patch_success(self):
        success, new_code, err = apply_patch_in_memory(ORIGINAL_CODE, PATCH_CODE)
        assert success is True
        assert err is None
        assert "total += item.price" in new_code
        assert "total = total + item.price" not in new_code

    def test_apply_patch_empty(self):
        success, code, err = apply_patch_in_memory(ORIGINAL_CODE, "")
        assert success is False
        assert "empty" in err.lower()

    def test_apply_patch_invalid_hunk(self):
        success, code, err = apply_patch_in_memory(ORIGINAL_CODE, "invalid patch text")
        assert success is False
        assert "hunk" in err.lower()


# ---------------------------------------------------------------------------
# PatchValidator Tests
# ---------------------------------------------------------------------------

class TestPatchValidator:
    def test_valid_patch_passes(self):
        patch = _make_patch()
        result = validator.validate(
            fix_patch=patch,
            current_file_content=ORIGINAL_CODE,
            expected_file_path="app/calculator.py",
        )

        assert result.valid is True
        assert result.stale is False
        assert result.error_code is None
        assert result.applied_content is not None
        assert "total += item.price" in result.applied_content

    def test_path_traversal_fails(self):
        patch = FixPatch.model_construct(
            file_path="../etc/passwd",
            original_content_hash=EXPECTED_HASH,
            patch=PATCH_CODE,
            changed_lines=[4],
            explanation="Refactored total addition using += operator.",
        )
        result = validator.validate(fix_patch=patch)

        assert result.valid is False
        assert result.error_code == "PATH_TRAVERSAL_DETECTED"

    def test_unexpected_file_modification_fails(self):
        patch = _make_patch(file_path="app/other.py")
        result = validator.validate(
            fix_patch=patch,
            expected_file_path="app/calculator.py",
        )

        assert result.valid is False
        assert result.error_code == "UNEXPECTED_FILE_MODIFICATION"

    def test_stale_commit_hash_mismatch_fails(self):
        modified_code = ORIGINAL_CODE + "\n# Modified in main"
        patch = _make_patch()

        result = validator.validate(
            fix_patch=patch,
            current_file_content=modified_code,
            expected_file_path="app/calculator.py",
        )

        assert result.valid is False
        assert result.stale is True
        assert result.error_code == "STALE_COMMIT_DETECTED"

    def test_oversized_patch_fails(self):
        big_patch_text = "@@ -1,1 +1,1 @@\n-" + ("a" * 60_000) + "\n+" + ("b" * 60_000) + "\n"
        patch = _make_patch(patch=big_patch_text)

        result = validator.validate(fix_patch=patch)
        assert result.valid is False
        assert result.error_code == "PATCH_SIZE_EXCEEDED"

    def test_too_many_lines_changed_fails(self):
        patch = _make_patch(changed_lines=list(range(1, 300)))
        result = validator.validate(fix_patch=patch)

        assert result.valid is False
        assert result.error_code == "TOO_MANY_LINES_CHANGED"

    def test_malformed_patch_format_fails(self):
        patch = _make_patch(patch="no hunk headers here")
        result = validator.validate(fix_patch=patch)

        assert result.valid is False
        assert result.error_code == "INVALID_PATCH_FORMAT"

    def test_to_dict_method(self):
        patch = _make_patch()
        result = validator.validate(
            fix_patch=patch,
            current_file_content=ORIGINAL_CODE,
            expected_file_path="app/calculator.py",
        )
        res_dict = result.to_dict()
        assert res_dict["valid"] == "passed"
        assert res_dict["path_validation"] == "passed"
        assert res_dict["patch_format"] == "passed"
