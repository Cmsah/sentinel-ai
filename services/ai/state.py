"""Agent state definitions for LangGraph orchestration.

Defines the shared state that flows through the agent graph.
Each agent reads from and writes to this state.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from langgraph.graph import add_messages
from pydantic import BaseModel, Field


class AnalysisFinding(BaseModel):
    """A single finding from an agent."""
    agent: str
    finding: str
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)


class AgentAnalysisResult(BaseModel):
    """Result from a single agent's analysis."""
    agent_name: str
    findings: list[str] = Field(default_factory=list)
    root_cause_hypothesis: str = ""
    confidence: float = 0.0
    raw_output: str = ""


class RemediationAction(BaseModel):
    """A proposed remediation action."""
    action_type: str  # rollback, config_fix, restart, scale, code_patch
    description: str
    priority: str  # immediate, short_term, long_term
    risk_level: str  # low, medium, high
    estimated_time: str = ""
    steps: list[str] = Field(default_factory=list)


class AgentState(BaseModel):
    """Shared state for the Sentinel AI multi-agent system.

    This state flows through the LangGraph graph. Each agent:
    1. Reads relevant fields from the state
    2. Performs its analysis
    3. Writes its results back to the state
    4. Passes the state to the next agent
    """
    # --- Input (populated by orchestrator) ---
    incident_id: str = ""
    service_name: str = ""
    title: str = ""
    description: str = ""
    severity: str = ""
    scenario: str = ""  # for simulation mode

    # --- Agent Results ---
    log_analysis: AgentAnalysisResult | None = None
    k8s_analysis: AgentAnalysisResult | None = None
    metrics_analysis: AgentAnalysisResult | None = None
    deployment_analysis: AgentAnalysisResult | None = None

    # --- Synthesized Results ---
    root_cause: str = ""
    root_cause_confidence: float = 0.0
    contributing_factors: list[str] = Field(default_factory=list)
    timeline: list[dict[str, str]] = Field(default_factory=list)

    # --- Remediation ---
    remediation_actions: list[RemediationAction] = Field(default_factory=list)
    prevention_suggestions: list[str] = Field(default_factory=list)

    # --- Metadata ---
    agents_used: list[str] = Field(default_factory=list)
    total_duration_seconds: float = 0.0
    is_simulation: bool = False
    errors: list[str] = Field(default_factory=list)

    # --- Messages (for LangGraph) ---
    messages: Annotated[list, add_messages] = Field(default_factory=list)

    def add_finding(self, agent_name: str, finding: str, confidence: float = 0.0) -> None:
        """Add a finding to the appropriate agent's results."""
        result = AgentAnalysisResult(
            agent_name=agent_name,
            findings=[finding],
            confidence=confidence,
        )
        if agent_name == "log_agent":
            if self.log_analysis is None:
                self.log_analysis = result
            else:
                self.log_analysis.findings.append(finding)
        elif agent_name == "k8s_agent":
            if self.k8s_analysis is None:
                self.k8s_analysis = result
            else:
                self.k8s_analysis.findings.append(finding)
        elif agent_name == "metrics_agent":
            if self.metrics_analysis is None:
                self.metrics_analysis = result
            else:
                self.metrics_analysis.findings.append(finding)
