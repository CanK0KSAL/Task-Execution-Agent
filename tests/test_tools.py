"""Tests for mock tools and ToolRegistry."""

from __future__ import annotations

import pytest

from task_agent.domain.models import (
    FailureReason,
    ToolName,
    ToolStatus,
)
from task_agent.tools.booking_service import booking_service
from task_agent.tools.calendar_check import calendar_check
from task_agent.tools.reminder_create import reminder_create
from task_agent.tools.registry import ToolRegistry
from task_agent.tools.search_service import search_service


def test_calendar_check_success_next_week_evenings() -> None:
    result = calendar_check("next week after 5pm")
    assert result.tool_name == ToolName.CALENDAR_CHECK
    assert result.status == ToolStatus.SUCCESS
    assert result.data["timezone"] == "Europe/Warsaw"
    avail = result.data["available_slots"]
    assert len(avail) >= 1
    assert all(s.get("available") is True for s in avail)


def test_calendar_check_unknown_range_no_results() -> None:
    result = calendar_check("sometime in the distant future never")
    assert result.status == ToolStatus.NO_RESULTS
    assert result.failure_reason == FailureReason.NO_RESULTS


def test_calendar_check_empty_validation() -> None:
    result = calendar_check("")
    assert result.status == ToolStatus.FAILURE
    assert result.failure_reason == FailureReason.VALIDATION_ERROR
    result_d = calendar_check({"date_range": "  "})
    assert result_d.status == ToolStatus.FAILURE


def test_search_coworking_warsaw_under_budget() -> None:
    q = "Find me 3 coworking spaces in Warsaw under $20/day"
    result = search_service(q)
    assert result.status == ToolStatus.SUCCESS
    results = result.data["results"]
    assert len(results) == 3
    assert result.data["result_count"] == 3
    for row in results:
        assert row["city"] == "Warsaw"
        assert float(row["price"]) <= 20
        assert str(row.get("currency", "")).upper() == "USD"
    ids = {r["id"] for r in results}
    assert ids == {"cw-low-18", "cw-low-20", "cw-low-16"}


def test_search_dentist_warsaw_includes_unavailable() -> None:
    result = search_service("dentist Warsaw")
    assert result.status == ToolStatus.SUCCESS
    ids = [r["id"] for r in result.data["results"]]
    assert "dent-unavailable-001" in ids
    assert any(r.get("available_for_booking") is True for r in result.data["results"])


def test_search_prague_trip_under_budget() -> None:
    result = search_service("Prague 2-day trip under 300 EUR")
    assert result.status == ToolStatus.SUCCESS
    for row in result.data["results"]:
        assert row.get("category") == "trip"
        assert float(row.get("price", 999)) <= 300
        assert str(row.get("currency", "")).upper() == "EUR"


def test_search_impossible_query_no_results() -> None:
    result = search_service("quantum waffle iron NowhereLand xyzabc")
    assert result.status == ToolStatus.NO_RESULTS
    assert result.failure_reason == FailureReason.NO_RESULTS


def test_search_empty_query_validation() -> None:
    result = search_service("")
    assert result.status == ToolStatus.FAILURE
    assert result.failure_reason == FailureReason.VALIDATION_ERROR
    result_d = search_service({"query": ""})
    assert result_d.status == ToolStatus.FAILURE


def test_booking_success_available_option() -> None:
    result = booking_service("cw-low-18")
    assert result.status == ToolStatus.SUCCESS
    assert result.data["booking_id"].startswith("bk-mock-")
    assert result.data["option_id"] == "cw-low-18"


def test_booking_unavailable_option() -> None:
    result = booking_service("dent-unavailable-001")
    assert result.status == ToolStatus.FAILURE
    assert result.failure_reason == FailureReason.TOOL_FAILURE


def test_booking_unknown_option() -> None:
    result = booking_service("does-not-exist-999")
    assert result.status == ToolStatus.FAILURE
    assert result.failure_reason == FailureReason.VALIDATION_ERROR


def test_booking_simulated_temporary_failure() -> None:
    result = booking_service("book-temp-fail-001")
    assert result.status == ToolStatus.TEMPORARY_FAILURE
    assert result.failure_reason == FailureReason.TEMPORARY_TOOL_FAILURE


def test_reminder_success() -> None:
    result = reminder_create(
        {"title": "Call back Dana", "reminder_time": "2026-05-07T09:00:00+02:00"},
    )
    assert result.status == ToolStatus.SUCCESS
    assert result.data["reminder_id"].startswith("rem-mock-")


def test_reminder_missing_time() -> None:
    result = reminder_create({"title": "No time provided"})
    assert result.status == ToolStatus.FAILURE
    assert result.failure_reason == FailureReason.VALIDATION_ERROR


def test_reminder_simulated_failure() -> None:
    result = reminder_create(
        {"title": "x", "when": "soon", "simulate_failure": True},
    )
    assert result.status == ToolStatus.TEMPORARY_FAILURE


def test_registry_get_by_enum() -> None:
    reg = ToolRegistry()
    fn = reg.get(ToolName.SEARCH_SERVICE)
    assert fn is search_service


def test_registry_get_by_string() -> None:
    reg = ToolRegistry()
    assert reg.get("calendar_check") is calendar_check


def test_registry_execute_search() -> None:
    reg = ToolRegistry()
    out = reg.execute(
        ToolName.SEARCH_SERVICE,
        {"query": "coworking Warsaw"},
    )
    assert out.status == ToolStatus.SUCCESS


def test_registry_unknown_tool_returns_failure_result() -> None:
    reg = ToolRegistry()
    out = reg.execute("not_a_real_tool", {})
    assert out.status == ToolStatus.FAILURE
    assert out.failure_reason == FailureReason.VALIDATION_ERROR
    assert out.metadata.get("unknown_tool") is True
