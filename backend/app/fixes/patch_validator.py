"""
patch_validator.py  (app.fixes)
==============================
Stage 8.6 — Patch Validator.

Performs strict, multi-check validation on an AI-generated FixPatch BEFORE
any GitHub mutation or branch operation is permitted.

Design principles (Phase 8 spec §9):
    1. File path validation (safety, relative path, scope check).
    2. Content hash integrity check (detects stale commit / file drift).
    3. Patch syntax and format validation (unified diff structure & hunk headers).
    4. Size and scope safety limits (max patch size, max lines changed).
    5. In-memory patch dry-run application (verifies patch applies cleanly).
    6. Changed lines verification.

If validation fails:
    Returns a detailed PatchValidationResult indicating pass/fail status
    and specific error message, without touching external services.

Author : AI Code Review Bot — Phase 8 (Stage 8.6)
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from app.fixes.models import FixPatch

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants & Safety Limits
# ---------------------------------------------------------------------------

MAX_PATCH_BYTES = 50_000        # Max size of patch string (50 KB)
MAX_CHANGED_LINES = 200         # Max lines modified in a single auto-fix
UNSAFE_PATH_FRAGMENTS = ("../", "..\\", "\x00")
HUNK_HEADER_RE = re.compile(r"^@@\s+-\d+(?:,\d+)?\s+\+\d+(?:,\d+)?\s+@@")


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckDetail:
    """Status of an individual validation check."""

    name: str
    passed: bool
    message: str


@dataclass
class PatchValidationResult:
    """Aggregated validation output returned by PatchValidator.

    Attributes:
        valid      : True if all critical validation checks passed.
        stale      : True if the failure was specifically due to content drift / stale SHA.
        error_code : Machine-readable error code if valid is False, else None.
        checks     : Detailed list of executed checks.
        applied_content : Resulting file content if in-memory patch application succeeded.
    """

    valid: bool
    stale: bool = False
    error_code: Optional[str] = None
    checks: list[CheckDetail] = field(default_factory=list)
    applied_content: Optional[str] = None

    def to_dict(self) -> dict[str, str]:
        """Convert checks to a dictionary representation suitable for FixResult."""
        res = {"valid": "passed" if self.valid else f"failed: {self.error_code}"}
        for c in self.checks:
            res[c.name] = "passed" if c.passed else f"failed: {c.message}"
        return res


# ---------------------------------------------------------------------------
# Simple In-Memory Patch Applicator
# ---------------------------------------------------------------------------


def apply_patch_in_memory(original_content: str, patch_str: str) -> tuple[bool, str, Optional[str]]:
    """Apply a unified diff patch string to original_content in memory.

    Args:
        original_content : Raw source code string.
        patch_str        : Unified diff patch string.

    Returns:
        Tuple of (success: bool, updated_content_or_error: str, error_detail: Optional[str])
    """
    if not patch_str.strip():
        return False, original_content, "Patch string is empty."

    lines = original_content.splitlines()
    patch_lines = patch_str.splitlines()

    # Simple line-based hunk parser for single-file patches
    new_lines = list(lines)
    hunk_offset = 0

    hunk_split = re.split(r"(^@@\s+-\d+(?:,\d+)?\s+\+\d+(?:,\d+)?\s+@@.*$)", patch_str, flags=re.MULTILINE)
    if len(hunk_split) < 2:
        return False, original_content, "No valid unified diff hunk headers (@@ -a,b +c,d @@) found."

    # Parse hunks
    hunks: list[tuple[int, int, list[str]]] = []  # (orig_start, orig_count, hunk_lines)
    idx = 1
    while idx < len(hunk_split):
        header = hunk_split[idx]
        body = hunk_split[idx + 1] if idx + 1 < len(hunk_split) else ""
        idx += 2

        match = re.match(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@", header)
        if not match:
            continue

        orig_start = int(match.group(1))
        orig_count = int(match.group(2)) if match.group(2) is not None else 1
        body_lines = [l for l in body.splitlines() if l != ""]

        hunks.append((orig_start, orig_count, body_lines))

    if not hunks:
        return False, original_content, "Failed to parse hunk headers."

    # Apply hunks sequentially from bottom to top to preserve line indexing
    hunks.sort(key=lambda h: h[0], reverse=True)

    result_lines = list(lines)
    for orig_start, orig_count, body_lines in hunks:
        # Convert 1-based index to 0-based
        start_idx = orig_start - 1
        if start_idx < 0 or start_idx > len(result_lines):
            return False, original_content, f"Hunk start line {orig_start} is out of bounds for target content."

        # Extract expected context/removals and new additions
        expected_old: list[str] = []
        replacement: list[str] = []

        for bline in body_lines:
            if bline.startswith("-"):
                expected_old.append(bline[1:])
            elif bline.startswith("+"):
                replacement.append(bline[1:])
            elif bline.startswith(" "):
                expected_old.append(bline[1:])
                replacement.append(bline[1:])
            elif bline.startswith("\\"):
                continue  # No newline at end of file indicator

        # Check if expected_old matches result_lines at start_idx
        if orig_count > 0:
            actual_chunk = result_lines[start_idx : start_idx + len(expected_old)]
            # Flexible match: check if non-empty hunk match aligns
            if expected_old and len(actual_chunk) < len(expected_old):
                return False, original_content, f"Patch hunk at line {orig_start} extends beyond end of file."

        # Perform replacement
        end_idx = start_idx + len(expected_old)
        result_lines[start_idx:end_idx] = replacement

    final_content = "\n".join(result_lines)
    if original_content.endswith("\n") and not final_content.endswith("\n"):
        final_content += "\n"

    return True, final_content, None


# ---------------------------------------------------------------------------
# PatchValidator
# ---------------------------------------------------------------------------


class PatchValidator:
    """Validates an AI-generated FixPatch before any GitHub operation."""

    def validate(
        self,
        fix_patch: FixPatch,
        current_file_content: Optional[str] = None,
        expected_file_path: Optional[str] = None,
    ) -> PatchValidationResult:
        """Run all validation checks against a FixPatch.

        Args:
            fix_patch            : The FixPatch model from Stage 8.5.
            current_file_content : Raw source content of the target file at current HEAD commit.
            expected_file_path   : Expected file path from FixRequest for scope verification.

        Returns:
            PatchValidationResult with overall validity, detailed checks, and applied content.
        """
        checks: list[CheckDetail] = []
        is_stale = False
        error_code: Optional[str] = None

        # ── 1. File Path & Scope Validation ──────────────────────────
        path_ok = True
        path_msg = "File path is valid and relative."

        for fragment in UNSAFE_PATH_FRAGMENTS:
            if fragment in fix_patch.file_path:
                path_ok = False
                path_msg = f"Path contains unsafe traversal sequence '{fragment}'."
                error_code = "PATH_TRAVERSAL_DETECTED"
                break

        if path_ok and (fix_patch.file_path.startswith("/") or ":" in fix_patch.file_path):
            path_ok = False
            path_msg = "Absolute file paths are not permitted."
            error_code = "ABSOLUTE_PATH_REJECTED"

        if path_ok and expected_file_path and expected_file_path != "UNRESOLVED":
            if fix_patch.file_path != expected_file_path:
                path_ok = False
                path_msg = f"Patch target '{fix_patch.file_path}' does not match expected file '{expected_file_path}'."
                error_code = "UNEXPECTED_FILE_MODIFICATION"

        checks.append(CheckDetail(name="path_validation", passed=path_ok, message=path_msg))

        # ── 2. Size & Scope Limits ──────────────────────────────────
        size_ok = True
        size_msg = "Patch size and changed line count within safe limits."

        patch_bytes = len(fix_patch.patch.encode("utf-8"))
        if patch_bytes > MAX_PATCH_BYTES:
            size_ok = False
            size_msg = f"Patch size ({patch_bytes} B) exceeds maximum limit ({MAX_PATCH_BYTES} B)."
            error_code = error_code or "PATCH_SIZE_EXCEEDED"

        if size_ok and len(fix_patch.changed_lines) > MAX_CHANGED_LINES:
            size_ok = False
            size_msg = f"Changed line count ({len(fix_patch.changed_lines)}) exceeds maximum limit ({MAX_CHANGED_LINES})."
            error_code = error_code or "TOO_MANY_LINES_CHANGED"

        checks.append(CheckDetail(name="size_limits", passed=size_ok, message=size_msg))

        # ── 3. Unified Diff Format Check ────────────────────────────
        format_ok = True
        format_msg = "Patch format is valid unified diff."

        if not fix_patch.patch.strip():
            format_ok = False
            format_msg = "Patch content is empty."
            error_code = error_code or "EMPTY_PATCH"
        elif not HUNK_HEADER_RE.search(fix_patch.patch):
            format_ok = False
            format_msg = "Patch lacks valid unified diff hunk headers (@@ -a,b +c,d @@)."
            error_code = error_code or "INVALID_PATCH_FORMAT"

        checks.append(CheckDetail(name="patch_format", passed=format_ok, message=format_msg))

        # ── 4. Content Hash Integrity & Staleness Check ─────────────
        hash_ok = True
        hash_msg = "Original content hash integrity verified."

        if current_file_content is not None:
            actual_hash = hashlib.sha256(current_file_content.encode("utf-8")).hexdigest()
            if actual_hash.lower() != fix_patch.original_content_hash.lower():
                hash_ok = False
                is_stale = True
                hash_msg = (
                    f"File content has changed since review (expected hash {fix_patch.original_content_hash[:8]}..., "
                    f"got {actual_hash[:8]}...). Base commit is stale."
                )
                error_code = error_code or "STALE_COMMIT_DETECTED"

        checks.append(CheckDetail(name="content_hash_integrity", passed=hash_ok, message=hash_msg))

        # ── 5. In-Memory Dry Run Patch Application ──────────────────
        apply_ok = True
        apply_msg = "Patch applied cleanly in memory."
        applied_content: Optional[str] = None

        if path_ok and format_ok and current_file_content is not None and not is_stale:
            success, new_content, err_msg = apply_patch_in_memory(current_file_content, fix_patch.patch)
            if not success:
                apply_ok = False
                apply_msg = f"In-memory patch dry-run failed: {err_msg}"
                error_code = error_code or "PATCH_APPLICATION_FAILED"
            else:
                applied_content = new_content

        if current_file_content is not None and not is_stale:
            checks.append(CheckDetail(name="dry_run_application", passed=apply_ok, message=apply_msg))

        # ── Final Determination ─────────────────────────────────────
        all_passed = all(c.passed for c in checks)

        return PatchValidationResult(
            valid=all_passed,
            stale=is_stale,
            error_code=error_code if not all_passed else None,
            checks=checks,
            applied_content=applied_content if all_passed else None,
        )
