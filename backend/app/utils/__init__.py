"""
app.utils
=========
Helper utilities for diff processing, JSON sanitisation, issue deduplication, diff hunk mapping, and exception handling.
"""

from app.utils.diff_mapper import map_line_to_diff_position, parse_unified_diff
from app.utils.diff_utils import (
    detect_language_from_diff,
    normalise_diff,
    split_diff_into_chunks,
)
from app.utils.error_handlers import register_exception_handlers
from app.utils.issue_utils import sort_and_deduplicate_issues
from app.utils.json_utils import extract_json_from_text

__all__ = [
    "normalise_diff",
    "detect_language_from_diff",
    "split_diff_into_chunks",
    "extract_json_from_text",
    "sort_and_deduplicate_issues",
    "parse_unified_diff",
    "map_line_to_diff_position",
    "register_exception_handlers",
]
