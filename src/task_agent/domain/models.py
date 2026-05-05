"""Core domain entities and enums (Pydantic v2)."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IntentType(str, Enum):
    BOOK_APPOINTMENT = "BOOK_APPOINTMENT"
    FIND_OPTIONS = "FIND_OPTIONS"
    PLAN_TRIP = "PLAN_TRIP"
    SCHEDULE_MEETING = "SCHEDULE_MEETING"
    CREATE_REMINDER = "CREATE_REMINDER"
    UNKNOWN = "UNKNOWN"


class ToolName(str, Enum):
    CALENDAR_CHECK = "calendar_check"
    SEARCH_SERVICE = "search_service"
    BOOKING_SERVICE = "booking_service"
    REMINDER_CREATE = "reminder_create"


class ToolStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    NO_RESULTS = "NO_RESULTS"
    TEMPORARY_FAILURE = "TEMPORARY_FAILURE"
    SKIPPED = "SKIPPED"


class AgentResponseType(str, Enum):
    CLARIFICATION = "CLARIFICATION"
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    BLOCKED = "BLOCKED"
    FAILURE = "FAILURE"


class FailureReason(str, Enum):
    MISSING_INFORMATION = "MISSING_INFORMATION"
    NO_RESULTS = "NO_RESULTS"
    TOOL_FAILURE = "TOOL_FAILURE"
    TEMPORARY_TOOL_FAILURE = "TEMPORARY_TOOL_FAILURE"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    UNSUPPORTED_REQUEST = "UNSUPPORTED_REQUEST"
    VALIDATION_ERROR = "VALIDATION_ERROR"


class Money(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: float = Field(..., gt=0)
    currency: str
    period: str | None = None


class DateRange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw: str
    start: str | None = None
    end: str | None = None
    timezone: str = "Europe/Warsaw"


class UserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    user_id: str | None = None
    locale: str = "en"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            msg = "UserRequest.text must not be empty"
            raise ValueError(msg)
        return stripped


class MissingField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    reason: str
    question: str
    required: bool = True

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            msg = "MissingField.question must not be empty"
            raise ValueError(msg)
        return stripped


class ToolCallPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: ToolName
    arguments: dict[str, Any] = Field(default_factory=dict)
    reason: str
    depends_on: list[str] = Field(default_factory=list)
    requires_confirmation: bool = False


class ToolCallResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: ToolName
    status: ToolStatus
    data: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    failure_reason: FailureReason | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int
    description: str
    tool_call: ToolCallPlan | None = None
    tool_result: ToolCallResult | None = None


class ExtractedTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: IntentType
    confidence: float = Field(..., ge=0, le=1)
    original_request: str
    slots: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[MissingField] = Field(default_factory=list)
    tool_plan: list[ToolCallPlan] = Field(default_factory=list)
    requires_user_confirmation: bool = False
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AgentFinalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_type: AgentResponseType
    message: str
    intent: IntentType = IntentType.UNKNOWN
    summary: str | None = None
    steps: list[AgentStep] = Field(default_factory=list)
    tool_results: list[ToolCallResult] = Field(default_factory=list)
    found_options: list[dict[str, Any]] = Field(default_factory=list)
    booked_item: dict[str, Any] | None = None
    reminder: dict[str, Any] | None = None
    missing_fields: list[MissingField] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    raw_task: ExtractedTask | None = None


class AgentMessage(BaseModel):
    """A single message in an agent conversation."""

    model_config = ConfigDict(extra="forbid")

    role: str = Field(..., description="e.g. system, user, assistant")
    content: str
