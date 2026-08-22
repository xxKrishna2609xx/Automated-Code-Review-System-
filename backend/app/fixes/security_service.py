"""
security_service.py  (app.fixes)
=================================
Stage 8.23 — Security Controls & Audit Logging Service.

Enforces non-negotiable Phase 8 safety invariants:
    1. Secret Masking        : Sanitizes credentials/keys before sending prompts to LLM.
    2. Path Traversal Guard  : Rejects arbitrary host file paths and parent path traversal.
    3. Protected Branch Guard: Enforces branch naming invariants (no main/master direct writes).
    4. Audit Logger          : Logs security events without leaking secrets.

Author : AI Code Review Bot — Phase 8 (Stage 8.23)
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from app.fixes.exceptions import FixValidationError

logger = logging.getLogger(__name__)

# Common secret regex patterns
SECRET_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9_]{36}"),  # GitHub Personal Access Token
    re.compile(r"github_pat_[A-Za-z0-9_]{82}"),  # GitHub Fine-grained PAT
    re.compile(r"AIzaSy[A-Za-z0-9_\-]{33}"),  # Google AI / Gemini Key
    re.compile(r"sk-[A-Za-z0-9]{32,}"),  # OpenAI / Generic API Key
    re.compile(r"(?i)(password|secret|bearer|token)\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{8,}[\"']?"),
]

PROTECTED_BRANCHES = {"main", "master", "develop", "production", "release", "staging"}


class FixSecurityService:
    """Provides security validation, secret masking, and audit logging for AI fixes."""

    @staticmethod
    def sanitize_llm_prompt(content: str) -> str:
        """Mask secrets, tokens, and sensitive credentials in code/prompt text.

        Args:
            content : Raw code string or prompt text.

        Returns:
            Sanitized string with sensitive tokens masked as '[REDACTED_SECRET]'.
        """
        if not content:
            return content

        sanitized = content
        for pattern in SECRET_PATTERNS:
            sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)

        return sanitized

    @staticmethod
    def validate_file_path(file_path: str) -> str:
        """Validate target file path against directory traversal attacks.

        Args:
            file_path : Candidate repository relative file path.

        Returns:
            Cleaned relative file path string.

        Raises:
            FixValidationError : If path contains traversal characters or absolute paths.
        """
        if not file_path or not file_path.strip():
            raise FixValidationError("File path cannot be empty.")

        cleaned = file_path.strip().replace("\\", "/")

        if (
            ".." in cleaned
            or cleaned.startswith("/")
            or cleaned.startswith("C:")
            or cleaned.startswith("D:")
            or "/../" in cleaned
        ):
            logger.warning("Path traversal attack blocked for path: %s", file_path)
            raise FixValidationError(f"Path traversal detected in path: '{file_path}'")

        return cleaned

    @staticmethod
    def validate_target_branch(branch_name: str) -> None:
        """Enforce branch protection invariant: never write directly to protected default branches.

        Args:
            branch_name : Target branch name.

        Raises:
            FixValidationError : If target branch is a protected default branch.
        """
        clean_branch = branch_name.strip().lower()
        if clean_branch in PROTECTED_BRANCHES or any(clean_branch.startswith(f"{pb}/") for pb in PROTECTED_BRANCHES):
            logger.error("Attempted direct mutation on protected branch: %s", branch_name)
            raise FixValidationError(
                f"Direct mutation on protected branch '{branch_name}' is strictly prohibited."
            )

    @staticmethod
    def log_audit_event(
        event_name: str,
        fix_request_id: str,
        user_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Log a security audit event without leaking secrets or sensitive payload text.

        Args:
            event_name     : Name of security event (e.g., 'APPROVAL_GRANTED').
            fix_request_id : Target FixRequest ID.
            user_id        : Actor user ID / GitHub handle.
            details        : Optional non-sensitive event metadata.

        Returns:
            Dict containing audit event log entry payload.
        """
        audit_entry = {
            "event": event_name,
            "fix_request_id": fix_request_id,
            "user_id": user_id,
            "details": details or {},
        }
        logger.info(
            "SECURITY AUDIT LOG: event=%s fix_request_id=%s user=%s",
            event_name,
            fix_request_id,
            user_id,
        )
        return audit_entry
