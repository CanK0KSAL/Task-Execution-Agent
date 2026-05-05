"""Mock reminder_create(details) — deterministic reminder records."""

from __future__ import annotations

import hashlib
from typing import Any

from task_agent.domain.models import FailureReason, ToolCallResult, ToolName, ToolStatus


def reminder_create(details: dict[str, Any]) -> ToolCallResult:
    """Create a mock reminder; requires title and a time field."""
    if not isinstance(details, dict):
        return ToolCallResult(
            tool_name=ToolName.REMINDER_CREATE,
            status=ToolStatus.FAILURE,
            error_message="details must be a dictionary with title and time fields.",
            failure_reason=FailureReason.VALIDATION_ERROR,
        )

    if details.get("simulate_failure") is True:
        return ToolCallResult(
            tool_name=ToolName.REMINDER_CREATE,
            status=ToolStatus.TEMPORARY_FAILURE,
            error_message="Reminder service timed out (simulated).",
            failure_reason=FailureReason.TEMPORARY_TOOL_FAILURE,
        )

    title = details.get("title")
    when = details.get("reminder_time") or details.get("when")
    if title is None or str(title).strip() == "":
        return ToolCallResult(
            tool_name=ToolName.REMINDER_CREATE,
            status=ToolStatus.FAILURE,
            error_message="Reminder title is required.",
            failure_reason=FailureReason.VALIDATION_ERROR,
        )
    if when is None or str(when).strip() == "":
        return ToolCallResult(
            tool_name=ToolName.REMINDER_CREATE,
            status=ToolStatus.FAILURE,
            error_message="Reminder time is required (reminder_time or when).",
            failure_reason=FailureReason.VALIDATION_ERROR,
        )

    title_s = str(title).strip()
    when_s = str(when).strip()
    digest = hashlib.sha256(f"{title_s}|{when_s}".encode("utf-8")).hexdigest()[:12]
    reminder_id = f"rem-mock-{digest}"

    return ToolCallResult(
        tool_name=ToolName.REMINDER_CREATE,
        status=ToolStatus.SUCCESS,
        data={
            "reminder_id": reminder_id,
            "title": title_s,
            "reminder_time": when_s,
            "message": f"Reminder set for '{title_s}' at {when_s} (mock).",
        },
    )
