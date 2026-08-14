"""
score_engine.py
===============
Review Score Engine for Phase 6 Multi-Agent AI Code Review.

Responsibilities:
- Accept a ``FinalReview`` (produced by ``ReviewAggregator``) with ``overall_score=-1``.
- Compute a 0–100 quality score using configurable per-severity deduction weights.
- Populate ``FinalReview.overall_score`` and return the updated model.

Scoring model (configurable — documented as a heuristic, not scientific):
    Start from 100 (perfect).
    For each finding:
        CRITICAL  → -25 points
        HIGH      → -15 points
        MEDIUM    →  -7 points
        LOW       →  -2 points
    Floor at 0 (cannot go negative).

Design decisions:
- Weights are stored in a ``ScoringWeights`` dataclass so they can be overridden
  per-request or via config without modifying application code.
- The engine NEVER mutates the input ``FinalReview`` in-place; it returns a new
  instance with ``overall_score`` set.
- Scoring is intentionally simple and transparent. The spec explicitly states:
  "avoid pretending the score is scientifically accurate."
- A ``ScoreBreakdown`` is also returned for logging and debugging without having
  to reparse the FinalReview.

Author : AI Code Review Bot — Phase 6 (Stage 6.11)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.models.agent_models import FinalReview
from app.models.review_models import Severity

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configurable Scoring Weights
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScoringWeights:
    """Per-severity score deduction weights.

    All values are positive integers representing points subtracted from 100.
    Configured as a frozen dataclass so they can be safely shared and reused.

    Attributes:
        critical : Points deducted per CRITICAL finding.
        high     : Points deducted per HIGH finding.
        medium   : Points deducted per MEDIUM finding.
        low      : Points deducted per LOW finding.
    """
    critical: int = 25
    high: int = 15
    medium: int = 7
    low: int = 2


# Default weights — matches the spec's example values.
DEFAULT_WEIGHTS = ScoringWeights()


# ---------------------------------------------------------------------------
# Score Breakdown (for logging / traceability)
# ---------------------------------------------------------------------------

@dataclass
class ScoreBreakdown:
    """Detailed breakdown of how the final score was computed.

    Attributes:
        base_score         : Always 100.
        critical_count     : Number of CRITICAL findings.
        high_count         : Number of HIGH findings.
        medium_count       : Number of MEDIUM findings.
        low_count          : Number of LOW findings.
        critical_deduction : Total points deducted for CRITICAL findings.
        high_deduction     : Total points deducted for HIGH findings.
        medium_deduction   : Total points deducted for MEDIUM findings.
        low_deduction      : Total points deducted for LOW findings.
        total_deduction    : Sum of all deductions before floor.
        final_score        : Clamped 0–100 score.
        weights            : The ``ScoringWeights`` used for this computation.
    """
    base_score: int = 100
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    critical_deduction: int = 0
    high_deduction: int = 0
    medium_deduction: int = 0
    low_deduction: int = 0
    total_deduction: int = 0
    final_score: int = 100
    weights: ScoringWeights = field(default_factory=ScoringWeights)


# ---------------------------------------------------------------------------
# ScoreEngine
# ---------------------------------------------------------------------------

class ScoreEngine:
    """Computes a 0–100 quality score for a ``FinalReview``.

    Usage::

        engine = ScoreEngine()
        scored_review, breakdown = engine.score(final_review)
        print(scored_review.overall_score)  # e.g. 68
    """

    def __init__(self, weights: ScoringWeights = DEFAULT_WEIGHTS) -> None:
        self._weights = weights
        logger.info(
            "ScoreEngine initialized — weights: critical=-%d high=-%d medium=-%d low=-%d",
            weights.critical, weights.high, weights.medium, weights.low,
        )

    def score(self, review: FinalReview) -> tuple[FinalReview, ScoreBreakdown]:
        """Compute the quality score and return an updated ``FinalReview``.

        The input ``review`` is NOT mutated. A new ``FinalReview`` instance
        with ``overall_score`` populated is returned alongside a ``ScoreBreakdown``.

        Args:
            review: Aggregated ``FinalReview`` from the ``ReviewAggregator``
                    (``overall_score`` is expected to be -1 / unscored).

        Returns:
            Tuple of (scored_FinalReview, ScoreBreakdown).
        """
        breakdown = self._compute_breakdown(review)

        # Return a new FinalReview with overall_score populated (no mutation).
        scored = review.model_copy(update={"overall_score": breakdown.final_score})

        logger.info(
            "ScoreEngine result — score=%d total_issues=%d "
            "(critical=%d high=%d medium=%d low=%d) total_deduction=%d",
            breakdown.final_score,
            review.total_issues,
            breakdown.critical_count,
            breakdown.high_count,
            breakdown.medium_count,
            breakdown.low_count,
            breakdown.total_deduction,
        )

        return scored, breakdown

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _compute_breakdown(self, review: FinalReview) -> ScoreBreakdown:
        """Build a full ``ScoreBreakdown`` from the review's issues_by_severity."""
        sev = review.issues_by_severity

        critical_count = sev.get("critical", 0)
        high_count     = sev.get("high", 0)
        medium_count   = sev.get("medium", 0)
        low_count      = sev.get("low", 0)

        critical_deduction = critical_count * self._weights.critical
        high_deduction     = high_count     * self._weights.high
        medium_deduction   = medium_count   * self._weights.medium
        low_deduction      = low_count      * self._weights.low

        total_deduction = (
            critical_deduction + high_deduction + medium_deduction + low_deduction
        )

        final_score = max(0, 100 - total_deduction)

        return ScoreBreakdown(
            base_score=100,
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            critical_deduction=critical_deduction,
            high_deduction=high_deduction,
            medium_deduction=medium_deduction,
            low_deduction=low_deduction,
            total_deduction=total_deduction,
            final_score=final_score,
            weights=self._weights,
        )
