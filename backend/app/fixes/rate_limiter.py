"""
rate_limiter.py  (app.fixes)
============================
Stage 8.24 — Rate Limiting & Concurrency Throttling Service.

Enforces operational boundaries for AI Code Fix Generation:
    1. Request Rate Limiting  : Sliding window cap (max 5 requests / min per repo).
    2. Concurrency Throttling : Max 2 concurrent patch generations per repo.

Author : AI Code Review Bot — Phase 8 (Stage 8.24)
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, List

from app.fixes.exceptions import FixValidationError

logger = logging.getLogger(__name__)

# Default limit parameters
MAX_REQUESTS_PER_MINUTE = 5
MAX_CONCURRENT_GENERATIONS = 2
WINDOW_SECONDS = 60.0

# In-memory rate limiting stores
_REPO_REQUEST_TIMESTAMPS: Dict[str, List[float]] = {}
_REPO_ACTIVE_GENERATIONS: Dict[str, int] = {}


class FixRateLimiter:
    """Sliding window rate limiter and concurrency control for fix requests."""

    def __init__(
        self,
        max_requests_per_minute: int = MAX_REQUESTS_PER_MINUTE,
        max_concurrent: int = MAX_CONCURRENT_GENERATIONS,
        window_seconds: float = WINDOW_SECONDS,
    ) -> None:
        self.max_requests = max_requests_per_minute
        self.max_concurrent = max_concurrent
        self.window_seconds = window_seconds

    def check_rate_limit(self, repository: str, user_id: str = "system") -> None:
        """Check if request rate for a repository exceeds allowed threshold.

        Args:
            repository : Repository slug ('owner/repo').
            user_id    : User or bot identifier.

        Raises:
            FixValidationError : If rate limit is exceeded.
        """
        now = time.time()
        cutoff = now - self.window_seconds

        timestamps = _REPO_REQUEST_TIMESTAMPS.setdefault(repository, [])
        # Prune old timestamps
        _REPO_REQUEST_TIMESTAMPS[repository] = [t for t in timestamps if t > cutoff]
        pruned_timestamps = _REPO_REQUEST_TIMESTAMPS[repository]

        if len(pruned_timestamps) >= self.max_requests:
            logger.warning(
                "Rate limit exceeded for repository '%s' (user: %s). %d requests in last 60s",
                repository,
                user_id,
                len(pruned_timestamps),
            )
            raise FixValidationError(
                f"Rate limit exceeded for repository '{repository}'. "
                f"Maximum allowed is {self.max_requests} fix requests per minute."
            )

        # Record current request timestamp
        _REPO_REQUEST_TIMESTAMPS[repository].append(now)

    def acquire_concurrency_slot(self, repository: str) -> None:
        """Acquire a concurrency slot for active patch generation.

        Args:
            repository : Repository slug ('owner/repo').

        Raises:
            FixValidationError : If maximum concurrent patch generations limit is reached.
        """
        active = _REPO_ACTIVE_GENERATIONS.get(repository, 0)
        if active >= self.max_concurrent:
            logger.warning(
                "Concurrency limit reached for repository '%s'. %d active generations",
                repository,
                active,
            )
            raise FixValidationError(
                f"Concurrency limit reached for repository '{repository}'. "
                f"Maximum allowed is {self.max_concurrent} simultaneous patch generations."
            )

        _REPO_ACTIVE_GENERATIONS[repository] = active + 1

    def release_concurrency_slot(self, repository: str) -> None:
        """Release a concurrency slot after patch generation completes.

        Args:
            repository : Repository slug ('owner/repo').
        """
        active = _REPO_ACTIVE_GENERATIONS.get(repository, 0)
        if active > 0:
            _REPO_ACTIVE_GENERATIONS[repository] = active - 1


def reset_rate_limiter_stores() -> None:
    """Utility helper for test suite cleanup."""
    _REPO_REQUEST_TIMESTAMPS.clear()
    _REPO_ACTIVE_GENERATIONS.clear()
