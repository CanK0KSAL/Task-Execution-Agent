"""CLI formatting helpers (non-interactive)."""

from __future__ import annotations

from rich.console import Console

from task_agent.domain.models import (
    AgentFinalResponse,
    AgentResponseType,
    IntentType,
    MissingField,
)
from task_agent.ui.cli import build_options_table, render_agent_response, summary_body


def test_build_options_table_empty() -> None:
    assert build_options_table([]) is None


def test_build_options_table_minimal_row() -> None:
    tbl = build_options_table([{"id": "x"}])
    assert tbl is not None
    assert len(tbl.rows) == 1


def test_summary_body_fallback_message() -> None:
    resp = AgentFinalResponse(
        response_type=AgentResponseType.SUCCESS,
        message="Hello",
    )
    assert "Hello" in summary_body(resp)


def test_summary_body_blockers_and_assumptions() -> None:
    resp = AgentFinalResponse(
        response_type=AgentResponseType.PARTIAL_SUCCESS,
        message="m",
        summary="s",
        blockers=["b1"],
        assumptions=["a1"],
    )
    text = summary_body(resp)
    assert "b1" in text and "a1" in text


def test_render_agent_response_no_crash_minimal() -> None:
    c = Console(record=True, width=100)
    resp = AgentFinalResponse(
        response_type=AgentResponseType.CLARIFICATION,
        message="Need more info",
        missing_fields=[
            MissingField(
                name="city",
                reason="need city",
                question="Which city?",
            ),
        ],
    )
    render_agent_response(resp, debug=False, console_=c)
    out = c.export_text()
    assert "Clarification" in out
    assert "Summary" in out


def test_render_agent_response_options_and_debug() -> None:
    c = Console(record=True, width=120)
    resp = AgentFinalResponse(
        response_type=AgentResponseType.SUCCESS,
        message="ok",
        summary="found items",
        intent=IntentType.FIND_OPTIONS,
        found_options=[{"title": "A", "price": 10, "currency": "USD"}],
    )
    render_agent_response(resp, debug=False, console_=c)
    assert "Options Found" in c.export_text()

    c2 = Console(record=True, width=120)
    resp2 = AgentFinalResponse(
        response_type=AgentResponseType.SUCCESS,
        message="ok",
        intent=IntentType.FIND_OPTIONS,
        tool_results=[],
    )
    render_agent_response(resp2, debug=True, console_=c2)
    assert "Debug" in c2.export_text()
