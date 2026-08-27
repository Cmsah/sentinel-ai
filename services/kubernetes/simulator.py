"""Kubernetes cluster state simulator.

Generates realistic pod, deployment, and event data that mirrors
what you'd get from kubectl. Used by the AI agents for analysis
when no real K8s cluster is available.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PodPhase(str, Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    UNKNOWN = "Unknown"


class PodCondition(str, Enum):
    READY = "Ready"
    CONTAINERS_READY = "ContainersReady"
    POD_SCHEDULED = "PodScheduled"
    INITIALIZED = "Initialized"


class RestartPolicy(str, Enum):
    ALWAYS = "Always"
    ON_FAILURE = "OnFailure"
    NEVER = "Never"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class ContainerStatus:
    name: str
    image: str
    ready: bool
    restart_count: int
    state: str  # running, waiting, terminated
    state_reason: str = ""
    exit_code: int = 0
    last_transition: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PodInfo:
    name: str
    namespace: str
    phase: PodPhase
    node: str
    pod_ip: str
    service_account: str
    containers: list[ContainerStatus]
    conditions: list[dict]
    events: list[dict]
    labels: dict[str, str] = field(default_factory=dict)
    restart_policy: str = "Always"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DeploymentInfo:
    name: str
    namespace: str
    replicas: int
    ready_replicas: int
    updated_replicas: int
    available_replicas: int
    strategy: str
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)
    conditions: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)


@dataclass
class ClusterEvent:
    type: str  # Normal, Warning
    reason: str
    message: str
    object_kind: str
    object_name: str
    namespace: str
    count: int = 1
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Simulator
# ---------------------------------------------------------------------------

class K8sSimulator:
    """Simulates Kubernetes cluster state for various failure scenarios.

    Generates realistic data that AI agents can analyze to determine
    root causes — just like real kubectl output.
    """

    def __init__(self) -> None:
        self._pods: dict[str, PodInfo] = {}
        self._deployments: dict[str, DeploymentInfo] = {}
        self._events: list[ClusterEvent] = []

    def simulate_crashloop_backoff(
        self,
        service_name: str = "sentinel-api",
        namespace: str = "default",
        failure_reason: str = "missing_env_var",
    ) -> dict:
        """Generate a CrashLoopBackOff scenario and return full cluster state.

        Scenarios:
        - missing_env_var: ConfigMap not mounted, env var missing
        - out_of_memory: Container OOMKilled
        - image_pull_error: Wrong image tag
        - application_error: App-level crash
        """
        now = datetime.now(timezone.utc)

        # Generate pod names
        replica_hash = f"{random.randint(10000, 99999)}"
        pod_name = f"{service_name}-{replica_hash}-{random.randint(1000, 9999)}"

        if failure_reason == "missing_env_var":
            return self._crashloop_missing_env(service_name, namespace, pod_name, now)
        elif failure_reason == "out_of_memory":
            return self._crashloop_oom(service_name, namespace, pod_name, now)
        elif failure_reason == "image_pull_error":
            return self._crashloop_image_pull(service_name, namespace, pod_name, now)
        else:
            return self._crashloop_app_error(service_name, namespace, pod_name, now)

    def _crashloop_missing_env(self, service: str, ns: str, pod: str, now: datetime) -> dict:
        """Simulate CrashLoopBackOff due to missing DATABASE_URL env var."""
        pod_info = PodInfo(
            name=pod,
            namespace=ns,
            phase=PodPhase.RUNNING,
            node="ip-10-0-1-42.ec2.internal",
            pod_ip="10.244.1.15",
            service_account=f"{service}-sa",
            labels={
                "app": service,
                "version": "v2.3.1",
                "environment": "production",
            },
            containers=[
                ContainerStatus(
                    name=service,
                    image=f"registry.internal/{service}:v2.3.1",
                    ready=False,
                    restart_count=7,
                    state="waiting",
                    state_reason="CrashLoopBackOff",
                    last_transition=now - timedelta(seconds=45),
                ),
                ContainerStatus(
                    name=f"{service}-sidecar",
                    image="fluent/fluent-bit:latest",
                    ready=True,
                    restart_count=0,
                    state="running",
                ),
            ],
            conditions=[
                {"type": "Initialized", "status": "True", "lastTransitionTime": now.isoformat()},
                {"type": "Ready", "status": "False", "reason": "ContainersNotReady", "lastTransitionTime": now.isoformat()},
                {"type": "ContainersReady", "status": "False", "reason": "ContainersNotReady", "lastTransitionTime": now.isoformat()},
                {"type": "PodScheduled", "status": "True", "lastTransitionTime": now.isoformat()},
            ],
            events=[
                {
                    "type": "Warning",
                    "reason": "BackOff",
                    "message": f"Back-off restarting failed container {service} in pod {pod}",
                    "count": 7,
                    "first_seen": (now - timedelta(minutes=8)).isoformat(),
                    "last_seen": now.isoformat(),
                },
                {
                    "type": "Normal",
                    "reason": "Started",
                    "message": f"Started container {service}-sidecar",
                    "count": 1,
                    "first_seen": (now - timedelta(minutes=10)).isoformat(),
                    "last_seen": (now - timedelta(minutes=10)).isoformat(),
                },
                {
                    "type": "Warning",
                    "reason": "FailedMount",
                    "message": "MountVolume.SetUp failed for volume 'config-volume': configmap 'app-config' not found",
                    "count": 1,
                    "first_seen": (now - timedelta(minutes=10)).isoformat(),
                    "last_seen": (now - timedelta(minutes=10)).isoformat(),
                },
            ],
        )

        deployment = DeploymentInfo(
            name=service,
            namespace=ns,
            replicas=3,
            ready_replicas=0,
            updated_replicas=3,
            available_replicas=0,
            strategy="RollingUpdate",
            labels={"app": service, "version": "v2.3.1"},
            annotations={
                "deployment.kubernetes.io/revision": "8",
                "kubernetes.io/change-cause": "Update env vars for database connection",
            },
            conditions=[
                {
                    "type": "Progressing",
                    "status": "True",
                    "reason": "NewReplicaSetAvailable",
                    "message": "replica set is progressing",
                    "lastTransitionTime": now.isoformat(),
                },
                {
                    "type": "Available",
                    "status": "False",
                    "reason": "MinimumReplicasUnavailable",
                    "message": "Deployment does not have minimum availability.",
                    "lastTransitionTime": now.isoformat(),
                },
            ],
            events=[
                {
                    "type": "Warning",
                    "reason": "ScalingReplicaSet",
                    "message": f"Scaled up replica set {service}-7d4f8b to 3",
                    "count": 1,
                    "first_seen": (now - timedelta(minutes=10)).isoformat(),
                    "last_seen": now.isoformat(),
                },
            ],
        )

        return {
            "scenario": "missing_env_var",
            "description": "ConfigMap 'app-config' not mounted — DATABASE_URL environment variable missing",
            "pod": self._pod_to_dict(pod_info),
            "deployment": self._deployment_to_dict(deployment),
            "cluster_events": self._events_to_list(pod_info.events),
            "kubernetes_logs": self._generate_logs_missing_env(service, pod, now),
            "configmap_status": {
                "name": "app-config",
                "exists": True,
                "data_keys": ["REDIS_HOST", "LOG_LEVEL"],
                "missing_keys": ["DATABASE_URL"],
                "last_modified": (now - timedelta(days=2)).isoformat(),
            },
        }

    def _crashloop_oom(self, service: str, ns: str, pod: str, now: datetime) -> dict:
        """Simulate CrashLoopBackOff due to OOMKilled."""
        pod_info = PodInfo(
            name=pod,
            namespace=ns,
            phase=PodPhase.RUNNING,
            node="ip-10-0-1-42.ec2.internal",
            pod_ip="10.244.1.15",
            service_account=f"{service}-sa",
            labels={"app": service, "version": "v2.3.1"},
            containers=[
                ContainerStatus(
                    name=service,
                    image=f"registry.internal/{service}:v2.3.1",
                    ready=False,
                    restart_count=5,
                    state="terminated",
                    state_reason="OOMKilled",
                    exit_code=137,
                    last_transition=now - timedelta(seconds=30),
                ),
            ],
            conditions=[
                {"type": "Initialized", "status": "True", "lastTransitionTime": now.isoformat()},
                {"type": "Ready", "status": "False", "reason": "ContainersNotReady", "lastTransitionTime": now.isoformat()},
                {"type": "ContainersReady", "status": "False", "reason": "ContainersNotReady", "lastTransitionTime": now.isoformat()},
                {"type": "PodScheduled", "status": "True", "lastTransitionTime": now.isoformat()},
            ],
            events=[
                {
                    "type": "Warning",
                    "reason": "OOMKilling",
                    "message": "Memory cgroup out of memory: Killed process",
                    "count": 5,
                    "first_seen": (now - timedelta(minutes=6)).isoformat(),
                    "last_seen": now.isoformat(),
                },
            ],
        )

        return {
            "scenario": "out_of_memory",
            "description": "Container OOMKilled — memory limit 256Mi exceeded, connection pool exhaustion caused memory spike",
            "pod": self._pod_to_dict(pod_info),
            "deployment": self._deployment_to_dict(DeploymentInfo(
                name=service, namespace=ns, replicas=3, ready_replicas=0,
                updated_replicas=3, available_replicas=0, strategy="RollingUpdate",
            )),
            "cluster_events": self._events_to_list(pod_info.events),
            "kubernetes_logs": self._generate_logs_oom(service, pod, now),
        }

    def _crashloop_image_pull(self, service: str, ns: str, pod: str, now: datetime) -> dict:
        pod_info = PodInfo(
            name=pod, namespace=ns, phase=PodPhase.PENDING,
            node="", pod_ip="", service_account=f"{service}-sa",
            labels={"app": service, "version": "v2.3.2"},
            containers=[
                ContainerStatus(
                    name=service,
                    image=f"registry.internal/{service}:v2.3.2-INVALID",
                    ready=False, restart_count=0, state="waiting",
                    state_reason="ImagePullBackOff",
                ),
            ],
            conditions=[
                {"type": "Initialized", "status": "True", "lastTransitionTime": now.isoformat()},
                {"type": "Ready", "status": "False", "reason": "ContainersNotReady", "lastTransitionTime": now.isoformat()},
                {"type": "PodScheduled", "status": "True", "lastTransitionTime": now.isoformat()},
            ],
            events=[{
                "type": "Warning", "reason": "Failed",
                "message": f"Failed to pull image 'registry.internal/{service}:v2.3.2-INVALID': rpc error: code = NotFound",
                "count": 3, "first_seen": (now - timedelta(minutes=2)).isoformat(), "last_seen": now.isoformat(),
            }],
        )
        return {
            "scenario": "image_pull_error",
            "description": "Image tag v2.3.2-INVALID does not exist in registry",
            "pod": self._pod_to_dict(pod_info),
            "deployment": self._deployment_to_dict(DeploymentInfo(
                name=service, namespace=ns, replicas=3, ready_replicas=0,
                updated_replicas=1, available_replicas=0, strategy="RollingUpdate",
            )),
            "cluster_events": self._events_to_list(pod_info.events),
        }

    def _crashloop_app_error(self, service: str, ns: str, pod: str, now: datetime) -> dict:
        pod_info = PodInfo(
            name=pod, namespace=ns, phase=PodPhase.RUNNING,
            node="ip-10-0-1-42.ec2.internal", pod_ip="10.244.1.15",
            service_account=f"{service}-sa",
            labels={"app": service, "version": "v2.3.1"},
            containers=[
                ContainerStatus(
                    name=service, image=f"registry.internal/{service}:v2.3.1",
                    ready=False, restart_count=3, state="terminated",
                    state_reason="Error", exit_code=1,
                    last_transition=now - timedelta(seconds=20),
                ),
            ],
            conditions=[
                {"type": "Ready", "status": "False", "reason": "ContainersNotReady", "lastTransitionTime": now.isoformat()},
                {"type": "PodScheduled", "status": "True", "lastTransitionTime": now.isoformat()},
            ],
            events=[{
                "type": "Warning", "reason": "BackOff",
                "message": f"Back-off restarting failed container in pod {pod}",
                "count": 3, "first_seen": (now - timedelta(minutes=3)).isoformat(), "last_seen": now.isoformat(),
            }],
        )
        return {
            "scenario": "application_error",
            "description": "Application crash — exit code 1",
            "pod": self._pod_to_dict(pod_info),
            "deployment": self._deployment_to_dict(DeploymentInfo(
                name=service, namespace=ns, replicas=3, ready_replicas=0,
                updated_replicas=3, available_replicas=0, strategy="RollingUpdate",
            )),
            "cluster_events": self._events_to_list(pod_info.events),
        }

    # -------------------------------------------------------------------
    # Helper methods
    # -------------------------------------------------------------------

    def _generate_logs_missing_env(self, service: str, pod: str, now: datetime) -> list[dict]:
        """Generate realistic application logs for missing env var scenario."""
        base_time = now - timedelta(minutes=5)
        return [
            {
                "timestamp": (base_time).isoformat(),
                "level": "INFO",
                "message": f"[{service}] Starting application v2.3.1",
                "pod": pod,
            },
            {
                "timestamp": (base_time + timedelta(seconds=2)).isoformat(),
                "level": "INFO",
                "message": f"[{service}] Loading configuration from environment variables",
                "pod": pod,
            },
            {
                "timestamp": (base_time + timedelta(seconds=3)).isoformat(),
                "level": "WARNING",
                "message": f"[{service}] DATABASE_URL environment variable not set",
                "pod": pod,
            },
            {
                "timestamp": (base_time + timedelta(seconds=3)).isoformat(),
                "level": "ERROR",
                "message": f"[{service}] ConnectionError: Could not connect to database — no connection string provided",
                "pod": pod,
            },
            {
                "timestamp": (base_time + timedelta(seconds=4)).isoformat(),
                "level": "ERROR",
                "message": f"[{service}] Fatal: Failed to initialize database connection pool after 3 retries",
                "pod": pod,
            },
            {
                "timestamp": (base_time + timedelta(seconds=5)).isoformat(),
                "level": "ERROR",
                "message": f"[{service}] Traceback (most recent call last):\n  File \"app/main.py\", line 42, in startup\n    db = await create_engine(settings.DATABASE_URL)\npsycopg2.OperationalError: connection to server timed out",
                "pod": pod,
            },
        ]

    def _generate_logs_oom(self, service: str, pod: str, now: datetime) -> list[dict]:
        base_time = now - timedelta(minutes=3)
        return [
            {"timestamp": base_time.isoformat(), "level": "INFO", "message": f"[{service}] Starting application v2.3.1", "pod": pod},
            {"timestamp": (base_time + timedelta(seconds=5)).isoformat(), "level": "INFO", "message": f"[{service}] Connected to database successfully", "pod": pod},
            {"timestamp": (base_time + timedelta(seconds=10)).isoformat(), "level": "INFO", "message": f"[{service}] Server listening on port 8080", "pod": pod},
            {"timestamp": (base_time + timedelta(minutes=1)).isoformat(), "level": "WARNING", "message": f"[{service}] Memory usage: 230MB / 256MB (89%)", "pod": pod},
            {"timestamp": (base_time + timedelta(minutes=1, seconds=15)).isoformat(), "level": "ERROR", "message": f"[{service}] Connection pool exhausted: max_connections=10 active=10 waiting=25", "pod": pod},
            {"timestamp": (base_time + timedelta(minutes=1, seconds=20)).isoformat(), "level": "ERROR", "message": f"[{service}] Memory usage: 248MB / 256MB (96%) — approaching limit", "pod": pod},
            {"timestamp": (base_time + timedelta(minutes=1, seconds=22)).isoformat(), "level": "ERROR", "message": f"[{service}] SIGKILL received — OOMKilled by kernel", "pod": pod},
        ]

    def _pod_to_dict(self, pod: PodInfo) -> dict:
        return {
            "metadata": {
                "name": pod.name,
                "namespace": pod.namespace,
                "labels": pod.labels,
                "created_at": pod.created_at.isoformat(),
            },
            "spec": {
                "node": pod.node,
                "pod_ip": pod.pod_ip,
                "service_account": pod.service_account,
                "restart_policy": pod.restart_policy,
                "containers": [
                    {
                        "name": c.name,
                        "image": c.image,
                        "ready": c.ready,
                        "restart_count": c.restart_count,
                        "state": c.state,
                        "state_reason": c.state_reason,
                        "exit_code": c.exit_code,
                        "last_transition": c.last_transition.isoformat(),
                    }
                    for c in pod.containers
                ],
            },
            "status": {
                "phase": pod.phase.value,
                "conditions": pod.conditions,
            },
        }

    def _deployment_to_dict(self, dep: DeploymentInfo) -> dict:
        return {
            "metadata": {
                "name": dep.name,
                "namespace": dep.namespace,
                "labels": dep.labels,
                "annotations": dep.annotations,
            },
            "spec": {
                "replicas": dep.replicas,
                "strategy": dep.strategy,
            },
            "status": {
                "replicas": dep.replicas,
                "ready_replicas": dep.ready_replicas,
                "updated_replicas": dep.updated_replicas,
                "available_replicas": dep.available_replicas,
            },
            "conditions": dep.conditions,
            "events": dep.events,
        }

    def _events_to_list(self, events: list[dict]) -> list[dict]:
        return events
