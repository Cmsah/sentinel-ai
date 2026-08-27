"""Incident API routes.

Endpoints:
- POST   /incidents           — Create a new incident
- GET    /incidents           — List incidents with filters
- GET    /incidents/{id}      — Get incident with full timeline
- PATCH  /incidents/{id}      — Update incident status/details
- POST   /incidents/{id}/analyze  — Trigger AI analysis
- WS     /ws/incidents/{id}   — Live WebSocket updates
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from services.gateway.dependencies import get_db
from services.incident.models import IncidentSeverity, IncidentStatus
from services.incident.publisher import publish_incident_created, publish_analysis_started
from services.incident.schemas import (
    IncidentCreate,
    IncidentFilters,
    IncidentListResponse,
    IncidentResponse,
    IncidentUpdate,
    IncidentWithEvents,
)
from services.incident.service import IncidentService
from services.shared.exceptions import NotFoundError

router = APIRouter()


# ---------------------------------------------------------------------------
# WebSocket Connection Manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    """Manages WebSocket connections for live incident updates."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, incident_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if incident_id not in self._connections:
            self._connections[incident_id] = []
        self._connections[incident_id].append(websocket)

    def disconnect(self, incident_id: str, websocket: WebSocket) -> None:
        if incident_id in self._connections:
            self._connections[incident_id] = [
                ws for ws in self._connections[incident_id] if ws != websocket
            ]

    async def broadcast(self, incident_id: str, message: dict) -> None:
        if incident_id in self._connections:
            for ws in self._connections[incident_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass


ws_manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/incidents", response_model=IncidentResponse, status_code=201)
async def create_incident(
    data: IncidentCreate,
    db: AsyncSession = Depends(get_db),
) -> IncidentResponse:
    """Create a new incident and publish an event."""
    service = IncidentService(db)
    incident = await service.create(data)

    # Publish Kafka event
    await publish_incident_created(
        incident_id=str(incident.id),
        title=incident.title,
        severity=incident.severity,
        service_name=incident.service_name,
        description=incident.description,
    )

    return IncidentResponse.model_validate(incident)


@router.get("/incidents", response_model=IncidentListResponse)
async def list_incidents(
    status: IncidentStatus | None = Query(None, description="Filter by status"),
    severity: IncidentSeverity | None = Query(None, description="Filter by severity"),
    service_name: str | None = Query(None, description="Filter by service"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> IncidentListResponse:
    """List incidents with optional filters and pagination."""
    service = IncidentService(db)
    incidents, total = await service.list_incidents(
        status=status, severity=severity, service_name=service_name,
        page=page, page_size=page_size,
    )

    return IncidentListResponse(
        items=[IncidentResponse.model_validate(i) for i in incidents],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/incidents/{incident_id}", response_model=IncidentWithEvents)
async def get_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
) -> IncidentWithEvents:
    """Get incident detail with full timeline."""
    service = IncidentService(db)
    incident = await service.get_by_id(incident_id)

    response = IncidentWithEvents.model_validate(incident)
    response.events = [
        {
            "id": e.id,
            "event_type": e.event_type,
            "message": e.message,
            "metadata": e.metadata_,
            "source": e.source,
            "timestamp": e.timestamp,
        }
        for e in sorted(incident.events, key=lambda x: x.timestamp)
    ]
    return response


@router.patch("/incidents/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: str,
    data: IncidentUpdate,
    db: AsyncSession = Depends(get_db),
) -> IncidentResponse:
    """Update incident status or details."""
    service = IncidentService(db)
    incident = await service.update(incident_id, data)

    # Broadcast update to WebSocket subscribers
    await ws_manager.broadcast(
        incident_id,
        {
            "type": "incident_updated",
            "incident_id": str(incident.id),
            "status": incident.status.value,
        },
    )

    return IncidentResponse.model_validate(incident)


@router.post("/incidents/{incident_id}/analyze", response_model=dict)
async def trigger_analysis(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger AI analysis for an incident."""
    service = IncidentService(db)
    incident = await service.get_by_id(incident_id)

    analysis_id = str(uuid.uuid4())

    # Update incident status
    await service.update(incident_id, IncidentUpdate(status=IncidentStatus.ANALYZING))

    # Add timeline event
    await service.add_event(
        incident_id,
        event_type="analysis_started",
        message=f"AI analysis started (ID: {analysis_id})",
        source="ai-orchestrator",
    )

    # Publish analysis started event
    await publish_analysis_started(incident_id=incident_id, analysis_id=analysis_id)

    # Broadcast to WebSocket subscribers
    await ws_manager.broadcast(
        incident_id,
        {
            "type": "analysis_started",
            "incident_id": incident_id,
            "analysis_id": analysis_id,
        },
    )

    return {
        "status": "analysis_triggered",
        "analysis_id": analysis_id,
        "incident_id": incident_id,
    }


@router.post("/incidents/simulate", response_model=IncidentResponse, status_code=201)
async def simulate_incident(
    scenario: str = Query("deployment_failure", description="Simulation scenario"),
    service_name: str = Query("sentinel-api", description="Service name"),
    db: AsyncSession = Depends(get_db),
) -> IncidentResponse:
    """Simulate an incident with realistic data for demo/testing."""
    from services.incident.schemas import IncidentCreate
    from services.shared.events import Severity
    from services.kubernetes.simulator import K8sSimulator

    k8s = K8sSimulator()
    k8s_state = k8s.simulate_crashloop_backoff(service_name=service_name, failure_reason="missing_env_var")

    severity = Severity.CRITICAL if scenario == "deployment_failure" else Severity.HIGH

    data = IncidentCreate(
        title=f"[SIMULATED] {scenario.replace('_', ' ').title()} — {service_name}",
        description=k8s_state["description"],
        severity=severity,
        service_name=service_name,
        metadata={
            "simulation": True,
            "scenario": scenario,
            "k8s_scenario": k8s_state["scenario"],
        },
    )

    service = IncidentService(db)
    incident = await service.create(data)

    await publish_incident_created(
        incident_id=str(incident.id),
        title=incident.title,
        severity=incident.severity,
        service_name=incident.service_name,
        description=incident.description,
    )

    return IncidentResponse.model_validate(incident)


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

@router.websocket("/ws/incidents/{incident_id}")
async def incident_websocket(websocket: WebSocket, incident_id: str) -> None:
    """WebSocket endpoint for live incident updates."""
    await ws_manager.connect(incident_id, websocket)
    try:
        while True:
            # Keep connection alive — receive pings/commands
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        ws_manager.disconnect(incident_id, websocket)
