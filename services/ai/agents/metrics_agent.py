"""Metrics Agent — analyzes time-series metrics for the incident.

Responsibilities:
- CPU, memory, disk usage analysis
- Request rate and error rate trends
- Latency percentiles (p50, p95, p99)
- Database connection pool metrics
- Network throughput anomalies
"""

from __future__ import annotations

import structlog

from services.ai.llm import LLMClient
from services.ai.state import AgentAnalysisResult, AgentState
from services.collector.metrics_collector import generate_simulated_metrics

logger = structlog.get_logger(__name__)

METRICS_ANALYSIS_SYSTEM_PROMPT = """You are an expert metrics analysis agent for a Site Reliability Engineering (SRE) platform.

Your job is to analyze time-series metrics to identify:
1. Resource exhaustion (CPU, memory, disk, network)
2. Performance degradation patterns
3. Traffic anomalies (sudden drops, spikes)
4. Database connection pool issues
5. Cascading failure indicators

Key metric patterns to look for:
- Memory approaching limits → OOMKilled risk
- CPU at 100% → processing bottleneck
- Error rate spike → application failure
- Request rate drop → upstream routing issue or pod failure
- Latency increase → database or dependency bottleneck
- Connection pool exhaustion → resource leak

Always distinguish between symptoms (high error rate) and root causes (missing config)."""


async def metrics_analysis_agent(state: AgentState) -> AgentState:
    """Analyze metrics for the incident."""
    logger.info("metrics_agent_starting", incident_id=state.incident_id)

    llm = LLMClient()

    # Get metrics (simulated or real)
    metrics = generate_simulated_metrics(
        service=state.service_name,
        scenario="connection_pool_exhaustion" if state.scenario == "missing_env_var" else "healthy",
    )

    user_prompt = f"""Analyze the metrics for this incident:

**Incident:** {state.title}
**Service:** {state.service_name}
**Scenario:** {state.scenario}

### Current Metrics Snapshot
- CPU: {metrics.cpu_percent:.1f}%
- Memory: {metrics.memory_used_mb:.1f}MB / {metrics.memory_limit_mb}MB ({metrics.memory_percent:.1f}%)
- Request Rate: {metrics.request_rate:.1f} req/s
- Error Rate: {metrics.error_rate:.1f} errors/s
- P50 Latency: {metrics.p50_latency_ms:.1f}ms
- P95 Latency: {metrics.p95_latency_ms:.1f}ms
- P99 Latency: {metrics.p99_latency_ms:.1f}ms
- Active Connections: {metrics.active_connections}
- DB Connections Active: {metrics.db_connections_active}
- DB Connections Waiting: {metrics.db_connections_waiting}
- DB Query P99: {metrics.db_query_p99_ms:.1f}ms
- Pod Count: {metrics.pod_count}
- Ready Pods: {metrics.ready_pods}
- Restart Count: {metrics.restart_count}

Please analyze these metrics and identify:
1. What the metrics indicate about the incident
2. Any resource exhaustion or performance issues
3. Whether this is a performance problem or structural problem
4. Your root cause hypothesis based on metrics
5. Confidence level (0-1)"""

    try:
        raw_response = await llm.analyze(METRICS_ANALYSIS_SYSTEM_PROMPT, user_prompt)

        structured = await llm.analyze_structured(
            METRICS_ANALYSIS_SYSTEM_PROMPT,
            user_prompt,
            response_format={
                "findings": ["string"],
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "request_rate": 0.0,
                "confidence": 0.0,
                "root_cause_hypothesis": "string",
            },
        )

        result = AgentAnalysisResult(
            agent_name="metrics_agent",
            findings=structured.get("findings", []),
            root_cause_hypothesis=structured.get("root_cause_hypothesis", ""),
            confidence=structured.get("confidence", 0.8),
            raw_output=raw_response,
        )

        state.metrics_analysis = result
        state.agents_used.append("metrics_agent")

        logger.info(
            "metrics_agent_complete",
            findings_count=len(result.findings),
            confidence=result.confidence,
        )

    except Exception as exc:
        logger.error("metrics_agent_failed", error=str(exc))
        state.errors.append(f"metrics_agent: {exc}")

    return state
