"""
review_orchestrator.py
======================
Parallel Async Review Orchestrator for Phase 6 Multi-Agent AI Code Review.

Responsibilities:
- Own a fixed registry of all 5 specialized agents (Bug, Security, Performance,
  Documentation, Testing).
- Execute ALL agents concurrently via ``asyncio.gather(return_exceptions=True)``.
- Convert any raw ``BaseException`` that escapes an agent into a safe
  ``AgentReview(success=False)`` so the pipeline never crashes.
- Preserve the deterministic agent order in the returned list regardless of which
  agents finish first.
- Return the complete ``list[AgentReview]`` to the caller (Aggregator).

Design decisions:
- Stage 6.8 replaces the Stage 6.7 sequential ``for`` loop with ``asyncio.gather``
  so all agents call Gemini simultaneously, cutting wall-clock time from ~5× to ~1×.
- ``return_exceptions=True`` means gather never raises — every slot is either an
  ``AgentReview`` or an unhandled ``BaseException`` which we normalize here.
- The orchestrator has NO knowledge of scoring, deduplication, or GitHub publishing;
  those belong to the Aggregator and the Phase 5 adapter respectively.

Author : AI Code Review Bot — Phase 6 (Stage 6.8)
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional, Union

from app.agents.base_agent import BaseAgent
from app.agents.bug_agent import BugAgent
from app.agents.documentation_agent import DocumentationAgent
from app.agents.performance_agent import PerformanceAgent
from app.agents.security_agent import SecurityAgent
from app.agents.testing_agent import TestingAgent
from app.ai.gemini_service import GeminiService, get_gemini_service
from app.models.agent_models import AgentCategory, AgentReview
from app.models.review_models import ReviewRequest

logger = logging.getLogger(__name__)


class ReviewOrchestrator:
    """Coordinates parallel async execution of all specialized review agents.

    All 5 agents are dispatched simultaneously with ``asyncio.gather``.
    Individual agent failures are absorbed and normalized to
    ``AgentReview(success=False)`` — the pipeline always returns exactly 5 entries.

    Attributes:
        _agents : Ordered list of BaseAgent instances to run concurrently.
    """

    def __init__(self, gemini_service: Optional[GeminiService] = None) -> None:
        svc = gemini_service or get_gemini_service()

        # Fixed registry — deterministic order preserved in results.
        self._agents: list[BaseAgent] = [
            BugAgent(gemini_service=svc),
            SecurityAgent(gemini_service=svc),
            PerformanceAgent(gemini_service=svc),
            DocumentationAgent(gemini_service=svc),
            TestingAgent(gemini_service=svc),
        ]

        logger.info(
            "ReviewOrchestrator initialized with %d agents (parallel mode): %s",
            len(self._agents),
            [a.name for a in self._agents],
        )

    async def run(self, request: ReviewRequest) -> list[AgentReview]:
        """Execute all agents concurrently and collect their reviews.

        Uses ``asyncio.gather(return_exceptions=True)`` so:
        - All agents start simultaneously.
        - A crash in one agent does NOT cancel the others.
        - Any raw exception that slips past an agent's own error handling is
          safely wrapped into an ``AgentReview(success=False)`` here.

        Args:
            request: Validated ``ReviewRequest`` DTO containing the diff and context.

        Returns:
            Ordered ``list[AgentReview]`` — one entry per agent, always length 5,
            in the same order as the internal ``_agents`` registry.
        """
        pipeline_start = time.monotonic()

        logger.info(
            "Orchestrator starting parallel review — agents=%d diff_len=%d",
            len(self._agents),
            len(request.diff),
        )

        # Dispatch all agents simultaneously
        raw_results: list[Union[AgentReview, BaseException]] = await asyncio.gather(
            *[agent.review(request) for agent in self._agents],
            return_exceptions=True,
        )

        # Normalize: wrap any unhandled exception into a failed AgentReview
        results: list[AgentReview] = []
        for agent, outcome in zip(self._agents, raw_results):
            if isinstance(outcome, AgentReview):
                results.append(outcome)
            else:
                # outcome is a BaseException that escaped agent.review()
                error_msg = str(outcome) if outcome else "Unknown error"
                logger.error(
                    "Agent '%s' raised unhandled exception: %s",
                    agent.name,
                    error_msg,
                    exc_info=outcome if isinstance(outcome, Exception) else None,
                )
                results.append(
                    AgentReview(
                        agent_name=agent.name,
                        category=agent.category,
                        issues=[],
                        summary=f"Agent '{agent.name}' encountered an unhandled error.",
                        execution_time_ms=0.0,
                        success=False,
                        error=error_msg,
                    )
                )

        pipeline_elapsed = (time.monotonic() - pipeline_start) * 1000.0
        successful = sum(1 for r in results if r.success)
        total_issues = sum(len(r.issues) for r in results)

        logger.info(
            "Orchestrator parallel pipeline complete — agents=%d successful=%d "
            "failed=%d total_issues=%d duration=%.2fms",
            len(results),
            successful,
            len(results) - successful,
            total_issues,
            pipeline_elapsed,
        )

        return results
