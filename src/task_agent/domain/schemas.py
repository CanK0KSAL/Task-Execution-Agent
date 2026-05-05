"""
Stable import surface for domain contracts.

Prefer `from task_agent.domain.schemas import ExtractedTask` at app boundaries.
"""

from __future__ import annotations

from task_agent.domain.errors import (
    AgentError,
    MissingRequiredInfoError,
    ToolExecutionError,
    ToolNoResultsError,
    ToolTemporaryFailureError,
    UnsupportedRequestError,
)
from task_agent.domain.models import (
    AgentFinalResponse,
    AgentMessage,
    AgentResponseType,
    AgentStep,
    DateRange,
    ExtractedTask,
    FailureReason,
    IntentType,
    MissingField,
    Money,
    ToolCallPlan,
    ToolCallResult,
    ToolName,
    ToolStatus,
    UserRequest,
)

__all__ = [
    "AgentError",
    "AgentFinalResponse",
    "AgentMessage",
    "AgentResponseType",
    "AgentStep",
    "DateRange",
    "ExtractedTask",
    "FailureReason",
    "IntentType",
    "MissingField",
    "MissingRequiredInfoError",
    "Money",
    "ToolCallPlan",
    "ToolCallResult",
    "ToolExecutionError",
    "ToolName",
    "ToolNoResultsError",
    "ToolStatus",
    "ToolTemporaryFailureError",
    "UnsupportedRequestError",
    "UserRequest",
]
