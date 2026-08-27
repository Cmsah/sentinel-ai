"""Domain-specific exception classes for Sentinel AI.

These exceptions provide structured error handling across all services.
Each exception carries a code, message, and optional details for
debugging and API responses.
"""

from __future__ import annotations

from typing import Any


class SentinelError(Exception):
    """Base exception for all Sentinel AI errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
        status_code: int = 500,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.status_code = status_code

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

class DatabaseError(SentinelError):
    def __init__(self, message: str = "Database operation failed", **kwargs: Any) -> None:
        super().__init__(message, code="DATABASE_ERROR", status_code=500, **kwargs)


class NotFoundError(SentinelError):
    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(
            f"{resource} with id '{resource_id}' not found",
            code="NOT_FOUND",
            details={"resource": resource, "id": resource_id},
            status_code=404,
        )


# ---------------------------------------------------------------------------
# Kafka
# ---------------------------------------------------------------------------

class KafkaError(SentinelError):
    def __init__(self, message: str = "Kafka operation failed", **kwargs: Any) -> None:
        super().__init__(message, code="KAFKA_ERROR", status_code=500, **kwargs)


# ---------------------------------------------------------------------------
# AI / LLM
# ---------------------------------------------------------------------------

class AIAnalysisError(SentinelError):
    def __init__(self, message: str = "AI analysis failed", **kwargs: Any) -> None:
        super().__init__(message, code="AI_ANALYSIS_ERROR", status_code=500, **kwargs)


class AgentTimeoutError(AIAnalysisError):
    def __init__(self, agent_name: str, timeout_seconds: int) -> None:
        super().__init__(
            f"Agent '{agent_name}' timed out after {timeout_seconds}s",
            code="AGENT_TIMEOUT",
            details={"agent": agent_name, "timeout": timeout_seconds},
        )


# ---------------------------------------------------------------------------
# External Services
# ---------------------------------------------------------------------------

class ExternalServiceError(SentinelError):
    def __init__(self, service: str, message: str = "External service call failed", **kwargs: Any) -> None:
        super().__init__(
            f"[{service}] {message}",
            code="EXTERNAL_SERVICE_ERROR",
            details={"service": service},
            status_code=502,
            **kwargs,
        )


class GitHubError(ExternalServiceError):
    def __init__(self, message: str = "GitHub API call failed", **kwargs: Any) -> None:
        super().__init__("github", message, **kwargs)


class JiraError(ExternalServiceError):
    def __init__(self, message: str = "Jira API call failed", **kwargs: Any) -> None:
        super().__init__("jira", message, **kwargs)


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

class WorkflowError(SentinelError):
    def __init__(self, message: str = "Workflow execution failed", **kwargs: Any) -> None:
        super().__init__(message, code="WORKFLOW_ERROR", status_code=500, **kwargs)


class WorkflowStepError(WorkflowError):
    def __init__(self, step_name: str, reason: str) -> None:
        super().__init__(
            f"Workflow step '{step_name}' failed: {reason}",
            code="WORKFLOW_STEP_ERROR",
            details={"step": step_name, "reason": reason},
        )
