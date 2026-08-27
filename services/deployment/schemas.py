"""Pydantic schemas for deployment API request/response."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from services.deployment.models import DeploymentStatus


class DeploymentCreate(BaseModel):
    """Request to record a new deployment."""
    service_name: str = Field(..., min_length=1, max_length=255)
    version: str = Field(..., min_length=1, max_length=100)
    commit_sha: str = Field(default="", max_length=40)
    deployed_by: str = Field(default="system", max_length=255)
    environment: str = Field(default="production", max_length=50)
    description: str = Field(default="")
    config_changes: dict | None = None


class DeploymentResponse(BaseModel):
    """Deployment detail response."""
    id: uuid.UUID
    service_name: str
    version: str
    commit_sha: str
    deployed_by: str
    status: DeploymentStatus
    environment: str
    description: str
    config_changes: dict | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DeploymentListResponse(BaseModel):
    """Paginated list of deployments."""
    items: list[DeploymentResponse]
    total: int
    page: int
    page_size: int
    pages: int


class RollbackResponse(BaseModel):
    """Rollback record response."""
    id: uuid.UUID
    deployment_id: uuid.UUID
    target_version: str
    reason: str
    initiated_by: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
