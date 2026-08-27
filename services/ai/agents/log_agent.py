"""Log Analysis Agent — examines application logs for error patterns.

Responsibilities:
- Read and parse application logs
- Cluster similar errors
- Find the first failure (root cause indicator)
- Detect anomalies in log patterns
"""

from __future__ import annotations

import structlog

from services.ai.llm import LLMClient
from services.ai.state import AgentAnalysisResult, AgentState

logger = structlog.get_logger(__name__)

LOG_ANALYSIS_SYSTEM_PROMPT = """You are an expert log analysis agent for a Site Reliability Engineering (SRE) platform.

Your job is to analyze application logs to identify:
1. The first error or anomaly (often the root cause indicator)
2. Patterns in recurring errors
3. Correlation between errors and events (deployments, config changes)
4. Error severity and blast radius

Focus on:
- Error sequences and causality chains
- Timestamps and ordering of events
- Distinguishing symptoms from root causes
- Confidence levels for your findings

Provide structured, actionable analysis. Be specific about timestamps, error messages, and patterns."""


async def log_analysis_agent(state: AgentState) -> AgentState:
    """Analyze application logs for the incident."""
    logger.info("log_agent_starting", incident_id=state.incident_id)

    llm = LLMClient()

    user_prompt = f"""Analyze the application logs for this incident:

**Incident:** {state.title}
**Service:** {state.service_name}
**Description:** {state.description}
**Severity:** {state.severity}
**Scenario:** {state.scenario}

Please examine the logs and identify:
1. The first error that occurred
2. Error patterns and frequency
3. Any correlation with deployment events
4. Your root cause hypothesis based on logs alone
5. Confidence level (0-1)"""

    try:
        raw_response = await llm.analyze(LOG_ANALYSIS_SYSTEM_PROMPT, user_prompt)

        # Parse structured result
        structured = await llm.analyze_structured(
            LOG_ANALYSIS_SYSTEM_PROMPT,
            user_prompt,
            response_format={
                "findings": ["string"],
                "error_pattern": "string",
                "first_error": "string",
                "confidence": 0.0,
                "root_cause_hypothesis": "string",
            },
        )

        result = AgentAnalysisResult(
            agent_name="log_agent",
            findings=structured.get("findings", []),
            root_cause_hypothesis=structured.get("root_cause_hypothesis", ""),
            confidence=structured.get("confidence", 0.8),
            raw_output=raw_response,
        )

        state.log_analysis = result
        state.agents_used.append("log_agent")

        logger.info(
            "log_agent_complete",
            findings_count=len(result.findings),
            confidence=result.confidence,
        )

    except Exception as exc:
        logger.error("log_agent_failed", error=str(exc))
        state.errors.append(f"log_agent: {exc}")

    return state
