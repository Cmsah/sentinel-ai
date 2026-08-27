"""LangGraph Multi-Agent Orchestrator for Sentinel AI.

Orchestrates the full incident analysis pipeline using LangGraph:

1. Three analysis agents run in parallel (log, K8s, metrics, deployment)
2. Root cause agent synthesizes all findings
3. Remediation agent proposes fixes

The graph structure:
                    ┌──→ log_agent ──┐
                    │                │
    start ──→ fan_out ──→ k8s_agent ──┤──→ root_cause_agent ──→ remediation_agent ──→ END
                    │                │
                    └──→ metrics_agent┘
                    │                │
                    └──→ deployment_agent┘

Supports both real LLM and simulation mode.
"""

from __future__ import annotations

import time
from typing import Annotated, Any, Literal

import structlog
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from services.ai.agents.deployment_agent import deployment_analysis_agent
from services.ai.agents.k8s_agent import k8s_analysis_agent
from services.ai.agents.log_agent import log_analysis_agent
from services.ai.agents.metrics_agent import metrics_analysis_agent
from services.ai.agents.remediation_agent import remediation_agent
from services.ai.agents.root_cause_agent import root_cause_agent
from services.ai.state import AgentState
from services.shared.config import get_settings

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Graph Routing
# ---------------------------------------------------------------------------

def _route_after_analysis(state: AgentState) -> str:
    """After parallel analysis completes, always go to root cause agent."""
    return "root_cause_agent"


def _route_after_root_cause(state: AgentState) -> str:
    """After root cause, go to remediation agent."""
    return "remediation_agent"


# ---------------------------------------------------------------------------
# Graph Builder
# ---------------------------------------------------------------------------

def build_analysis_graph() -> CompiledStateGraph:
    """Build the LangGraph analysis graph.

    The graph has:
    - 4 parallel analysis agents (log, k8s, metrics, deployment)
    - 1 root cause synthesis agent
    - 1 remediation agent

    Returns a compiled graph ready for execution.
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("log_agent", log_analysis_agent)
    graph.add_node("k8s_agent", k8s_analysis_agent)
    graph.add_node("metrics_agent", metrics_analysis_agent)
    graph.add_node("deployment_agent", deployment_analysis_agent)
    graph.add_node("root_cause_agent", root_cause_agent)
    graph.add_node("remediation_agent", remediation_agent)

    # Entry point: fan out to all analysis agents in parallel
    graph.set_entry_point("log_agent")

    # Parallel analysis agents all lead to root cause
    for agent_name in ["log_agent", "k8s_agent", "metrics_agent", "deployment_agent"]:
        graph.add_conditional_edges(
            agent_name,
            _route_after_analysis,
            {
                "root_cause_agent": "root_cause_agent",
            },
        )

    # Root cause → remediation
    graph.add_conditional_edges(
        "root_cause_agent",
        _route_after_root_cause,
        {
            "remediation_agent": "remediation_agent",
        },
    )

    # Remediation → end
    graph.add_edge("remediation_agent", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class SentinelOrchestrator:
    """High-level orchestrator that manages the AI analysis pipeline.

    Usage:
        orchestrator = SentinelOrchestrator()
        result = await orchestrator.analyze(
            incident_id="...",
            service_name="sentinel-api",
            title="Deployment failure",
            description="...",
            severity="critical",
        )
    """

    def __init__(self) -> None:
        self._graph = build_analysis_graph()
        self._settings = get_settings()
        logger.info(
            "orchestrator_initialized",
            llm_provider=self._settings.llm.provider,
            is_simulation=self._settings.llm.is_simulation,
        )

    async def analyze(
        self,
        incident_id: str,
        service_name: str,
        title: str,
        description: str,
        severity: str = "high",
        scenario: str = "",
    ) -> dict[str, Any]:
        """Run the full analysis pipeline on an incident.

        Args:
            incident_id: The incident to analyze.
            service_name: Name of the affected service.
            title: Incident title.
            description: Incident description.
            severity: Severity level (critical, high, medium, low).
            scenario: Optional scenario hint for simulation mode.

        Returns:
            Complete analysis result with root cause, remediation, and timeline.
        """
        start_time = time.perf_counter()

        logger.info(
            "analysis_started",
            incident_id=incident_id,
            service_name=service_name,
            severity=severity,
        )

        # Initialize state
        initial_state = AgentState(
            incident_id=incident_id,
            service_name=service_name,
            title=title,
            description=description,
            severity=severity,
            scenario=scenario or self._infer_scenario(title, description),
            is_simulation=self._settings.llm.is_simulation,
        )

        try:
            # Run the graph
            final_state = await self._graph.ainvoke(initial_state)
            duration = time.perf_counter() - start_time

            # Convert to dict for API response
            if isinstance(final_state, dict):
                result_state = AgentState(**final_state)
            else:
                result_state = final_state

            result = self._format_result(result_state, duration)

            logger.info(
                "analysis_complete",
                incident_id=incident_id,
                confidence=result_state.root_cause_confidence,
                agents_used=result_state.agents_used,
                duration_seconds=round(duration, 2),
            )

            return result

        except Exception as exc:
            duration = time.perf_counter() - start_time
            logger.error("analysis_failed", incident_id=incident_id, error=str(exc))
            return {
                "status": "failed",
                "incident_id": incident_id,
                "error": str(exc),
                "duration_seconds": round(duration, 2),
            }

    def _format_result(self, state: AgentState, duration: float) -> dict[str, Any]:
        """Format the final agent state into a clean API response."""
        return {
            "status": "complete",
            "incident_id": state.incident_id,
            "service_name": state.service_name,
            "is_simulation": state.is_simulation,
            "agents_used": state.agents_used,
            "duration_seconds": round(duration, 2),

            # Root cause
            "root_cause": {
                "analysis": state.root_cause,
                "confidence": state.root_cause_confidence,
                "contributing_factors": state.contributing_factors,
                "timeline": state.timeline,
            },

            # Agent summaries
            "agent_results": {
                "log_analysis": {
                    "findings": state.log_analysis.findings if state.log_analysis else [],
                    "hypothesis": state.log_analysis.root_cause_hypothesis if state.log_analysis else "",
                    "confidence": state.log_analysis.confidence if state.log_analysis else 0,
                },
                "k8s_analysis": {
                    "findings": state.k8s_analysis.findings if state.k8s_analysis else [],
                    "hypothesis": state.k8s_analysis.root_cause_hypothesis if state.k8s_analysis else "",
                    "confidence": state.k8s_analysis.confidence if state.k8s_analysis else 0,
                },
                "metrics_analysis": {
                    "findings": state.metrics_analysis.findings if state.metrics_analysis else [],
                    "hypothesis": state.metrics_analysis.root_cause_hypothesis if state.metrics_analysis else "",
                    "confidence": state.metrics_analysis.confidence if state.metrics_analysis else 0,
                },
                "deployment_analysis": {
                    "findings": state.deployment_analysis.findings if state.deployment_analysis else [],
                    "hypothesis": state.deployment_analysis.root_cause_hypothesis if state.deployment_analysis else "",
                    "confidence": state.deployment_analysis.confidence if state.deployment_analysis else 0,
                },
            },

            # Remediation
            "remediation": {
                "actions": [
                    {
                        "type": a.action_type,
                        "description": a.description,
                        "priority": a.priority,
                        "risk_level": a.risk_level,
                        "estimated_time": a.estimated_time,
                        "steps": a.steps,
                    }
                    for a in state.remediation_actions
                ],
                "prevention": state.prevention_suggestions,
            },

            # Errors
            "errors": state.errors if state.errors else None,
        }

    @staticmethod
    def _infer_scenario(title: str, description: str) -> str:
        """Infer the failure scenario from incident text for simulation mode."""
        combined = (title + " " + description).lower()
        if "oom" in combined or "out of memory" in combined or "memory" in combined:
            return "out_of_memory"
        elif "image" in combined or "pull" in combined:
            return "image_pull_error"
        elif "config" in combined or "env" in combined or "database_url" in combined:
            return "missing_env_var"
        elif "timeout" in combined:
            return "timeout"
        return "missing_env_var"  # default
