"""Metrics collector — generates and queries time-series metrics.

In production, this queries Prometheus. In simulation mode, generates
realistic CPU, memory, network, and request metrics for AI analysis.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta


@dataclass
class MetricPoint:
    timestamp: str
    metric_name: str
    value: float
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class MetricsSnapshot:
    """Complete metrics picture at a point in time."""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_limit_mb: float
    network_in_bytes: float
    network_out_bytes: float
    request_rate: float  # requests per second
    error_rate: float  # errors per second
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    active_connections: int
    db_connections_active: int
    db_connections_waiting: int
    db_query_p99_ms: float
    pod_count: int
    ready_pods: int
    restart_count: int


class MetricsCollector:
    """Collects and queries metrics data."""

    def __init__(self) -> None:
        self._points: list[MetricPoint] = []

    def ingest(self, point: MetricPoint) -> None:
        self._points.append(point)

    def query_range(
        self,
        metric_name: str,
        start: datetime,
        end: datetime,
        step_seconds: int = 60,
        labels: dict[str, str] | None = None,
    ) -> list[MetricPoint]:
        """Query metric data over a time range."""
        results = [
            p for p in self._points
            if p.metric_name == metric_name
            and start <= datetime.fromisoformat(p.timestamp) <= end
        ]
        if labels:
            results = [
                p for p in results
                if all(p.labels.get(k) == v for k, v in labels.items())
            ]
        return results


def generate_simulated_metrics(
    service: str,
    scenario: str = "healthy",
    minutes_back: int = 10,
) -> MetricsSnapshot:
    """Generate a realistic metrics snapshot based on the scenario."""
    now = datetime.now(timezone.utc)

    if scenario == "healthy":
        return MetricsSnapshot(
            cpu_percent=random.uniform(15, 35),
            memory_percent=random.uniform(40, 60),
            memory_used_mb=random.uniform(100, 150),
            memory_limit_mb=256,
            network_in_bytes=random.uniform(1e6, 5e6),
            network_out_bytes=random.uniform(5e6, 2e7),
            request_rate=random.uniform(50, 200),
            error_rate=random.uniform(0, 0.5),
            p50_latency_ms=random.uniform(10, 30),
            p95_latency_ms=random.uniform(50, 100),
            p99_latency_ms=random.uniform(100, 200),
            active_connections=random.randint(20, 50),
            db_connections_active=random.randint(5, 15),
            db_connections_waiting=0,
            db_query_p99_ms=random.uniform(5, 20),
            pod_count=3,
            ready_pods=3,
            restart_count=0,
        )
    elif scenario == "memory_spike":
        return MetricsSnapshot(
            cpu_percent=random.uniform(75, 95),
            memory_percent=random.uniform(90, 99),
            memory_used_mb=random.uniform(235, 252),
            memory_limit_mb=256,
            network_in_bytes=random.uniform(1e5, 1e6),
            network_out_bytes=random.uniform(1e5, 5e6),
            request_rate=random.uniform(5, 20),
            error_rate=random.uniform(10, 50),
            p50_latency_ms=random.uniform(500, 2000),
            p95_latency_ms=random.uniform(5000, 15000),
            p99_latency_ms=random.uniform(10000, 30000),
            active_connections=random.randint(10, 10),
            db_connections_active=random.randint(10, 10),
            db_connections_waiting=random.randint(15, 40),
            db_query_p99_ms=random.uniform(2000, 10000),
            pod_count=3,
            ready_pods=0,
            restart_count=5,
        )
    elif scenario == "connection_pool_exhaustion":
        return MetricsSnapshot(
            cpu_percent=random.uniform(40, 60),
            memory_percent=random.uniform(60, 80),
            memory_used_mb=random.uniform(150, 200),
            memory_limit_mb=256,
            network_in_bytes=random.uniform(1e5, 5e5),
            network_out_bytes=random.uniform(1e5, 5e5),
            request_rate=random.uniform(100, 300),
            error_rate=random.uniform(20, 60),
            p50_latency_ms=random.uniform(2000, 8000),
            p95_latency_ms=random.uniform(10000, 25000),
            p99_latency_ms=random.uniform(25000, 60000),
            active_connections=10,
            db_connections_active=10,
            db_connections_waiting=random.randint(20, 50),
            db_query_p99_ms=random.uniform(5000, 15000),
            pod_count=3,
            ready_pods=3,
            restart_count=0,
        )
    else:
        return generate_simulated_metrics(service, "healthy", minutes_back)


def generate_metrics_timeline(
    service: str,
    scenario: str = "healthy",
    minutes_back: int = 30,
    step_seconds: int = 60,
) -> list[dict]:
    """Generate a time-series of metric data points."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=minutes_back)
    points = []

    current = start
    while current <= now:
        progress = (current - start).total_seconds() / (now - start).total_seconds()

        if scenario == "memory_spike":
            # Gradual memory increase until OOM
            cpu = 20 + progress * 70
            mem = 40 + progress * 55
            error_rate = progress * 50
            latency = 15 + progress * 5000
        elif scenario == "connection_pool_exhaustion":
            # Sudden spike at 60% through the window
            spike = 1.0 if progress > 0.6 else 0.0
            cpu = 30 + spike * 30
            mem = 50 + spike * 30
            error_rate = spike * 40
            latency = 20 + spike * 8000
        else:
            cpu = 20 + random.uniform(-5, 5)
            mem = 50 + random.uniform(-5, 5)
            error_rate = random.uniform(0, 0.5)
            latency = 15 + random.uniform(-5, 5)

        points.append({
            "timestamp": current.isoformat(),
            "cpu_percent": round(min(cpu + random.uniform(-2, 2), 100), 2),
            "memory_percent": round(min(mem + random.uniform(-1, 1), 100), 2),
            "error_rate": round(max(error_rate + random.uniform(-1, 1), 0), 2),
            "latency_p99_ms": round(max(latency + random.uniform(-10, 10), 0), 2),
        })

        current += timedelta(seconds=step_seconds)

    return points
