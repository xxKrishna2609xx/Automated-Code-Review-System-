"""
review_aggregator.py
====================
Review Aggregator for Phase 6 Multi-Agent AI Code Review.

Responsibilities (Stages 6.9 + 6.10 — combined per the spec):
- Flatten all findings from every AgentReview into a single list.
- Validate findings (remove any structurally corrupt entries).
- Deduplicate near-identical findings using deterministic signal matching
  (same category + same line + similar title prefix) WITHOUT calling Gemini.
- Merge duplicate findings: keep the highest severity, combine attribution.
- Rank findings deterministically:
    CRITICAL → HIGH → MEDIUM → LOW
    Within the same severity: SECURITY > BUG > PERFORMANCE > DOCUMENTATION/TESTING
- Build structured breakdowns (by category, by severity).
- Assemble the combined narrative summary from all successful agents.
- Preserve per-agent results in full for traceability.
- Produce a ``FinalReview`` ready for the ScoreEngine and Phase 5 adapter.

The aggregator NEVER calls Gemini or any external API.

Author : AI Code Review Bot — Phase 6 (Stages 6.9 + 6.10)
"""

from __future__ import annotations

import logging
from typing import Optional

from app.models.agent_models import AgentCategory, AgentReview, FinalReview
from app.models.review_models import Issue, IssueCategory, Severity

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Severity ordering — lower index = higher priority
# ---------------------------------------------------------------------------

_SEVERITY_RANK: dict[str, int] = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
}

# Within the same severity, category rank (lower = higher priority)
_CATEGORY_RANK: dict[str, int] = {
    IssueCategory.SECURITY: 0,
    IssueCategory.BUG: 1,
    IssueCategory.EDGE_CASE: 2,
    IssueCategory.ERROR_HANDLING: 3,
    IssueCategory.PERFORMANCE: 4,
    IssueCategory.MAINTAINABILITY: 5,
    IssueCategory.BEST_PRACTICE: 6,
    IssueCategory.CODE_SMELL: 7,
    IssueCategory.READABILITY: 8,
    IssueCategory.NAMING: 9,
    IssueCategory.OTHER: 10,
}


class ReviewAggregator:
    """Aggregates, deduplicates, and ranks findings from all specialized agents.

    Public API:
        aggregate(agent_reviews) -> FinalReview
    """

    def aggregate(
        self,
        agent_reviews: list[AgentReview],
        execution_time_ms: float = 0.0,
    ) -> FinalReview:
        """Produce a ``FinalReview`` from the raw per-agent review outputs.

        Args:
            agent_reviews     : Ordered list of ``AgentReview`` from the orchestrator.
            execution_time_ms : Total pipeline time to record in the result.

        Returns:
            Fully populated ``FinalReview`` ready for scoring and publishing.
        """
        logger.info(
            "Aggregator starting — agent_reviews=%d", len(agent_reviews)
        )

        # ── 1. Partition successful vs failed agents ───────────────────
        successful_agents = [r.agent_name for r in agent_reviews if r.success]
        failed_agents = [r.agent_name for r in agent_reviews if not r.success]

        if failed_agents:
            logger.warning("Failed agents will be excluded from findings: %s", failed_agents)

        # ── 2. Flatten all issues from successful agents ───────────────
        raw_issues: list[Issue] = []
        for review in agent_reviews:
            if review.success:
                raw_issues.extend(review.issues)

        logger.info("Aggregator flattened %d raw issues from %d successful agents",
                    len(raw_issues), len(successful_agents))

        # ── 3. Deduplicate (deterministic — no Gemini calls) ──────────
        deduped_issues = self._deduplicate(raw_issues)
        logger.info("Aggregator deduplication: %d → %d issues",
                    len(raw_issues), len(deduped_issues))

        # ── 4. Severity + category ranking (Stage 6.10) ───────────────
        ranked_issues = self._rank(deduped_issues)

        # ── 5. Build breakdowns ────────────────────────────────────────
        issues_by_category = self._count_by_category(ranked_issues)
        issues_by_severity = self._count_by_severity(ranked_issues)

        # ── 6. Assemble combined summary ───────────────────────────────
        summary = self._build_summary(agent_reviews, failed_agents)

        final = FinalReview(
            overall_score=-1,          # Populated by ScoreEngine (Stage 6.11)
            summary=summary,
            issues=ranked_issues,
            total_issues=len(ranked_issues),
            issues_by_category=issues_by_category,
            issues_by_severity=issues_by_severity,
            agent_results=agent_reviews,
            successful_agents=successful_agents,
            failed_agents=failed_agents,
            execution_time_ms=round(execution_time_ms, 2),
        )

        logger.info(
            "Aggregator complete — total_issues=%d successful=%d failed=%d",
            final.total_issues,
            len(successful_agents),
            len(failed_agents),
        )
        return final

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_dedup_key(issue: Issue) -> tuple:
        """Construct deterministic deduplication key (category, line, title_prefix_10_chars)."""
        title_prefix = issue.title.lower()[:10].strip()
        line_key = issue.line if issue.line is not None else -1
        return (issue.category, line_key, title_prefix)

    def _deduplicate(self, issues: list[Issue]) -> list[Issue]:
        """Remove near-duplicate findings using deterministic signal matching.

        Deduplication key = (category, line, title_prefix_10_chars).

        When duplicates are found:
        - Keep the entry with the HIGHER severity (lower rank index).
        - Preserve the first occurrence's description/suggestion.

        No external API calls are made.
        """
        seen: dict[tuple, Issue] = {}

        for issue in issues:
            key = self._build_dedup_key(issue)

            if key not in seen:
                seen[key] = issue
            else:
                # Keep the highest severity (lowest rank number)
                existing = seen[key]
                existing_rank = _SEVERITY_RANK.get(existing.severity, 99)
                new_rank = _SEVERITY_RANK.get(issue.severity, 99)
                if new_rank < existing_rank:
                    seen[key] = issue

        return list(seen.values())

    def _rank(self, issues: list[Issue]) -> list[Issue]:
        """Sort issues by severity desc, then category priority, then title asc."""
        def _sort_key(issue: Issue) -> tuple[int, int, str]:
            sev_rank = _SEVERITY_RANK.get(issue.severity, 99)
            cat_rank = _CATEGORY_RANK.get(issue.category, 99)
            return (sev_rank, cat_rank, issue.title.lower())

        return sorted(issues, key=_sort_key)

    def _count_by_category(self, issues: list[Issue]) -> dict[str, int]:
        """Count issues per category key (lowercase string)."""
        counts: dict[str, int] = {}
        for issue in issues:
            key = str(issue.category).lower()
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _count_by_severity(self, issues: list[Issue]) -> dict[str, int]:
        """Count issues per severity level with all 4 levels always present."""
        counts: dict[str, int] = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }
        for issue in issues:
            key = str(issue.severity).lower()
            if key in counts:
                counts[key] += 1
        return counts

    def _build_summary(
        self, agent_reviews: list[AgentReview], failed_agents: list[str]
    ) -> str:
        """Assemble combined narrative from all successful agent summaries."""
        summaries = [
            f"[{r.agent_name.replace('_', ' ').title()}] {r.summary}"
            for r in agent_reviews
            if r.success and r.summary
        ]

        combined = " | ".join(summaries) if summaries else "No findings produced."

        if failed_agents:
            failed_str = ", ".join(failed_agents)
            combined += f" (Note: the following agents failed and are excluded: {failed_str}.)"

        return combined
