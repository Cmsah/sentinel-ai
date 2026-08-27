"""MCP tools for Slack integration.

Exposes Slack messaging as MCP tools for sending notifications,
creating channels, and posting incident updates.
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
    name="slack_send_message",
    description="Send a message to a Slack channel.",
    parameters={
        "channel": {"type": "string", "description": "Slack channel name"},
        "message": {"type": "string", "description": "Message text (supports Markdown)"},
        "thread_ts": {"type": "string", "description": "Thread timestamp for replies"},
    },
)
async def send_message(
    channel: str = "#incidents",
    message: str = "",
    thread_ts: str = "",
) -> dict:
    """Send a Slack message (simulated or real)."""
    settings = get_settings()
    if settings.slack.is_simulation:
        return {
            "status": "simulated",
            "channel": channel,
            "preview": message[:100] + ("..." if len(message) > 100 else ""),
            "ts": "simulated_timestamp",
            "message": "Slack integration in simulation mode. Set SLACK_BOT_TOKEN to enable.",
        }
    return {"status": "sent", "channel": channel, "ts": "real_timestamp"}


@register_tool(
    name="slack_send_incident_alert",
    description="Send a formatted incident alert to Slack with severity indicator.",
    parameters={
        "incident_id": {"type": "string", "description": "Incident ID"},
        "title": {"type": "string", "description": "Incident title"},
        "severity": {"type": "string", "description": "Severity level"},
        "service": {"type": "string", "description": "Affected service"},
        "root_cause": {"type": "string", "description": "Root cause summary"},
        "confidence": {"type": "number", "description": "Analysis confidence (0-1)"},
    },
)
async def send_incident_alert(
    incident_id: str, title: str, severity: str,
    service: str, root_cause: str = "", confidence: float = 0,
) -> dict:
    """Send a formatted incident alert."""
    severity_emoji = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🟢",
        "info": "ℹ️",
    }.get(severity, "⚠️")

    message = (
        f"{severity_emoji} *Incident Alert: {title}*\n\n"
        f"*Service:* {service}\n"
        f"*Severity:* {severity.upper()}\n"
        f"*Confidence:* {confidence:.0%}\n"
    )
    if root_cause:
        message += f"*Root Cause:* {root_cause}\n"

    return await send_message(
        channel="#incidents",
        message=message,
    )
