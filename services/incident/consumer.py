"""Kafka consumer for the incident service.

Listens for:
- deployments.failed → auto-creates an incident
- ai.analysis.completed → updates incident with root cause
- ai.remediation.proposed → adds remediation event to timeline
"""

from __future__ import annotations

from typing import Any

import structlog

from services.incident.publisher import publish_incident_created
from services.shared.events import Severity
from services.shared.kafka import KafkaConsumer

logger = structlog.get_logger(__name__)


class IncidentConsumer(KafkaConsumer):
    """Consumes events relevant to incident management."""

    def __init__(self) -> None:
        settings_topics = [
            "deployments.failed",
            "ai.analysis.completed",
            "ai.remediation.proposed",
        ]
        super().__init__(topics=settings_topics)

    async def handle_message(
        self,
        topic: str,
        key: str | None,
        value: dict[str, Any],
        headers: dict[str, str],
    ) -> None:
        event_type = value.get("event_type", "unknown")
        logger.info(
            "incident_consumer_received",
            topic=topic,
            event_type=event_type,
            key=key,
        )

        if event_type == "deployment.failed":
            await self._handle_deployment_failed(value)
        elif event_type == "analysis.completed":
            await self._handle_analysis_completed(value)
        elif event_type == "remediation.proposed":
            await self._handle_remediation_proposed(value)
        else:
            logger.warning("unhandled_event_type", event_type=event_type, topic=topic)

    async def _handle_deployment_failed(self, event: dict[str, Any]) -> None:
        """Auto-create an incident when a deployment fails."""
        service_name = event.get("service_name", "unknown")
        version = event.get("version", "unknown")
        error_message = event.get("error_message", "Unknown error")

        logger.info(
            "auto_creating_incident_from_deployment_failure",
            service_name=service_name,
            version=version,
        )

        # Determine severity based on failure reason
        failure_reason = event.get("failure_reason", "")
        severity = self._classify_severity(failure_reason)

        await publish_incident_created(
            incident_id=event.get("deployment_id", ""),
            title=f"Deployment failure: {service_name}@{version}",
            severity=severity,
            service_name=service_name,
            description=(
                f"Deployment {version} of {service_name} failed.\n"
                f"Error: {error_message}\n"
                f"Reason: {failure_reason}"
            ),
        )

    async def _handle_analysis_completed(self, event: dict[str, Any]) -> None:
        """Update incident when AI analysis is complete."""
        incident_id = event.get("incident_id")
        root_cause = event.get("root_cause", "")
        confidence = event.get("confidence_score", 0.0)

        logger.info(
            "ai_analysis_completed_for_incident",
            incident_id=incident_id,
            confidence=confidence,
        )
        # The gateway service will handle the DB update via REST
        # This consumer is for cross-service awareness and audit

    async def _handle_remediation_proposed(self, event: dict[str, Any]) -> None:
        """Log remediation proposal for audit trail."""
        logger.info(
            "remediation_proposed",
            incident_id=event.get("incident_id"),
            action_type=event.get("action_type"),
        )

    @staticmethod
    def _classify_severity(failure_reason: str) -> Severity:
        """Classify incident severity based on failure characteristics."""
        critical_signals = ["outofmemory", "crashloopbackoff", "database", "data_loss"]
        high_signals = ["timeout", "connection_refused", "503", "502"]
        medium_signals = ["config", "env", "secret"]

        reason_lower = failure_reason.lower()
        for signal in critical_signals:
            if signal in reason_lower:
                return Severity.CRITICAL
        for signal in high_signals:
            if signal in reason_lower:
                return Severity.HIGH
        for signal in medium_signals:
            if signal in reason_lower:
                return Severity.MEDIUM
        return Severity.HIGH
