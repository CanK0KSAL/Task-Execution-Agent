"""Tool registry: name resolution and structured execution."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from task_agent.domain.models import FailureReason, ToolCallResult, ToolName, ToolStatus
from task_agent.tools import booking_service, calendar_check, reminder_create, search_service

ToolFn = Callable[..., ToolCallResult]

_TOOL_FUNCTIONS: dict[str, ToolFn] = {
    ToolName.CALENDAR_CHECK.value: calendar_check.calendar_check,
    ToolName.SEARCH_SERVICE.value: search_service.search_service,
    ToolName.BOOKING_SERVICE.value: booking_service.booking_service,
    ToolName.REMINDER_CREATE.value: reminder_create.reminder_create,
}

REGISTRY: dict[str, ToolFn] = _TOOL_FUNCTIONS


def _normalize_tool_name(tool_name: ToolName | str) -> str:
    if isinstance(tool_name, ToolName):
        return tool_name.value
    return str(tool_name).strip()


def get_tool(name: str) -> ToolFn:
    """Return a registered tool callable by string name (raises if unknown)."""
    if name not in REGISTRY:
        msg = f"Unknown tool: {name}"
        raise KeyError(msg)
    return REGISTRY[name]


class ToolRegistry:
    """Maps tool names to callables and dispatches structured execution."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolFn] = dict(_TOOL_FUNCTIONS)

    def get(self, tool_name: ToolName | str) -> ToolFn:
        key = _normalize_tool_name(tool_name)
        if key not in self._tools:
            msg = f"Unknown tool: {key}"
            raise KeyError(msg)
        return self._tools[key]

    def execute(
        self,
        tool_name: ToolName | str,
        arguments: dict[str, Any],
    ) -> ToolCallResult:
        """Run a tool by name; unknown tools return a failure `ToolCallResult`."""
        key = _normalize_tool_name(tool_name)
        if key not in self._tools:
            return ToolCallResult(
                tool_name=ToolName.CALENDAR_CHECK,
                status=ToolStatus.FAILURE,
                error_message=(
                    f"Unknown tool '{key}'. Registered tools: "
                    f"{', '.join(sorted(self._tools))}."
                ),
                failure_reason=FailureReason.VALIDATION_ERROR,
                metadata={"requested_tool": key, "unknown_tool": True},
            )

        args = dict(arguments or {})

        if key == ToolName.CALENDAR_CHECK.value:
            date_range = args.get("date_range", "")
            return calendar_check.calendar_check(date_range)

        if key == ToolName.SEARCH_SERVICE.value:
            query = args.get("query", "")
            return search_service.search_service(query)

        if key == ToolName.BOOKING_SERVICE.value:
            option = args.get("option")
            if option is None:
                option = {k: v for k, v in args.items() if k != "tool_name"}
            return booking_service.booking_service(option)

        if key == ToolName.REMINDER_CREATE.value:
            details = args.get("details")
            if details is None:
                return ToolCallResult(
                    tool_name=ToolName.REMINDER_CREATE,
                    status=ToolStatus.FAILURE,
                    error_message=(
                        "reminder_create requires a 'details' dict "
                        "(title, reminder_time or when)."
                    ),
                    failure_reason=FailureReason.VALIDATION_ERROR,
                )
            if not isinstance(details, dict):
                return ToolCallResult(
                    tool_name=ToolName.REMINDER_CREATE,
                    status=ToolStatus.FAILURE,
                    error_message="reminder_create 'details' must be an object.",
                    failure_reason=FailureReason.VALIDATION_ERROR,
                )
            return reminder_create.reminder_create(details)

        return ToolCallResult(
            tool_name=ToolName.CALENDAR_CHECK,
            status=ToolStatus.FAILURE,
            error_message=f"Internal registry error for tool '{key}'.",
            failure_reason=FailureReason.VALIDATION_ERROR,
            metadata={"requested_tool": key},
        )
