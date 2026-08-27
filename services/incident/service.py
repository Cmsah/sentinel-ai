"""Incident service — business logic for incident management.

Handles:
- Creating and updating incidents
- Status transitions (state machine)
- Adding timeline events
- Querying with filters and pagination
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.incident.models import Incident, IncidentEvent, IncidentSeverity, IncidentStatus
from services.incident.schemas import IncidentCreate, IncidentUpdate
from services.shared.events import Severity
from services.shared.exceptions import NotFoundError


# Valid status transitions
VALID_TRANSITIONS: dict[IncidentStatus, set[IncidentStatus]] = {
    IncidentStatus.DETECTED: {IncidentStatus.INVESTIGATING, IncidentStatus.ESCALATED},
    IncidentStatus.INVESTIGATING: {IncidentStatus.ANALYZING, IncidentStatus.ESCALATED},
    IncidentStatus.ANALYZING: {IncidentStatus.ROOT_CAUSE_FOUND, IncidentStatus.ESCALATED},
    IncidentStatus.ROOT_CAUSE_FOUND: {IncidentStatus.REMEDIATING, IncidentStatus.RESOLVED},
    IncidentStatus.REMEDIATING: {IncidentStatus.RESOLVED, IncidentStatus.ESCALATED},
    IncidentStatus.RESOLVED: set(),
    IncidentStatus.ESCALATED: set(),
}


class IncidentService:
    """Business logic layer for incidents."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: IncidentCreate) -> Incident:
        """Create a new incident with initial timeline event."""
        incident = Incident(
            id=uuid.uuid4(),
            title=data.title,
            description=data.description,
            severity=data.severity,
            status=IncidentStatus.DETECTED,
            service_name=data.service_name,
            metadata_=data.metadata,
        )
        self.db.add(incident)

        # Add initial timeline event
        event = IncidentEvent(
            id=uuid.uuid4(),
            incident_id=incident.id,
            event_type="incident_detected",
            message=f"Incident detected: {data.title}",
            metadata_={"severity": data.severity.value, "service": data.service_name},
            source="sentinel-system",
        )
        self.db.add(event)

        await self.db.flush()
        return incident

    async def get_by_id(self, incident_id: str | uuid.UUID) -> Incident:
        """Get incident by ID with timeline events."""
        stmt = (
            select(Incident)
            .where(Incident.id == str(incident_id))
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(stmt)
        incident = result.scalar_one_or_none()
        if not incident:
            raise NotFoundError("Incident", str(incident_id))

        # Eagerly load events
        await self.db.refresh(incident, ["events"])
        return incident

    async def update(self, incident_id: str | uuid.UUID, data: IncidentUpdate) -> Incident:
        """Update incident status and/or fields with timeline tracking."""
        incident = await self.get_by_id(incident_id)

        if data.status and data.status != incident.status:
            # Validate state transition
            allowed = VALID_TRANSITIONS.get(incident.status, set())
            if data.status not in allowed:
                raise ValueError(
                    f"Invalid transition: {incident.status.value} → {data.status.value}. "
                    f"Allowed: {[s.value for s in allowed]}"
                )

            # Add timeline event
            event = IncidentEvent(
                id=uuid.uuid4(),
                incident_id=incident.id,
                event_type="status_changed",
                message=f"Status changed: {incident.status.value} → {data.status.value}",
                metadata_={
                    "old_status": incident.status.value,
                    "new_status": data.status.value,
                },
                source="sentinel-system",
            )
            self.db.add(event)

            incident.status = data.status

        if data.severity is not None:
            incident.severity = data.severity
        if data.root_cause is not None:
            incident.root_cause = data.root_cause
            incident.confidence_score = data.confidence_score
        if data.resolution is not None:
            incident.resolution = data.resolution
            incident.resolved_at = datetime.now(timezone.utc)

        await self.db.flush()
        return incident

    async def add_event(
        self,
        incident_id: str | uuid.UUID,
        event_type: str,
        message: str,
        source: str = "system",
        metadata: dict | None = None,
    ) -> IncidentEvent:
        """Add a timeline event to an incident."""
        event = IncidentEvent(
            id=uuid.uuid4(),
            incident_id=str(incident_id),
            event_type=event_type,
            message=message,
            metadata_=metadata,
            source=source,
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def list_incidents(
        self,
        status: IncidentStatus | None = None,
        severity: IncidentSeverity | None = None,
        service_name: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Incident], int]:
        """List incidents with filters and pagination. Returns (items, total)."""
        stmt = select(Incident)
        count_stmt = select(func.count()).select_from(Incident)

        if status:
            stmt = stmt.where(Incident.status == status)
            count_stmt = count_stmt.where(Incident.status == status)
        if severity:
            stmt = stmt.where(Incident.severity == severity)
            count_stmt = count_stmt.where(Incident.severity == severity)
        if service_name:
            stmt = stmt.where(Incident.service_name == service_name)
            count_stmt = count_stmt.where(Incident.service_name == service_name)

        # Total count
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Paginated results
        offset = (page - 1) * page_size
        stmt = stmt.order_by(Incident.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(stmt)
        incidents = list(result.scalars().all())

        return incidents, total
