"""SQLAlchemy models for deployment tracking.

Tracks every deployment attempt, its status, and any rollbacks performed.
Used by the Deployment Service and AI Deployment Agent.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.shared.database import Base


class DeploymentStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class Deployment(Base):
    """A single deployment record."""

    __tablename__ = "deployments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    deployed_by: Mapped[str] = mapped_column(String(255), nullable=False, default="system")
    status: Mapped[DeploymentStatus] = mapped_column(
        Enum(DeploymentStatus, name="deployment_status"),
        nullable=False,
        default=DeploymentStatus.PENDING,
    )
    environment: Mapped[str] = mapped_column(String(50), nullable=False, default="production")

    # Change details
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    config_changes: Mapped[dict | None] = mapped_column("config_changes", JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    rollbacks: Mapped[list["RollbackRecord"]] = relationship(
        back_populates="deployment",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_deployments_status_created", "status", "created_at"),
        Index("ix_deployments_service_status", "service_name", "status"),
    )

    def __repr__(self) -> str:
        return f"<Deployment {self.service_name}@{self.version} [{self.status.value}]>"


class RollbackRecord(Base):
    """Records a rollback action taken for a failed deployment."""

    __tablename__ = "rollback_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deployment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deployments.id", ondelete="CASCADE"), nullable=False
    )
    target_version: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    initiated_by: Mapped[str] = mapped_column(String(255), nullable=False, default="sentinel-ai")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="completed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    deployment: Mapped["Deployment"] = relationship(back_populates="rollbacks")

    def __repr__(self) -> str:
        return f"<Rollback {self.deployment_id} → {self.target_version}>"
