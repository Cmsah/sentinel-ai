"""Webhook receivers for external services.

- AlertManager → auto-create incidents from Prometheus alerts
- GitHub → record deployments from CI/CD pipeline
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Header, Request

router = APIRouter()
logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# AlertManager Webhook
# ---------------------------------------------------------------------------

@router.post("/api/v1/webhooks/alertmanager")
async def receive_alertmanager(request: Request) -> dict[str, Any]:
    """Receive alerts from Prometheus AlertManager.

    When AlertManager fires an alert, it sends a POST to this endpoint.
    Sentinel AI automatically creates an incident from the alert.

    Payload format: https://prometheus.io/docs/alerting/latest/configuration/#webhook_config
    """
    payload = await request.json()

    alerts = payload.get("alerts", [])
    created = []

    for alert in alerts:
        status = alert.get("status", "firing")
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})

        if status == "firing":
            # Create incident from alert
            incident = {
                "title": annotations.get("summary", labels.get("alertname", "Unknown alert")),
                "description": annotations.get("description", ""),
                "severity": labels.get("severity", "medium"),
                "service": labels.get("namespace", "unknown"),
                "source": "prometheus",
                "metadata": {
                    "alertname": labels.get("alertname"),
                    "namespace": labels.get("namespace"),
                    "pod": labels.get("pod"),
                    "node": labels.get("node"),
                    "starts_at": alert.get("startsAt"),
                    "fingerprint": alert.get("fingerprint"),
                },
            }

            logger.info(
                "alertmanager_alert_received",
                alertname=labels.get("alertname"),
                severity=labels.get("severity"),
                namespace=labels.get("namespace"),
            )

            # TODO: Call incident_service.create(incident) when DB is connected
            # For now, log it so you can see it's working
            created.append(incident)

        elif status == "resolved":
            logger.info(
                "alertmanager_alert_resolved",
                alertname=labels.get("alertname"),
                namespace=labels.get("namespace"),
            )

    return {
        "status": "processed",
        "alerts_received": len(alerts),
        "incidents_created": len(created),
        "incidents": created,
    }


# ---------------------------------------------------------------------------
# GitHub Webhook
# ---------------------------------------------------------------------------

@router.post("/api/v1/webhooks/github")
async def receive_github(
    request: Request,
    x_hub_signature_256: str = Header(default=""),
) -> dict[str, Any]:
    """Receive webhooks from GitHub.

    Tracks deployment events from GitHub Actions to link deployments
    to incidents automatically.

    Configure at: Settings → Webhooks → Add webhook
    Events: Workflow runs
    """
    payload = await request.json()
    event_type = request.headers.get("X-GitHub-Event", "unknown")

    logger.info("github_webhook_received", event=event_type, action=payload.get("action"))

    if event_type == "workflow_run":
        action = payload.get("action", "")
        workflow_run = payload.get("workflow_run", {})

        if action == "completed" and workflow_run.get("conclusion") == "success":
            deployment = {
                "service": _infer_service_from_workflow(workflow_run),
                "version": workflow_run.get("head_sha", "")[:7],
                "branch": workflow_run.get("head_branch", ""),
                "status": "deployed",
                "source": "github_actions",
                "metadata": {
                    "workflow_name": workflow_run.get("name"),
                    "run_id": workflow_run.get("id"),
                    "html_url": workflow_run.get("html_url"),
                },
            }

            logger.info(
                "github_deployment_recorded",
                service=deployment["service"],
                version=deployment["version"],
            )

            # TODO: Call deployment_service.create(deployment) when DB is connected
            return {"status": "recorded", "deployment": deployment}

    return {"status": "ignored", "event": event_type}


def _infer_service_from_workflow(workflow_run: dict) -> str:
    """Infer which service was deployed from the workflow name/branch."""
    name = workflow_run.get("name", "").lower()
    branch = workflow_run.get("head_branch", "").lower()

    if "sentinel" in name or "sentinel" in branch:
        return "sentinel-api"
    if "frontend" in name or "dashboard" in name:
        return "sentinel-dashboard"
    return name or "unknown-service"
