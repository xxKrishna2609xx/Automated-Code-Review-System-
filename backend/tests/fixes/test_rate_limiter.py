"""
test_rate_limiter.py  (tests.fixes)
====================================
Unit tests for Stage 8.24 — FixRateLimiter.

Tests cover:
    - Sliding window rate limit enforcement (5 req / min)
    - Sliding window timestamp pruning
    - Concurrency throttling (max 2 active patch generations)
    - Slot release cycle

Author : AI Code Review Bot — Phase 8 (Stage 8.24)
"""

from __future__ import annotations

import time
import pytest

from app.fixes.exceptions import FixValidationError
from app.fixes.rate_limiter import FixRateLimiter, reset_rate_limiter_stores


@pytest.fixture(autouse=True)
def clean_rate_limiter():
    reset_rate_limiter_stores()
    yield
    reset_rate_limiter_stores()


class TestFixRateLimiter:
    def test_rate_limit_allows_under_cap(self):
        limiter = FixRateLimiter(max_requests_per_minute=5)
        for i in range(5):
            limiter.check_rate_limit("owner/repo-a")

    def test_rate_limit_exceeded_raises_error(self):
        limiter = FixRateLimiter(max_requests_per_minute=3)
        for i in range(3):
            limiter.check_rate_limit("owner/repo-b")

        with pytest.raises(FixValidationError, match="Rate limit exceeded"):
            limiter.check_rate_limit("owner/repo-b")

    def test_rate_limit_prunes_old_timestamps(self):
        limiter = FixRateLimiter(max_requests_per_minute=2, window_seconds=0.1)
        limiter.check_rate_limit("owner/repo-c")
        limiter.check_rate_limit("owner/repo-c")

        # Sleep to allow window expiration
        time.sleep(0.15)

        # Should pass now because old timestamps expired
        limiter.check_rate_limit("owner/repo-c")

    def test_concurrency_slots_acquire_and_release(self):
        limiter = FixRateLimiter(max_concurrent=2)

        limiter.acquire_concurrency_slot("owner/repo-d")
        limiter.acquire_concurrency_slot("owner/repo-d")

        with pytest.raises(FixValidationError, match="Concurrency limit reached"):
            limiter.acquire_concurrency_slot("owner/repo-d")

        # Release one slot
        limiter.release_concurrency_slot("owner/repo-d")

        # Now acquisition should succeed
        limiter.acquire_concurrency_slot("owner/repo-d")
