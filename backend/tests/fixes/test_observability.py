"""
test_observability.py  (tests.fixes)
=====================================
Unit tests for Stage 8.27 — Phase 8 Operational Telemetry & Observability.

Tests cover:
    - FixTelemetryLogger JSON format and event recording
    - Secret masking in telemetry event metadata and JSON strings
    - FixMetricsCollector operational metrics calculation (counts, pass rate, latency)
    - Reset and state isolation
    - Global telemetry_logger and metrics_collector singletons

Author : AI Code Review Bot — Phase 8 (Stage 8.27)
"""

from __future__ import annotations

import json
import logging
from unittest.mock import MagicMock

import pytest

from app.fixes.observability import (
    FixMetricsCollector,
    FixTelemetryLogger,
    TelemetryEvent,
    metrics_collector,
    telemetry_logger,
)


@pytest.fixture(autouse=True)
def clean_observability():
    telemetry_logger.clear_history()
    metrics_collector.reset()
    yield
    telemetry_logger.clear_history()
    metrics_collector.reset()


class TestFixTelemetryLogger:
    def test_log_event_records_event_and_returns_telemetry_event(self):
        logger_mock = MagicMock(spec=logging.Logger)
        t_logger = FixTelemetryLogger(logger_instance=logger_mock)

        evt = t_logger.log_event(
            event_type="fix_requested",
            fix_request_id="req-123",
            repository="owner/repo",
            status="REQUESTED",
            duration_ms=125.4,
            issue_title="Bug in math function",
        )

        assert isinstance(evt, TelemetryEvent)
        assert evt.event_type == "fix_requested"
        assert evt.fix_request_id == "req-123"
        assert evt.repository == "owner/repo"
        assert evt.status == "REQUESTED"
        assert evt.duration_ms == 125.4
        assert evt.metadata["issue_title"] == "Bug in math function"

        history = t_logger.get_history()
        assert len(history) == 1
        assert history[0] == evt
        logger_mock.info.assert_called_once()

    def test_secret_masking_in_telemetry_json(self):
        t_logger = FixTelemetryLogger()

        evt = t_logger.log_event(
            event_type="patch_generated",
            fix_request_id="req-secret-1",
            repository="owner/repo",
            status="READY_FOR_APPROVAL",
            secret_token="ghp_" + "a" * 36,
            gemini_key="AIzaSy" + "b" * 33,
        )

        raw_dict = evt.to_dict()
        json_output = evt.to_json()

        assert "ghp_" not in json_output
        assert "AIzaSy" not in json_output
        assert "[REDACTED_SECRET]" in json_output

    def test_warning_logged_for_failed_events(self):
        logger_mock = MagicMock(spec=logging.Logger)
        t_logger = FixTelemetryLogger(logger_instance=logger_mock)

        t_logger.log_event(
            event_type="verification_failed",
            fix_request_id="req-fail-1",
            repository="owner/repo",
            status="FAILED",
            error_code="REGRESSION_DETECTED",
        )

        logger_mock.warning.assert_called_once()


class TestFixMetricsCollector:
    def test_record_metrics_and_compute_summary(self):
        collector = FixMetricsCollector()

        collector.record_request_created("Bug")
        collector.record_request_created("Security")
        collector.record_status_transition("COMPLETED")
        collector.record_status_transition("FAILED")
        collector.record_security_block()
        collector.record_generation_latency(1500.0)
        collector.record_generation_latency(2500.0)
        collector.record_verification_result(success=True)
        collector.record_verification_result(success=True)
        collector.record_verification_result(success=False)

        summary = collector.get_summary()

        assert summary["total_requests"] == 2
        assert summary["requests_by_category"] == {"Bug": 1, "Security": 1}
        assert summary["requests_by_status"] == {"COMPLETED": 1, "FAILED": 1}
        assert summary["security_blocks_total"] == 1
        assert summary["avg_generation_latency_ms"] == 2000.0
        assert summary["verification_passes"] == 2
        assert summary["verification_failures"] == 1
        assert summary["verification_pass_rate"] == 66.67

    def test_reset_clears_all_counters(self):
        collector = FixMetricsCollector()
        collector.record_request_created("Bug")
        collector.record_security_block()

        collector.reset()
        summary = collector.get_summary()

        assert summary["total_requests"] == 0
        assert summary["security_blocks_total"] == 0
        assert summary["verification_pass_rate"] == 0.0
