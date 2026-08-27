"""AI Analysis API routes.

Endpoints:
- POST /analysis/run          — Run full AI analysis on an incident
- GET  /analysis/{id}         — Get analysis results
- GET  /analysis/simulate     — Get simulated analysis for demo
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from services.gateway.dependencies import get_db
from services.incident.service import IncidentService
from services.incident.schemas import IncidentUpdate
from services.incident.models import IncidentStatus
from services.ai.orchestrator import SentinelOrchestrator
from services.shared.events import Severity

router = APIRouter()


@router.post("/analysis/run")
async def run_analysis(
    incident_id: str = Query(..., description="Incident to analyze"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Run full AI analysis on an incident using the multi-agent orchestrator.

    This triggers:
    1. Log analysis agent
    2. K8s analysis agent
    3. Metrics analysis agent
    4. Root cause agent (synthesizes findings)
    5. Remediation agent (proposes fixes)
    """
    service = IncidentService(db)
    incident = await service.get_by_id(incident_id)

    # Update status
    await service.update(incident_id, IncidentUpdate(status=IncidentStatus.ANALYZING))

    # Run the orchestrator
    orchestrator = SentinelOrchestrator()
    start_time = time.perf_counter()

    result = await orchestrator.analyze(
        incident_id=str(incident.id),
        service_name=incident.service_name,
        title=incident.title,
        description=incident.description,
        severity=incident.severity.value,
    )

    duration = time.perf_counter() - start_time

    # Update incident with results
    root_cause_analysis = result.get("root_cause", {})
    await service.update(
        incident_id,
        IncidentUpdate(
            status=IncidentStatus.ROOT_CAUSE_FOUND,
            root_cause=root_cause_analysis.get("analysis", ""),
            confidence_score=root_cause_analysis.get("confidence", 0.0),
        ),
    )

    # Add timeline events
    for step in result.get("steps", []):
        await service.add_event(
            incident_id,
            event_type=step["event_type"],
            message=step["message"],
            source=step.get("source", "ai-orchestrator"),
            metadata=step.get("metadata"),
        )

    return {
        "status": "analysis_complete",
        "incident_id": incident_id,
        "analysis": result,
        "duration_seconds": round(duration, 2),
    }


@router.get("/analysis/simulate")
async def simulate_analysis(
    scenario: str = Query("missing_env_var", description="Scenario to simulate"),
) -> dict:
    """Return a pre-computed simulated analysis for demo purposes.

    No real AI calls are made — returns deterministic, realistic output.
    """
    from services.ai.llm import LLMClient

    llm = LLMClient()

    # Simulate the full analysis pipeline
    if scenario == "missing_env_var":
        return {
            "scenario": scenario,
            "log_analysis": {
                "agent": "log_agent",
                "confidence": 0.95,
                "findings": [
                    "First error at 02:31:15 — DATABASE_URL environment variable not set",
                    "All 7 restarts show identical error pattern",
                    "No errors from sidecar container (fluent-bit)",
                    "Application crashes within 3 seconds of startup on every attempt",
                ],
                "root_cause_hypothesis": "Missing DATABASE_URL environment variable in pod spec",
            },
            "k8s_analysis": {
                "agent": "k8s_agent",
                "confidence": 0.92,
                "findings": [
                    "Pod in CrashLoopBackOff — exit code 1",
                    "ConfigMap 'app-config' exists but missing DATABASE_URL key",
                    "Deployment #8 annotation shows 'Update env vars for database connection'",
                    "MountVolume.SetUp failed for config-volume",
                ],
                "root_cause_hypothesis": "ConfigMap 'app-config' updated without DATABASE_URL key",
            },
            "metrics_analysis": {
                "agent": "metrics_agent",
                "confidence": 0.88,
                "findings": [
                    "All 3 pods have 0 ready replicas for 8 minutes",
                    "Request rate dropped to 0 — no healthy pods to serve traffic",
                    "Memory usage normal (no OOM)",
                    "No CPU spike — application fails before reaching steady state",
                ],
                "root_cause_hypothesis": "Complete service outage due to zero healthy pods",
            },
            "root_cause": {
                "agent": "root_cause_agent",
                "confidence": 0.94,
                "analysis": (
                    "Deployment #812 updated the 'app-config' ConfigMap to add database "
                    "connection configuration. However, the DATABASE_URL key was omitted "
                    "from the ConfigMap data. When the pods restarted with the new ConfigMap "
                    "mount, the application could not find the required environment variable "
                    "and crashed on startup with exit code 1. The ConfigMap was successfully "
                    "mounted (volume exists) but the key was simply missing from the data section."
                ),
                "timeline": [
                    "02:30:00 — Deployment #812 started (3 replicas rolling update)",
                    "02:30:45 — First pod terminated with exit code 1",
                    "02:31:00 — Pod restarted, crashed again within 3s",
                    "02:31:15 — Kubernetes entered CrashLoopBackOff backoff",
                    "02:35:00 — All 3 replicas in CrashLoopBackOff, 0 ready",
                ],
            },
            "remediation": {
                "agent": "remediation_agent",
                "confidence": 0.91,
                "recommended_actions": [
                    {
                        "action": "config_fix",
                        "priority": "immediate",
                        "description": "Add DATABASE_URL to ConfigMap 'app-config' and restart pods",
                        "risk_level": "low",
                        "estimated_downtime": "0 minutes (rolling restart)",
                    },
                    {
                        "action": "rollback",
                        "priority": "alternative",
                        "description": "Roll back to deployment #811 which had the env var inline",
                        "risk_level": "medium",
                        "estimated_downtime": "~30 seconds (rolling update)",
                    },
                ],
                "prevention_suggestions": [
                    "Add ConfigMap validation to CI/CD pipeline",
                    "Implement startup probe to detect missing env vars faster",
                    "Add pre-deployment ConfigMap diff check in deployment workflow",
                ],
            },
        }
    else:
        return {
            "scenario": scenario,
            "status": "simulated",
            "message": f"Simulation for '{scenario}' scenario not yet available",
        }



