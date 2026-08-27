"""Deployment service — business logic for deployment tracking.

Handles:
- Recording deployment attempts
- Tracking deployment status changes
- Detecting failures and triggering incident creation
- Rollback management
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.deployment.models import Deployment, DeploymentStatus, RollbackRecord
from services.deployment.schemas import DeploymentCreate
from services.shared.exceptions import NotFoundError


class DeploymentService:
    """Business logic layer for deployments."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: DeploymentCreate) -> Deployment:
        """Record a new deployment attempt."""
        deployment = Deployment(
            id=uuid.uuid4(),
            service_name=data.service_name,
            version=data.version,
            commit_sha=data.commit_sha,
            deployed_by=data.deployed_by,
            environment=data.environment,
            description=data.description,
            config_changes=data.config_changes,
            status=DeploymentStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(deployment)
        await self.db.flush()
        return deployment

    async def get_by_id(self, deployment_id: str | uuid.UUID) -> Deployment:
        """Get deployment by ID."""
        stmt = select(Deployment).where(Deployment.id == str(deployment_id))
        result = await self.db.execute(stmt)
        deployment = result.scalar_one_or_none()
        if not deployment:
            raise NotFoundError("Deployment", str(deployment_id))
        return deployment

    async def update_status(
        self,
        deployment_id: str | uuid.UUID,
        status: DeploymentStatus,
        error_message: str | None = None,
    ) -> Deployment:
        """Update deployment status."""
        deployment = await self.get_by_id(deployment_id)
        deployment.status = status
        deployment.error_message = error_message

        if status == DeploymentStatus.IN_PROGRESS and not deployment.started_at:
            deployment.started_at = datetime.now(timezone.utc)
        elif status in (DeploymentStatus.FAILED, DeploymentStatus.SUCCEEDED, DeploymentStatus.ROLLED_BACK):
            deployment.completed_at = datetime.now(timezone.utc)

        await self.db.flush()
        return deployment

    async def record_rollback(
        self,
        deployment_id: str | uuid.UUID,
        target_version: str,
        reason: str,
        initiated_by: str = "sentinel-ai",
    ) -> RollbackRecord:
        """Record a rollback for a failed deployment."""
        deployment = await self.get_by_id(deployment_id)

        rollback = RollbackRecord(
            id=uuid.uuid4(),
            deployment_id=deployment.id,
            target_version=target_version,
            reason=reason,
            initiated_by=initiated_by,
            status="completed",
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(rollback)

        # Update deployment status
        deployment.status = DeploymentStatus.ROLLED_BACK
        deployment.completed_at = datetime.now(timezone.utc)

        await self.db.flush()
        return rollback

    async def list_deployments(
        self,
        service_name: str | None = None,
        status: DeploymentStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Deployment], int]:
        """List deployments with filters and pagination."""
        stmt = select(Deployment)
        count_stmt = select(func.count()).select_from(Deployment)

        if service_name:
            stmt = stmt.where(Deployment.service_name == service_name)
            count_stmt = count_stmt.where(Deployment.service_name == service_name)
        if status:
            stmt = stmt.where(Deployment.status == status)
            count_stmt = count_stmt.where(Deployment.status == status)

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        stmt = stmt.order_by(Deployment.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(stmt)
        deployments = list(result.scalars().all())

        return deployments, total

    async def get_latest_for_service(self, service_name: str) -> Deployment | None:
        """Get the most recent deployment for a given service."""
        stmt = (
            select(Deployment)
            .where(Deployment.service_name == service_name)
            .order_by(Deployment.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
