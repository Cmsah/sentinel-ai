"""Initial schema — incidents, incident_events, deployments, rollback_records.

Revision ID: 001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Enums ---
    incident_severity = postgresql.ENUM(
        "critical", "high", "medium", "low", "info",
        name="incident_severity",
        create_type=False,
    )
    incident_severity.create(op.get_bind(), checkfirst=True)

    incident_status = postgresql.ENUM(
        "detected", "investigating", "analyzing", "root_cause_found",
        "remediating", "resolved", "escalated",
        name="incident_status",
        create_type=False,
    )
    incident_status.create(op.get_bind(), checkfirst=True)

    deployment_status = postgresql.ENUM(
        "pending", "in_progress", "succeeded", "failed", "rolled_back",
        name="deployment_status",
        create_type=False,
    )
    deployment_status.create(op.get_bind(), checkfirst=True)

    # --- Incidents ---
    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("severity", sa.Enum("critical", "high", "medium", "low", "info",
                                       name="incident_severity"), nullable=False),
        sa.Column("status", sa.Enum("detected", "investigating", "analyzing",
                                     "root_cause_found", "remediating", "resolved", "escalated",
                                     name="incident_status"), nullable=False),
        sa.Column("service_name", sa.String(255), nullable=False),
        sa.Column("root_cause", sa.Text, nullable=True),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("analysis_id", sa.String(255), nullable=True),
        sa.Column("resolution", sa.Text, nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_incidents_service_name", "incidents", ["service_name"])
    op.create_index("ix_incidents_status_created", "incidents", ["status", "created_at"])
    op.create_index("ix_incidents_severity_status", "incidents", ["severity", "status"])

    # --- Incident Events ---
    op.create_table(
        "incident_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("source", sa.String(100), nullable=False, server_default="system"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_incident_events_incident_timestamp",
                     "incident_events", ["incident_id", "timestamp"])

    # --- Deployments ---
    op.create_table(
        "deployments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("service_name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column("commit_sha", sa.String(40), nullable=False, server_default=""),
        sa.Column("deployed_by", sa.String(255), nullable=False, server_default="system"),
        sa.Column("status", sa.Enum("pending", "in_progress", "succeeded", "failed", "rolled_back",
                                     name="deployment_status"), nullable=False),
        sa.Column("environment", sa.String(50), nullable=False, server_default="production"),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("config_changes", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_deployments_service_name", "deployments", ["service_name"])
    op.create_index("ix_deployments_status_created", "deployments", ["status", "created_at"])
    op.create_index("ix_deployments_service_status", "deployments", ["service_name", "status"])

    # --- Rollback Records ---
    op.create_table(
        "rollback_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("deployment_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("deployments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_version", sa.String(100), nullable=False),
        sa.Column("reason", sa.Text, nullable=False, server_default=""),
        sa.Column("initiated_by", sa.String(255), nullable=False, server_default="sentinel-ai"),
        sa.Column("status", sa.String(50), nullable=False, server_default="completed"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("rollback_records")
    op.drop_table("deployments")
    op.drop_table("incident_events")
    op.drop_table("incidents")
    op.execute("DROP TYPE IF EXISTS deployment_status")
    op.execute("DROP TYPE IF EXISTS incident_status")
    op.execute("DROP TYPE IF EXISTS incident_severity")
