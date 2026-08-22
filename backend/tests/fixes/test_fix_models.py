"""
test_fix_models.py  (tests.fixes)
==================================
Unit tests for Phase 8 Fix Domain Models (Stage 8.1).

Tests cover:
    - Valid model instantiation for all four types
    - Invalid / unknown FixStatus rejection
    - Missing required fields (issue_id, review_id, etc.)
    - Invalid repository identifiers (empty, wrong format)
    - Unsafe file paths (path traversal, absolute paths)
    - base_commit_sha format validation
    - original_content_hash format validation
    - FixStatus state set completeness (all 14 states present)
    - FixResult.original_issue_resolved three-state semantics
    - Serialization → deserialization round-trip

Author : AI Code Review Bot — Phase 8 (Stage 8.1)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.fixes.models import FixPatch, FixRequest, FixResult, FixStatus


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

VALID_SHA = "a" * 40          # 40-char lowercase hex
VALID_HASH = "b" * 64         # 64-char lowercase hex


def _valid_fix_request(**overrides) -> dict:
    base = dict(
        review_id="64f1a2b3c4d5e6f7a8b9c0d1",
        issue_id="security-0",
        repository="owner/repo",
        pull_request_number=42,
        base_commit_sha=VALID_SHA,
        file_path="app/database.py",
        issue_title="SQL Injection Risk",
        issue_description="The query is concatenated directly from user input without parameterization.",
        suggestion="Use parameterized queries instead of string concatenation.",
        created_by="dev_user",
    )
    base.update(overrides)
    return base


def _valid_fix_patch(**overrides) -> dict:
    base = dict(
        file_path="app/database.py",
        original_content_hash=VALID_HASH,
        patch="@@ -42,1 +42,1 @@\n-query = f\"SELECT * FROM users WHERE id={user_id}\"\n+query = \"SELECT * FROM users WHERE id=%s\"\n",
        changed_lines=[42],
        explanation="Replaced string-formatted SQL with a parameterized query to prevent SQL injection.",
    )
    base.update(overrides)
    return base


def _valid_fix_result(**overrides) -> dict:
    base = dict(
        fix_request_id="fix-uuid-abc123",
        status=FixStatus.COMPLETED,
    )
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# FixStatus
# ---------------------------------------------------------------------------


class TestFixStatus:
    def test_all_fourteen_states_present(self):
        expected = {
            "REQUESTED", "GENERATING", "GENERATED", "VALIDATING",
            "READY_FOR_APPROVAL", "APPROVED", "APPLYING", "COMMITTED",
            "PR_CREATED", "REVIEWING", "COMPLETED",
            "REJECTED", "FAILED", "STALE",
        }
        actual = {s.value for s in FixStatus}
        assert actual == expected, f"Missing states: {expected - actual}"

    def test_valid_status_from_string(self):
        assert FixStatus("REQUESTED") == FixStatus.REQUESTED
        assert FixStatus("COMPLETED") == FixStatus.COMPLETED
        assert FixStatus("STALE") == FixStatus.STALE

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError):
            FixStatus("PENDING")  # PENDING belongs to ReviewStatus, not FixStatus

    def test_fix_status_is_string_enum(self):
        assert isinstance(FixStatus.REQUESTED, str)


# ---------------------------------------------------------------------------
# FixRequest — valid construction
# ---------------------------------------------------------------------------


class TestFixRequestValid:
    def test_minimal_valid(self):
        fr = FixRequest(**_valid_fix_request())
        assert fr.review_id == "64f1a2b3c4d5e6f7a8b9c0d1"
        assert fr.issue_id == "security-0"
        assert fr.repository == "owner/repo"
        assert fr.pull_request_number == 42
        assert fr.status == FixStatus.REQUESTED.value

    def test_optional_fields_default_to_none_or_sentinel(self):
        fr = FixRequest(**_valid_fix_request())
        assert fr.id is None
        assert fr.line is None
        assert fr.repository_id is None

    def test_created_by_default(self):
        data = _valid_fix_request()
        data.pop("created_by", None)
        fr = FixRequest(**data)
        assert fr.created_by == "system"

    def test_sha_normalised_to_lowercase(self):
        data = _valid_fix_request(base_commit_sha="ABCD1234" * 5)
        fr = FixRequest(**data)
        assert fr.base_commit_sha == fr.base_commit_sha.lower()

    def test_timestamps_are_utc(self):
        import datetime
        fr = FixRequest(**_valid_fix_request())
        assert fr.created_at.tzinfo is not None
        assert fr.updated_at.tzinfo is not None


# ---------------------------------------------------------------------------
# FixRequest — missing required fields
# ---------------------------------------------------------------------------


class TestFixRequestMissingFields:
    def test_missing_review_id(self):
        data = _valid_fix_request()
        del data["review_id"]
        with pytest.raises(ValidationError) as exc_info:
            FixRequest(**data)
        assert "review_id" in str(exc_info.value)

    def test_missing_issue_id(self):
        data = _valid_fix_request()
        del data["issue_id"]
        with pytest.raises(ValidationError) as exc_info:
            FixRequest(**data)
        assert "issue_id" in str(exc_info.value)

    def test_missing_issue_title(self):
        data = _valid_fix_request()
        del data["issue_title"]
        with pytest.raises(ValidationError):
            FixRequest(**data)

    def test_missing_repository(self):
        data = _valid_fix_request()
        del data["repository"]
        with pytest.raises(ValidationError):
            FixRequest(**data)

    def test_missing_base_commit_sha(self):
        data = _valid_fix_request()
        del data["base_commit_sha"]
        with pytest.raises(ValidationError):
            FixRequest(**data)


# ---------------------------------------------------------------------------
# FixRequest — invalid repository identifiers
# ---------------------------------------------------------------------------


class TestFixRequestInvalidRepository:
    def test_empty_repository(self):
        with pytest.raises(ValidationError) as exc_info:
            FixRequest(**_valid_fix_request(repository=""))
        assert "empty" in str(exc_info.value).lower() or "repository" in str(exc_info.value).lower()

    def test_repository_without_slash(self):
        with pytest.raises(ValidationError):
            FixRequest(**_valid_fix_request(repository="owner-only"))

    def test_repository_with_double_slash(self):
        with pytest.raises(ValidationError):
            FixRequest(**_valid_fix_request(repository="owner//repo"))

    def test_repository_with_spaces(self):
        with pytest.raises(ValidationError):
            FixRequest(**_valid_fix_request(repository="my owner/my repo"))

    def test_repository_valid_formats(self):
        # Various valid slug formats
        for slug in ["owner/repo", "My-Org/My.Repo", "user_123/project-x"]:
            fr = FixRequest(**_valid_fix_request(repository=slug))
            assert fr.repository == slug


# ---------------------------------------------------------------------------
# FixRequest — unsafe file paths
# ---------------------------------------------------------------------------


class TestFixRequestUnsafeFilePaths:
    def test_path_traversal_dotdot_forward(self):
        with pytest.raises(ValidationError) as exc_info:
            FixRequest(**_valid_fix_request(file_path="../etc/passwd"))
        assert "traversal" in str(exc_info.value).lower() or "unsafe" in str(exc_info.value).lower()

    def test_path_traversal_dotdot_back(self):
        with pytest.raises(ValidationError):
            FixRequest(**_valid_fix_request(file_path="..\\windows\\system32"))

    def test_absolute_path_unix(self):
        with pytest.raises(ValidationError) as exc_info:
            FixRequest(**_valid_fix_request(file_path="/etc/passwd"))
        assert "absolute" in str(exc_info.value).lower()

    def test_absolute_path_windows(self):
        with pytest.raises(ValidationError):
            FixRequest(**_valid_fix_request(file_path="C:\\secret.py"))

    def test_null_byte_injection(self):
        with pytest.raises(ValidationError):
            FixRequest(**_valid_fix_request(file_path="app/\x00evil.py"))

    def test_valid_relative_paths(self):
        for path in ["app/database.py", "src/main/java/App.java", "tests/test_utils.py"]:
            fr = FixRequest(**_valid_fix_request(file_path=path))
            assert fr.file_path == path


# ---------------------------------------------------------------------------
# FixRequest — base_commit_sha validation
# ---------------------------------------------------------------------------


class TestFixRequestCommitSha:
    def test_valid_full_sha(self):
        fr = FixRequest(**_valid_fix_request(base_commit_sha="a" * 40))
        assert len(fr.base_commit_sha) == 40

    def test_valid_short_sha(self):
        fr = FixRequest(**_valid_fix_request(base_commit_sha="abc1234"))
        assert fr.base_commit_sha == "abc1234"

    def test_invalid_sha_too_short(self):
        with pytest.raises(ValidationError):
            FixRequest(**_valid_fix_request(base_commit_sha="abc12"))  # 5 chars < 7

    def test_invalid_sha_non_hex(self):
        with pytest.raises(ValidationError):
            FixRequest(**_valid_fix_request(base_commit_sha="gggggggggggggggggggggggggggggggggggggggg"))

    def test_sha_coerced_to_lowercase(self):
        fr = FixRequest(**_valid_fix_request(base_commit_sha="ABCDEF1234567"))
        assert fr.base_commit_sha == "abcdef1234567"


# ---------------------------------------------------------------------------
# FixPatch — valid construction
# ---------------------------------------------------------------------------


class TestFixPatchValid:
    def test_minimal_valid(self):
        fp = FixPatch(**_valid_fix_patch())
        assert fp.file_path == "app/database.py"
        assert len(fp.original_content_hash) == 64
        assert fp.changed_lines == [42]

    def test_empty_changed_lines_allowed(self):
        data = _valid_fix_patch(changed_lines=[])
        fp = FixPatch(**data)
        assert fp.changed_lines == []

    def test_hash_coerced_to_lowercase(self):
        data = _valid_fix_patch(original_content_hash="B" * 64)
        fp = FixPatch(**data)
        assert fp.original_content_hash == "b" * 64


# ---------------------------------------------------------------------------
# FixPatch — invalid paths and hashes
# ---------------------------------------------------------------------------


class TestFixPatchValidation:
    def test_path_traversal_rejected(self):
        with pytest.raises(ValidationError):
            FixPatch(**_valid_fix_patch(file_path="../malicious.py"))

    def test_invalid_hash_wrong_length(self):
        with pytest.raises(ValidationError):
            FixPatch(**_valid_fix_patch(original_content_hash="abc123"))

    def test_invalid_hash_non_hex(self):
        with pytest.raises(ValidationError):
            FixPatch(**_valid_fix_patch(original_content_hash="z" * 64))

    def test_changed_lines_must_be_positive(self):
        with pytest.raises(ValidationError):
            FixPatch(**_valid_fix_patch(changed_lines=[0]))  # 0 is not 1-based

    def test_changed_lines_must_be_integers(self):
        with pytest.raises(ValidationError):
            FixPatch(**_valid_fix_patch(changed_lines=["line_42"]))


# ---------------------------------------------------------------------------
# FixResult — three-state original_issue_resolved
# ---------------------------------------------------------------------------


class TestFixResultResolutionStates:
    def test_resolved_true(self):
        result = FixResult(**_valid_fix_result(original_issue_resolved=True))
        assert result.original_issue_resolved is True

    def test_still_present_false(self):
        result = FixResult(**_valid_fix_result(original_issue_resolved=False))
        assert result.original_issue_resolved is False

    def test_not_yet_verified_none(self):
        result = FixResult(**_valid_fix_result())
        assert result.original_issue_resolved is None

    def test_new_issues_defaults_false(self):
        result = FixResult(**_valid_fix_result())
        assert result.new_issues_detected is False

    def test_new_issues_can_be_true(self):
        result = FixResult(**_valid_fix_result(new_issues_detected=True))
        assert result.new_issues_detected is True


# ---------------------------------------------------------------------------
# FixResult — optional GitHub fields
# ---------------------------------------------------------------------------


class TestFixResultOptionalFields:
    def test_defaults_are_none(self):
        result = FixResult(**_valid_fix_result())
        assert result.branch_name is None
        assert result.commit_sha is None
        assert result.pr_number is None
        assert result.pr_url is None
        assert result.post_fix_review_id is None
        assert result.error_code is None

    def test_pr_number_must_be_positive(self):
        with pytest.raises(ValidationError):
            FixResult(**_valid_fix_result(pr_number=0))

    def test_validation_results_dict(self):
        vr = {"path_validator": "passed", "hash_validator": "passed", "syntax_validator": "passed"}
        result = FixResult(**_valid_fix_result(validation_results=vr))
        assert result.validation_results["path_validator"] == "passed"


# ---------------------------------------------------------------------------
# Serialization / deserialization round-trip
# ---------------------------------------------------------------------------


class TestRoundTrip:
    def test_fix_request_round_trip(self):
        original = FixRequest(**_valid_fix_request())
        serialized = original.model_dump(mode="json")
        restored = FixRequest(**serialized)
        assert restored.review_id == original.review_id
        assert restored.repository == original.repository
        assert restored.status == original.status

    def test_fix_patch_round_trip(self):
        original = FixPatch(**_valid_fix_patch())
        serialized = original.model_dump(mode="json")
        restored = FixPatch(**serialized)
        assert restored.file_path == original.file_path
        assert restored.original_content_hash == original.original_content_hash

    def test_fix_result_round_trip(self):
        original = FixResult(**_valid_fix_result(
            branch_name="ai-fix/abc123",
            commit_sha="abc" * 13 + "a",
            pr_number=99,
            original_issue_resolved=True,
        ))
        serialized = original.model_dump(mode="json")
        restored = FixResult(**serialized)
        assert restored.branch_name == original.branch_name
        assert restored.pr_number == original.pr_number
        assert restored.original_issue_resolved is True
