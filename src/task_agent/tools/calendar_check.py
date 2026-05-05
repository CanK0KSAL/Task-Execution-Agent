"""Mock calendar_check(date_range) — deterministic availability from local JSON."""

from __future__ import annotations

from typing import Any

from task_agent.domain.models import FailureReason, ToolCallResult, ToolName, ToolStatus
from task_agent.tools.helpers import (
    calendar_pattern_key,
    load_json_data,
    normalize_date_range_key,
)


def calendar_check(date_range: str | dict[str, Any]) -> ToolCallResult:
    """Return calendar slots for known demo phrases; otherwise NO_RESULTS or validation FAILURE."""
    normalized = normalize_date_range_key(date_range)
    if not normalized:
        return ToolCallResult(
            tool_name=ToolName.CALENDAR_CHECK,
            status=ToolStatus.FAILURE,
            error_message="date_range is required and cannot be empty.",
            failure_reason=FailureReason.VALIDATION_ERROR,
        )

    key = calendar_pattern_key(normalized)
    if key is None:
        return ToolCallResult(
            tool_name=ToolName.CALENDAR_CHECK,
            status=ToolStatus.NO_RESULTS,
            error_message=(
                "No calendar availability was found for that date range in the mock calendar."
            ),
            failure_reason=FailureReason.NO_RESULTS,
            data={
                "query": normalized,
                "available_slots": [],
                "busy_slots": [],
                "timezone": "Europe/Warsaw",
            },
        )

    payload = load_json_data("mock_calendar.json")
    groups: dict[str, Any] = payload.get("groups", {})
    group = groups.get(key)
    if not group:
        return ToolCallResult(
            tool_name=ToolName.CALENDAR_CHECK,
            status=ToolStatus.NO_RESULTS,
            error_message="Calendar group missing in mock data.",
            failure_reason=FailureReason.NO_RESULTS,
            data={
                "query": normalized,
                "available_slots": [],
                "busy_slots": [],
                "timezone": payload.get("timezone_default", "Europe/Warsaw"),
            },
        )

    slots: list[dict[str, Any]] = list(group.get("slots", []))
    available = [s for s in slots if s.get("available") is True]
    busy = [s for s in slots if s.get("available") is False]
    tz = str(group.get("timezone") or payload.get("timezone_default", "Europe/Warsaw"))

    return ToolCallResult(
        tool_name=ToolName.CALENDAR_CHECK,
        status=ToolStatus.SUCCESS,
        data={
            "query": normalized,
            "available_slots": available,
            "busy_slots": busy,
            "timezone": tz,
        },
    )
