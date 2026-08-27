"""Pydantic schemas for incident API request/response."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from services.incident.models import IncidentSeverity, IncidentStatus


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class IncidentCreate(BaseModel):
    """Request to create a new incident."""
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="")
    severity: IncidentSeverity
    service_name: str = Field(..., min_length=1, max_length=255)
    metadata: dict | None = None


class IncidentUpdate(BaseModel):
    """Request to update an incident."""
    status: IncidentStatus | None = None
    severity: IncidentSeverity | None = None
    root_cause: str | None = None
    confidence_score: float | None = Field(None, ge=0.0, le=1.0)
    resolution: str | None = None


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------

class IncidentEventResponse(BaseModel):
    """Single event in an incident timeline."""
    id: uuid.UUID
    event_type: str
    message: str
    metadata: dict | None = None
    source: str
    timestamp: datetime

    model_config = {"from_attributes": True}


class IncidentResponse(BaseModel):
    """Incident detail response."""
    id: uuid.UUID
    title: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus
    service_name: str
    root_cause: str | None = None
    confidence_score: float | None = None
    analysis_id: str | None = None
    resolution: str | None = None
    resolved_at: datetime | None = None
    metadata: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IncidentWithEvents(IncidentResponse):
    """Incident with full timeline."""
    events: list[IncidentEventResponse] = []


class IncidentListResponse(BaseModel):
    """Paginated list of incidents."""
    items: list[IncidentResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ---------------------------------------------------------------------------
# Filter Schema
# ---------------------------------------------------------------------------

class IncidentFilters(BaseModel):
    """Query parameters for filtering incidents."""
    status: IncidentStatus | None = None
    severity: IncidentSeverity | None = None
    service_name: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
