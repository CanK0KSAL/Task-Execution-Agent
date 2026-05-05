"""Official demo/evaluation scenarios for requirement traceability."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoTurn:
    """One user utterance in a multi-turn scenario."""

    user: str
    expected_response_type: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class DemoScenario:
    """A scripted conversation with requirement tags for evaluators."""

    id: str
    title: str
    requirement_focus: tuple[str, ...]
    turns: tuple[DemoTurn, ...]


DENTIST_CLARIFICATION_BOOKING = DemoScenario(
    id="dentist_clarification_booking",
    title="Dentist: city clarification, search, confirm, book + reminder",
    requirement_focus=(
        "missing info",
        "clarification",
        "calendar_check",
        "search_service",
        "confirmation before booking",
        "booking_service",
        "reminder_create",
    ),
    turns=(
        DemoTurn(
            user="Book me a dentist appointment next week after 5pm.",
            expected_response_type="CLARIFICATION",
            note="Missing city; no tools.",
        ),
        DemoTurn(
            user="Warsaw",
            expected_response_type="PARTIAL_SUCCESS",
            note="Options found; booking_service not called yet.",
        ),
        DemoTurn(
            user="book the first one",
            expected_response_type="SUCCESS",
            note="Booking + post-booking reminder.",
        ),
    ),
)

COWORKING_SEARCH = DemoScenario(
    id="coworking_search",
    title="Coworking search with budget and limit",
    requirement_focus=(
        "search_service",
        "budget filter",
        "result limit",
        "three options in output",
    ),
    turns=(
        DemoTurn(
            user="Find me 3 coworking spaces in Warsaw under $20/day.",
            expected_response_type="SUCCESS",
        ),
    ),
)

PRAGUE_TRIP = DemoScenario(
    id="prague_trip",
    title="Trip planning: duration, budget, search",
    requirement_focus=(
        "plan_trip intent",
        "search_service",
        "budget/duration extraction",
        "summary",
    ),
    turns=(
        DemoTurn(
            user="Plan a 2-day trip to Prague under 300 EUR.",
            expected_response_type="SUCCESS",
        ),
    ),
)

MEETING_SCHEDULE = DemoScenario(
    id="meeting_schedule",
    title="Meeting: calendar, lookup, confirmation, reminder",
    requirement_focus=(
        "schedule_meeting intent",
        "calendar_check",
        "contact/search lookup",
        "confirmation flow",
    ),
    turns=(
        DemoTurn(
            user="Schedule a meeting with John next Tuesday afternoon.",
            expected_response_type="PARTIAL_SUCCESS",
        ),
        DemoTurn(
            user="select 1",
            expected_response_type="PARTIAL_SUCCESS",
        ),
    ),
)

CONSTRAINT_UPDATE = DemoScenario(
    id="constraint_update",
    title="Coworking budget constraint update (replan)",
    requirement_focus=(
        "context management",
        "constraint update",
        "replanning",
    ),
    turns=(
        DemoTurn(
            user="Find me 3 coworking spaces in Warsaw under $20/day.",
            expected_response_type="SUCCESS",
        ),
        DemoTurn(
            user="Actually under $35/day.",
            expected_response_type="SUCCESS",
        ),
    ),
)

CANCEL_PENDING_BOOKING = DemoScenario(
    id="cancel_pending_booking",
    title="Cancel pending dentist confirmation",
    requirement_focus=(
        "pending confirmation",
        "cancel/abort",
        "no booking made",
    ),
    turns=(
        DemoTurn(
            user="Book me a dentist appointment in Warsaw next week after 5pm.",
            expected_response_type="PARTIAL_SUCCESS",
        ),
        DemoTurn(
            user="cancel",
            expected_response_type="SUCCESS",
        ),
    ),
)

NEW_TASK_PIVOTS_PENDING = DemoScenario(
    id="new_task_pivots_pending",
    title="New task clears pending dentist booking",
    requirement_focus=(
        "context management",
        "pending cleared",
        "new task handled safely",
    ),
    turns=(
        DemoTurn(
            user="Book me a dentist appointment in Warsaw next week after 5pm.",
            expected_response_type="PARTIAL_SUCCESS",
        ),
        DemoTurn(
            user="Find me 3 coworking spaces in Warsaw under $20/day.",
            expected_response_type="SUCCESS",
        ),
    ),
)

UNKNOWN_REQUEST = DemoScenario(
    id="unknown_request",
    title="Vague / unsupported request",
    requirement_focus=(
        "unsupported/vague request",
        "blocking",
        "no tool calls",
    ),
    turns=(
        DemoTurn(
            user="Can you handle this for me?",
            expected_response_type="BLOCKED",
        ),
    ),
)

ALL_SCENARIOS: tuple[DemoScenario, ...] = (
    DENTIST_CLARIFICATION_BOOKING,
    COWORKING_SEARCH,
    PRAGUE_TRIP,
    MEETING_SCHEDULE,
    CONSTRAINT_UPDATE,
    CANCEL_PENDING_BOOKING,
    NEW_TASK_PIVOTS_PENDING,
    UNKNOWN_REQUEST,
)
