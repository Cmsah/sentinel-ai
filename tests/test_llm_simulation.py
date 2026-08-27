"""Tests for the LLM client in simulation mode."""

from __future__ import annotations

import json

import pytest

from services.ai.llm import LLMClient


class TestLLMSimulation:
    """Tests for the LLM client's simulation mode."""

    def test_simulation_mode_detection(self, llm_client):
        """Client should be in simulation mode when no API keys are set."""
        assert llm_client._mode == "simulation"

    @pytest.mark.asyncio
    async def test_analyze_returns_string(self, llm_client):
        """analyze() returns a non-empty string in simulation."""
        response = await llm_client.analyze(
            system_prompt="You are an SRE agent.",
            user_prompt="Analyze the logs for this incident.",
        )
        assert isinstance(response, str)
        assert len(response) > 100

    @pytest.mark.asyncio
    async def test_simulate_log_analysis(self, llm_client):
        """Log analysis simulation returns structured findings."""
        response = await llm_client.analyze(
            system_prompt="You are a log analysis agent.",
            user_prompt="Examine the logs and identify errors.",
        )
        assert "Log Analysis" in response
        assert "DATABASE_URL" in response or "error" in response.lower()

    @pytest.mark.asyncio
    async def test_simulate_k8s_analysis(self, llm_client):
        """K8s analysis simulation returns structured findings."""
        response = await llm_client.analyze(
            system_prompt="You are a Kubernetes analysis agent.",
            user_prompt="Analyze the Kubernetes cluster state.",
        )
        assert "Kubernetes" in response or "k8s" in response.lower()
        assert "CrashLoopBackOff" in response or "pod" in response.lower()

    @pytest.mark.asyncio
    async def test_simulate_metrics_analysis(self, llm_client):
        """Metrics analysis simulation returns structured findings."""
        response = await llm_client.analyze(
            system_prompt="You are a metrics analysis agent.",
            user_prompt="Analyze the time-series metrics.",
        )
        assert "Metrics" in response or "metric" in response.lower()

    @pytest.mark.asyncio
    async def test_simulate_root_cause(self, llm_client):
        """Root cause simulation returns a coherent analysis."""
        response = await llm_client.analyze(
            system_prompt="You are the root cause analysis agent.",
            user_prompt="Synthesize all findings into a root cause.",
        )
        assert "Root Cause" in response or "root cause" in response.lower()

    @pytest.mark.asyncio
    async def test_simulate_remediation(self, llm_client):
        """Remediation simulation returns actionable steps."""
        response = await llm_client.analyze(
            system_prompt="You are the remediation agent.",
            user_prompt="Propose remediation actions for the incident.",
        )
        assert "Remediation" in response or "remediation" in response.lower() or "Fix" in response


class TestLLMStructured:
    """Tests for structured output in simulation mode."""

    @pytest.mark.asyncio
    async def test_structured_log_output(self, llm_client):
        """Structured log analysis returns expected JSON structure."""
        result = await llm_client.analyze_structured(
            system_prompt="Log analysis agent",
            user_prompt="Analyze logs",
            response_format={"findings": ["string"], "confidence": 0.0},
        )
        assert isinstance(result, dict)
        assert "findings" in result
        assert isinstance(result["findings"], list)
        assert len(result["findings"]) > 0

    @pytest.mark.asyncio
    async def test_structured_k8s_output(self, llm_client):
        """Structured K8s analysis returns expected JSON structure."""
        result = await llm_client.analyze_structured(
            system_prompt="Kubernetes analysis agent",
            user_prompt="Analyze kubernetes",
            response_format={"findings": ["string"], "confidence": 0.0},
        )
        assert isinstance(result, dict)
        assert "findings" in result
        assert len(result["findings"]) > 0

    @pytest.mark.asyncio
    async def test_structured_root_cause_output(self, llm_client):
        """Structured root cause output returns timeline."""
        result = await llm_client.analyze_structured(
            system_prompt="Root cause agent",
            user_prompt="Synthesize root cause",
            response_format={"root_cause": "string", "timeline": []},
        )
        assert isinstance(result, dict)
        assert "root_cause" in result
        assert isinstance(result["root_cause"], str)
        assert len(result["root_cause"]) > 50

    @pytest.mark.asyncio
    async def test_structured_remediation_output(self, llm_client):
        """Structured remediation output returns actions."""
        result = await llm_client.analyze_structured(
            system_prompt="Remediation agent",
            user_prompt="Propose remediation",
            response_format={"recommended_actions": [], "prevention": []},
        )
        assert isinstance(result, dict)
        assert "recommended_actions" in result
        assert isinstance(result["recommended_actions"], list)
        assert len(result["recommended_actions"]) > 0
        assert "prevention" in result
