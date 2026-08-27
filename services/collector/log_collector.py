"""Log collector — aggregates and stores application logs.

In production, this would receive logs from Fluentd/Filebeat and index
them in OpenSearch. In simulation mode, it generates realistic log data
for the AI agents to analyze.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field


@dataclass
class LogEntry:
    timestamp: str
    level: str  # INFO, WARNING, ERROR, CRITICAL
    service: str
    message: str
    pod: str | None = None
    container: str | None = None
    trace_id: str | None = None
    request_id: str | None = None
    metadata: dict = field(default_factory=dict)


class LogCollector:
    """Collects and retrieves logs for analysis.

    In simulation mode, generates realistic logs based on a scenario.
    """

    def __init__(self) -> None:
        self._logs: list[LogEntry] = []

    def ingest(self, entry: LogEntry) -> None:
        """Ingest a single log entry."""
        self._logs.append(entry)

    def ingest_batch(self, entries: list[LogEntry]) -> None:
        """Ingest multiple log entries."""
        self._logs.extend(entries)

    def query(
        self,
        service: str | None = None,
        level: str | None = None,
        since: datetime | None = None,
        keyword: str | None = None,
        limit: int = 100,
    ) -> list[LogEntry]:
        """Query logs with filters."""
        results = self._logs

        if service:
            results = [l for l in results if l.service == service]
        if level:
            results = [l for l in results if l.level == level]
        if since:
            results = [l for l in results if datetime.fromisoformat(l.timestamp) >= since]
        if keyword:
            results = [l for l in results if keyword.lower() in l.message.lower()]

        return results[-limit:]

    def get_error_summary(self, service: str | None = None) -> dict:
        """Get a summary of errors for a service."""
        logs = self.query(service=service, level="ERROR")
        errors_by_message: dict[str, int] = {}
        for log in logs:
            # Normalize error message (strip timestamps, IDs)
            key = log.message[:200]
            errors_by_message[key] = errors_by_message.get(key, 0) + 1

        return {
            "total_errors": len(logs),
            "unique_errors": len(errors_by_message),
            "top_errors": sorted(
                errors_by_message.items(), key=lambda x: x[1], reverse=True
            )[:10],
        }

    def get_timeline(self, service: str, window_minutes: int = 30) -> list[dict]:
        """Get log volume over time for a service."""
        now = datetime.now(timezone.utc)
        window = now - timedelta(minutes=window_minutes)

        logs = [l for l in self._logs if l.service == service]
        logs = [l for l in logs if datetime.fromisoformat(l.timestamp) >= window]

        # Bucket by minute
        buckets: dict[str, dict[str, int]] = {}
        for log in logs:
            ts = datetime.fromisoformat(log.timestamp)
            minute_key = ts.strftime("%Y-%m-%dT%H:%M:00Z")
            if minute_key not in buckets:
                buckets[minute_key] = {"INFO": 0, "WARNING": 0, "ERROR": 0, "CRITICAL": 0}
            level = log.level if log.level in buckets[minute_key] else "ERROR"
            buckets[minute_key][level] += 1

        return [
            {"timestamp": k, "counts": v}
            for k, v in sorted(buckets.items())
        ]


def generate_simulated_logs(
    service: str,
    scenario: str = "deployment_failure",
    pod_name: str | None = None,
) -> list[LogEntry]:
    """Generate realistic simulated logs for a given scenario."""
    now = datetime.now(timezone.utc)
    pod = pod_name or f"{service}-{random.randint(10000, 99999)}-{random.randint(1000, 9999)}"

    if scenario == "deployment_failure":
        return [
            LogEntry(timestamp=(now - timedelta(minutes=5)).isoformat(), level="INFO", service=service, message=f"Starting {service} v2.3.1", pod=pod),
            LogEntry(timestamp=(now - timedelta(minutes=4, seconds=55)).isoformat(), level="INFO", service=service, message="Loading configuration from environment", pod=pod),
            LogEntry(timestamp=(now - timedelta(minutes=4, seconds=53)).isoformat(), level="WARNING", service=service, message="DATABASE_URL not found in environment", pod=pod),
            LogEntry(timestamp=(now - timedelta(minutes=4, seconds=52)).isoformat(), level="ERROR", service=service, message="psycopg2.OperationalError: connection to server timed out", pod=pod),
            LogEntry(timestamp=(now - timedelta(minutes=4, seconds=50)).isoformat(), level="ERROR", service=service, message="Failed to initialize database connection pool", pod=pod),
            LogEntry(timestamp=(now - timedelta(minutes=4, seconds=48)).isoformat(), level="ERROR", service=service, message="Application startup failed with exit code 1", pod=pod),
        ]
    elif scenario == "memory_spike":
        return [
            LogEntry(timestamp=(now - timedelta(minutes=3)).isoformat(), level="INFO", service=service, message="Server listening on port 8080", pod=pod),
            LogEntry(timestamp=(now - timedelta(minutes=2)).isoformat(), level="INFO", service=service, message="Request processed: GET /api/users — 200 OK (12ms)", pod=pod),
            LogEntry(timestamp=(now - timedelta(minutes=1, seconds=30)).isoformat(), level="WARNING", service=service, message="Memory usage: 230MB / 256MB (89%)", pod=pod),
            LogEntry(timestamp=(now - timedelta(minutes=1, seconds=10)).isoformat(), level="ERROR", service=service, message="Connection pool exhausted: active=10 waiting=25 timeout=30s", pod=pod),
            LogEntry(timestamp=(now - timedelta(minutes=1)).isoformat(), level="ERROR", service=service, message="Memory usage: 248MB / 256MB (96%) — OOMKilled imminent", pod=pod),
        ]
    else:
        return [
            LogEntry(timestamp=now.isoformat(), level="INFO", service=service, message=f"Starting {service}", pod=pod),
            LogEntry(timestamp=now.isoformat(), level="ERROR", service=service, message="Unexpected error", pod=pod),
        ]
