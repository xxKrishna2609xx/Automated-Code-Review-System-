"""
review_formatter.py
===================
Pure, prompt-and-API agnostic review formatter that converts Gemini ReviewResponse
objects into GitHub Review payloads and rich Markdown comments.

Responsibilities:
• Calculate overall review event (APPROVE | REQUEST_CHANGES | COMMENT).
• Generate inline review comments with severity badges and code suggestions.
• Generate rich GitHub PR review summary with metrics tables and collapsible sections.
• Map file line numbers to diff positions using diff_mapper.

Author : AI Code Review Bot — Phase 5
"""

from __future__ import annotations

import logging
from typing import Optional

from app.models.github_models import (
    GitHubInlineComment,
    GitHubReviewEvent,
    GitHubReviewPayload,
)
from app.models.review_models import Issue, ReviewResponse, Severity
from app.utils.diff_mapper import map_line_to_diff_position

logger = logging.getLogger(__name__)

SEVERITY_BADGES = {
    Severity.CRITICAL: "🔴 **Critical**",
    Severity.HIGH: "🟠 **High**",
    Severity.MEDIUM: "🟡 **Medium**",
    Severity.LOW: "🔵 **Low**",
}


class ReviewFormatter:
    """Formatter that converts AI ReviewResponse DTOs into GitHub API review payloads."""

    def format_review(
        self,
        response: ReviewResponse,
        diff_text: str,
        commit_sha: Optional[str] = None,
        pr_number: Optional[int] = None,
        files_reviewed_count: int = 1,
        review_duration_seconds: float = 0.0,
    ) -> GitHubReviewPayload:
        """Format an AI ReviewResponse into a GitHubReviewPayload.

        Args:
            response               : AI ReviewResponse containing summary & issue list.
            diff_text              : Unified Git diff text for line position mapping.
            commit_sha             : Head commit SHA.
            pr_number              : Target PR number.
            files_reviewed_count   : Total count of files reviewed.
            review_duration_seconds: Wall-clock execution time for AI review.

        Returns:
            Fully structured ``GitHubReviewPayload``.
        """
        # 1. Determine Review Event
        event = self._determine_review_event(response.issues, response.summary)

        # 2. Build Inline Comments
        inline_comments = self._build_inline_comments(response.issues, diff_text)

        # 3. Build Summary Markdown
        summary_md = self.format_summary_markdown(
            response=response,
            pr_number=pr_number,
            files_reviewed_count=files_reviewed_count,
            review_duration_seconds=review_duration_seconds,
        )

        return GitHubReviewPayload(
            commit_id=commit_sha,
            body=summary_md,
            event=event,
            comments=inline_comments,
        )

    def _build_inline_comments(
        self, issues: list[Issue], diff_text: str
    ) -> list[GitHubInlineComment]:
        """Convert issues with line annotations into GitHub inline comments."""
        inline_comments: list[GitHubInlineComment] = []
        for issue in issues:
            if not issue.line:
                continue

            comment_body = self.format_inline_comment(issue)
            file_path = getattr(issue, "file_path", None) or "main.py"
            pos, actual_line, side = map_line_to_diff_position(diff_text, file_path, issue.line)

            inline_comments.append(
                GitHubInlineComment(
                    path=file_path,
                    line=actual_line,
                    side=side,
                    position=pos,
                    body=comment_body,
                )
            )
        return inline_comments

    def format_inline_comment(self, issue: Issue) -> str:
        """Format a single Issue into a markdown inline comment body."""
        badge = SEVERITY_BADGES.get(issue.severity, f"**{issue.severity}**")

        lines = [
            f"{badge} | **{issue.category}**: {issue.title}",
            "",
            issue.description,
        ]

        if issue.suggestion:
            lines.extend([
                "",
                "**💡 Recommendation / Suggested Fix:**",
                "```suggestion",
                issue.suggestion,
                "```",
            ])

        return "\n".join(lines)

    @staticmethod
    def _compute_health_score(critical: int, high: int, medium: int, low: int) -> tuple[int, str]:
        """Compute heuristic code health score and qualitative badge."""
        score = max(0, 100 - (critical * 25 + high * 15 + medium * 5 + low * 2))
        badge = "🟢 Excellent" if score >= 85 else ("🟡 Needs Attention" if score >= 65 else "🔴 Action Required")
        return score, badge

    def format_summary_markdown(
        self,
        response: ReviewResponse,
        pr_number: Optional[int] = None,
        files_reviewed_count: int = 1,
        review_duration_seconds: float = 0.0,
    ) -> str:
        """Generate a GitHub Markdown summary for the Pull Request."""
        critical_count = sum(1 for i in response.issues if i.severity == Severity.CRITICAL)
        high_count = sum(1 for i in response.issues if i.severity == Severity.HIGH)
        medium_count = sum(1 for i in response.issues if i.severity == Severity.MEDIUM)
        low_count = sum(1 for i in response.issues if i.severity == Severity.LOW)
        total_issues = len(response.issues)

        score, score_badge = self._compute_health_score(
            critical_count, high_count, medium_count, low_count
        )

        lines = [
            f"# 🤖 AI Code Review Summary {f'(PR #{pr_number})' if pr_number else ''}",
            "",
            f"**Overall Quality Score:** `{score} / 100` — {score_badge}",
            "",
            "### 📊 Review Metrics",
            "| Metric | Value |",
            "| :--- | :--- |",
            f"| 📁 **Files Reviewed** | `{files_reviewed_count}` |",
            f"| ⚡ **Total Issues Found** | `{total_issues}` |",
            f"| 🔴 **Critical Severity** | `{critical_count}` |",
            f"| 🟠 **High Severity** | `{high_count}` |",
            f"| 🟡 **Medium Severity** | `{medium_count}` |",
            f"| 🔵 **Low Severity** | `{low_count}` |",
            f"| ⏱️ **Review Duration** | `{review_duration_seconds:.2f}s` |",
            "",
            "### 📝 Executive Summary",
            response.summary,
            "",
        ]

        if response.issues:
            lines.extend([
                "<details>",
                "<summary><b>🔍 View All Detected Issues Breakdown</b></summary>",
                "",
                "| Line | Severity | Category | Issue Title |",
                "| :--- | :--- | :--- | :--- |",
            ])
            for issue in response.issues:
                line_str = f"`L{issue.line}`" if issue.line else "`N/A`"
                lines.append(f"| {line_str} | {issue.severity} | {issue.category} | {issue.title} |")
            lines.extend(["", "</details>", ""])

        lines.extend([
            "---",
            "*Automated code review generated by AI Code Review Bot (Phase 5).* 👋",
        ])

        return "\n".join(lines)

    @staticmethod
    def _determine_review_event(issues: list[Issue], summary: str) -> GitHubReviewEvent:
        """Calculate the GitHub Review Event based on findings.

        Rules:
        - Critical issues > 0 -> REQUEST_CHANGES
        - High issues >= 3 -> REQUEST_CHANGES
        - Otherwise -> APPROVE (or COMMENT if issues exist)
        """
        critical_count = sum(1 for i in issues if i.severity == Severity.CRITICAL)
        high_count = sum(1 for i in issues if i.severity == Severity.HIGH)

        if critical_count > 0 or high_count >= 3:
            return GitHubReviewEvent.REQUEST_CHANGES
        elif len(issues) == 0:
            return GitHubReviewEvent.APPROVE

        return GitHubReviewEvent.COMMENT
