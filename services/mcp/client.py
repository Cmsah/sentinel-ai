"""MCP client for AI agents to invoke tools programmatically.

This client wraps the MCP server and provides a clean interface
for agents to call external tools during analysis.
"""

from __future__ import annotations

from typing import Any

import structlog

from services.mcp.server import get_mcp_server

logger = structlog.get_logger(__name__)


class SentinelMCPClient:
    """Client interface for invoking MCP tools from AI agents.

    Usage:
        client = SentinelMCPClient()
        result = await client.kubernetes_get_pods(namespace="default")
        result = await client.invoke("github_create_pull_request", title="Fix...")
    """

    def __init__(self) -> None:
        self._server = get_mcp_server()

    async def invoke(self, tool_name: str, **kwargs: Any) -> dict[str, Any]:
        """Invoke any MCP tool by name."""
        return await self._server.invoke_tool(tool_name, kwargs)

    # --- Convenience methods ---

    async def kubernetes_get_pods(
        self, namespace: str = "default", label_selector: str = "",
    ) -> dict:
        return await self.invoke("kubernetes_get_pods", namespace=namespace, label_selector=label_selector)

    async def kubernetes_describe_deployment(
        self, name: str, namespace: str = "default",
    ) -> dict:
        return await self.invoke("kubernetes_describe_deployment", name=name, namespace=namespace)

    async def kubernetes_get_events(
        self, namespace: str = "default", field_selector: str = "",
    ) -> dict:
        return await self.invoke("kubernetes_get_events", namespace=namespace, field_selector=field_selector)

    async def kubernetes_get_logs(
        self, pod_name: str, namespace: str = "default",
        container: str = "", tail_lines: int = 100,
    ) -> dict:
        return await self.invoke(
            "kubernetes_get_logs",
            pod_name=pod_name, namespace=namespace,
            container=container, tail_lines=tail_lines,
        )

    async def prometheus_query(
        self, query: str = "", service: str = "sentinel-api",
    ) -> dict:
        return await self.invoke("prometheus_query_instant", query=query, service=service)

    async def prometheus_query_range(
        self, query: str = "", service: str = "sentinel-api", minutes_back: int = 30,
    ) -> dict:
        return await self.invoke("prometheus_query_range", query=query, service=service, minutes_back=minutes_back)

    async def github_create_pr(
        self, title: str, body: str, branch: str = "fix/proposed",
    ) -> dict:
        return await self.invoke("github_create_pull_request", title=title, body=body, branch=branch)

    async def github_create_issue(
        self, title: str, body: str, labels: list[str] | None = None,
    ) -> dict:
        return await self.invoke("github_create_issue", title=title, body=body, labels=labels or [])

    async def jira_create_issue(self, project_key: str = "SENTINEL", summary: str = "", description: str = "", issue_type: str = "Incident", priority: str = "High") -> dict:
        return await self.invoke(
            "jira_create_issue", project_key=project_key, summary=summary,
            description=description, issue_type=issue_type, priority=priority,
        )

    async def jira_add_comment(self, issue_key: str = "", comment: str = "") -> dict:
        return await self.invoke("jira_add_comment", issue_key=issue_key, comment=comment)

    async def jira_update_status(self, issue_key: str = "", status: str = "") -> dict:
        return await self.invoke("jira_update_status", issue_key=issue_key, status=status)

    async def slack_send_incident_alert(
        self, incident_id: str, title: str, severity: str,
        service: str, root_cause: str = "", confidence: float = 0,
    ) -> dict:
        return await self.invoke(
            "slack_send_incident_alert",
            incident_id=incident_id, title=title, severity=severity,
            service=service, root_cause=root_cause, confidence=confidence,
        )

    def list_available_tools(self) -> list[str]:
        """List all available tool names."""
        return [t["name"] for t in self._server.list_tools()]
