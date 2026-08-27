"""SQLAlchemy models for incidents and incident timeline events.

Incident lifecycle:
  detected → investigating → analyzing → root_cause_found → remediating → resolved/escalated
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.shared.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class IncidentSeverity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IncidentStatus(str, enum.Enum):
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    ANALYZING = "analyzing"
    ROOT_CAUSE_FOUND = "root_cause_found"
    REMEDIATING = "remediating"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Incident(Base):
    """Represents a single incident detected in the system."""

    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    severity: Mapped[IncidentSeverity] = mapped_column(
        Enum(IncidentSeverity, name="incident_severity"), nullable=False
    )
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, name="incident_status"),
        nullable=False,
        default=IncidentStatus.DETECTED,
    )
    service_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Root cause analysis results
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    analysis_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Resolution
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Metadata
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    events: Mapped[list["IncidentEvent"]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="IncidentEvent.timestamp",
    )

    __table_args__ = (
        Index("ix_incidents_status_created", "status", "created_at"),
        Index("ix_incidents_severity_status", "severity", "status"),
    )

    def __repr__(self) -> str:
        return f"<Incident {self.id} [{self.severity.value}] {self.status.value}>"


class IncidentEvent(Base):
    """A single event in an incident's timeline (event sourcing pattern)."""

    __tablename__ = "incident_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="system")
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    incident: Mapped["Incident"] = relationship(back_populates="events")

    __table_args__ = (
        Index("ix_incident_events_incident_timestamp", "incident_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<IncidentEvent {self.event_type} @ {self.timestamp}>"
