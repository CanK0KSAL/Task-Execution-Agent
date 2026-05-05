"""Planner behavior: mock mode, clarifications, and OpenAI fallback."""

from __future__ import annotations

import pytest

from task_agent.agent.planner import MockPlanner, OpenAIPlanner, get_planner
from task_agent.config import Config
from task_agent.domain.schemas import (
    IntentType,
    ToolName,
    UserRequest,
)


def _names(task: object) -> list[str]:
    return [p.tool_name.value for p in task.tool_plan]  # type: ignore[attr-defined]


def _no_booking(task: object) -> None:
    assert ToolName.BOOKING_SERVICE.value not in _names(task)


@pytest.fixture
def mock_planner() -> MockPlanner:
    return MockPlanner()


def test_dentist_booking_missing_city(mock_planner: MockPlanner) -> None:
    text = "Book me a dentist appointment next week after 5pm."
    task = mock_planner.plan(UserRequest(text=text))
    assert task.intent == IntentType.BOOK_APPOINTMENT
    assert any(m.name == "city" for m in task.missing_fields)
    assert any(
        m.question == "What city should I search in?" for m in task.missing_fields
    )
    assert task.tool_plan == []
    assert task.requires_user_confirmation is True
    assert task.slots.get("service_type") == "dentist"
    assert task.slots.get("date_range") == "next week after 5pm"
    _no_booking(task)


def test_dentist_booking_warsaw_includes_search_and_calendar(
    mock_planner: MockPlanner,
) -> None:
    text = "Book me a dentist appointment in Warsaw next week after 5pm."
    task = mock_planner.plan(UserRequest(text=text))
    assert task.intent == IntentType.BOOK_APPOINTMENT
    assert task.slots.get("city") == "Warsaw"
    names = _names(task)
    assert ToolName.CALENDAR_CHECK.value in names
    assert ToolName.SEARCH_SERVICE.value in names
    assert task.requires_user_confirmation is True
    assert ToolName.BOOKING_SERVICE.value not in names
    _no_booking(task)


def test_coworking_search(mock_planner: MockPlanner) -> None:
    text = "Find me 3 coworking spaces in Warsaw under $20/day."
    task = mock_planner.plan(UserRequest(text=text))
    assert task.intent == IntentType.FIND_OPTIONS
    assert ToolName.SEARCH_SERVICE.value in _names(task)
    assert task.requires_user_confirmation is False
    budget = task.slots.get("budget")
    assert budget["amount"] == 20
    assert budget["currency"] == "USD"
    assert budget["period"] == "day"
    assert task.slots.get("result_count") == 3
    assert task.slots.get("category") == "coworking space"
    _no_booking(task)


def test_prague_trip(mock_planner: MockPlanner) -> None:
    text = "Plan a 2-day trip to Prague under €300."
    task = mock_planner.plan(UserRequest(text=text))
    assert task.intent == IntentType.PLAN_TRIP
    assert task.slots.get("destination") == "Prague"
    assert task.slots.get("duration_days") == 2
    budget = task.slots.get("budget")
    assert budget["amount"] == 300
    assert budget["currency"] == "EUR"
    assert ToolName.SEARCH_SERVICE.value in _names(task)
    assert task.requires_user_confirmation is False
    _no_booking(task)


def test_meeting_with_john(mock_planner: MockPlanner) -> None:
    text = "Schedule a meeting with John next Tuesday afternoon."
    task = mock_planner.plan(UserRequest(text=text))
    assert task.intent == IntentType.SCHEDULE_MEETING
    assert task.slots.get("person") == "John"
    assert task.slots.get("date_range") == "next Tuesday afternoon"
    assert any("30-minute" in a for a in task.assumptions)
    names = _names(task)
    assert ToolName.CALENDAR_CHECK.value in names
    assert ToolName.SEARCH_SERVICE.value in names
    assert task.requires_user_confirmation is True
    _no_booking(task)


def test_reminder_call_john(mock_planner: MockPlanner) -> None:
    text = "Remind me to call John tomorrow morning."
    task = mock_planner.plan(UserRequest(text=text))
    assert task.intent == IntentType.CREATE_REMINDER
    assert ToolName.REMINDER_CREATE.value in _names(task)
    assert "call John" in task.slots.get("title", "")
    details = next(
        p.arguments.get("details")
        for p in task.tool_plan
        if p.tool_name == ToolName.REMINDER_CREATE
    )
    assert details["title"] == "call John"
    assert details["when"] == "tomorrow morning"
    _no_booking(task)


def test_unknown_vague_request(mock_planner: MockPlanner) -> None:
    text = "Can you handle this for me?"
    task = mock_planner.plan(UserRequest(text=text))
    assert task.intent == IntentType.UNKNOWN
    assert task.confidence < 0.4
    assert task.missing_fields
    assert task.tool_plan == []


def test_openai_planner_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = Config(
        agent_llm_mode="openai",
        openai_api_key="sk-test-not-real",
        openai_model="gpt-4.1-mini",
    )
    planner = OpenAIPlanner(cfg, MockPlanner())

    def boom(_request: UserRequest) -> str:
        raise RuntimeError("simulated OpenAI failure")

    monkeypatch.setattr(planner, "_call_openai", boom)
    task = planner.plan(
        UserRequest(text="Find me 3 coworking spaces in Warsaw under $20/day."),
    )
    assert task.intent == IntentType.FIND_OPTIONS
    assert any("OpenAI planner failed" in w for w in task.warnings)
    _no_booking(task)


def test_get_planner_selects_mock_without_key() -> None:
    cfg = Config(
        agent_llm_mode="openai",
        openai_api_key=None,
        openai_model="gpt-4.1-mini",
    )
    planner = get_planner(cfg)
    assert isinstance(planner, MockPlanner)
