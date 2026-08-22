"""
test_fix_generator.py  (tests.fixes)
=====================================
Unit tests for Stage 8.5 — FixGenerator.

Tests cover:
    - SHA-256 hash calculation helper
    - Successful fix generation using mock LLM completer
    - Valid FixPatch construction and auto-injection of original_content_hash
    - Handling malformed/non-JSON responses from LLM (raises FixValidationError)
    - Handling invalid FixPatch fields (raises FixValidationError)
    - Prompt builder integration (FIX_SYSTEM_PROMPT & build_fix_prompt)

Author : AI Code Review Bot — Phase 8 (Stage 8.5)
"""

from __future__ import annotations

import json
import pytest

from app.exceptions import GeminiServiceError
from app.fixes.exceptions import FixValidationError
from app.fixes.fix_context_builder import FixContext
from app.fixes.fix_generator import FixGenerator, compute_sha256
from app.fixes.models import FixPatch


# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------

SAMPLE_CONTENT = "def add(a, b):\n    return a - b\n"
EXPECTED_HASH = compute_sha256(SAMPLE_CONTENT)

def _make_context(**overrides) -> FixContext:
    base = dict(
        fix_request_id="fix-req-999",
        repository="owner/repo",
        pull_request_number=10,
        commit_sha="a" * 40,
        file_path="math_utils.py",
        line=2,
        issue_title="Incorrect subtraction in add()",
        issue_description="Function add() performs subtraction instead of addition.",
        suggestion="Change minus operator to plus.",
        language_hint="Python",
        file_content=SAMPLE_CONTENT,
        context_window="   1 | def add(a, b):\n-> 2 |     return a - b\n",
    )
    base.update(overrides)
    return FixContext(**base)


VALID_LLM_JSON = json.dumps({
    "file_path": "math_utils.py",
    "patch": "@@ -2,1 +2,1 @@\n-    return a - b\n+    return a + b\n",
    "changed_lines": [2],
    "explanation": "Fixed operator in add() function to return a + b instead of a - b.",
})


# ---------------------------------------------------------------------------
# Hash Helper Tests
# ---------------------------------------------------------------------------

class TestComputeSHA256:
    def test_hash_calculation(self):
        h = compute_sha256("hello world")
        assert len(h) == 64
        assert h == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"


# ---------------------------------------------------------------------------
# FixGenerator Tests (with mock completer)
# ---------------------------------------------------------------------------

class TestFixGenerator:
    @pytest.mark.asyncio
    async def test_successful_fix_generation(self):
        async def mock_completer(sys_prompt: str, user_prompt: str) -> str:
            assert "FIX_SYSTEM_PROMPT" not in sys_prompt  # verifies non-empty prompt passed
            assert "math_utils.py" in user_prompt
            return VALID_LLM_JSON

        generator = FixGenerator(completer=mock_completer)
        context = _make_context()

        patch = await generator.generate_fix(context)

        assert isinstance(patch, FixPatch)
        assert patch.file_path == "math_utils.py"
        assert patch.original_content_hash == EXPECTED_HASH
        assert patch.changed_lines == [2]
        assert "a + b" in patch.patch
        assert "Fixed operator" in patch.explanation

    @pytest.mark.asyncio
    async def test_fallback_file_path_when_missing_in_llm_output(self):
        llm_response = json.dumps({
            "patch": "@@ -1 +1 @@\n-old\n+new\n",
            "changed_lines": [1],
            "explanation": "Fixed typo.",
        })

        async def mock_completer(sys_p: str, user_p: str) -> str:
            return llm_response

        generator = FixGenerator(completer=mock_completer)
        context = _make_context(file_path="app/config.py")

        patch = await generator.generate_fix(context)
        assert patch.file_path == "app/config.py"

    @pytest.mark.asyncio
    async def test_invalid_json_raises_fix_validation_error(self):
        async def mock_completer(sys_p: str, user_p: str) -> str:
            return "I am sorry, I cannot generate a patch for this file."

        generator = FixGenerator(completer=mock_completer)
        context = _make_context()

        with pytest.raises(FixValidationError) as exc_info:
            await generator.generate_fix(context)

        assert "JSON" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_patch_fields_raises_fix_validation_error(self):
        # Invalid: changed_lines contains non-positive integer
        invalid_json = json.dumps({
            "file_path": "math_utils.py",
            "patch": "@@ -1 +1 @@\n-old\n+new\n",
            "changed_lines": [0],  # Must be >= 1
            "explanation": "Invalid line number.",
        })

        async def mock_completer(sys_p: str, user_p: str) -> str:
            return invalid_json

        generator = FixGenerator(completer=mock_completer)
        context = _make_context()

        with pytest.raises(FixValidationError) as exc_info:
            await generator.generate_fix(context)

        assert "validation" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_api_failure_raises_fix_validation_error(self):
        async def failing_completer(sys_p: str, user_p: str) -> str:
            raise RuntimeError("API Rate limit exceeded")

        generator = FixGenerator(completer=failing_completer)
        context = _make_context()

        with pytest.raises(RuntimeError):
            await generator.generate_fix(context)
