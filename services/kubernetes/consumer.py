"""Kafka consumer for Kubernetes-related events.

Listens for deployment events to simulate K8s state changes.
"""

from __future__ import annotations

from typing import Any

import structlog

from services.shared.kafka import KafkaConsumer

logger = structlog.get_logger(__name__)


class KubernetesConsumer(KafkaConsumer):
    """Consumes events and updates simulated K8s cluster state."""

    def __init__(self) -> None:
        super().__init__(topics=["deployments.created", "deployments.failed"])

    async def handle_message(
        self,
        topic: str,
        key: str | None,
        value: dict[str, Any],
        headers: dict[str, str],
    ) -> None:
        event_type = value.get("event_type", "unknown")
        logger.info("k8s_consumer_received", topic=topic, event_type=event_type)

        if event_type == "deployment.created":
            logger.info(
                "k8s_deployment_tracked",
                service=value.get("service_name"),
                version=value.get("version"),
            )
        elif event_type == "deployment.failed":
            logger.warning(
                "k8s_deployment_failure_detected",
                service=value.get("service_name"),
                error=value.get("error_message"),
            )
