"""Kafka consumer for the deployment service.

Listens for:
- ai.remediation.proposed (rollback actions)
- incidents.resolved (update deployment context)
"""

from __future__ import annotations

from typing import Any

import structlog

from services.shared.kafka import KafkaConsumer

logger = structlog.get_logger(__name__)


class DeploymentConsumer(KafkaConsumer):
    """Consumes events relevant to deployment tracking."""

    def __init__(self) -> None:
        super().__init__(topics=["ai.remediation.proposed", "incidents.resolved"])

    async def handle_message(
        self,
        topic: str,
        key: str | None,
        value: dict[str, Any],
        headers: dict[str, str],
    ) -> None:
        event_type = value.get("event_type", "unknown")
        logger.info("deployment_consumer_received", topic=topic, event_type=event_type)

        if event_type == "remediation.proposed":
            action_type = value.get("action_type", "")
            if action_type == "rollback":
                await self._handle_rollback_proposed(value)

    async def _handle_rollback_proposed(self, event: dict[str, Any]) -> None:
        """Process a proposed rollback."""
        logger.info(
            "rollback_proposed",
            incident_id=event.get("incident_id"),
            remediation_id=event.get("remediation_id"),
        )
        # In production: update deployment status, trigger rollback pipeline
