"""
analytics_service.py
=====================
High-level service layer for computing engineering analytics, score trends,
and distribution metrics across review history (Phase 7 Stage 7.9).

Responsibilities:
- Dashboard overview metrics computation.
- Repository-level analytics & health score calculations.
- Security metrics aggregation.
- Agent performance & distribution metrics.
- Centralized metric calculation logic (prevents duplication across route handlers).

Author : AI Code Review Bot — Phase 7 (Stage 7.9)
"""

from __future__ import annotations

import datetime
import logging
from typing import Optional

from app.db.review_repository import ReviewFilter, ReviewRepository
from app.models.persistence_models import PersistedReview

logger = logging.getLogger(__name__)


def calculate_health_score(avg_score: float, critical_count: int, high_count: int, pr_count: int) -> float:
    """Calculate transparent health score (0-100) based on quality score & critical/high issue density."""
    if pr_count == 0:
        return 100.0
    penalty = ((critical_count * 10.0) + (high_count * 5.0)) / max(1, pr_count)
    return round(max(0.0, min(100.0, avg_score - penalty)), 2)


class AnalyticsService:
    """Centralized service for processing and aggregating code review analytics."""

    def __init__(self, repository: Optional[ReviewRepository] = None) -> None:
        self._repo = repository or ReviewRepository()

    async def get_overview_metrics(self, repository: Optional[str] = None) -> dict:
        """Compute aggregated metrics, trends, and distributions for dashboard overview."""
        now = datetime.datetime.now(datetime.timezone.utc)
        seven_days_ago = now - datetime.timedelta(days=7)
        thirty_days_ago = now - datetime.timedelta(days=30)

        # Recent reviews
        recent_filter = ReviewFilter(page=1, page_size=5, repository=repository, sort_by="created_at", sort_order="desc")
        recent_reviews, total_count = await self._repo.list_reviews(recent_filter)

        if total_count == 0:
            return {
                "total_prs_reviewed": 0,
                "total_issues": 0,
                "average_score": 100.0,
                "security_issues": 0,
                "severity_distribution": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                "category_distribution": {},
                "reviews_last_7_days": 0,
                "reviews_last_30_days": 0,
                "average_review_duration_ms": 0.0,
                "recent_reviews": [],
                "score_trend": [],
            }

        # Fetch review dataset for analytics calculations
        all_filter = ReviewFilter(page=1, page_size=100, repository=repository, sort_by="created_at", sort_order="desc")
        all_reviews, _ = await self._repo.list_reviews(all_filter)

        total_issues = sum(r.total_issues for r in all_reviews)
        valid_scores = [r.overall_score for r in all_reviews if r.overall_score >= 0]
        avg_score = round(sum(valid_scores) / len(valid_scores), 2) if valid_scores else 100.0

        durations = [r.review_duration_ms for r in all_reviews if r.review_duration_ms > 0]
        avg_duration = round(sum(durations) / len(durations), 2) if durations else 0.0

        sev_dist: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        cat_dist: dict[str, int] = {}
        sec_count = 0
        cnt_7 = 0
        cnt_30 = 0

        daily_scores: dict[str, list[int]] = {}

        for r in all_reviews:
            if r.created_at >= seven_days_ago:
                cnt_7 += 1
            if r.created_at >= thirty_days_ago:
                cnt_30 += 1

            for sev, count in r.severity_counts.items():
                s_key = str(sev).lower()
                sev_dist[s_key] = sev_dist.get(s_key, 0) + count

            for cat, count in r.category_counts.items():
                c_key = str(cat).lower()
                cat_dist[c_key] = cat_dist.get(c_key, 0) + count
                if c_key == "security":
                    sec_count += count

            day_str = r.created_at.strftime("%Y-%m-%d")
            if r.overall_score >= 0:
                daily_scores.setdefault(day_str, []).append(r.overall_score)

        score_trend = [
            {"date": day, "average_score": round(sum(daily_scores[day]) / len(daily_scores[day]), 2), "review_count": len(daily_scores[day])}
            for day in sorted(daily_scores.keys())
        ]

        return {
            "total_prs_reviewed": total_count,
            "total_issues": total_issues,
            "average_score": avg_score,
            "security_issues": sec_count,
            "severity_distribution": sev_dist,
            "category_distribution": cat_dist,
            "reviews_last_7_days": cnt_7,
            "reviews_last_30_days": cnt_30,
            "average_review_duration_ms": avg_duration,
            "recent_reviews": recent_reviews,
            "score_trend": score_trend,
        }

    async def get_repository_metrics(self, repository_id: str) -> dict:
        """Compute real-time analytics breakdown for a given repository_id ('owner/repo')."""
        clean_repo_id = repository_id.strip().lower()
        filter_params = ReviewFilter(page=1, page_size=100, repository=clean_repo_id)
        reviews, total_count = await self._repo.list_reviews(filter_params)

        if total_count == 0:
            parts = clean_repo_id.split("/")
            owner = parts[0] if len(parts) > 1 else "unknown"
            repo_name = parts[1] if len(parts) > 1 else clean_repo_id

            return {
                "repository_id": repository_id,
                "owner": owner,
                "repo_name": repo_name,
                "health_score": 100.0,
                "average_score": 100.0,
                "pr_count": 0,
                "issue_count": 0,
                "security_issues": 0,
                "bug_issues": 0,
                "performance_issues": 0,
                "testing_issues": 0,
                "documentation_issues": 0,
                "severity_distribution": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                "category_distribution": {},
                "score_trend": [],
            }

        owner = reviews[0].owner
        repo_name = reviews[0].repo_name

        total_issues = sum(r.total_issues for r in reviews)
        valid_scores = [r.overall_score for r in reviews if r.overall_score >= 0]
        avg_score = round(sum(valid_scores) / len(valid_scores), 2) if valid_scores else 100.0

        sev_dist: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        cat_dist: dict[str, int] = {}
        daily_scores: dict[str, list[int]] = {}

        for r in reviews:
            for sev, c in r.severity_counts.items():
                s_key = str(sev).lower()
                sev_dist[s_key] = sev_dist.get(s_key, 0) + c

            for cat, c in r.category_counts.items():
                c_key = str(cat).lower()
                cat_dist[c_key] = cat_dist.get(c_key, 0) + c

            day_str = r.created_at.strftime("%Y-%m-%d")
            if r.overall_score >= 0:
                daily_scores.setdefault(day_str, []).append(r.overall_score)

        crit_count = sev_dist.get("critical", 0)
        high_count = sev_dist.get("high", 0)
        health_score = calculate_health_score(avg_score, crit_count, high_count, total_count)

        score_trend = [
            {"date": day, "average_score": round(sum(daily_scores[day]) / len(daily_scores[day]), 2), "review_count": len(daily_scores[day])}
            for day in sorted(daily_scores.keys())
        ]

        return {
            "repository_id": reviews[0].repository,
            "owner": owner,
            "repo_name": repo_name,
            "health_score": health_score,
            "average_score": avg_score,
            "pr_count": total_count,
            "issue_count": total_issues,
            "security_issues": cat_dist.get("security", 0),
            "bug_issues": cat_dist.get("bug", 0),
            "performance_issues": cat_dist.get("performance", 0),
            "testing_issues": cat_dist.get("testing", 0),
            "documentation_issues": cat_dist.get("documentation", 0),
            "severity_distribution": sev_dist,
            "category_distribution": cat_dist,
            "score_trend": score_trend,
        }

    async def get_security_metrics(self, repository: Optional[str] = None) -> dict:
        """Compute security-focused analytics across review documents."""
        filter_params = ReviewFilter(page=1, page_size=100, repository=repository, category="security")
        reviews, _ = self._repo.list_reviews and await self._repo.list_reviews(filter_params)

        if not reviews:
            return {
                "total_security_issues": 0,
                "critical_security_issues": 0,
                "high_security_issues": 0,
                "security_trend": [],
                "top_vulnerable_repositories": [],
                "common_security_types": [],
            }

        total_sec = 0
        crit_sec = 0
        high_sec = 0
        daily_sec_counts: dict[str, int] = {}
        repo_sec_counts: dict[str, int] = {}
        title_counts: dict[str, int] = {}

        for r in reviews:
            sec_in_review = r.category_counts.get("security", 0)
            if sec_in_review == 0:
                continue

            total_sec += sec_in_review
            crit_sec += r.severity_counts.get("critical", 0)
            high_sec += r.severity_counts.get("high", 0)

            day_str = r.created_at.strftime("%Y-%m-%d")
            daily_sec_counts[day_str] = daily_sec_counts.get(day_str, 0) + sec_in_review

            repo_slug = r.repository
            repo_sec_counts[repo_slug] = repo_sec_counts.get(repo_slug, 0) + sec_in_review

            for issue in r.issues:
                cat_val = getattr(issue.category, "value", str(issue.category)).lower()
                if cat_val == "security":
                    t = issue.title.strip()
                    title_counts[t] = title_counts.get(t, 0) + 1

        sec_trend = [
            {"date": day, "security_issue_count": count}
            for day, count in sorted(daily_sec_counts.items())
        ]

        top_vulnerable = [
            {"repository_id": repo_slug, "security_issue_count": count}
            for repo_slug, count in sorted(repo_sec_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        common_types = [
            {"title": title, "count": count}
            for title, count in sorted(title_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        return {
            "total_security_issues": total_sec,
            "critical_security_issues": crit_sec,
            "high_security_issues": high_sec,
            "security_trend": sec_trend,
            "top_vulnerable_repositories": top_vulnerable,
            "common_security_types": common_types,
        }

    async def get_agent_metrics(self) -> dict:
        """Compute execution counts, success rates, and average duration per agent."""
        filter_params = ReviewFilter(page=1, page_size=100)
        reviews, _ = await self._repo.list_reviews(filter_params)

        if not reviews:
            return {
                "total_agent_executions": 0,
                "agent_distribution": {},
                "agent_success_rates": {},
                "agent_average_durations_ms": {},
            }

        agent_counts: dict[str, int] = {}
        agent_successes: dict[str, int] = {}
        agent_durations: dict[str, list[float]] = {}
        total_executions = 0

        for r in reviews:
            for ag in r.agent_results:
                name = ag.agent_name.lower()
                agent_counts[name] = agent_counts.get(name, 0) + 1
                total_executions += 1

                if ag.success:
                    agent_successes[name] = agent_successes.get(name, 0) + 1

                if ag.execution_time_ms > 0:
                    agent_durations.setdefault(name, []).append(ag.execution_time_ms)

        success_rates: dict[str, float] = {}
        avg_durations: dict[str, float] = {}

        for name, count in agent_counts.items():
            succ = agent_successes.get(name, 0)
            success_rates[name] = round((succ / count) * 100.0, 2)

            durs = agent_durations.get(name, [])
            avg_durations[name] = round(sum(durs) / len(durs), 2) if durs else 0.0

        return {
            "total_agent_executions": total_executions,
            "agent_distribution": agent_counts,
            "agent_success_rates": success_rates,
            "agent_average_durations_ms": avg_durations,
        }


def get_analytics_service() -> AnalyticsService:
    """FastAPI dependency provider for AnalyticsService."""
    from app.db.review_repository import get_review_repository
    return AnalyticsService(repository=get_review_repository())
