"""
phase5_adapter.py
=================
Phase 5 Adapter for Phase 6 Multi-Agent AI Code Review.

Bridges the gap between the new multi-agent pipeline output (``FinalReview``)
and the existing Phase 5 publisher layer (which expects ``ReviewResponse``).

Architecture per the spec:

    MultiAgentFinalReview (Phase 6)
            ↓
    Phase5Adapter.adapt()         ← THIS FILE
            ↓
    ReviewResponse (Phase 5)
            ↓
    Existing ReviewFormatter      (Phase 5 — UNCHANGED)
            ↓
    Existing ReviewPublisher      (Phase 5 — UNCHANGED)
            ↓
    GitHub PR Review

Rules:
- Do NOT modify ``ReviewResponse``, ``ReviewFormatter``, or ``ReviewPublisher``.
- Do NOT modify any Phase 5 service code.
- The adapter is the ONLY layer that knows about both Phase 5 and Phase 6 types.
- If ``FinalReview`` has zero issues, produce a clean ``ReviewResponse`` summary
  so the GitHub review is still published (not silently suppressed).
- Inject the quality score into the summary text so it appears on the PR.

Author : AI Code Review Bot — Phase 6 (Stage 6.12)
"""

from __future__ import annotations

import logging

from app.models.agent_models import FinalReview
from app.models.review_models import ReviewResponse

logger = logging.getLogger(__name__)


class Phase5Adapter:
    """Converts a ``FinalReview`` into a Phase 5-compatible ``ReviewResponse``.

    This is a pure, stateless transformation — no I/O, no Gemini calls.

    Usage::

        adapter = Phase5Adapter()
        review_response = adapter.adapt(final_review)
        # Pass review_response to the existing PublishService / ReviewFormatter
    """

    def adapt(self, final_review: FinalReview) -> ReviewResponse:
        """Convert a scored ``FinalReview`` into a ``ReviewResponse``.

        Args:
            final_review: Fully populated and scored ``FinalReview``
                          (``overall_score`` must already be set by ScoreEngine).

        Returns:
            A ``ReviewResponse`` with the same issues and an enriched summary
            that includes the quality score and agent attribution.
        """
        summary = self._build_summary(final_review)

        response = ReviewResponse(
            summary=summary,
            issues=final_review.issues,          # already deduplicated + ranked
            reviewed_chunks=len(final_review.agent_results) or 1,
        )

        logger.info(
            "Phase5Adapter adapted FinalReview → ReviewResponse — "
            "score=%d issues=%d reviewed_chunks=%d",
            final_review.overall_score,
            response.total_issues,
            response.reviewed_chunks,
        )

        return response

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_summary(self, final_review: FinalReview) -> str:
        """Assemble the PR-visible summary from FinalReview fields.

        Includes:
        - Quality score with emoji badge.
        - Per-severity issue counts.
        - Per-category issue counts.
        - Multi-agent attribution.
        - Failed agent warnings (if any).
        - The aggregated agent narrative.
        """
        score = final_review.overall_score
        total = final_review.total_issues

        # ── Score badge line ───────────────────────────────────────────
        score_badge = self._score_badge(score)
        score_line = f"## 🤖 Multi-Agent Code Review — Quality Score: {score}/100 {score_badge}"

        # ── Issue count line ───────────────────────────────────────────
        if total == 0:
            count_line = "✅ **No issues detected.** The diff looks clean across all review dimensions."
        else:
            sev = final_review.issues_by_severity
            parts = []
            if sev.get("critical", 0):
                parts.append(f"🔴 **{sev['critical']} Critical**")
            if sev.get("high", 0):
                parts.append(f"🟠 **{sev['high']} High**")
            if sev.get("medium", 0):
                parts.append(f"🟡 {sev['medium']} Medium")
            if sev.get("low", 0):
                parts.append(f"🔵 {sev['low']} Low")
            count_line = f"**{total} issue{'s' if total != 1 else ''} found:** " + " · ".join(parts)

        # ── Agent attribution line ─────────────────────────────────────
        agent_count = len(final_review.successful_agents)
        failed_count = len(final_review.failed_agents)
        agent_line = (
            f"_Reviewed by {agent_count} specialized agent{'s' if agent_count != 1 else ''}: "
            + ", ".join(final_review.successful_agents)
            + "._"
        )
        if failed_count:
            failed_names = ", ".join(final_review.failed_agents)
            agent_line += f" ⚠️ _The following agents encountered errors: {failed_names}._"

        # ── Narrative summary ──────────────────────────────────────────
        narrative = final_review.summary.strip() if final_review.summary else ""
        # Trim to keep GitHub review body manageable
        if len(narrative) > 1500:
            narrative = narrative[:1500] + "… _(truncated)_"

        # ── Assemble ───────────────────────────────────────────────────
        parts_list = [score_line, count_line, agent_line]
        if narrative and narrative != "No findings produced.":
            parts_list.append(f"\n---\n{narrative}")

        return "\n\n".join(parts_list)

    @staticmethod
    def _score_badge(score: int) -> str:
        """Return an emoji quality badge based on the score range."""
        if score >= 90:
            return "🟢"
        if score >= 70:
            return "🟡"
        if score >= 50:
            return "🟠"
        return "🔴"
