"""Tests for log and metrics collectors."""

from __future__ import annotations

import pytest

from services.collector.log_collector import (
    LogCollector,
    LogEntry,
    generate_simulated_logs,
)
from services.collector.metrics_collector import (
    MetricsCollector,
    MetricPoint,
    MetricsSnapshot,
    generate_metrics_timeline,
    generate_simulated_metrics,
)


class TestLogCollector:
    """Tests for the LogCollector."""

    def test_ingest_and_query(self):
        """Ingesting logs makes them queryable."""
        collector = LogCollector()
        collector.ingest(LogEntry(
            timestamp="2026-08-23T10:00:00Z",
            level="ERROR",
            service="sentinel-api",
            message="Connection failed",
            pod="pod-1",
        ))

        results = collector.query(service="sentinel-api", level="ERROR")
        assert len(results) == 1
        assert results[0].message == "Connection failed"

    def test_query_filters(self):
        """Query filters work correctly."""
        collector = LogCollector()
        for level in ["INFO", "INFO", "ERROR", "WARNING", "ERROR"]:
            collector.ingest(LogEntry(
                timestamp="2026-08-23T10:00:00Z",
                level=level,
                service="sentinel-api",
                message=f"Message {level}",
            ))

        errors = collector.query(level="ERROR")
        assert len(errors) == 2

        infos = collector.query(level="INFO")
        assert len(infos) == 2

    def test_error_summary(self):
        """Error summary counts correctly."""
        collector = LogCollector()
        collector.ingest(LogEntry(
            timestamp="2026-08-23T10:00:00Z",
            level="ERROR",
            service="sentinel-api",
            message="DB connection failed",
        ))
        collector.ingest(LogEntry(
            timestamp="2026-08-23T10:01:00Z",
            level="ERROR",
            service="sentinel-api",
            message="DB connection failed",
        ))

        summary = collector.get_error_summary(service="sentinel-api")
        assert summary["total_errors"] == 2

    def test_timeline(self):
        """Timeline buckets logs by minute."""
        collector = LogCollector()
        collector.ingest(LogEntry(
            timestamp="2026-08-23T10:00:00Z",
            level="INFO",
            service="sentinel-api",
            message="Started",
        ))
        collector.ingest(LogEntry(
            timestamp="2026-08-23T10:00:30Z",
            level="ERROR",
            service="sentinel-api",
            message="Failed",
        ))

        timeline = collector.get_timeline("sentinel-api", window_minutes=60)
        assert len(timeline) > 0


class TestSimulatedLogs:
    """Tests for simulated log generation."""

    def test_deployment_failure_logs(self):
        """Deployment failure scenario generates realistic logs."""
        logs = generate_simulated_logs("sentinel-api", "deployment_failure")
        assert len(logs) > 0
        assert any("DATABASE_URL" in log.message for log in logs)
        assert any(log.level == "ERROR" for log in logs)

    def test_memory_spike_logs(self):
        """Memory spike scenario generates memory-related logs."""
        logs = generate_simulated_logs("sentinel-api", "memory_spike")
        assert len(logs) > 0
        assert any("memory" in log.message.lower() or "Memory" in log.message for log in logs)


class TestMetricsCollector:
    """Tests for the MetricsCollector."""

    def test_ingest_and_query(self):
        """Ingesting metrics makes them queryable."""
        collector = MetricsCollector()
        collector.ingest(MetricPoint(
            timestamp="2026-08-23T10:00:00Z",
            metric_name="cpu_percent",
            value=45.0,
            labels={"service": "sentinel-api"},
        ))

        from datetime import datetime, timezone
        results = collector.query_range(
            "cpu_percent",
            start=datetime(2026, 8, 23, 9, 0, tzinfo=timezone.utc),
            end=datetime(2026, 8, 23, 11, 0, tzinfo=timezone.utc),
        )
        assert len(results) == 1
        assert results[0].value == 45.0


class TestSimulatedMetrics:
    """Tests for simulated metrics generation."""

    def test_healthy_metrics(self):
        """Healthy scenario returns normal values."""
        metrics = generate_simulated_metrics("sentinel-api", "healthy")
        assert isinstance(metrics, MetricsSnapshot)
        assert 0 < metrics.cpu_percent < 100
        assert metrics.memory_percent > 0
        assert metrics.request_rate > 0
        assert metrics.ready_pods == 3

    def test_memory_spike_metrics(self):
        """Memory spike shows high memory and low ready pods."""
        metrics = generate_simulated_metrics("sentinel-api", "memory_spike")
        assert metrics.memory_percent > 90
        assert metrics.ready_pods == 0
        assert metrics.restart_count > 0

    def test_connection_pool_exhaustion(self):
        """Connection pool exhaustion shows high waiting connections."""
        metrics = generate_simulated_metrics("sentinel-api", "connection_pool_exhaustion")
        assert metrics.db_connections_waiting > 0
        assert metrics.db_connections_active == 10

    def test_metrics_timeline(self):
        """Timeline generation produces data points."""
        timeline = generate_metrics_timeline("sentinel-api", "healthy", minutes_back=10)
        assert len(timeline) > 0
        assert all("timestamp" in point for point in timeline)
        assert all("cpu_percent" in point for point in timeline)
