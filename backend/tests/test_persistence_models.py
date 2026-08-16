"""
test_persistence_models.py
===========================
Unit tests for Stage 7.1 PersistedReview & ReviewStatus models.

Tests cover:
- Valid model creation.
- Serialization and deserialization (dict/JSON roundtrip).
- Status validation and normalisation.
- Missing required fields validation.
- generate_review_key deterministic formatting.
- from_final_review factory mapping (COMPLETED, PARTIAL, FAILED statuses).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.agent_models import AgentCategory, AgentReview, FinalReview
from app.models.persistence_models import (
    PersistedReview,
    ReviewStatus,
    generate_review_key,
)
from app.models.review_models import Issue, IssueCategory, Severity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_issue() -> Issue:
    return Issue(
        title="SQL Injection vulnerability",
        severity=Severity.CRITICAL,
        line=42,
        category=IssueCategory.SECURITY,
        description="Unsanitized string formatting in database query.",
        suggestion="Use parameterized query.",
    )


def _sample_final_review(
    score: int = 85,
    successful_agents: list[str] | None = None,
    failed_agents: list[str] | None = None,
) -> FinalReview:
    issue = _sample_issue()
    succ = successful_agents if successful_agents is not None else ["bug_agent", "security_agent"]
    fail = failed_agents if failed_agents is not None else []

    agent_reviews = [
        AgentReview(
            agent_name=name,
            category=AgentCategory.BUG,
            issues=[issue] if name == "bug_agent" else [],
            summary=f"{name} review complete",
            execution_time_ms=100.0,
            success=True,
        )
        for name in succ
    ] + [
        AgentReview(
            agent_name=name,
            category=AgentCategory.SECURITY,
            issues=[],
            summary=f"{name} failed",
            execution_time_ms=50.0,
            success=False,
            error="API error",
        )
        for name in fail
    ]

    return FinalReview(
        overall_score=score,
        summary="Overall code review summary",
        issues=[issue],
        total_issues=1,
        issues_by_category={"security": 1},
        issues_by_severity={"critical": 1, "high": 0, "medium": 0, "low": 0},
        agent_results=agent_reviews,
        successful_agents=succ,
        failed_agents=fail,
        execution_time_ms=250.0,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_generate_review_key_format():
    """Verify generate_review_key generates deterministic lowercase key."""
    key = generate_review_key("TestOwner", "TestRepo", 42, "a1b2c3d4")
    assert key == "testowner/testrepo#42@a1b2c3d4"

    key_no_sha = generate_review_key("Owner", "Repo", 10)
    assert key_no_sha == "owner/repo#10@head"


def test_persisted_review_valid_instantiation():
    """Verify valid PersistedReview instantiation and field defaults."""
    doc = PersistedReview(
        review_key="owner/repo#1@sha123",
        repository="owner/repo",
        owner="owner",
        repo_name="repo",
        pull_request_number=1,
        overall_score=90,
    )
    assert doc.review_key == "owner/repo#1@sha123"
    assert doc.review_status == ReviewStatus.COMPLETED
    assert doc.author == "unknown"
    assert doc.created_at is not None


def test_persisted_review_serialization_roundtrip():
    """Verify dict/JSON serialization roundtrip preserves data."""
    issue = _sample_issue()
    doc = PersistedReview(
        review_key="owner/repo#5@def456",
        repository="owner/repo",
        owner="owner",
        repo_name="repo",
        pull_request_number=5,
        overall_score=75,
        issues=[issue],
        severity_counts={"critical": 1},
    )

    dumped_dict = doc.model_dump()
    reloaded = PersistedReview.model_validate(dumped_dict)

    assert reloaded.review_key == doc.review_key
    assert reloaded.overall_score == 75
    assert len(reloaded.issues) == 1
    assert reloaded.issues[0].title == issue.title


def test_persisted_review_status_normalisation():
    """Verify lowercase/mixed-case status strings normalise to ReviewStatus enum."""
    doc = PersistedReview(
        review_key="owner/repo#1@head",
        repository="owner/repo",
        owner="owner",
        repo_name="repo",
        pull_request_number=1,
        review_status="completed",  # type: ignore
    )
    assert doc.review_status == ReviewStatus.COMPLETED


def test_persisted_review_invalid_status_raises_error():
    """Verify invalid status string raises ValidationError."""
    with pytest.raises(ValidationError):
        PersistedReview(
            review_key="owner/repo#1@head",
            repository="owner/repo",
            owner="owner",
            repo_name="repo",
            pull_request_number=1,
            review_status="INVALID_STATUS",  # type: ignore
        )


def test_persisted_review_missing_required_fields():
    """Verify missing required fields raise ValidationError."""
    with pytest.raises(ValidationError):
        PersistedReview(
            owner="owner",
            repo_name="repo",
            # missing review_key, repository, pull_request_number
        )


def test_from_final_review_factory_completed():
    """Verify from_final_review mapping when all agents succeed."""
    fr = _sample_final_review(successful_agents=["bug_agent", "security_agent"], failed_agents=[])
    doc = PersistedReview.from_final_review(
        final_review=fr,
        owner="acme",
        repo_name="widget",
        pull_request_number=99,
        commit_sha="fedcba98",
        author="alice",
    )

    assert doc.review_key == "acme/widget#99@fedcba98"
    assert doc.repository == "acme/widget"
    assert doc.author == "alice"
    assert doc.overall_score == 85
    assert doc.total_issues == 1
    assert doc.review_status == ReviewStatus.COMPLETED
    assert doc.agent_counts == {"bug_agent": 1, "security_agent": 0}


def test_from_final_review_factory_partial_and_failed():
    """Verify status mapping for partial and complete agent failures."""
    fr_partial = _sample_final_review(successful_agents=["bug_agent"], failed_agents=["security_agent"])
    doc_partial = PersistedReview.from_final_review(
        final_review=fr_partial, owner="acme", repo_name="widget", pull_request_number=100
    )
    assert doc_partial.review_status == ReviewStatus.PARTIAL

    fr_failed = _sample_final_review(successful_agents=[], failed_agents=["bug_agent", "security_agent"])
    doc_failed = PersistedReview.from_final_review(
        final_review=fr_failed, owner="acme", repo_name="widget", pull_request_number=101
    )
    assert doc_failed.review_status == ReviewStatus.FAILED
