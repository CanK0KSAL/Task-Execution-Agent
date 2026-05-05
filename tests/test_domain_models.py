"""Tests for domain models, enums, and errors."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from task_agent.domain.schemas import (
    AgentError,
    AgentFinalResponse,
    AgentResponseType,
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


def test_user_request_rejects_empty_text() -> None:
    with pytest.raises(ValidationError):
        UserRequest(text="")
    with pytest.raises(ValidationError):
        UserRequest(text="   \n")


def test_money_rejects_non_positive_amount() -> None:
    with pytest.raises(ValidationError):
        Money(amount=-1.0, currency="USD")
    with pytest.raises(ValidationError):
        Money(amount=0, currency="EUR")


def test_extracted_task_coworking_search() -> None:
    task = ExtractedTask(
        intent=IntentType.FIND_OPTIONS,
        confidence=0.86,
        original_request="Find coworking spaces with fast Wi‑Fi near the center",
        slots={"category": "coworking", "needs": ["wifi"], "area": "city_center"},
        tool_plan=[
            ToolCallPlan(
                tool_name=ToolName.SEARCH_SERVICE,
                arguments={"query": "coworking fast wifi city center"},
                reason="Locate options matching workspace criteria",
            )
        ],
    )
    assert task.intent == IntentType.FIND_OPTIONS
    assert task.tool_plan[0].tool_name == ToolName.SEARCH_SERVICE
    assert task.slots["category"] == "coworking"


def test_extracted_task_dentist_missing_city() -> None:
    task = ExtractedTask(
        intent=IntentType.BOOK_APPOINTMENT,
        confidence=0.72,
        original_request="Book a dentist appointment next week",
        slots={"specialty": "dentistry", "timeframe": "next_week"},
        missing_fields=[
            MissingField(
                name="city",
                reason="Location is required to search clinics.",
                question="Which city should I look in for the dentist?",
            )
        ],
    )
    assert task.intent == IntentType.BOOK_APPOINTMENT
    assert len(task.missing_fields) == 1
    assert task.missing_fields[0].name == "city"


def test_tool_call_plan_serializes_enum_value() -> None:
    plan = ToolCallPlan(
        tool_name=ToolName.CALENDAR_CHECK,
        arguments={"date_range": "2026-05-10 to 2026-05-12"},
        reason="Check availability before proposing slots",
    )
    dumped = plan.model_dump(mode="json")
    assert dumped["tool_name"] == "calendar_check"
    assert isinstance(dumped["arguments"], dict)


def test_tool_call_result_success() -> None:
    result = ToolCallResult(
        tool_name=ToolName.SEARCH_SERVICE,
        status=ToolStatus.SUCCESS,
        data={"items": [{"id": "a1", "title": "Option A"}]},
    )
    assert result.failure_reason is None
    assert result.status == ToolStatus.SUCCESS


def test_tool_call_result_failure_with_reason() -> None:
    result = ToolCallResult(
        tool_name=ToolName.BOOKING_SERVICE,
        status=ToolStatus.FAILURE,
        error_message="Payment declined",
        failure_reason=FailureReason.TOOL_FAILURE,
    )
    assert result.failure_reason == FailureReason.TOOL_FAILURE


def test_agent_final_response_clarification_serializes() -> None:
    response = AgentFinalResponse(
        response_type=AgentResponseType.CLARIFICATION,
        message="I need a bit more detail to continue.",
        intent=IntentType.BOOK_APPOINTMENT,
        missing_fields=[
            MissingField(
                name="preferred_time",
                reason="Narrow appointment window.",
                question="What time of day works best for you?",
            )
        ],
    )
    payload = response.model_dump(mode="json")
    serialized = json.dumps(payload)
    data = json.loads(serialized)
    assert data["response_type"] == "CLARIFICATION"
    assert data["missing_fields"][0]["name"] == "preferred_time"


def test_agent_final_response_success_with_found_options() -> None:
    response = AgentFinalResponse(
        response_type=AgentResponseType.SUCCESS,
        message="Here are matching options.",
        intent=IntentType.FIND_OPTIONS,
        found_options=[
            {"id": "1", "name": "Hub A", "price_per_day": 20},
            {"id": "2", "name": "Hub B", "price_per_day": 25},
        ],
    )
    assert len(response.found_options) == 2
    dumped = response.model_dump(mode="json")
    assert dumped["found_options"][0]["name"] == "Hub A"


def test_agent_error_carries_details() -> None:
    err = AgentError(
        "Tool timed out",
        tool_name="search_service",
        failure_reason=FailureReason.TEMPORARY_TOOL_FAILURE,
        details={"status_code": 503, "retry_after": 30},
    )
    assert err.message == "Tool timed out"
    assert err.tool_name == "search_service"
    assert err.failure_reason == FailureReason.TEMPORARY_TOOL_FAILURE
    assert err.details["status_code"] == 503
