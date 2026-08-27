"""Kafka event publisher for incident lifecycle events."""

from __future__ import annotations

import structlog

from services.shared.events import (
    AnalysisCompletedEvent,
    AnalysisStartedEvent,
    IncidentCreatedEvent,
    IncidentResolvedEvent,
    IncidentUpdatedEvent,
    RemediationProposedEvent,
    Severity,
)
from services.shared.kafka import KafkaProducer

logger = structlog.get_logger(__name__)

_producer: KafkaProducer | None = None


async def get_publisher() -> KafkaProducer:
    """Get or create the shared publisher instance."""
    global _producer
    if _producer is None:
        _producer = KafkaProducer()
        await _producer.start()
    return _producer


async def publish_incident_created(
    incident_id: str,
    title: str,
    severity: Severity,
    service_name: str,
    description: str,
) -> None:
    """Publish an incident.created event."""
    publisher = await get_publisher()
    event = IncidentCreatedEvent(
        incident_id=incident_id,
        title=title,
        severity=severity,
        service_name=service_name,
        description=description,
    )
    await publisher.publish(
        topic="incidents.created",
        value=event.model_dump(),
        key=incident_id,
        headers={"event_id": event.event_id},
    )
    logger.info("incident_created_published", incident_id=incident_id)


async def publish_incident_updated(
    incident_id: str,
    status: str,
    message: str,
) -> None:
    """Publish an incident.updated event."""
    publisher = await get_publisher()
    event = IncidentUpdatedEvent(
        incident_id=incident_id,
        status=status,
        message=message,
    )
    await publisher.publish(
        topic="incidents.updated",
        value=event.model_dump(),
        key=incident_id,
        headers={"event_id": event.event_id},
    )


async def publish_incident_resolved(
    incident_id: str,
    resolution: str,
    root_cause: str,
    confidence_score: float,
) -> None:
    """Publish an incident.resolved event."""
    publisher = await get_publisher()
    event = IncidentResolvedEvent(
        incident_id=incident_id,
        resolution=resolution,
        root_cause=root_cause,
        confidence_score=confidence_score,
    )
    await publisher.publish(
        topic="incidents.resolved",
        value=event.model_dump(),
        key=incident_id,
        headers={"event_id": event.event_id},
    )


async def publish_analysis_started(incident_id: str, analysis_id: str) -> None:
    publisher = await get_publisher()
    event = AnalysisStartedEvent(
        incident_id=incident_id,
        analysis_id=analysis_id,
        agents_invoked=["log_agent", "k8s_agent", "metrics_agent"],
    )
    await publisher.publish(
        topic="ai.analysis.started",
        value=event.model_dump(),
        key=incident_id,
        headers={"event_id": event.event_id},
    )


async def publish_analysis_completed(
    incident_id: str,
    analysis_id: str,
    root_cause: str,
    confidence_score: float,
    agents_used: list[str],
    duration_seconds: float,
) -> None:
    publisher = await get_publisher()
    event = AnalysisCompletedEvent(
        incident_id=incident_id,
        analysis_id=analysis_id,
        root_cause=root_cause,
        confidence_score=confidence_score,
        agents_used=agents_used,
        duration_seconds=duration_seconds,
    )
    await publisher.publish(
        topic="ai.analysis.completed",
        value=event.model_dump(),
        key=incident_id,
        headers={"event_id": event.event_id},
    )


async def publish_remediation_proposed(
    incident_id: str,
    remediation_id: str,
    action_type: str,
    description: str,
    risk_level: Severity,
) -> None:
    publisher = await get_publisher()
    event = RemediationProposedEvent(
        incident_id=incident_id,
        remediation_id=remediation_id,
        action_type=action_type,
        description=description,
        risk_level=risk_level,
    )
    await publisher.publish(
        topic="ai.remediation.proposed",
        value=event.model_dump(),
        key=incident_id,
        headers={"event_id": event.event_id},
    )
