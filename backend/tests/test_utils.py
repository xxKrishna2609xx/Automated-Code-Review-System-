"""
test_utils.py
=============
Unit tests for backend utility functions in app.utils.
"""

from __future__ import annotations

import pytest
from app.models.review_models import Issue, Severity
from app.utils.diff_utils import (
    detect_language_from_diff,
    normalise_diff,
    split_diff_into_chunks,
)
from app.utils.issue_utils import sort_and_deduplicate_issues
from app.utils.json_utils import extract_json_from_text


# ---------------------------------------------------------------------------
# diff_utils tests
# ---------------------------------------------------------------------------


def test_normalise_diff_windows_line_endings():
    raw_diff = "line1 \r\nline2\t  \r\nline3\r"
    cleaned = normalise_diff(raw_diff)
    assert cleaned == "line1\nline2\nline3"


def test_detect_language_from_diff():
    py_diff = """--- a/backend/app/main.py\n+++ b/backend/app/main.py\n@@ -1,3 +1,3 @@\n-import os\n+import sys\n"""
    assert detect_language_from_diff(py_diff) == "Python"

    ts_diff = """--- a/frontend/app/page.tsx\n+++ b/frontend/app/page.tsx\n@@ -1,3 +1,3 @@\n-const x = 1;\n+const x = 2;\n"""
    assert detect_language_from_diff(ts_diff) == "TypeScript"

    unknown_diff = "no headers here"
    assert detect_language_from_diff(unknown_diff) is None


def test_split_diff_into_chunks():
    diff = "line1\nline2\nline3\nline4\nline5\n"
    # Small max_chars forces chunking
    chunks = split_diff_into_chunks(diff, max_chars=12, overlap_lines=1)
    assert len(chunks) > 1
    assert "".join(chunks[0]) != diff


# ---------------------------------------------------------------------------
# json_utils tests
# ---------------------------------------------------------------------------


def test_extract_json_from_markdown_fence():
    raw = "Here is the response:\n```json\n{\"summary\": \"OK\", \"issues\": []}\n```\nHope it helps!"
    extracted = extract_json_from_text(raw)
    assert extracted == '{"summary": "OK", "issues": []}'


def test_extract_json_from_braces():
    raw = 'Some text before {"key": "value"} some text after'
    extracted = extract_json_from_text(raw)
    assert extracted == '{"key": "value"}'


def test_extract_json_raw_fallback():
    raw = '{"raw": true}'
    assert extract_json_from_text(raw) == '{"raw": true}'


# ---------------------------------------------------------------------------
# issue_utils tests
# ---------------------------------------------------------------------------


def test_sort_and_deduplicate_issues():
    issues = [
        Issue(
            title="Low severity bug",
            line=10,
            severity=Severity.LOW,
            category="Bug",
            description="Detailed low severity issue description.",
            suggestion="Fix the low issue",
        ),
        Issue(
            title="Critical security vulnerability",
            line=5,
            severity=Severity.CRITICAL,
            category="Security",
            description="Detailed critical security vulnerability description.",
            suggestion="Fix critical vulnerability",
        ),
        Issue(
            title="Low severity bug",  # Duplicate title & line
            line=10,
            severity=Severity.LOW,
            category="Bug",
            description="Detailed duplicate low severity description.",
            suggestion="Fix the low issue",
        ),
    ]

    processed = sort_and_deduplicate_issues(issues)

    assert len(processed) == 2
    assert processed[0].severity == Severity.CRITICAL
    assert processed[1].severity == Severity.LOW
