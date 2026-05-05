"""Executor failure and edge-case handling."""

from __future__ import annotations

import pytest

from task_agent.agent.executor import AgentExecutor
from task_agent.agent.planner import MockPlanner
from task_agent.agent.state import ConversationState
from task_agent.domain.models import (
    AgentResponseType,
    ToolCallResult,
    ToolName,
    ToolStatus,
)
from task_agent.tools.registry import ToolRegistry


@pytest.fixture
def executor() -> AgentExecutor:
    return AgentExecutor(planner=MockPlanner(), tool_registry=ToolRegistry())


def test_selection_without_pending_blocked(executor: AgentExecutor) -> None:
    resp = executor.execute("book the first one")
    assert resp.response_type == AgentResponseType.BLOCKED
    assert "nothing on hold" in resp.message.lower()


def test_selection_out_of_range(executor: AgentExecutor) -> None:
    state = ConversationState()
    state.set_pending_options(
        [{"id": "cw-low-18", "title": "Only"}],
        "book_option",
        "demo",
    )
    resp = executor.execute("book option 3", state)
    assert resp.response_type == AgentResponseType.BLOCKED
    assert state.has_pending_confirmation()


def test_no_search_results(executor: AgentExecutor) -> None:
    resp = executor.execute(
        "Find me coworking spaces in NowhereLandZZ under $5/day.",
    )
    assert resp.response_type in (
        AgentResponseType.BLOCKED,
        AgentResponseType.PARTIAL_SUCCESS,
    )
    assert resp.booked_item is None
    assert resp.blockers
    blob = " ".join([resp.message, resp.summary or "", *resp.blockers]).lower()
    assert "no booking" in blob
    assert "no matching" in blob or "could not find" in blob


def test_booking_unavailable_option(executor: AgentExecutor) -> None:
    state = ConversationState()
    state.set_pending_options(
        [{"id": "dent-unavailable-001", "title": "Closed clinic"}],
        "book_option",
        "demo",
    )
    resp = executor.execute("book the first one", state)
    assert resp.booked_item is None
    assert not any(r.tool_name == ToolName.REMINDER_CREATE for r in resp.tool_results)
    assert resp.response_type in (AgentResponseType.BLOCKED, AgentResponseType.FAILURE)


def test_booking_temporary_failure(executor: AgentExecutor) -> None:
    state = ConversationState()
    state.set_pending_options(
        [{"id": "book-temp-fail-001", "title": "Temp"}],
        "book_option",
        "demo",
    )
    resp = executor.execute("select 1", state)
    assert resp.response_type == AgentResponseType.FAILURE
    assert resp.booked_item is None
    assert not any(r.tool_name == ToolName.REMINDER_CREATE for r in resp.tool_results)
    assert state.has_pending_confirmation()
    joined = " ".join([resp.message, resp.summary or "", *resp.blockers]).lower()
    assert "temporary" in joined


def test_reminder_failure_after_booking_partial_success(
    executor: AgentExecutor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(details: dict) -> ToolCallResult:  # noqa: ARG001
        return ToolCallResult(
            tool_name=ToolName.REMINDER_CREATE,
            status=ToolStatus.TEMPORARY_FAILURE,
            error_message="simulated outage",
        )

    monkeypatch.setattr(
        "task_agent.tools.reminder_create.reminder_create",
        boom,
    )
    exec2 = AgentExecutor(planner=MockPlanner(), tool_registry=ToolRegistry())
    state = ConversationState()
    exec2.execute(
        "Book me a dentist appointment in Warsaw next week after 5pm.",
        state,
    )
    resp = exec2.execute("book the first one", state)
    assert resp.response_type == AgentResponseType.PARTIAL_SUCCESS
    assert resp.booked_item
    assert resp.reminder is None
    assert resp.blockers
    joined = " ".join(resp.blockers).lower()
    assert "reminder creation failed" in joined


@pytest.mark.parametrize(
    "user_text",
    [
        "Find me 3 coworking spaces in Warsaw under $20/day.",
        "Book me a dentist appointment in Warsaw next week after 5pm.",
        "Remind me to call John tomorrow morning.",
        "Plan a 2-day trip to Prague under 300 EUR.",
    ],
)
def test_common_flows_non_empty_message_and_summary(
    executor: AgentExecutor,
    user_text: str,
) -> None:
    resp = executor.execute(user_text)
    assert resp.message.strip()
    assert (resp.summary or "").strip()
