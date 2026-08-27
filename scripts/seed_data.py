#!/usr/bin/env python3
"""Seed the database with sample incidents and deployments.

Usage:
    python -m scripts.seed_data
    python -m scripts.seed_data --count 10
"""

from __future__ import annotations

import argparse
import asyncio
import random
import uuid
from datetime import datetime, timezone, timedelta

from services.shared.database import init_db, get_session_context, close_db
from services.incident.models import Incident, IncidentEvent, IncidentSeverity, IncidentStatus
from services.deployment.models import Deployment, DeploymentStatus


SAMPLE_SERVICES = [
    "sentinel-api",
    "api-gateway",
    "auth-service",
    "worker-service",
    "notification-service",
]

SAMPLE_TITLES = [
    "CrashLoopBackOff — missing DATABASE_URL",
    "OOMKilled — memory limit exceeded",
    "ImagePullBackOff — invalid image tag",
    "High latency — database connection pool exhausted",
    "503 Service Unavailable — all pods unhealthy",
]

SAMPLE_ROOT_CAUSES = [
    "Deployment #812 updated ConfigMap but omitted the DATABASE_URL key",
    "Memory limit set too low for the application's working set size",
    "Image tag v2.3.2-INVALID was promoted to production without registry validation",
    "Connection pool max_size was not increased after traffic growth",
    "Anti-affinity rules concentrated all pods on a single node that failed",
]


async def seed_incidents(count: int = 5) -> list[str]:
    """Create sample incidents with timeline events."""
    incident_ids = []

    async with get_session_context() as session:
        for i in range(count):
            incident_id = uuid.uuid4()
            severity = random.choice(list(IncidentSeverity))
            status = random.choice(list(IncidentStatus))
            service = random.choice(SAMPLE_SERVICES)
            title = random.choice(SAMPLE_TITLES)

            incident = Incident(
                id=incident_id,
                title=f"[SEED] {title}",
                description=f"Sample incident #{i+1} for {service}",
                severity=severity,
                status=status,
                service_name=service,
            )
            session.add(incident)

            # Add timeline events
            base_time = datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 48))
            events = [
                ("incident_detected", f"Incident detected: {title}", "sentinel-system"),
                ("analysis_started", "AI analysis initiated", "ai-orchestrator"),
                ("analysis_completed", "Root cause analysis complete", "ai-orchestrator"),
            ]

            for j, (event_type, message, source) in enumerate(events):
                event = IncidentEvent(
                    id=uuid.uuid4(),
                    incident_id=incident_id,
                    event_type=event_type,
                    message=message,
                    source=source,
                    timestamp=base_time + timedelta(minutes=j * 2),
                )
                session.add(event)

            incident_ids.append(str(incident_id))
            print(f"  ✅ Incident {i+1}/{count}: {title} ({service}) — {status.value}")

    return incident_ids


async def seed_deployments(count: int = 5) -> list[str]:
    """Create sample deployment records."""
    deployment_ids = []

    async with get_session_context() as session:
        for i in range(count):
            dep_id = uuid.uuid4()
            service = random.choice(SAMPLE_SERVICES)
            status = random.choice([
                DeploymentStatus.SUCCEEDED,
                DeploymentStatus.SUCCEEDED,
                DeploymentStatus.SUCCEEDED,
                DeploymentStatus.FAILED,
                DeploymentStatus.ROLLED_BACK,
            ])

            deployment = Deployment(
                id=dep_id,
                service_name=service,
                version=f"v2.{random.randint(0,5)}.{random.randint(0,9)}",
                commit_sha=f"{random.randint(100000, 999999):06x}",
                deployed_by=random.choice(["ci-pipeline", "developer", "dependabot"]),
                environment="production",
                description=f"Sample deployment #{i+1}",
                status=status,
                created_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 72)),
            )
            session.add(deployment)
            deployment_ids.append(str(dep_id))
            print(f"  ✅ Deployment {i+1}/{count}: {service} — {status.value}")

    return deployment_ids


async def main(count: int = 5) -> None:
    """Seed the database."""
    print(f"\n{'='*60}")
    print(f"  Sentinel AI — Database Seeder")
    print(f"  Creating {count} sample incidents and deployments")
    print(f"{'='*60}\n")

    print("📦 Initializing database...")
    await init_db()

    print("\n📋 Creating incidents...")
    incident_ids = await seed_incidents(count)

    print("\n🚀 Creating deployments...")
    deployment_ids = await seed_deployments(count)

    print(f"\n{'='*60}")
    print(f"  Seeding complete!")
    print(f"  Incidents: {len(incident_ids)}")
    print(f"  Deployments: {len(deployment_ids)}")
    print(f"{'='*60}\n")

    await close_db()


def run():
    parser = argparse.ArgumentParser(description="Seed Sentinel AI database")
    parser.add_argument("--count", type=int, default=5, help="Number of items to seed")
    args = parser.parse_args()
    asyncio.run(main(args.count))


if __name__ == "__main__":
    run()
