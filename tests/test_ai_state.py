"""Tests for AI agent state models."""

from __future__ import annotations

import pytest

from services.ai.state import (
    AgentAnalysisResult,
    AgentState,
    AnalysisFinding,
    RemediationAction,
)


class TestAgentState:
    """Tests for the shared AgentState model."""

    def test_default_state(self):
        """Default state has empty fields."""
        state = AgentState()
        assert state.incident_id == ""
        assert state.title == ""
        assert state.severity == ""
        assert state.root_cause == ""
        assert state.root_cause_confidence == 0.0
        assert state.agents_used == []
        assert state.errors == []
        assert state.remediation_actions == []

    def test_state_with_data(self, sample_agent_state):
        """State can be initialized with incident data."""
        state = sample_agent_state
        assert state.incident_id == "test-incident-001"
        assert state.service_name == "sentinel-api"
        assert state.is_simulation is True

    def test_add_finding_to_log_agent(self):
        """Adding findings to log_agent creates analysis result."""
        state = AgentState()
        state.add_finding("log_agent", "DATABASE_URL not set", confidence=0.95)

        assert state.log_analysis is not None
        assert len(state.log_analysis.findings) == 1
        assert state.log_analysis.findings[0] == "DATABASE_URL not set"

    def test_add_multiple_findings(self):
        """Multiple findings accumulate in the same agent."""
        state = AgentState()
        state.add_finding("log_agent", "Finding 1", 0.9)
        state.add_finding("log_agent", "Finding 2", 0.8)

        assert state.log_analysis is not None
        assert len(state.log_analysis.findings) == 2

    def test_add_findings_to_different_agents(self):
        """Findings go to the correct agent based on name."""
        state = AgentState()
        state.add_finding("log_agent", "Log finding")
        state.add_finding("k8s_agent", "K8s finding")
        state.add_finding("metrics_agent", "Metrics finding")

        assert state.log_analysis is not None
        assert state.k8s_analysis is not None
        assert state.metrics_analysis is not None
        assert state.log_analysis.findings[0] == "Log finding"
        assert state.k8s_analysis.findings[0] == "K8s finding"
        assert state.metrics_analysis.findings[0] == "Metrics finding"


class TestAnalysisFinding:
    """Tests for the AnalysisFinding model."""

    def test_finding_creation(self):
        finding = AnalysisFinding(
            agent="log_agent",
            finding="Missing DATABASE_URL",
            confidence=0.95,
            evidence=["log output shows error"],
        )
        assert finding.agent == "log_agent"
        assert finding.confidence == 0.95
        assert len(finding.evidence) == 1


class TestAgentAnalysisResult:
    """Tests for AgentAnalysisResult."""

    def test_result_creation(self):
        result = AgentAnalysisResult(
            agent_name="log_agent",
            findings=["Finding 1", "Finding 2"],
            root_cause_hypothesis="Missing env var",
            confidence=0.92,
            raw_output="Raw text here",
        )
        assert result.agent_name == "log_agent"
        assert len(result.findings) == 2
        assert result.confidence == 0.92


class TestRemediationAction:
    """Tests for RemediationAction model."""

    def test_action_creation(self):
        action = RemediationAction(
            action_type="config_fix",
            description="Add DATABASE_URL to ConfigMap",
            priority="immediate",
            risk_level="low",
            estimated_time="2 minutes",
            steps=["Edit configmap", "Restart pods"],
        )
        assert action.action_type == "config_fix"
        assert action.risk_level == "low"
        assert len(action.steps) == 2

    def test_action_defaults(self):
        action = RemediationAction(
            action_type="restart",
            description="Restart service",
            priority="immediate",
            risk_level="low",
        )
        assert action.estimated_time == ""
        assert action.steps == []
