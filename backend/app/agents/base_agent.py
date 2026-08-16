"""
base_agent.py
=============
Abstract Base Agent contract for all specialized AI Code Review Agents (Phase 6).

Provides:
- Enforced category & agent name attributes.
- Shared diff pre-processing and validation (detecting empty diffs).
- Execution timing instrumentation in milliseconds.
- Standardized, fault-tolerant error isolation so one agent failure
  does not crash the entire review pipeline.

Author : AI Code Review Bot — Phase 6
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

from app.ai.gemini_service import GeminiService, get_gemini_service
from app.exceptions import EmptyDiffError
from app.models.agent_models import AgentCategory, AgentReview
from app.models.review_models import Issue, IssueCategory, ReviewRequest
from app.utils import detect_language_from_diff, normalise_diff

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all specialized review agents.

    Attributes:
        name     : Unique name identifying the agent (e.g. 'bug_agent').
        category : Primary AgentCategory taxonomy for this reviewer.
    """

    def __init__(
        self,
        name: str,
        category: AgentCategory,
        gemini_service: Optional[GeminiService] = None,
    ) -> None:
        self.name = name
        self.category = category
        self._gemini = gemini_service or get_gemini_service()
        logger.info("Agent '%s' [%s] initialized.", self.name, self.category.value)

    # ------------------------------------------------------------------
    # Public Review Contract
    # ------------------------------------------------------------------

    async def review(self, request: ReviewRequest) -> AgentReview:
        """Run specialized review on the provided ReviewRequest DTO.

        Performs shared pre-processing, measures execution time, and catches
        all internal exceptions to ensure error isolation.

        Args:
            request: Validated ``ReviewRequest`` input DTO.

        Returns:
            Structured ``AgentReview`` containing findings or failure details.

        Raises:
            EmptyDiffError: Raised if the diff is empty after normalisation.
        """
        start_ts = time.monotonic()

        # ── Pre-process & Validate ─────────────────────────────────────
        diff, language_hint = self._pre_process(request)

        logger.info(
            "Agent '%s' starting review — diff_len=%d language=%s",
            self.name,
            len(diff),
            language_hint or "unknown",
        )

        # ── Execute Specialized Agent Logic ────────────────────────────
        try:
            summary, issues = await self._execute_review(
                diff=diff,
                pr_title=request.pr_title,
                pr_description=request.pr_description,
                language_hint=language_hint,
            )
            elapsed_ms = (time.monotonic() - start_ts) * 1000.0

            logger.info(
                "Agent '%s' finished — issues=%d duration=%.2fms",
                self.name,
                len(issues),
                elapsed_ms,
            )

            return AgentReview(
                agent_name=self.name,
                category=self.category,
                issues=issues,
                summary=summary,
                execution_time_ms=round(elapsed_ms, 2),
                success=True,
                error=None,
            )

        except EmptyDiffError:
            raise  # Reraise validation errors for caller awareness

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start_ts) * 1000.0
            logger.error("Agent '%s' failed: %s", self.name, exc, exc_info=True)

            return AgentReview(
                agent_name=self.name,
                category=self.category,
                issues=[],
                summary=f"Agent '{self.name}' failed during review execution.",
                execution_time_ms=round(elapsed_ms, 2),
                success=False,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Abstract Execution Hook
    # ------------------------------------------------------------------

    @abstractmethod
    async def _execute_review(
        self,
        diff: str,
        pr_title: Optional[str],
        pr_description: Optional[str],
        language_hint: Optional[str],
    ) -> tuple[str, list[Issue]]:
        """Internal execution hook implemented by concrete specialized agents.

        Args:
            diff           : Normalised unified diff string.
            pr_title       : PR title context string.
            pr_description : PR description context string.
            language_hint  : Primary programming language hint.

        Returns:
            Tuple of (category_summary, list_of_issues).
        """
        ...

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    def _pre_process(self, request: ReviewRequest) -> tuple[str, Optional[str]]:
        """Validate and normalise the incoming diff string."""
        diff = normalise_diff(request.diff)

        if not diff.strip():
            raise EmptyDiffError(
                f"Agent '{self.name}' received an empty diff after normalisation."
            )

        language_hint = request.language_hint or detect_language_from_diff(diff)
        return diff, language_hint

    async def _run_specialized_review(
        self,
        user_prompt: str,
        system_prompt: str,
        target_category: IssueCategory,
    ) -> tuple[str, list[Issue]]:
        """Helper for concrete agents to execute custom Gemini reviews and enforce issue category boundaries."""
        summary, issues = await self._gemini.generate_custom_review(
            user_prompt=user_prompt,
            system_instruction=system_prompt,
        )
        for issue in issues:
            issue.category = target_category
        return summary, issues

