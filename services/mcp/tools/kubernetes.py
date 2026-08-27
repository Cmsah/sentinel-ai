"""MCP tools for Kubernetes cluster interaction.

Exposes kubectl-like operations as MCP tools that AI agents can invoke
during incident analysis.
"""

from __future__ import annotations

from typing import Any

from services.kubernetes.simulator import K8sSimulator


# Tool registry for MCP
TOOLS: dict[str, dict[str, Any]] = {}


def register_tool(name: str, description: str, parameters: dict):
    """Register an MCP tool."""
    def decorator(func):
        TOOLS[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "handler": func,
        }
        return func
    return decorator


_simulator = K8sSimulator()


@register_tool(
    name="kubernetes_get_pods",
    description="Get pod status for a namespace. Returns pod names, phases, restart counts, and container states.",
    parameters={
        "namespace": {"type": "string", "description": "Kubernetes namespace", "default": "default"},
        "label_selector": {"type": "string", "description": "Label selector filter (e.g., app=sentinel-api)"},
    },
)
async def get_pods(namespace: str = "default", label_selector: str = "") -> dict:
    """Get pods from the cluster (simulated)."""
    state = _simulator.simulate_crashloop_backoff()
    return {
        "namespace": namespace,
        "pods": [state["pod"]],
        "total": 1,
    }


@register_tool(
    name="kubernetes_describe_deployment",
    description="Describe a Kubernetes deployment. Returns replicas, strategy, conditions, and events.",
    parameters={
        "name": {"type": "string", "description": "Deployment name"},
        "namespace": {"type": "string", "description": "Kubernetes namespace", "default": "default"},
    },
)
async def describe_deployment(name: str, namespace: str = "default") -> dict:
    """Describe a deployment (simulated)."""
    state = _simulator.simulate_crashloop_backoff(service_name=name)
    return state["deployment"]


@register_tool(
    name="kubernetes_get_events",
    description="Get recent Kubernetes events for a namespace. Returns warnings, errors, and normal events.",
    parameters={
        "namespace": {"type": "string", "description": "Kubernetes namespace", "default": "default"},
        "field_selector": {"type": "string", "description": "Field selector (e.g., involvedObject.name=pod-name)"},
    },
)
async def get_events(namespace: str = "default", field_selector: str = "") -> dict:
    """Get cluster events (simulated)."""
    state = _simulator.simulate_crashloop_backoff()
    return {
        "namespace": namespace,
        "events": state["cluster_events"],
    }


@register_tool(
    name="kubernetes_get_logs",
    description="Get container logs from a pod. Returns recent log lines.",
    parameters={
        "pod_name": {"type": "string", "description": "Pod name"},
        "namespace": {"type": "string", "description": "Kubernetes namespace", "default": "default"},
        "container": {"type": "string", "description": "Container name (for multi-container pods)"},
        "tail_lines": {"type": "integer", "description": "Number of recent lines to return", "default": 100},
    },
)
async def get_logs(
    pod_name: str, namespace: str = "default",
    container: str = "", tail_lines: int = 100,
) -> dict:
    """Get pod logs (simulated)."""
    state = _simulator.simulate_crashloop_backoff()
    return {
        "pod": pod_name,
        "namespace": namespace,
        "container": container or "main",
        "logs": state.get("kubernetes_logs", []),
    }


@register_tool(
    name="kubernetes_get_configmap",
    description="Get a ConfigMap's data. Returns key-value pairs.",
    parameters={
        "name": {"type": "string", "description": "ConfigMap name"},
        "namespace": {"type": "string", "description": "Kubernetes namespace", "default": "default"},
    },
)
async def get_configmap(name: str, namespace: str = "default") -> dict:
    """Get ConfigMap data (simulated)."""
    state = _simulator.simulate_crashloop_backoff()
    return state.get("configmap_status", {"name": name, "exists": False})
