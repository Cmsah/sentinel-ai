"""MCP tools for Prometheus metrics querying.

Exposes PromQL-like query capabilities as MCP tools.
"""

from __future__ import annotations

from typing import Any

from services.collector.metrics_collector import generate_simulated_metrics, generate_metrics_timeline

TOOLS: dict[str, dict[str, Any]] = {}


def register_tool(name: str, description: str, parameters: dict):
    def decorator(func):
        TOOLS[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "handler": func,
        }
        return func
    return decorator


@register_tool(
    name="prometheus_query_instant",
    description="Execute an instant PromQL query. Returns current metric values.",
    parameters={
        "query": {"type": "string", "description": "PromQL query"},
        "service": {"type": "string", "description": "Service name filter"},
    },
)
async def query_instant(query: str = "", service: str = "sentinel-api") -> dict:
    """Execute an instant query (simulated)."""
    metrics = generate_simulated_metrics(service=service, scenario="connection_pool_exhaustion")
    return {
        "query": query,
        "result_type": "vector",
        "results": {
            "cpu_percent": round(metrics.cpu_percent, 2),
            "memory_percent": round(metrics.memory_percent, 2),
            "memory_used_mb": round(metrics.memory_used_mb, 2),
            "request_rate": round(metrics.request_rate, 2),
            "error_rate": round(metrics.error_rate, 2),
            "p99_latency_ms": round(metrics.p99_latency_ms, 2),
            "active_connections": metrics.active_connections,
            "db_connections_active": metrics.db_connections_active,
            "db_connections_waiting": metrics.db_connections_waiting,
            "pod_count": metrics.pod_count,
            "ready_pods": metrics.ready_pods,
            "restart_count": metrics.restart_count,
        },
    }


@register_tool(
    name="prometheus_query_range",
    description="Execute a range PromQL query. Returns metric values over a time window.",
    parameters={
        "query": {"type": "string", "description": "PromQL query"},
        "service": {"type": "string", "description": "Service name filter"},
        "minutes_back": {"type": "integer", "description": "Time window in minutes", "default": 30},
    },
)
async def query_range(
    query: str = "", service: str = "sentinel-api", minutes_back: int = 30,
) -> dict:
    """Execute a range query (simulated)."""
    timeline = generate_metrics_timeline(
        service=service, scenario="connection_pool_exhaustion", minutes_back=minutes_back,
    )
    return {
        "query": query,
        "result_type": "matrix",
        "data_points": len(timeline),
        "timeline": timeline,
    }
