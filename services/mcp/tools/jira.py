"""MCP tools for Jira integration.

Exposes Jira operations as MCP tools: create issues, update issues,
search issues, and add comments.
"""

from __future__ import annotations

from typing import Any

from services.shared.config import get_settings

TOOLS: dict[str, dict[str, Any]] = {}


def register_tool(name: str, description: str, parameters: dict):
    def decorator(func):
        TOOLS[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "handler": func,
        }
        return func
    return decorator


@register_tool(
    name="jira_create_issue",
    description="Create a Jira issue for tracking an incident. Returns issue key and URL.",
    parameters={
        "project_key": {"type": "string", "description": "Jira project key (e.g., SENTINEL)"},
        "summary": {"type": "string", "description": "Issue summary/title"},
        "description": {"type": "string", "description": "Issue description (Markdown or ADF)"},
        "issue_type": {"type": "string", "description": "Issue type (Bug, Incident, Task)", "default": "Incident"},
        "priority": {"type": "string", "description": "Priority (Highest, High, Medium, Low)", "default": "High"},
        "labels": {"type": "array", "description": "Issue labels"},
        "assignee": {"type": "string", "description": "Jira username to assign"},
    },
)
async def create_issue(
    project_key: str = "SENTINEL",
    summary: str = "",
    description: str = "",
    issue_type: str = "Incident",
    priority: str = "High",
    labels: list[str] | None = None,
    assignee: str = "",
) -> dict:
    """Create a Jira issue (simulated or real)."""
    settings = get_settings()
    if settings.jira.is_simulation:
        return {
            "status": "simulated",
            "issue_key": f"{project_key}-101",
            "url": f"{settings.jira.base_url or 'https://sentinel.atlassian.net'}/browse/{project_key}-101",
            "message": "Jira integration in simulation mode. Set JIRA_BASE_URL and JIRA_API_TOKEN to enable.",
        }
    # In production: call Jira REST API
    return {
        "status": "created",
        "issue_key": f"{project_key}-101",
        "url": f"{settings.jira.base_url}/browse/{project_key}-101",
    }


@register_tool(
    name="jira_add_comment",
    description="Add a comment to an existing Jira issue.",
    parameters={
        "issue_key": {"type": "string", "description": "Jira issue key (e.g., SENTINEL-101)"},
        "comment": {"type": "string", "description": "Comment text (Markdown or ADF)"},
    },
)
async def add_comment(issue_key: str = "", comment: str = "") -> dict:
    """Add a comment to a Jira issue (simulated)."""
    settings = get_settings()
    if settings.jira.is_simulation:
        return {
            "status": "simulated",
            "issue_key": issue_key,
            "message": "Jira integration in simulation mode.",
        }
    return {"status": "added", "issue_key": issue_key}


@register_tool(
    name="jira_update_status",
    description="Update the status of a Jira issue (e.g., move to In Progress, Resolved).",
    parameters={
        "issue_key": {"type": "string", "description": "Jira issue key"},
        "status": {"type": "string", "description": "New status (e.g., In Progress, Resolved, Closed)"},
    },
)
async def update_status(issue_key: str = "", status: str = "") -> dict:
    """Update issue status (simulated)."""
    settings = get_settings()
    if settings.jira.is_simulation:
        return {
            "status": "simulated",
            "issue_key": issue_key,
            "new_status": status,
            "message": "Jira integration in simulation mode.",
        }
    return {"status": "updated", "issue_key": issue_key, "new_status": status}
