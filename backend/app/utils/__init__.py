"""
app.utils
=========
Helper utilities for diff processing, JSON sanitisation, and issue deduplication.
"""

from app.utils.diff_utils import (
    detect_language_from_diff,
    normalise_diff,
    split_diff_into_chunks,
)
from app.utils.issue_utils import sort_and_deduplicate_issues
from app.utils.json_utils import extract_json_from_text

__all__ = [
    "normalise_diff",
    "detect_language_from_diff",
    "split_diff_into_chunks",
    "extract_json_from_text",
    "sort_and_deduplicate_issues",
]
