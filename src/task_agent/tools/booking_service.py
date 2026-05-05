"""Mock booking_service(option) — deterministic bookings against mock data."""

from __future__ import annotations

from typing import Any

from task_agent.domain.models import FailureReason, ToolCallResult, ToolName, ToolStatus
from task_agent.tools.helpers import load_json_data


def _resolve_option_id(option: str | dict[str, Any]) -> str:
    if isinstance(option, dict):
        for key in ("option_id", "id", "option"):
            val = option.get(key)
            if val is not None and str(val).strip():
                return str(val).strip()
        return ""
    return str(option).strip()


def _find_option(option_id: str) -> dict[str, Any] | None:
    index = load_json_data("mock_search_index.json")
    for item in index.get("items", []):
        if str(item.get("id")) == option_id:
            return item
    return None


def booking_service(option: str | dict[str, Any]) -> ToolCallResult:
    """Book a mock option by id; enforces availability and simulated failures."""
    option_id = _resolve_option_id(option)
    if not option_id:
        return ToolCallResult(
            tool_name=ToolName.BOOKING_SERVICE,
            status=ToolStatus.FAILURE,
            error_message="option id is required to make a booking.",
            failure_reason=FailureReason.VALIDATION_ERROR,
        )

    item = _find_option(option_id)
    if item is None:
        return ToolCallResult(
            tool_name=ToolName.BOOKING_SERVICE,
            status=ToolStatus.FAILURE,
            error_message=f"No option with id '{option_id}' exists in the mock catalog.",
            failure_reason=FailureReason.VALIDATION_ERROR,
        )

    rules = load_json_data("mock_bookings.json")
    temp_ids = set(rules.get("temporary_failure_option_ids", []))
    unavailable_ids = set(rules.get("unavailable_option_ids", []))

    if option_id in temp_ids:
        return ToolCallResult(
            tool_name=ToolName.BOOKING_SERVICE,
            status=ToolStatus.TEMPORARY_FAILURE,
            error_message=(
                "The booking partner API returned a temporary error (simulated). "
                "No booking was completed."
            ),
            failure_reason=FailureReason.TEMPORARY_TOOL_FAILURE,
            data={"option_id": option_id},
        )

    if option_id in unavailable_ids or item.get("available_for_booking") is False:
        return ToolCallResult(
            tool_name=ToolName.BOOKING_SERVICE,
            status=ToolStatus.FAILURE,
            error_message=(
                f"Option '{option_id}' is unavailable; no booking was made."
            ),
            failure_reason=FailureReason.TOOL_FAILURE,
            data={"option_id": option_id, "title": item.get("title")},
        )

    title = str(item.get("title") or item.get("provider_name") or option_id)
    slot_id = item.get("available_slot_id")
    confirmed_time = None
    if slot_id:
        confirmed_time = f"slot:{slot_id}"

    booking_id = f"bk-mock-{option_id}"

    return ToolCallResult(
        tool_name=ToolName.BOOKING_SERVICE,
        status=ToolStatus.SUCCESS,
        data={
            "booking_id": booking_id,
            "option_id": option_id,
            "title": title,
            "confirmed_time": confirmed_time,
            "message": f"Booking confirmed for '{title}' (mock).",
        },
    )
