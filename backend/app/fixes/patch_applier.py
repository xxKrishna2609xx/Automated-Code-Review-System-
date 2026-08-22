"""
patch_applier.py  (app.fixes)
============================
Stage 8.11 — Apply Patch In Memory & Git Tree Preparation.

Performs in-memory patch application and constructs GitHub Git Data API tree
item payloads without writing files to host disk or executing local shell commands.

Design principles (Phase 8 spec §14):
    1. ZERO host disk writes (no open(..., 'w'), no temp files).
    2. ZERO shell execution (no `git apply`, no `patch` CLI).
    3. Pure Python string manipulation and buffer processing.
    4. Re-validates post-patch static syntax.
    5. Prepares structured Git Tree Item payload for Stage 8.12/8.13 Git Data API calls:
       `{"path": "<file_path>", "mode": "100644", "type": "blob", "content": "<updated_content>"}`

Author : AI Code Review Bot — Phase 8 (Stage 8.11)
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Any, Optional

from app.fixes.exceptions import FixValidationError
from app.fixes.models import FixPatch, FixRequest
from app.fixes.patch_validator import apply_patch_in_memory
from app.validation.syntax_validator import SyntaxValidator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AppliedPatchResult:
    """Outcome of in-memory patch application and Git Tree Item payload preparation.

    Attributes:
        file_path            : Target relative file path.
        original_hash        : SHA-256 digest of source content before patch.
        updated_hash         : SHA-256 digest of updated content after patch.
        updated_content      : Complete updated text content of target file.
        git_tree_item        : GitHub Git Data API tree item dictionary payload:
                               `{"path": file_path, "mode": "100644", "type": "blob", "content": updated_content}`
    """

    file_path: str
    original_hash: str
    updated_hash: str
    updated_content: str
    git_tree_item: dict[str, Any]


# ---------------------------------------------------------------------------
# InMemoryPatchService
# ---------------------------------------------------------------------------


class InMemoryPatchService:
    """Applies FixPatch in memory and prepares Git Tree payload without host disk writes.

    Args:
        syntax_validator : Optional SyntaxValidator instance for post-patch check.
    """

    def __init__(self, syntax_validator: Optional[SyntaxValidator] = None) -> None:
        self._syntax_validator = syntax_validator or SyntaxValidator()

    def apply_patch(
        self,
        fix_request: FixRequest,
        fix_patch: FixPatch,
        base_file_content: str,
        file_mode: str = "100644",
    ) -> AppliedPatchResult:
        """Apply a FixPatch to base_file_content entirely in memory.

        Validation steps:
            1. Base content hash matches ``fix_patch.original_content_hash``.
            2. Apply GNU unified diff patch in memory via ``apply_patch_in_memory``.
            3. Run static syntax check on updated content.
            4. Calculate updated content SHA-256 hash.
            5. Construct GitHub Git Data API tree item payload.

        Args:
            fix_request       : Target FixRequest model.
            fix_patch         : Validated FixPatch model from Stage 8.5/8.6.
            base_file_content : Raw source code string at base_commit_sha.
            file_mode         : Git file mode (default "100644" for standard files, "100755" for executables).

        Returns:
            AppliedPatchResult containing updated content and Git Tree Item payload.

        Raises:
            FixValidationError : If hash fails, patch application fails, or post-patch syntax is invalid.
        """
        logger.info(
            "Applying patch in memory for fix request %s (file=%s)",
            fix_request.id,
            fix_patch.file_path,
        )

        # ── 1. Validate Original Content Hash ────────────────────────
        actual_original_hash = hashlib.sha256(base_file_content.encode("utf-8")).hexdigest()
        if actual_original_hash.lower() != fix_patch.original_content_hash.lower():
            raise FixValidationError(
                f"Content hash mismatch for '{fix_patch.file_path}'. "
                f"Expected {fix_patch.original_content_hash[:8]}..., got {actual_original_hash[:8]}... "
                "Source file has drifted since fix generation."
            )

        # ── 2. Apply Patch in Memory ─────────────────────────────────
        success, updated_content, err_msg = apply_patch_in_memory(
            original_content=base_file_content,
            patch_str=fix_patch.patch,
        )

        if not success:
            raise FixValidationError(
                f"In-memory patch application failed for '{fix_patch.file_path}': {err_msg}"
            )

        # ── 3. Post-Patch Syntax Check ───────────────────────────────
        syn_result = self._syntax_validator.validate_syntax(
            content=updated_content,
            language_or_path=fix_patch.file_path,
        )
        if not syn_result.valid:
            raise FixValidationError(
                f"Post-patch syntax validation failed for '{fix_patch.file_path}': {syn_result.error_message}"
            )

        # ── 4. Compute Updated Content Hash ──────────────────────────
        updated_hash = hashlib.sha256(updated_content.encode("utf-8")).hexdigest()

        # ── 5. Prepare GitHub Git Data API Tree Item ──────────────────
        git_tree_item: dict[str, Any] = {
            "path": fix_patch.file_path,
            "mode": file_mode,
            "type": "blob",
            "content": updated_content,
        }

        logger.info(
            "In-memory patch applied successfully: file=%s, old_hash=%s..., new_hash=%s...",
            fix_patch.file_path,
            actual_original_hash[:8],
            updated_hash[:8],
        )

        return AppliedPatchResult(
            file_path=fix_patch.file_path,
            original_hash=actual_original_hash,
            updated_hash=updated_hash,
            updated_content=updated_content,
            git_tree_item=git_tree_item,
        )
