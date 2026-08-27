"""Deployment API routes.

Endpoints:
- POST   /deployments           — Record a new deployment
- GET    /deployments           — List deployments with filters
- GET    /deployments/{id}      — Get deployment detail
- PATCH  /deployments/{id}      — Update deployment status
- POST   /deployments/simulate  — Simulate a deployment failure
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from services.gateway.dependencies import get_db
from services.deployment.models import DeploymentStatus
from services.deployment.publisher import (
    publish_deployment_created,
    publish_deployment_failed,
)
from services.deployment.schemas import (
    DeploymentCreate,
    DeploymentListResponse,
    DeploymentResponse,
)
from services.deployment.service import DeploymentService
from services.shared.exceptions import NotFoundError

router = APIRouter()


@router.post("/deployments", response_model=DeploymentResponse, status_code=201)
async def create_deployment(
    data: DeploymentCreate,
    db: AsyncSession = Depends(get_db),
) -> DeploymentResponse:
    """Record a new deployment and publish an event."""
    service = DeploymentService(db)
    deployment = await service.create(data)

    await publish_deployment_created(
        deployment_id=str(deployment.id),
        service_name=deployment.service_name,
        version=deployment.version,
        commit_sha=deployment.commit_sha,
        deployed_by=deployment.deployed_by,
    )

    return DeploymentResponse.model_validate(deployment)


@router.get("/deployments", response_model=DeploymentListResponse)
async def list_deployments(
    service_name: str | None = Query(None),
    status: DeploymentStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> DeploymentListResponse:
    """List deployments with optional filters."""
    service = DeploymentService(db)
    deployments, total = await service.list_deployments(
        service_name=service_name, status=status,
        page=page, page_size=page_size,
    )
    return DeploymentListResponse(
        items=[DeploymentResponse.model_validate(d) for d in deployments],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/deployments/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
) -> DeploymentResponse:
    """Get deployment detail."""
    service = DeploymentService(db)
    deployment = await service.get_by_id(deployment_id)
    return DeploymentResponse.model_validate(deployment)


@router.post("/deployments/simulate", response_model=DeploymentResponse, status_code=201)
async def simulate_deployment_failure(
    service_name: str = Query("sentinel-api"),
    version: str = Query("v2.3.1"),
    failure_reason: str = Query("missing_env_var", description="Reason for simulated failure"),
    db: AsyncSession = Depends(get_db),
) -> DeploymentResponse:
    """Simulate a deployment that fails — triggers the full incident lifecycle.

    This is the main demo endpoint. It:
    1. Creates a deployment record
    2. Publishes deployment.created
    3. Immediately marks it as failed
    4. Publishes deployment.failed → triggers auto-incident creation
    """
    service = DeploymentService(db)

    # Step 1: Create deployment
    deployment = await service.create(DeploymentCreate(
        service_name=service_name,
        version=version,
        commit_sha="abc123def456",
        deployed_by="ci-pipeline",
        description=f"Simulated deployment of {service_name}@{version}",
        config_changes={"DATABASE_URL": "postgresql://new-host:5432/db"},
    ))

    # Step 2: Mark as in progress
    await service.update_status(deployment.id, DeploymentStatus.IN_PROGRESS)

    # Step 3: Mark as failed
    error_messages = {
        "missing_env_var": "CrashLoopBackOff — DATABASE_URL environment variable not found",
        "out_of_memory": "OOMKilled — container exceeded 256Mi memory limit",
        "image_pull_error": "ImagePullBackOff — tag v2.3.2-INVALID not found in registry",
    }
    error_msg = error_messages.get(failure_reason, f"Unknown error: {failure_reason}")

    deployment = await service.update_status(
        deployment.id,
        DeploymentStatus.FAILED,
        error_message=error_msg,
    )

    # Step 4: Publish failure event → triggers incident auto-creation
    await publish_deployment_failed(
        deployment_id=str(deployment.id),
        service_name=service_name,
        version=version,
        error_message=error_msg,
        failure_reason=failure_reason,
    )

    return DeploymentResponse.model_validate(deployment)
