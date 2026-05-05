"""Constraint updates and pivot flows (deterministic executor behavior)."""

from __future__ import annotations

import pytest

from task_agent.agent.executor import AgentExecutor
from task_agent.agent.planner import MockPlanner
from task_agent.agent.state import ConversationState
from task_agent.domain.models import (
    AgentResponseType,
    FailureReason,
    IntentType,
    ToolCallResult,
    ToolName,
    ToolStatus,
)
from task_agent.tools.registry import ToolRegistry


@pytest.fixture
def executor() -> AgentExecutor:
    return AgentExecutor(planner=MockPlanner(), tool_registry=ToolRegistry())


def test_cancel_pending_booking_clears_state(executor: AgentExecutor) -> None:
    state = ConversationState()
    executor.execute(
        "Book me a dentist appointment in Warsaw next week after 5pm.",
        state,
    )
    assert state.has_pending_confirmation()
    resp = executor.execute("cancel", state)
    assert resp.response_type == AgentResponseType.SUCCESS
    assert not state.has_pending_confirmation()
    assert resp.booked_item is None
    assert ToolName.BOOKING_SERVICE not in {t.tool_name for t in resp.tool_results}


def test_new_task_while_pending_clears_and_runs_search(
    executor: AgentExecutor,
) -> None:
    state = ConversationState()
    executor.execute(
        "Book me a dentist appointment in Warsaw next week after 5pm.",
        state,
    )
    assert state.has_pending_confirmation()
    resp = executor.execute(
        "Find me 3 coworking spaces in Warsaw under $20/day.",
        state,
    )
    assert not state.has_pending_confirmation()
    assert resp.response_type == AgentResponseType.SUCCESS
    assert resp.intent == IntentType.FIND_OPTIONS
    assert len(resp.found_options) == 3
    assert resp.booked_item is None
    assert any(
        "Canceled the previous pending action" in a for a in resp.assumptions
    )


def test_coworking_budget_update_reruns_search(executor: AgentExecutor) -> None:
    state = ConversationState()
    r1 = executor.execute(
        "Find me 3 coworking spaces in Warsaw under $20/day.",
        state,
    )
    assert r1.response_type == AgentResponseType.SUCCESS
    under_20 = {o["id"] for o in r1.found_options}
    r2 = executor.execute("Actually under $35/day.", state)
    assert r2.response_type == AgentResponseType.SUCCESS
    ids_35 = {o["id"] for o in r2.found_options}
    assert ids_35.issuperset(under_20)
    search = next(
        r for r in r2.tool_results if r.tool_name == ToolName.SEARCH_SERVICE
    )
    filters = (search.data or {}).get("filters_applied") or []
    assert any("35" in str(f) for f in filters)
    assert r2.booked_item is None


def test_pending_dentist_date_update_replans_and_keeps_confirmation(
    executor: AgentExecutor,
) -> None:
    state = ConversationState()
    executor.execute(
        "Book me a dentist appointment in Warsaw next week after 5pm.",
        state,
    )
    assert state.has_pending_confirmation()
    resp = executor.execute("Actually tomorrow morning.", state)
    assert state.has_pending_confirmation()
    assert resp.booked_item is None
    assert ToolName.BOOKING_SERVICE not in {t.tool_name for t in resp.tool_results}
    assert resp.found_options
    search = next(
        r for r in resp.tool_results if r.tool_name == ToolName.SEARCH_SERVICE
    )
    assert search.status == ToolStatus.SUCCESS
    q = (search.data or {}).get("query", "")
    assert "tomorrow morning" in str(q).lower()


def test_merge_under_usd_per_day() -> None:
    from task_agent.agent.planner_support import merge_constraint_update

    prev = "Find me 3 coworking spaces in Warsaw under $20/day."
    merged = merge_constraint_update(prev, "under 35 USD/day")
    assert merged
    assert "35" in merged
    assert "$20" not in merged


def test_dentist_search_no_results_has_no_booking_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exec2 = AgentExecutor(planner=MockPlanner(), tool_registry=ToolRegistry())

    def no_results(query: str | dict) -> ToolCallResult:  # noqa: ARG001
        return ToolCallResult(
            tool_name=ToolName.SEARCH_SERVICE,
            status=ToolStatus.NO_RESULTS,
            error_message="No mock search results matched the query.",
            failure_reason=FailureReason.NO_RESULTS,
            data={"query": "", "results": [], "result_count": 0},
        )

    monkeypatch.setattr(
        "task_agent.tools.search_service.search_service",
        no_results,
    )
    state = ConversationState()
    resp = exec2.execute(
        "Book me a dentist appointment in Warsaw next week after 5pm.",
        state,
    )
    assert resp.response_type == AgentResponseType.PARTIAL_SUCCESS
    assert resp.booked_item is None
    combined = " ".join(
        [resp.message, resp.summary or "", *resp.blockers],
    ).lower()
    assert "no booking" in combined
    assert "no matching" in combined or "could not find" in combined
