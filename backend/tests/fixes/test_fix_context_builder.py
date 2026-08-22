"""
test_fix_context_builder.py  (tests.fixes)
============================================
Unit tests for Stage 8.4 — FixContextBuilder.

Tests cover:
    - Context building with in-memory files and content
    - Language hint detection from file extension / diff
    - Context window extraction with line numbers and target marker
    - Fallback behavior when file_path is "UNRESOLVED"
    - Integration with mocked GitHubClient and FileContentProvider

Author : AI Code Review Bot — Phase 8 (Stage 8.4)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.fixes.fix_context_builder import (
    FixContext,
    FixContextBuilder,
    extract_context_window,
)
from app.fixes.models import FixRequest, FixStatus
from app.models.github_models import GitHubFile


# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------

VALID_SHA = "a" * 40

def _make_fix_request(**overrides) -> FixRequest:
    base = dict(
        id="fix-req-123",
        review_id="rev-456",
        issue_id="security-0",
        repository="owner/repo",
        pull_request_number=42,
        base_commit_sha=VALID_SHA,
        file_path="app/database.py",
        line=3,
        issue_title="SQL Injection Risk",
        issue_description="Unsanitized user input concatenated into query.",
        suggestion="Use parameterized query.",
        status=FixStatus.REQUESTED,
    )
    base.update(overrides)
    return FixRequest(**base)


SAMPLE_FILE_CONTENT = "\n".join([
    "import os",
    "import sqlite3",
    "def get_user(user_id):",
    "    conn = sqlite3.connect('db.sq3')",
    "    cursor = conn.cursor()",
    "    query = f'SELECT * FROM users WHERE id={user_id}'",
    "    return cursor.execute(query).fetchall()",
    "def list_users():",
    "    pass",
])

SAMPLE_PATCH = """@@ -1,5 +1,5 @@
 import os
 import sqlite3
 def get_user(user_id):
-    query = f'SELECT * FROM users WHERE id={user_id}'
+    query = 'SELECT * FROM users WHERE id=?'
"""


# ---------------------------------------------------------------------------
# Context Window Extraction Tests
# ---------------------------------------------------------------------------

class TestExtractContextWindow:
    def test_extract_window_valid(self):
        window = extract_context_window(SAMPLE_FILE_CONTENT, target_line=3, window_size=1)
        assert window is not None
        assert "2 | import sqlite3" in window
        assert "->    3 | def get_user(user_id):" in window
        assert "4 |     conn = sqlite3.connect('db.sq3')" in window

    def test_extract_window_boundary_first_line(self):
        window = extract_context_window(SAMPLE_FILE_CONTENT, target_line=1, window_size=2)
        assert window is not None
        assert "->    1 | import os" in window
        assert "2 | import sqlite3" in window

    def test_extract_window_none_line(self):
        assert extract_context_window(SAMPLE_FILE_CONTENT, target_line=None) is None

    def test_extract_window_invalid_line(self):
        assert extract_context_window(SAMPLE_FILE_CONTENT, target_line=0) is None
        assert extract_context_window(SAMPLE_FILE_CONTENT, target_line=-5) is None

    def test_extract_window_empty_content(self):
        assert extract_context_window("", target_line=1) is None


# ---------------------------------------------------------------------------
# FixContextBuilder Tests
# ---------------------------------------------------------------------------

class TestFixContextBuilder:
    @pytest.mark.asyncio
    async def test_build_context_with_direct_inputs(self):
        builder = FixContextBuilder()
        fix_req = _make_fix_request()

        gh_file = GitHubFile(
            filename="app/database.py",
            patch=SAMPLE_PATCH,
            status="modified",
        )

        context = await builder.build_context(
            fix_request=fix_req,
            files=[gh_file],
            file_content=SAMPLE_FILE_CONTENT,
        )

        assert isinstance(context, FixContext)
        assert context.fix_request_id == "fix-req-123"
        assert context.repository == "owner/repo"
        assert context.file_path == "app/database.py"
        assert context.language_hint == "Python"
        assert context.file_diff_patch == SAMPLE_PATCH
        assert context.file_content == SAMPLE_FILE_CONTENT
        assert context.context_window is not None
        assert "->    3 | def get_user(user_id):" in context.context_window

    @pytest.mark.asyncio
    async def test_language_hint_fallback_extension(self):
        builder = FixContextBuilder()
        fix_req = _make_fix_request(file_path="src/index.ts")

        gh_file = GitHubFile(
            filename="src/index.ts",
            patch="",  # No patch
        )

        context = await builder.build_context(fix_request=fix_req, files=[gh_file])
        assert context.language_hint == "TypeScript"

    @pytest.mark.asyncio
    async def test_unresolved_file_path_resolution(self):
        builder = FixContextBuilder()
        fix_req = _make_fix_request(file_path="UNRESOLVED")

        gh_file = GitHubFile(
            filename="src/auth.py",
            patch=SAMPLE_PATCH,
        )

        context = await builder.build_context(fix_request=fix_req, files=[gh_file])
        assert context.file_path == "src/auth.py"

    @pytest.mark.asyncio
    async def test_github_client_integration(self):
        mock_gh = MagicMock()
        mock_gh.get_pull_request_files = AsyncMock(return_value=[
            GitHubFile(filename="app/database.py", patch=SAMPLE_PATCH)
        ])

        builder = FixContextBuilder(github_client=mock_gh)
        fix_req = _make_fix_request()

        context = await builder.build_context(fix_request=fix_req)
        assert context.file_path == "app/database.py"
        assert context.file_diff_patch == SAMPLE_PATCH
        mock_gh.get_pull_request_files.assert_awaited_once_with(
            owner="owner", repo="repo", pull_number=42
        )

    @pytest.mark.asyncio
    async def test_content_provider_integration(self):
        mock_provider = MagicMock()
        mock_provider.get_file_content = AsyncMock(return_value=SAMPLE_FILE_CONTENT)

        builder = FixContextBuilder(file_content_provider=mock_provider)
        fix_req = _make_fix_request(line=3)

        context = await builder.build_context(fix_request=fix_req)
        assert context.file_content == SAMPLE_FILE_CONTENT
        assert context.context_window is not None
        mock_provider.get_file_content.assert_awaited_once_with(
            owner="owner", repo="repo", file_path="app/database.py", ref=VALID_SHA
        )
