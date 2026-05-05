"""Domain-level errors (planner, tools, validation)."""

from __future__ import annotations

from typing import Any

from task_agent.domain.models import FailureReason


class AgentError(Exception):
    """Base error for the task agent."""

    def __init__(
        self,
        message: str,
        *,
        tool_name: str | None = None,
        failure_reason: FailureReason | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.tool_name = tool_name
        self.failure_reason = failure_reason
        self.details = details or {}


class MissingRequiredInfoError(AgentError):
    """Raised when required user information is absent."""

    def __init__(
        self,
        message: str,
        *,
        tool_name: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            tool_name=tool_name,
            failure_reason=FailureReason.MISSING_INFORMATION,
            details=details,
        )


class ToolExecutionError(AgentError):
    """Raised when a tool fails in a non-recoverable way."""

    def __init__(
        self,
        message: str,
        *,
        tool_name: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            tool_name=tool_name,
            failure_reason=FailureReason.TOOL_FAILURE,
            details=details,
        )


class ToolNoResultsError(AgentError):
    """Raised when a tool completes but finds nothing."""

    def __init__(
        self,
        message: str,
        *,
        tool_name: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            tool_name=tool_name,
            failure_reason=FailureReason.NO_RESULTS,
            details=details,
        )


class ToolTemporaryFailureError(AgentError):
    """Raised for transient tool/API failures."""

    def __init__(
        self,
        message: str,
        *,
        tool_name: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            tool_name=tool_name,
            failure_reason=FailureReason.TEMPORARY_TOOL_FAILURE,
            details=details,
        )


class UnsupportedRequestError(AgentError):
    """Raised when the request cannot be handled by the agent."""

    def __init__(
        self,
        message: str,
        *,
        tool_name: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            tool_name=tool_name,
            failure_reason=FailureReason.UNSUPPORTED_REQUEST,
            details=details,
        )


# Backward-compatible alias for early scaffold code.
TaskAgentError = AgentError
