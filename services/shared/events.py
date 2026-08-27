"""Event type definitions for Kafka messaging.

All events flow through the Kafka event bus and are serialized as JSON.
Each event carries a unique ID, timestamp, and type discriminator for
routing and idempotency.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_serializer


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IncidentStatus(str, Enum):
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    ANALYZING = "analyzing"
    ROOT_CAUSE_FOUND = "root_cause_found"
    REMEDIATING = "remediating"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class DeploymentStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Base Event
# ---------------------------------------------------------------------------

class BaseEvent(BaseModel):
    """Base class for all Kafka events."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "sentinel-ai"
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_serializer("timestamp")
    def serialize_timestamp(self, dt: datetime) -> str:
        return dt.isoformat()


# ---------------------------------------------------------------------------
# Incident Events
# ---------------------------------------------------------------------------

class IncidentCreatedEvent(BaseEvent):
    event_type: Literal["incident.created"] = "incident.created"
    incident_id: str
    title: str
    severity: Severity
    service_name: str
    description: str


class IncidentUpdatedEvent(BaseEvent):
    event_type: Literal["incident.updated"] = "incident.updated"
    incident_id: str
    status: IncidentStatus
    message: str


class IncidentResolvedEvent(BaseEvent):
    event_type: Literal["incident.resolved"] = "incident.resolved"
    incident_id: str
    resolution: str
    root_cause: str
    confidence_score: float


# ---------------------------------------------------------------------------
# Deployment Events
# ---------------------------------------------------------------------------

class DeploymentCreatedEvent(BaseEvent):
    event_type: Literal["deployment.created"] = "deployment.created"
    deployment_id: str
    service_name: str
    version: str
    commit_sha: str
    deployed_by: str


class DeploymentFailedEvent(BaseEvent):
    event_type: Literal["deployment.failed"] = "deployment.failed"
    deployment_id: str
    service_name: str
    version: str
    error_message: str
    failure_reason: str


# ---------------------------------------------------------------------------
# AI Analysis Events
# ---------------------------------------------------------------------------

class AnalysisStartedEvent(BaseEvent):
    event_type: Literal["analysis.started"] = "analysis.started"
    incident_id: str
    analysis_id: str
    agents_invoked: list[str] = Field(default_factory=list)


class AnalysisCompletedEvent(BaseEvent):
    event_type: Literal["analysis.completed"] = "analysis.completed"
    incident_id: str
    analysis_id: str
    root_cause: str
    confidence_score: float
    agents_used: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Remediation Events
# ---------------------------------------------------------------------------

class RemediationProposedEvent(BaseEvent):
    event_type: Literal["remediation.proposed"] = "remediation.proposed"
    incident_id: str
    remediation_id: str
    action_type: str  # rollback, restart, scale, config_fix, code_patch
    description: str
    risk_level: Severity
    requires_approval: bool = True


# ---------------------------------------------------------------------------
# Notification Events
# ---------------------------------------------------------------------------

class NotificationEvent(BaseEvent):
    event_type: Literal["notification"] = "notification"
    channel: str  # slack, jira, email
    severity: Severity
    title: str
    message: str
    incident_id: str | None = None


# ---------------------------------------------------------------------------
# Event Union (for deserialization)
# ---------------------------------------------------------------------------

SentinelEvent = Annotated[
    Union[
        IncidentCreatedEvent,
        IncidentUpdatedEvent,
        IncidentResolvedEvent,
        DeploymentCreatedEvent,
        DeploymentFailedEvent,
        AnalysisStartedEvent,
        AnalysisCompletedEvent,
        RemediationProposedEvent,
        NotificationEvent,
    ],
    Field(discriminator="event_type"),
]


# ---------------------------------------------------------------------------
# Topic Registry
# ---------------------------------------------------------------------------

EVENT_TOPIC_MAP: dict[str, str] = {
    "incident.created": "incidents.created",
    "incident.updated": "incidents.updated",
    "incident.resolved": "incidents.resolved",
    "deployment.created": "deployments.created",
    "deployment.failed": "deployments.failed",
    "analysis.started": "ai.analysis.started",
    "analysis.completed": "ai.analysis.completed",
    "remediation.proposed": "ai.remediation.proposed",
    "notification": "notifications",
}


def get_topic_for_event(event: BaseEvent) -> str:
    """Map an event to its Kafka topic."""
    return EVENT_TOPIC_MAP.get(event.event_type, "unknown")
