"""
issue_utils.py
==============
Utilities for sorting, deduplicating, and post-processing code review issues.

Author : AI Code Review Bot — Phase 4
"""

from __future__ import annotations

from app.models.review_models import Issue, Severity

_SEVERITY_ORDER: dict[str, int] = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
}


def sort_and_deduplicate_issues(issues: list[Issue]) -> list[Issue]:
    """Sort issues by severity and remove duplicate/near-identical findings.

    Rules:
    1. Sort by severity: Critical (0) → High (1) → Medium (2) → Low (3).
    2. Primary deduplication key: (line, title).

    Args:
        issues: List of raw Issue objects.

    Returns:
        Sorted and deduplicated list of Issue objects.
    """
    seen: set[tuple[Optional[int], str]] = set()
    deduped: list[Issue] = []

    for issue in issues:
        key = (issue.line, issue.title.strip().lower())
        if key not in seen:
            seen.add(key)
            deduped.append(issue)

    # Sort by severity rank, then by line number
    deduped.sort(
        key=lambda i: (
            _SEVERITY_ORDER.get(i.severity, 99),
            i.line if i.line is not None else 999999,
        )
    )

    return deduped
