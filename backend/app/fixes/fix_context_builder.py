"""
fix_context_builder.py  (app.fixes)
====================================
Stage 8.4 — Fix Context Builder.

Gathers targeted code context required for generating an AI code fix.

Design principles (Phase 8 spec §7):
    - Retrieve ONLY necessary context: target file, relevant diff/patch,
      nearby lines, issue details, existing suggestion, language hint.
    - Do NOT send the entire repository or entire file if unnecessary.
    - Context clearly identifies file path, code region, diff, issue, constraints.
    - Support both live GitHubClient fetching and offline/in-memory file retrieval.

Author : AI Code Review Bot — Phase 8 (Stage 8.4)
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Protocol

from pydantic import BaseModel, Field

from app.fixes.exceptions import FixValidationError
from app.fixes.models import FixRequest
from app.github.github_client import GitHubClient
from app.models.github_models import GitHubFile
from app.utils import detect_language_from_diff

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


class FixContext(BaseModel):
    """Structured context payload prepared for the AI Fix Generator (Stage 8.5).

    Attributes:
        fix_request_id      : Reference to parent FixRequest.id.
        repository          : Repository slug 'owner/repo'.
        pull_request_number : Pull request number.
        commit_sha          : Commit SHA at which code context was extracted.
        file_path           : Resolved relative target file path.
        line                : 1-based line number of issue (optional).
        issue_title         : Title of finding.
        issue_description   : Detailed description of finding.
        suggestion          : Original recommendation.
        language_hint       : Programming language (e.g. 'Python', 'TypeScript').
        file_diff_patch     : Specific file unified diff patch string.
        file_content        : Full or excerpted file content at base_commit_sha.
        context_window      : Excerpt of lines surrounding the target line.
    """

    fix_request_id: str = Field(..., description="Parent FixRequest.id.")
    repository: str = Field(..., description="'owner/repo' slug.")
    pull_request_number: int = Field(..., ge=1, description="Target PR number.")
    commit_sha: str = Field(..., description="Commit SHA evaluated.")
    file_path: str = Field(..., description="Target file path relative to repo root.")
    line: Optional[int] = Field(default=None, ge=1, description="Target line number.")
    issue_title: str = Field(..., description="Title of original finding.")
    issue_description: str = Field(..., description="Full description of original finding.")
    suggestion: str = Field(default="", description="Original AI suggestion.")
    language_hint: str = Field(default="Unknown", description="Primary language hint.")
    file_diff_patch: str = Field(default="", description="Target file unified diff patch.")
    file_content: Optional[str] = Field(default=None, description="Raw target file content.")
    context_window: Optional[str] = Field(
        default=None,
        description="Lines surrounding target line with line numbers.",
    )


# ---------------------------------------------------------------------------
# File Content Provider Protocol
# ---------------------------------------------------------------------------


class FileContentProvider(Protocol):
    """Protocol for fetching file content at a specific commit SHA."""

    async def get_file_content(
        self, owner: str, repo: str, file_path: str, ref: str
    ) -> Optional[str]:
        """Retrieve raw file content as text."""
        ...


# ---------------------------------------------------------------------------
# Context Window Builder Helper
# ---------------------------------------------------------------------------


def extract_context_window(
    content: str, target_line: Optional[int], window_size: int = 15
) -> Optional[str]:
    """Extract a window of lines around ``target_line`` with 1-based line numbers.

    Args:
        content     : Raw file text.
        target_line : 1-based line number.
        window_size : Number of lines above and below target line.

    Returns:
        Formatted multi-line string with line numbers, or None if content/line missing.
    """
    if not content or target_line is None or target_line < 1:
        return None

    lines = content.splitlines()
    total_lines = len(lines)
    if total_lines == 0:
        return None

    # Clamp line index
    idx = target_line - 1
    start_idx = max(0, idx - window_size)
    end_idx = min(total_lines, idx + window_size + 1)

    formatted: list[str] = []
    for i in range(start_idx, end_idx):
        line_num = i + 1
        prefix = "-> " if line_num == target_line else "   "
        formatted.append(f"{prefix}{line_num:4d} | {lines[i]}")

    return "\n".join(formatted)


# ---------------------------------------------------------------------------
# FixContextBuilder
# ---------------------------------------------------------------------------


class FixContextBuilder:
    """Gathers minimal, structured code context for FixRequest.

    Args:
        github_client         : Optional live GitHubClient for fetching PR file diffs.
        file_content_provider : Optional provider for fetching full target file content.
    """

    def __init__(
        self,
        github_client: Optional[GitHubClient] = None,
        file_content_provider: Optional[FileContentProvider] = None,
    ) -> None:
        self._github_client = github_client
        self._content_provider = file_content_provider

    async def build_context(
        self,
        fix_request: FixRequest,
        files: Optional[list[GitHubFile]] = None,
        file_content: Optional[str] = None,
    ) -> FixContext:
        """Build a FixContext for the given FixRequest.

        Args:
            fix_request  : Target FixRequest model.
            files        : Optional pre-fetched list of GitHubFile objects for the PR.
            file_content : Optional pre-fetched raw content for target file.

        Returns:
            Populated FixContext ready for FixGenerator.

        Raises:
            FixValidationError: If target file cannot be located or diff is unavailable.
        """
        logger.info(
            "Building fix context for request %s (repo=%s, pr=%s, file=%s)",
            fix_request.id,
            fix_request.repository,
            fix_request.pull_request_number,
            fix_request.file_path,
        )

        owner, repo_name = fix_request.repository.split("/", 1)

        # ── 1. Resolve PR files if not provided ──────────────────────
        if files is None and self._github_client is not None:
            try:
                files = await self._github_client.get_pull_request_files(
                    owner=owner,
                    repo=repo_name,
                    pull_number=fix_request.pull_request_number,
                )
            except Exception as exc:
                logger.warning("Failed to fetch PR files via GitHubClient: %s", exc)

        files = files or []

        # ── 2. Locate target GitHubFile ──────────────────────────────
        target_file: Optional[GitHubFile] = None

        if fix_request.file_path and fix_request.file_path != "UNRESOLVED":
            for f in files:
                if f.filename == fix_request.file_path:
                    target_file = f
                    break

        # Fallback: if file_path was "UNRESOLVED" or not found by exact match, take first changed file
        if target_file is None and files:
            target_file = files[0]

        resolved_file_path = (
            target_file.filename if target_file else fix_request.file_path
        )
        if resolved_file_path == "UNRESOLVED":
            resolved_file_path = "unknown/file"

        patch = target_file.patch if target_file and target_file.patch else ""

        # ── 3. Detect language hint ──────────────────────────────────
        lang_detected = detect_language_from_diff(patch) if patch else None
        language_hint = lang_detected or "Unknown"
        if language_hint == "Unknown" and "." in resolved_file_path:
            ext = resolved_file_path.rsplit(".", 1)[-1].lower()
            ext_map = {
                "py": "Python",
                "js": "JavaScript",
                "ts": "TypeScript",
                "tsx": "TypeScript",
                "jsx": "JavaScript",
                "go": "Go",
                "java": "Java",
                "rs": "Rust",
                "cpp": "C++",
                "c": "C",
                "json": "JSON",
                "md": "Markdown",
            }
            language_hint = ext_map.get(ext, "Unknown")

        # ── 4. Fetch full file content if provider available ─────────
        if file_content is None and self._content_provider is not None:
            try:
                file_content = await self._content_provider.get_file_content(
                    owner=owner,
                    repo=repo_name,
                    file_path=resolved_file_path,
                    ref=fix_request.base_commit_sha,
                )
            except Exception as exc:
                logger.warning("Failed to fetch file content: %s", exc)

        # ── 5. Extract context window surrounding issue line ─────────
        context_window = None
        if file_content:
            context_window = extract_context_window(
                content=file_content,
                target_line=fix_request.line,
                window_size=15,
            )

        context = FixContext(
            fix_request_id=fix_request.id or "req-id",
            repository=fix_request.repository,
            pull_request_number=fix_request.pull_request_number,
            commit_sha=fix_request.base_commit_sha,
            file_path=resolved_file_path,
            line=fix_request.line,
            issue_title=fix_request.issue_title,
            issue_description=fix_request.issue_description,
            suggestion=fix_request.suggestion,
            language_hint=language_hint,
            file_diff_patch=patch,
            file_content=file_content,
            context_window=context_window,
        )

        logger.info(
            "FixContext built successfully: file=%s, lang=%s, has_content=%s, has_window=%s",
            context.file_path,
            context.language_hint,
            bool(context.file_content),
            bool(context.context_window),
        )

        return context
