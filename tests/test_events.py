"""Tests for Kafka event models and serialization."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from services.shared.events import (
    AnalysisCompletedEvent,
    AnalysisStartedEvent,
    BaseEvent,
    DeploymentCreatedEvent,
    DeploymentFailedEvent,
    IncidentCreatedEvent,
    IncidentResolvedEvent,
    NotificationEvent,
    RemediationProposedEvent,
    Severity,
    get_topic_for_event,
)


class TestSeverity:
    """Tests for Severity enum."""

    def test_all_values(self):
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.LOW.value == "low"
        assert Severity.INFO.value == "info"

    def test_string_comparison(self):
        assert Severity.CRITICAL == "critical"


class TestBaseEvent:
    """Tests for the BaseEvent model."""

    def test_auto_generates_event_id(self):
        event = BaseEvent(event_type="test.event")
        assert event.event_id is not None
        uuid.UUID(event.event_id)  # Should not raise

    def test_auto_generates_timestamp(self):
        before = datetime.now(timezone.utc)
        event = BaseEvent(event_type="test.event")
        after = datetime.now(timezone.utc)
        assert before <= event.timestamp <= after

    def test_serialization(self):
        event = BaseEvent(event_type="test.event", source="test")
        data = event.model_dump()
        assert data["event_type"] == "test.event"
        assert data["source"] == "test"
        assert isinstance(data["timestamp"], str)


class TestIncidentEvents:
    """Tests for incident-related events."""

    def test_incident_created(self):
        event = IncidentCreatedEvent(
            incident_id="inc-001",
            title="Test incident",
            severity=Severity.CRITICAL,
            service_name="test-service",
            description="A test incident",
        )
        assert event.event_type == "incident.created"
        assert event.incident_id == "inc-001"
        assert event.severity == Severity.CRITICAL

        data = event.model_dump()
        assert data["event_type"] == "incident.created"

    def test_incident_resolved(self):
        event = IncidentResolvedEvent(
            incident_id="inc-001",
            resolution="Fixed by rollback",
            root_cause="Missing env var",
            confidence_score=0.95,
        )
        assert event.event_type == "incident.resolved"
        assert event.confidence_score == 0.95


class TestDeploymentEvents:
    """Tests for deployment events."""

    def test_deployment_created(self):
        event = DeploymentCreatedEvent(
            deployment_id="dep-001",
            service_name="test-service",
            version="v1.0.0",
            commit_sha="abc123",
            deployed_by="ci-pipeline",
        )
        assert event.event_type == "deployment.created"

    def test_deployment_failed(self):
        event = DeploymentFailedEvent(
            deployment_id="dep-001",
            service_name="test-service",
            version="v1.0.0",
            error_message="CrashLoopBackOff",
            failure_reason="missing_env_var",
        )
        assert event.event_type == "deployment.failed"


class TestAIEvents:
    """Tests for AI analysis events."""

    def test_analysis_started(self):
        event = AnalysisStartedEvent(
            incident_id="inc-001",
            analysis_id="analysis-001",
            agents_invoked=["log_agent", "k8s_agent"],
        )
        assert event.event_type == "analysis.started"
        assert len(event.agents_invoked) == 2

    def test_analysis_completed(self):
        event = AnalysisCompletedEvent(
            incident_id="inc-001",
            analysis_id="analysis-001",
            root_cause="Missing DATABASE_URL",
            confidence_score=0.94,
            agents_used=["log_agent", "k8s_agent", "metrics_agent"],
            duration_seconds=3.5,
        )
        assert event.event_type == "analysis.completed"
        assert event.duration_seconds == 3.5


class TestTopicMapping:
    """Tests for event-to-topic mapping."""

    def test_incident_created_topic(self):
        event = IncidentCreatedEvent(
            incident_id="inc-001",
            title="test",
            severity=Severity.HIGH,
            service_name="test",
            description="test",
        )
        assert get_topic_for_event(event) == "incidents.created"

    def test_deployment_failed_topic(self):
        event = DeploymentFailedEvent(
            deployment_id="dep-001",
            service_name="test",
            version="v1",
            error_message="error",
            failure_reason="reason",
        )
        assert get_topic_for_event(event) == "deployments.failed"

    def test_analysis_completed_topic(self):
        event = AnalysisCompletedEvent(
            incident_id="inc-001",
            analysis_id="a-001",
            root_cause="rc",
            confidence_score=0.9,
        )
        assert get_topic_for_event(event) == "ai.analysis.completed"

    def test_unknown_event_returns_unknown(self):
        event = BaseEvent(event_type="custom.event")
        assert get_topic_for_event(event) == "unknown"
