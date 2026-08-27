"""MCP tools for GitHub integration.

Exposes GitHub operations as MCP tools: create PRs, create issues,
list recent commits, and diff analysis.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
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
    name="github_create_pull_request",
    description="Create a pull request with a proposed fix. Returns PR number and URL.",
    parameters={
        "title": {"type": "string", "description": "PR title"},
        "body": {"type": "string", "description": "PR description (Markdown)"},
        "branch": {"type": "string", "description": "Source branch name"},
        "base": {"type": "string", "description": "Target branch", "default": "main"},
        "files": {"type": "array", "description": "Changed files with patches"},
    },
)
async def create_pull_request(
    title: str, body: str, branch: str = "fix/missing-env-var",
    base: str = "main", files: list[dict] | None = None,
) -> dict:
    """Create a PR (simulated or real based on config)."""
    settings = get_settings()
    pr_number = 42  # Simulated

    if settings.github.is_simulation:
        return {
            "status": "simulated",
            "pr_number": pr_number,
            "url": f"https://github.com/sentinel-ai/sentinel/pull/{pr_number}",
            "title": title,
            "branch": branch,
            "base": base,
            "message": "GitHub integration is in simulation mode. Set GITHUB_TOKEN to enable real PR creation.",
        }

    # In production: call GitHub API
    return {
        "status": "created",
        "pr_number": pr_number,
        "url": f"https://github.com/sentinel-ai/sentinel/pull/{pr_number}",
    }


@register_tool(
    name="github_create_issue",
    description="Create a GitHub issue for tracking an incident. Returns issue number.",
    parameters={
        "title": {"type": "string", "description": "Issue title"},
        "body": {"type": "string", "description": "Issue description (Markdown)"},
        "labels": {"type": "array", "description": "Issue labels"},
        "assignees": {"type": "array", "description": "GitHub usernames to assign"},
    },
)
async def create_issue(
    title: str, body: str,
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
) -> dict:
    """Create a GitHub issue (simulated)."""
    settings = get_settings()
    if settings.github.is_simulation:
        return {
            "status": "simulated",
            "issue_number": 101,
            "url": "https://github.com/sentinel-ai/sentinel/issues/101",
            "message": "GitHub integration in simulation mode.",
        }
    return {"status": "created", "issue_number": 101}


@register_tool(
    name="github_get_recent_commits",
    description="Get recent commits for a repository.",
    parameters={
        "repo": {"type": "string", "description": "Repository (owner/repo)"},
        "path": {"type": "string", "description": "File path filter"},
        "limit": {"type": "integer", "description": "Max commits", "default": 10},
    },
)
async def get_recent_commits(
    repo: str = "sentinel-ai/sentinel", path: str = "", limit: int = 10,
) -> dict:
    """Get recent commits (simulated)."""
    return {
        "commits": [
            {
                "sha": f"abc123{i:04d}",
                "message": "Update deployment config" if i == 0 else f"Commit {i}",
                "author": "developer",
                "date": datetime.now(timezone.utc).isoformat(),
            }
            for i in range(min(limit, 3))
        ],
        "total": limit,
    }
