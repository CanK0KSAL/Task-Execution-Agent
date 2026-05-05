"""End-to-end executor flows (mock planner, no OpenAI)."""

from __future__ import annotations

import pytest

from task_agent.agent.executor import AgentExecutor
from task_agent.agent.planner import MockPlanner
from task_agent.agent.state import ConversationState
from task_agent.domain.models import AgentResponseType, IntentType, ToolName, ToolStatus
from task_agent.tools.registry import ToolRegistry


@pytest.fixture
def executor() -> AgentExecutor:
    return AgentExecutor(planner=MockPlanner(), tool_registry=ToolRegistry())


def test_dentist_missing_city_clarification(executor: AgentExecutor) -> None:
    state = ConversationState()
    resp = executor.execute(
        "Book me a dentist appointment next week after 5pm.",
        state,
    )
    assert resp.response_type == AgentResponseType.CLARIFICATION
    assert any(m.name == "city" for m in resp.missing_fields)
    assert resp.tool_results == []
    assert resp.found_options == []


def test_city_followup_then_options(executor: AgentExecutor) -> None:
    state = ConversationState()
    r1 = executor.execute(
        "Book me a dentist appointment next week after 5pm.",
        state,
    )
    assert r1.response_type == AgentResponseType.CLARIFICATION
    r2 = executor.execute("Warsaw", state)
    assert r2.found_options
    assert state.has_pending_confirmation()
    assert r2.booked_item is None
    assert ToolName.BOOKING_SERVICE not in {t.tool_name for t in r2.tool_results}


def test_dentist_warsaw_runs_search_without_booking(executor: AgentExecutor) -> None:
    state = ConversationState()
    resp = executor.execute(
        "Book me a dentist appointment in Warsaw next week after 5pm.",
        state,
    )
    assert resp.found_options
    assert state.has_pending_confirmation()
    assert resp.booked_item is None
    names = {r.tool_name for r in resp.tool_results}
    assert ToolName.CALENDAR_CHECK in names
    assert ToolName.SEARCH_SERVICE in names
    assert ToolName.BOOKING_SERVICE not in names


def test_booking_confirmation_creates_booking_and_reminder(
    executor: AgentExecutor,
) -> None:
    state = ConversationState()
    executor.execute(
        "Book me a dentist appointment in Warsaw next week after 5pm.",
        state,
    )
    assert state.has_pending_confirmation()
    resp = executor.execute("book the first one", state)
    assert resp.response_type == AgentResponseType.SUCCESS
    assert resp.booked_item
    assert resp.reminder
    assert any(r.tool_name == ToolName.BOOKING_SERVICE for r in resp.tool_results)
    assert any(r.tool_name == ToolName.REMINDER_CREATE for r in resp.tool_results)
    assert not state.has_pending_confirmation()


def test_coworking_search_success(executor: AgentExecutor) -> None:
    resp = executor.execute(
        "Find me 3 coworking spaces in Warsaw under $20/day.",
    )
    assert resp.response_type == AgentResponseType.SUCCESS
    assert len(resp.found_options) == 3
    assert resp.booked_item is None
    assert not resp.blockers


def test_prague_trip_summary(executor: AgentExecutor) -> None:
    resp = executor.execute("Plan a 2-day trip to Prague under 300 EUR.")
    assert resp.response_type == AgentResponseType.SUCCESS
    assert resp.found_options
    summary = (resp.summary or "").lower()
    assert "prague" in summary
    assert "2" in summary
    assert "300" in summary or "eur" in summary


def test_reminder_flow(executor: AgentExecutor) -> None:
    resp = executor.execute("Remind me to call John tomorrow morning.")
    assert resp.response_type == AgentResponseType.SUCCESS
    assert resp.reminder
    assert any(r.tool_name == ToolName.REMINDER_CREATE for r in resp.tool_results)


def test_unknown_request(executor: AgentExecutor) -> None:
    resp = executor.execute("Can you handle this for me?")
    assert resp.response_type == AgentResponseType.BLOCKED
    assert resp.tool_results == []
    assert "clearer task" in resp.message.lower()
    assert "coworking" in resp.message.lower()
    assert "dentist" in resp.message.lower()
