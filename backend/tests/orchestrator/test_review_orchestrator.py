"""
test_review_orchestrator.py
============================
Unit tests for Stage 6.7/6.8 ReviewOrchestrator.

Stage 6.7 tests (sequential contract):
- All 5 agents are run and their results collected.
- Deterministic result order matches agent registry.
- A failing agent does NOT stop the pipeline.
- All agents failing returns 5 failure reviews.

Stage 6.8 additions (parallel contract):
- All 5 agent coroutines are launched concurrently (asyncio.gather).
- An unhandled raw exception escaping agent.review() is normalized to
  AgentReview(success=False) without crashing the pipeline.
- Parallel results are returned in the same deterministic order as the registry.

All agent Gemini calls are mocked — no real API calls are made.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.agent_models import AgentCategory, AgentReview
from app.models.review_models import Issue, IssueCategory, ReviewRequest, Severity
from app.orchestrator.review_orchestrator import ReviewOrchestrator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_DIFF = (
    "--- a/main.py\n+++ b/main.py\n"
    "@@ -1,4 +1,4 @@\n"
    "-def foo():\n"
    "+def foo(x: int) -> int:\n"
    "+    return x * 2\n"
)


def _make_success_review(name: str, category: AgentCategory, n_issues: int = 1) -> AgentReview:
    """Build a mock successful AgentReview with n_issues."""
    issues = [
        Issue(
            title=f"Issue {i} from {name}",
            severity=Severity.MEDIUM,
            line=i + 1,
            category=IssueCategory.BUG,
            description=f"Description for issue {i} from {name}.",
            suggestion=f"Fix suggestion {i} from {name}.",
        )
        for i in range(n_issues)
    ]
    return AgentReview(
        agent_name=name,
        category=category,
        issues=issues,
        summary=f"{name} completed successfully.",
        execution_time_ms=42.0,
        success=True,
        error=None,
    )


def _make_failure_review(name: str, category: AgentCategory) -> AgentReview:
    """Build a mock failed AgentReview."""
    return AgentReview(
        agent_name=name,
        category=category,
        issues=[],
        summary=f"Agent '{name}' failed during review execution.",
        execution_time_ms=5.0,
        success=False,
        error=f"Simulated failure in {name}",
    )


def _patch_all_agents(reviews: list[AgentReview]):
    """Context manager factory that patches all 5 agent classes."""
    names = ["BugAgent", "SecurityAgent", "PerformanceAgent", "DocumentationAgent", "TestingAgent"]
    patches = [patch(f"app.orchestrator.review_orchestrator.{n}") for n in names]
    return patches, reviews


# ---------------------------------------------------------------------------
# Stage 6.7 Tests — Correctness of Collection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_orchestrator_runs_all_five_agents():
    """Verify all 5 agents are executed and exactly 5 reviews are returned."""
    mock_svc = MagicMock()
    agent_reviews = [
        _make_success_review("bug_agent", AgentCategory.BUG, n_issues=2),
        _make_success_review("security_agent", AgentCategory.SECURITY, n_issues=1),
        _make_success_review("performance_agent", AgentCategory.PERFORMANCE, n_issues=0),
        _make_success_review("documentation_agent", AgentCategory.DOCUMENTATION, n_issues=1),
        _make_success_review("testing_agent", AgentCategory.TESTING, n_issues=3),
    ]

    with (
        patch("app.orchestrator.review_orchestrator.BugAgent") as MockBug,
        patch("app.orchestrator.review_orchestrator.SecurityAgent") as MockSec,
        patch("app.orchestrator.review_orchestrator.PerformanceAgent") as MockPerf,
        patch("app.orchestrator.review_orchestrator.DocumentationAgent") as MockDoc,
        patch("app.orchestrator.review_orchestrator.TestingAgent") as MockTest,
    ):
        for MockCls, review in zip(
            [MockBug, MockSec, MockPerf, MockDoc, MockTest], agent_reviews
        ):
            instance = MagicMock()
            instance.name = review.agent_name
            instance.category = review.category
            instance.review = AsyncMock(return_value=review)
            MockCls.return_value = instance

        orchestrator = ReviewOrchestrator(gemini_service=mock_svc)
        results = await orchestrator.run(ReviewRequest(diff=VALID_DIFF, pr_title="Test PR"))

    assert len(results) == 5
    assert all(isinstance(r, AgentReview) for r in results)


@pytest.mark.asyncio
async def test_orchestrator_collects_correct_results_in_order():
    """Verify results from each agent are collected in deterministic registry order."""
    mock_svc = MagicMock()
    reviews = [
        _make_success_review("bug_agent", AgentCategory.BUG, n_issues=2),
        _make_success_review("security_agent", AgentCategory.SECURITY, n_issues=1),
        _make_success_review("performance_agent", AgentCategory.PERFORMANCE, n_issues=0),
        _make_success_review("documentation_agent", AgentCategory.DOCUMENTATION, n_issues=1),
        _make_success_review("testing_agent", AgentCategory.TESTING, n_issues=3),
    ]

    with (
        patch("app.orchestrator.review_orchestrator.BugAgent") as MockBug,
        patch("app.orchestrator.review_orchestrator.SecurityAgent") as MockSec,
        patch("app.orchestrator.review_orchestrator.PerformanceAgent") as MockPerf,
        patch("app.orchestrator.review_orchestrator.DocumentationAgent") as MockDoc,
        patch("app.orchestrator.review_orchestrator.TestingAgent") as MockTest,
    ):
        for MockCls, review in zip(
            [MockBug, MockSec, MockPerf, MockDoc, MockTest], reviews
        ):
            instance = MagicMock()
            instance.name = review.agent_name
            instance.category = review.category
            instance.review = AsyncMock(return_value=review)
            MockCls.return_value = instance

        orchestrator = ReviewOrchestrator(gemini_service=mock_svc)
        results = await orchestrator.run(ReviewRequest(diff=VALID_DIFF))

    assert results[0].agent_name == "bug_agent"
    assert results[1].agent_name == "security_agent"
    assert results[2].agent_name == "performance_agent"
    assert results[3].agent_name == "documentation_agent"
    assert results[4].agent_name == "testing_agent"
    assert len(results[0].issues) == 2
    assert len(results[2].issues) == 0
    assert len(results[4].issues) == 3


@pytest.mark.asyncio
async def test_orchestrator_continues_after_single_agent_failure():
    """Verify a single agent failure (AgentReview success=False) does not stop others."""
    mock_svc = MagicMock()
    reviews = [
        _make_failure_review("bug_agent", AgentCategory.BUG),
        _make_success_review("security_agent", AgentCategory.SECURITY, n_issues=1),
        _make_success_review("performance_agent", AgentCategory.PERFORMANCE, n_issues=0),
        _make_success_review("documentation_agent", AgentCategory.DOCUMENTATION, n_issues=2),
        _make_success_review("testing_agent", AgentCategory.TESTING, n_issues=1),
    ]

    with (
        patch("app.orchestrator.review_orchestrator.BugAgent") as MockBug,
        patch("app.orchestrator.review_orchestrator.SecurityAgent") as MockSec,
        patch("app.orchestrator.review_orchestrator.PerformanceAgent") as MockPerf,
        patch("app.orchestrator.review_orchestrator.DocumentationAgent") as MockDoc,
        patch("app.orchestrator.review_orchestrator.TestingAgent") as MockTest,
    ):
        for MockCls, review in zip(
            [MockBug, MockSec, MockPerf, MockDoc, MockTest], reviews
        ):
            instance = MagicMock()
            instance.name = review.agent_name
            instance.category = review.category
            instance.review = AsyncMock(return_value=review)
            MockCls.return_value = instance

        orchestrator = ReviewOrchestrator(gemini_service=mock_svc)
        results = await orchestrator.run(ReviewRequest(diff=VALID_DIFF))

    assert len(results) == 5
    assert results[0].success is False
    assert results[0].error == "Simulated failure in bug_agent"
    assert all(r.success for r in results[1:])


@pytest.mark.asyncio
async def test_orchestrator_handles_all_agents_failing():
    """Verify all-failure case still returns 5 AgentReview entries."""
    mock_svc = MagicMock()
    reviews = [
        _make_failure_review("bug_agent", AgentCategory.BUG),
        _make_failure_review("security_agent", AgentCategory.SECURITY),
        _make_failure_review("performance_agent", AgentCategory.PERFORMANCE),
        _make_failure_review("documentation_agent", AgentCategory.DOCUMENTATION),
        _make_failure_review("testing_agent", AgentCategory.TESTING),
    ]

    with (
        patch("app.orchestrator.review_orchestrator.BugAgent") as MockBug,
        patch("app.orchestrator.review_orchestrator.SecurityAgent") as MockSec,
        patch("app.orchestrator.review_orchestrator.PerformanceAgent") as MockPerf,
        patch("app.orchestrator.review_orchestrator.DocumentationAgent") as MockDoc,
        patch("app.orchestrator.review_orchestrator.TestingAgent") as MockTest,
    ):
        for MockCls, review in zip(
            [MockBug, MockSec, MockPerf, MockDoc, MockTest], reviews
        ):
            instance = MagicMock()
            instance.name = review.agent_name
            instance.category = review.category
            instance.review = AsyncMock(return_value=review)
            MockCls.return_value = instance

        orchestrator = ReviewOrchestrator(gemini_service=mock_svc)
        results = await orchestrator.run(ReviewRequest(diff=VALID_DIFF))

    assert len(results) == 5
    assert all(r.success is False for r in results)
    assert all(r.issues == [] for r in results)


# ---------------------------------------------------------------------------
# Stage 6.8 Tests — Parallel-specific behaviour
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_orchestrator_runs_agents_concurrently():
    """Verify agents are dispatched concurrently via asyncio.gather.

    Strategy: give each agent a short sleep delay. If run sequentially total
    time would be ~5 × delay. Concurrently it should be ~1 × delay.
    """
    mock_svc = MagicMock()
    DELAY = 0.05  # 50 ms per agent

    async def _delayed_review(request):
        await asyncio.sleep(DELAY)
        return _make_success_review("agent", AgentCategory.BUG, n_issues=0)

    with (
        patch("app.orchestrator.review_orchestrator.BugAgent") as MockBug,
        patch("app.orchestrator.review_orchestrator.SecurityAgent") as MockSec,
        patch("app.orchestrator.review_orchestrator.PerformanceAgent") as MockPerf,
        patch("app.orchestrator.review_orchestrator.DocumentationAgent") as MockDoc,
        patch("app.orchestrator.review_orchestrator.TestingAgent") as MockTest,
    ):
        for idx, (MockCls, name) in enumerate(zip(
            [MockBug, MockSec, MockPerf, MockDoc, MockTest],
            ["bug_agent", "security_agent", "performance_agent", "documentation_agent", "testing_agent"],
        )):
            instance = MagicMock()
            instance.name = name
            instance.category = AgentCategory.BUG
            instance.review = _delayed_review
            MockCls.return_value = instance

        orchestrator = ReviewOrchestrator(gemini_service=mock_svc)

        import time as _time
        start = _time.monotonic()
        results = await orchestrator.run(ReviewRequest(diff=VALID_DIFF))
        elapsed = _time.monotonic() - start

    assert len(results) == 5
    # Parallel: should finish in ~DELAY, not ~5×DELAY (allow 3× margin for CI overhead)
    assert elapsed < DELAY * 3, (
        f"Orchestrator took {elapsed:.3f}s — expected parallel execution ~{DELAY:.2f}s"
    )


@pytest.mark.asyncio
async def test_orchestrator_normalizes_unhandled_raw_exception():
    """Verify a raw BaseException escaping agent.review() is wrapped into AgentReview(success=False).

    This tests the asyncio.gather normalization layer — the last line of defense
    beyond agent-level error isolation.
    """
    mock_svc = MagicMock()

    success_review = _make_success_review("security_agent", AgentCategory.SECURITY, n_issues=1)

    with (
        patch("app.orchestrator.review_orchestrator.BugAgent") as MockBug,
        patch("app.orchestrator.review_orchestrator.SecurityAgent") as MockSec,
        patch("app.orchestrator.review_orchestrator.PerformanceAgent") as MockPerf,
        patch("app.orchestrator.review_orchestrator.DocumentationAgent") as MockDoc,
        patch("app.orchestrator.review_orchestrator.TestingAgent") as MockTest,
    ):
        # BugAgent raises raw RuntimeError (bypasses agent-level isolation)
        bug_instance = MagicMock()
        bug_instance.name = "bug_agent"
        bug_instance.category = AgentCategory.BUG
        bug_instance.review = AsyncMock(side_effect=RuntimeError("Catastrophic unhandled error"))
        MockBug.return_value = bug_instance

        # All other agents succeed normally
        for MockCls, (name, cat) in zip(
            [MockSec, MockPerf, MockDoc, MockTest],
            [
                ("security_agent", AgentCategory.SECURITY),
                ("performance_agent", AgentCategory.PERFORMANCE),
                ("documentation_agent", AgentCategory.DOCUMENTATION),
                ("testing_agent", AgentCategory.TESTING),
            ],
        ):
            r = _make_success_review(name, cat, n_issues=0)
            instance = MagicMock()
            instance.name = name
            instance.category = cat
            instance.review = AsyncMock(return_value=r)
            MockCls.return_value = instance

        orchestrator = ReviewOrchestrator(gemini_service=mock_svc)
        results = await orchestrator.run(ReviewRequest(diff=VALID_DIFF))

    assert len(results) == 5

    # BugAgent slot normalized to failure
    assert results[0].agent_name == "bug_agent"
    assert results[0].success is False
    assert "Catastrophic unhandled error" in results[0].error

    # All other agents succeeded
    assert all(r.success for r in results[1:])
