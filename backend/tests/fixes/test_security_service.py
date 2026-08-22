"""
test_security_service.py  (tests.fixes)
========================================
Unit tests for Stage 8.23 — FixSecurityService.

Tests cover:
    - Secret masking & prompt sanitization
    - Path traversal validation
    - Protected branch validation
    - Security audit event logging

Author : AI Code Review Bot — Phase 8 (Stage 8.23)
"""

from __future__ import annotations

import pytest

from app.fixes.exceptions import FixValidationError
from app.fixes.security_service import FixSecurityService


class TestFixSecurityService:
    def test_sanitize_llm_prompt_masks_github_pat(self):
        raw_prompt = "Here is my token: ghp_1234567890abcdefghijklmnopqrstuvwxyz and code"
        sanitized = FixSecurityService.sanitize_llm_prompt(raw_prompt)

        assert "ghp_1234567890" not in sanitized
        assert "[REDACTED_SECRET]" in sanitized
        assert "and code" in sanitized

    def test_sanitize_llm_prompt_masks_gemini_api_key(self):
        raw_prompt = "API_KEY = 'AIzaSyA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q'"
        sanitized = FixSecurityService.sanitize_llm_prompt(raw_prompt)

        assert "AIzaSy" not in sanitized
        assert "[REDACTED_SECRET]" in sanitized

    def test_validate_file_path_success(self):
        clean_path = FixSecurityService.validate_file_path("backend/app/main.py")
        assert clean_path == "backend/app/main.py"

    def test_validate_file_path_rejects_parent_traversal(self):
        with pytest.raises(FixValidationError, match="Path traversal detected"):
            FixSecurityService.validate_file_path("../../../etc/passwd")

    def test_validate_file_path_rejects_absolute_windows_path(self):
        with pytest.raises(FixValidationError, match="Path traversal detected"):
            FixSecurityService.validate_file_path("C:\\Windows\\System32\\config")

    def test_validate_target_branch_success(self):
        FixSecurityService.validate_target_branch("ai-fix/fix-12345")

    def test_validate_target_branch_rejects_main_and_master(self):
        with pytest.raises(FixValidationError, match="protected branch"):
            FixSecurityService.validate_target_branch("main")

        with pytest.raises(FixValidationError, match="protected branch"):
            FixSecurityService.validate_target_branch("master")

        with pytest.raises(FixValidationError, match="protected branch"):
            FixSecurityService.validate_target_branch("production")

    def test_log_audit_event_structure(self):
        audit = FixSecurityService.log_audit_event(
            event_name="APPROVAL_GRANTED",
            fix_request_id="fix-req-123",
            user_id="developer_alice",
            details={"branch": "ai-fix/fix-123"},
        )

        assert audit["event"] == "APPROVAL_GRANTED"
        assert audit["fix_request_id"] == "fix-req-123"
        assert audit["user_id"] == "developer_alice"
        assert audit["details"]["branch"] == "ai-fix/fix-123"
