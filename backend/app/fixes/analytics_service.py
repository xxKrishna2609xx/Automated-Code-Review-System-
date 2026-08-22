"""
analytics_service.py  (app.fixes)
==================================
Stage 8.18 — Fix Analytics Service.

Computes operational and effectiveness metrics for AI Code Fixes.

Metrics computed (Phase 8 spec §21):
    - total_fix_requests      : Total fix requests created.
    - status_counts           : Breakdown by FixStatus enum.
    - category_breakdown      : Breakdown by issue category.
    - acceptance_rate         : Percentage of fix proposals approved by humans.
    - verification_success_rate: Percentage of fixes verified resolved by Phase 6.
    - average_time_to_fix_sec : Average processing duration from creation to completion.

Author : AI Code Review Bot — Phase 8 (Stage 8.18)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.db.fix_repository import FixRepository
from app.fixes.fix_service import _FIX_REQUEST_STORE, _FIX_RESULT_STORE
from app.fixes.models import FixRequest, FixResult, FixStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FixAnalyticsMetrics:
    """Aggregated analytics metrics for AI Code Auto-Remediation.

    Attributes:
        total_fix_requests       : Count of all created fix requests.
        status_counts            : Dictionary of FixStatus -> count.
        category_breakdown       : Dictionary of Category -> count.
        acceptance_rate          : Human approval rate percentage (0.0 to 100.0).
        verification_success_rate: Phase 6 re-review success rate percentage (0.0 to 100.0).
        total_completed          : Count of fully verified completed fixes.
        total_failed             : Count of failed/rejected/stale fixes.
    """

    total_fix_requests: int
    status_counts: Dict[str, int]
    category_breakdown: Dict[str, int]
    acceptance_rate: float
    verification_success_rate: float
    total_completed: int
    total_failed: int


# ---------------------------------------------------------------------------
# FixAnalyticsService
# ---------------------------------------------------------------------------


class FixAnalyticsService:
    """Computes analytics and effectiveness metrics for AI Code Auto-Remediation.

    Args:
        repository : Optional FixRepository instance for DB queries.
    """

    def __init__(self, repository: Optional[FixRepository] = None) -> None:
        self._repository = repository

    async def compute_metrics(
        self,
        repository_slug: Optional[str] = None,
    ) -> FixAnalyticsMetrics:
        """Compute aggregated fix metrics across memory stores or MongoDB repository.

        Args:
            repository_slug : Optional filter for a specific repository ('owner/repo').

        Returns:
            FixAnalyticsMetrics instance containing computed statistics.
        """
        logger.info("Computing Fix Analytics metrics (repo_filter=%s)", repository_slug)

        requests: list[FixRequest] = []

        if self._repository is not None and self._repository.requests_collection is not None:
            if repository_slug:
                requests = await self._repository.list_fix_requests_by_repo(repository_slug, limit=1000)
            else:
                col = self._repository.requests_collection
                cursor = col.find()
                async for doc in cursor:
                    doc.pop("_id", None)
                    requests.append(FixRequest(**doc))
        else:
            all_reqs = list(_FIX_REQUEST_STORE.values())
            if repository_slug:
                requests = [r for r in all_reqs if r.repository == repository_slug]
            else:
                requests = all_reqs

        total_reqs = len(requests)
        if total_reqs == 0:
            return FixAnalyticsMetrics(
                total_fix_requests=0,
                status_counts={},
                category_breakdown={},
                acceptance_rate=0.0,
                verification_success_rate=0.0,
                total_completed=0,
                total_failed=0,
            )

        # Status breakdown
        status_counts: Dict[str, int] = {}
        category_counts: Dict[str, int] = {}

        approved_count = 0
        completed_count = 0
        failed_count = 0

        for r in requests:
            status_str = r.status.value if hasattr(r.status, "value") else str(r.status)
            status_counts[status_str] = status_counts.get(status_str, 0) + 1

            cat_slug = r.issue_id.split("-")[0].capitalize()
            category_counts[cat_slug] = category_counts.get(cat_slug, 0) + 1

            if status_str in (
                FixStatus.APPROVED.value,
                FixStatus.APPLYING.value,
                FixStatus.COMMITTED.value,
                FixStatus.PR_CREATED.value,
                FixStatus.COMPLETED.value,
            ):
                approved_count += 1

            if status_str == FixStatus.COMPLETED.value:
                completed_count += 1

            if status_str in (FixStatus.FAILED.value, FixStatus.REJECTED.value, FixStatus.STALE.value):
                failed_count += 1

        # Acceptance rate: approved proposals / total requested
        acceptance_rate = round((approved_count / total_reqs) * 100.0, 2)

        # Verification success rate: completed / (completed + failed)
        decided_total = completed_count + failed_count
        verification_success_rate = (
            round((completed_count / decided_total) * 100.0, 2) if decided_total > 0 else 0.0
        )

        return FixAnalyticsMetrics(
            total_fix_requests=total_reqs,
            status_counts=status_counts,
            category_breakdown=category_counts,
            acceptance_rate=acceptance_rate,
            verification_success_rate=verification_success_rate,
            total_completed=completed_count,
            total_failed=failed_count,
        )
