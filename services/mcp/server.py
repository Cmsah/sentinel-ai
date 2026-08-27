"""MCP (Model Context Protocol) server for Sentinel AI.

Exposes all external system integrations as MCP tools that can be
invoked by AI agents or external MCP clients.

Tool catalog:
- Kubernetes: get_pods, describe_deployment, get_events, get_logs, get_configmap
- GitHub: create_pull_request, create_issue, get_recent_commits
- Prometheus: query_instant, query_range
- Slack: send_message, send_incident_alert
"""

from __future__ import annotations

from typing import Any

import structlog

from services.mcp.tools.kubernetes import TOOLS as K8S_TOOLS
from services.mcp.tools.github import TOOLS as GITHUB_TOOLS
from services.mcp.tools.jira import TOOLS as JIRA_TOOLS
from services.mcp.tools.prometheus import TOOLS as PROM_TOOLS
from services.mcp.tools.slack import TOOLS as SLACK_TOOLS

logger = structlog.get_logger(__name__)

# Merge all tools into a single registry
ALL_TOOLS: dict[str, dict[str, Any]] = {}
ALL_TOOLS.update(K8S_TOOLS)
ALL_TOOLS.update(GITHUB_TOOLS)
ALL_TOOLS.update(JIRA_TOOLS)
ALL_TOOLS.update(PROM_TOOLS)
ALL_TOOLS.update(SLACK_TOOLS)


class SentinelMCPServer:
    """MCP server that exposes Sentinel AI tools.

    This can be run standalone or embedded within the FastAPI app.
    """

    def __init__(self) -> None:
        self._tools = ALL_TOOLS
        logger.info("mcp_server_initialized", tool_count=len(self._tools))

    def list_tools(self) -> list[dict[str, Any]]:
        """Return all available MCP tools."""
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
            }
            for tool in self._tools.values()
        ]

    async def invoke_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke an MCP tool by name with arguments."""
        if name not in self._tools:
            return {
                "error": f"Tool '{name}' not found. Available: {list(self._tools.keys())}",
            }

        tool = self._tools[name]
        handler = tool["handler"]

        logger.info("mcp_tool_invoked", tool=name, arguments=list(arguments.keys()))

        try:
            result = await handler(**arguments)
            return {
                "status": "success",
                "tool": name,
                "result": result,
            }
        except Exception as exc:
            logger.error("mcp_tool_failed", tool=name, error=str(exc))
            return {
                "status": "error",
                "tool": name,
                "error": str(exc),
            }

    def get_tool_catalog(self) -> dict[str, Any]:
        """Return a complete tool catalog for documentation."""
        return {
            "server": "sentinel-ai-mcp",
            "version": "0.1.0",
            "tool_count": len(self._tools),
            "categories": {
                "kubernetes": [t for t in K8S_TOOLS.keys()],
                "github": [t for t in GITHUB_TOOLS.keys()],
                "jira": [t for t in JIRA_TOOLS.keys()],
                "prometheus": [t for t in PROM_TOOLS.keys()],
                "slack": [t for t in SLACK_TOOLS.keys()],
            },
            "tools": self.list_tools(),
        }


# Singleton
_server: SentinelMCPServer | None = None


def get_mcp_server() -> SentinelMCPServer:
    """Get or create the MCP server singleton."""
    global _server
    if _server is None:
        _server = SentinelMCPServer()
    return _server
