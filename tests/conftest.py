"""Shared pytest fixtures for Sentinel AI tests."""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_incident_data() -> dict:
    """Sample incident data for tests."""
    return {
        "title": "Deployment failure — sentinel-api",
        "description": "Deployment v2.3.1 caused CrashLoopBackOff due to missing DATABASE_URL",
        "severity": "critical",
        "service_name": "sentinel-api",
        "metadata": {
            "simulation": True,
            "scenario": "missing_env_var",
        },
    }


@pytest.fixture
def sample_deployment_data() -> dict:
    """Sample deployment data for tests."""
    return {
        "service_name": "sentinel-api",
        "version": "v2.3.1",
        "commit_sha": "abc123def456",
        "deployed_by": "ci-pipeline",
        "description": "Update database connection configuration",
        "config_changes": {"DATABASE_URL": "postgresql://new-host:5432/db"},
    }


@pytest.fixture
def k8s_simulator():
    """Return a K8sSimulator instance."""
    from services.kubernetes.simulator import K8sSimulator
    return K8sSimulator()


@pytest.fixture
def llm_client():
    """Return an LLMClient in simulation mode."""
    from services.ai.llm import LLMClient
    return LLMClient()


@pytest.fixture
def sample_agent_state():
    """Return a sample AgentState for testing."""
    from services.ai.state import AgentState
    return AgentState(
        incident_id="test-incident-001",
        service_name="sentinel-api",
        title="Deployment failure — sentinel-api",
        description="Deployment v2.3.1 caused CrashLoopBackOff",
        severity="critical",
        scenario="missing_env_var",
        is_simulation=True,
    )
