"""Evaluation scenario runner (mock-only)."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from task_agent.domain.models import ToolName
from task_agent.evaluation.runner import run_all_scenarios, run_scenario
from task_agent.evaluation.scenarios import ALL_SCENARIOS, COWORKING_SEARCH, UNKNOWN_REQUEST
from task_agent.ui.cli import app


def test_run_all_scenarios_non_empty() -> None:
    results = run_all_scenarios()
    assert len(results) == len(ALL_SCENARIOS)
    assert all(r.turn_results for r in results)


def test_all_scenarios_pass_basic_checks() -> None:
    results = run_all_scenarios()
    failed = [r.scenario_id for r in results if not r.passed_basic_checks]
    assert not failed, f"Failed: {failed}, warnings: {[r.warnings for r in results if r.warnings]}"


def test_coworking_scenario_three_options() -> None:
    res = run_scenario(COWORKING_SEARCH)
    assert res.passed_basic_checks
    assert res.turn_results[0].found_option_count == 3


def test_dentist_booking_tool_orchestration() -> None:
    dentist = next(s for s in ALL_SCENARIOS if s.id == "dentist_clarification_booking")
    res = run_scenario(dentist)
    assert res.passed_basic_checks, res.warnings
    t0, t1, t2 = res.turn_results
    assert t0.tool_names_called == []
    assert ToolName.CALENDAR_CHECK.value in t1.tool_names_called
    assert ToolName.SEARCH_SERVICE.value in t1.tool_names_called
    assert ToolName.BOOKING_SERVICE.value not in t1.tool_names_called
    assert ToolName.BOOKING_SERVICE.value in t2.tool_names_called
    assert ToolName.REMINDER_CREATE.value in t2.tool_names_called


def test_unknown_scenario_no_tools() -> None:
    res = run_scenario(UNKNOWN_REQUEST)
    assert res.passed_basic_checks
    assert res.turn_results[0].tool_names_called == []


def test_runner_ignores_openai_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-key-for-test")
    monkeypatch.setenv("AGENT_LLM_MODE", "openai")
    results = run_all_scenarios()
    assert all(r.passed_basic_checks for r in results)


def test_cli_demo_smoke() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 0
    out = (result.stdout or "").lower()
    assert "scenarios passed" in out
