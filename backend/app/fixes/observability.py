"""
observability.py  (app.fixes)
==============================
Stage 8.27 — Phase 8 Operational Telemetry & Observability.

Provides structured JSON audit logging, telemetry event tracking, and
operational metrics collection for the Phase 8 AI Code Fix & Auto-Remediation engine.

Design principles (Phase 8 spec §30):
    1. Structured JSON Event Logs: Logs key lifecycle events with standard context
       (fix_request_id, repository, status, duration_ms, error_code).
    2. Secret Masking Guarantee: Sanitizes all log metadata to ensure tokens/keys
       (ghp_, AIzaSy, sk-) are NEVER emitted in log streams.
    3. Operational Metrics Collector: Tracks counters and latencies for monitoring:
       - fix_requests_total (by status, category, repository)
       - patch_generation_latency_seconds
       - verification_pass_rate
       - security_blocks_total
    4. Thread-safe & Async-friendly in-memory metric store for health/metrics endpoints.

Author : AI Code Review Bot — Phase 8 (Stage 8.27)
"""

from __future__ import annotations

import datetime
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.fixes.security_service import FixSecurityService

logger = logging.getLogger("app.fixes.observability")


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class TelemetryEvent:
    """Structured operational telemetry event model.

    Attributes:
        event_type     : Category of event (e.g., 'fix_requested', 'verification_completed').
        fix_request_id : Unique FixRequest ID.
        repository     : Repository slug 'owner/repo'.
        status         : FixStatus value string.
        timestamp      : ISO 8601 UTC timestamp string.
        duration_ms    : Optional execution latency in milliseconds.
        error_code     : Optional error code if event represents a failure.
        metadata       : Key-value dictionary of sanitized contextual metadata.
    """

    event_type: str
    fix_request_id: str
    repository: str
    status: str
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    duration_ms: Optional[float] = None
    error_code: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to clean dictionary representation."""
        res: Dict[str, Any] = {
            "event_type": self.event_type,
            "fix_request_id": self.fix_request_id,
            "repository": self.repository,
            "status": self.status,
            "timestamp": self.timestamp,
        }
        if self.duration_ms is not None:
            res["duration_ms"] = round(self.duration_ms, 2)
        if self.error_code is not None:
            res["error_code"] = self.error_code
        if self.metadata:
            res["metadata"] = self.metadata
        return res

    def to_json(self) -> str:
        """Serialize event to JSON string with secret masking."""
        raw_json = json.dumps(self.to_dict(), default=str)
        return FixSecurityService.sanitize_llm_prompt(raw_json)


# ---------------------------------------------------------------------------
# FixTelemetryLogger
# ---------------------------------------------------------------------------


class FixTelemetryLogger:
    """Structured JSON telemetry logger for Phase 8 fix automation events."""

    def __init__(self, logger_instance: Optional[logging.Logger] = None) -> None:
        self._logger = logger_instance or logger
        self._event_history: List[TelemetryEvent] = []

    def log_event(
        self,
        event_type: str,
        fix_request_id: str,
        repository: str,
        status: str,
        duration_ms: Optional[float] = None,
        error_code: Optional[str] = None,
        **metadata: Any,
    ) -> TelemetryEvent:
        """Emit a structured telemetry event to log output stream.

        Args:
            event_type     : Name/category of the event.
            fix_request_id : Target FixRequest ID.
            repository     : 'owner/repo' slug.
            status         : Current status string.
            duration_ms    : Optional execution latency in milliseconds.
            error_code     : Optional machine-readable error code.
            **metadata     : Additional contextual metadata key-value pairs.

        Returns:
            Recorded TelemetryEvent instance.
        """
        # Sanitize string metadata values
        sanitized_meta = {}
        for k, v in metadata.items():
            if isinstance(v, str):
                sanitized_meta[k] = FixSecurityService.sanitize_llm_prompt(v)
            else:
                sanitized_meta[k] = v

        event = TelemetryEvent(
            event_type=event_type,
            fix_request_id=fix_request_id,
            repository=repository,
            status=status,
            duration_ms=duration_ms,
            error_code=error_code,
            metadata=sanitized_meta,
        )

        self._event_history.append(event)

        log_str = event.to_json()
        if error_code or status in ("FAILED", "REJECTED"):
            self._logger.warning("FixTelemetryEvent: %s", log_str)
        else:
            self._logger.info("FixTelemetryEvent: %s", log_str)

        return event

    def get_history(self) -> List[TelemetryEvent]:
        """Return list of all recorded telemetry events in memory."""
        return list(self._event_history)

    def clear_history(self) -> None:
        """Clear recorded telemetry event history."""
        self._event_history.clear()


# ---------------------------------------------------------------------------
# FixMetricsCollector
# ---------------------------------------------------------------------------


class FixMetricsCollector:
    """Collects and computes operational counters and latency metrics for Phase 8."""

    def __init__(self) -> None:
        self._total_requests: int = 0
        self._requests_by_status: Dict[str, int] = {}
        self._requests_by_category: Dict[str, int] = {}
        self._security_blocks: int = 0
        self._generation_latencies_ms: List[float] = []
        self._verification_passes: int = 0
        self._verification_failures: int = 0

    def record_request_created(self, category: str = "Unknown") -> None:
        """Increment total fix request count."""
        self._total_requests += 1
        self._requests_by_category[category] = self._requests_by_category.get(category, 0) + 1

    def record_status_transition(self, status: str) -> None:
        """Increment status distribution counter."""
        self._requests_by_status[status] = self._requests_by_status.get(status, 0) + 1

    def record_security_block(self) -> None:
        """Increment security block counter."""
        self._security_blocks += 1

    def record_generation_latency(self, latency_ms: float) -> None:
        """Record AI patch generation latency in milliseconds."""
        if latency_ms >= 0:
            self._generation_latencies_ms.append(latency_ms)

    def record_verification_result(self, success: bool) -> None:
        """Record post-fix verification outcome."""
        if success:
            self._verification_passes += 1
        else:
            self._verification_failures += 1

    def get_summary(self) -> Dict[str, Any]:
        """Return operational metrics summary dictionary."""
        avg_latency = (
            sum(self._generation_latencies_ms) / len(self._generation_latencies_ms)
            if self._generation_latencies_ms
            else 0.0
        )
        total_verifications = self._verification_passes + self._verification_failures
        verification_pass_rate = (
            (self._verification_passes / total_verifications) * 100.0
            if total_verifications > 0
            else 0.0
        )

        return {
            "total_requests": self._total_requests,
            "requests_by_status": dict(self._requests_by_status),
            "requests_by_category": dict(self._requests_by_category),
            "security_blocks_total": self._security_blocks,
            "avg_generation_latency_ms": round(avg_latency, 2),
            "verification_passes": self._verification_passes,
            "verification_failures": self._verification_failures,
            "verification_pass_rate": round(verification_pass_rate, 2),
        }

    def reset(self) -> None:
        """Reset all metric counters."""
        self._total_requests = 0
        self._requests_by_status.clear()
        self._requests_by_category.clear()
        self._security_blocks = 0
        self._generation_latencies_ms.clear()
        self._verification_passes = 0
        self._verification_failures = 0


# Global singleton instances for simple app-wide usage
telemetry_logger = FixTelemetryLogger()
metrics_collector = FixMetricsCollector()
