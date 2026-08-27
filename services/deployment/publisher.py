"""Kafka event publisher for deployment lifecycle events."""

from __future__ import annotations

import structlog

from services.shared.events import DeploymentCreatedEvent, DeploymentFailedEvent
from services.shared.kafka import KafkaProducer

logger = structlog.get_logger(__name__)

_producer: KafkaProducer | None = None


async def get_publisher() -> KafkaProducer:
    global _producer
    if _producer is None:
        _producer = KafkaProducer()
        await _producer.start()
    return _producer


async def publish_deployment_created(
    deployment_id: str,
    service_name: str,
    version: str,
    commit_sha: str,
    deployed_by: str,
) -> None:
    """Publish a deployment.created event."""
    publisher = await get_publisher()
    event = DeploymentCreatedEvent(
        deployment_id=deployment_id,
        service_name=service_name,
        version=version,
        commit_sha=commit_sha,
        deployed_by=deployed_by,
    )
    await publisher.publish(
        topic="deployments.created",
        value=event.model_dump(),
        key=deployment_id,
        headers={"event_id": event.event_id},
    )
    logger.info("deployment_created_published", deployment_id=deployment_id)


async def publish_deployment_failed(
    deployment_id: str,
    service_name: str,
    version: str,
    error_message: str,
    failure_reason: str,
) -> None:
    """Publish a deployment.failed event — triggers incident auto-creation."""
    publisher = await get_publisher()
    event = DeploymentFailedEvent(
        deployment_id=deployment_id,
        service_name=service_name,
        version=version,
        error_message=error_message,
        failure_reason=failure_reason,
    )
    await publisher.publish(
        topic="deployments.failed",
        value=event.model_dump(),
        key=deployment_id,
        headers={"event_id": event.event_id},
    )
    logger.warning("deployment_failed_published", deployment_id=deployment_id, reason=failure_reason)
