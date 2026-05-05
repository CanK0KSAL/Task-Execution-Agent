"""Mock search_service(query) — deterministic search over mock_search_index.json."""

from __future__ import annotations

from typing import Any

from task_agent.domain.models import FailureReason, ToolCallResult, ToolName, ToolStatus
from task_agent.tools.helpers import (
    extract_budget_filter,
    extract_result_limit,
    load_json_data,
    normalize_query,
)


def _item_matches_budget(item: dict[str, Any], max_amount: float, currency: str) -> bool:
    price = item.get("price")
    if price is None:
        return False
    try:
        p = float(price)
    except (TypeError, ValueError):
        return False
    cur = str(item.get("currency") or "").upper()
    return cur == currency.upper() and p <= max_amount


def search_service(query: str | dict[str, Any]) -> ToolCallResult:
    """Search the local mock index with light keyword and budget filters."""
    if isinstance(query, str) and not query.strip():
        return ToolCallResult(
            tool_name=ToolName.SEARCH_SERVICE,
            status=ToolStatus.FAILURE,
            error_message="query is required and cannot be empty.",
            failure_reason=FailureReason.VALIDATION_ERROR,
        )

    text = normalize_query(query)
    if not text:
        return ToolCallResult(
            tool_name=ToolName.SEARCH_SERVICE,
            status=ToolStatus.FAILURE,
            error_message="query is required and cannot be empty.",
            failure_reason=FailureReason.VALIDATION_ERROR,
        )

    original = query if isinstance(query, str) else str(query.get("query") or text)
    filters_applied: list[str] = []
    budget = extract_budget_filter(original.lower())
    limit = extract_result_limit(original.lower())

    index = load_json_data("mock_search_index.json")
    items: list[dict[str, Any]] = list(index.get("items", []))
    results = list(items)

    if "john" in text and ("meeting" in text or "schedule" in text or "call" in text):
        filters_applied.append("contact_john")
        results = [
            i
            for i in results
            if i.get("category") == "contact"
            and str(i.get("contact_name", "")).lower() == "john"
        ]
    elif "prague" in text or "praha" in text:
        filters_applied.append("destination_prague")
        results = [
            i
            for i in results
            if str(i.get("city", "")).lower() == "prague"
            or str(i.get("destination", "")).lower() == "prague"
        ]
        if "trip" in text or "2-day" in text or "2 day" in text or "two day" in text:
            filters_applied.append("trip_planning")
            results = [i for i in results if i.get("category") == "trip"]
        if budget and budget[1].upper() == "EUR":
            max_eur, _ = budget
            filters_applied.append(f"max_price_{max_eur}_EUR")
            results = [i for i in results if _item_matches_budget(i, max_eur, "EUR")]
    elif "dentist" in text or "dental" in text:
        filters_applied.append("category_dentist")
        results = [i for i in results if i.get("category") == "dentist"]
        if "warsaw" in text:
            filters_applied.append("city_warsaw")
            results = [
                i for i in results if str(i.get("city", "")).lower() == "warsaw"
            ]
        if (
            "after 5" in text
            or "5pm" in text
            or "17:" in text
            or ("next week" in text and "after" in text)
        ):
            filters_applied.append("evening_next_week")
            results = [i for i in results if i.get("evening_next_week") is True]
    elif "coworking" in text or "co-working" in text:
        filters_applied.append("category_coworking")
        results = [i for i in results if i.get("category") == "coworking"]
        if "warsaw" in text:
            filters_applied.append("city_warsaw")
            results = [
                i for i in results if str(i.get("city", "")).lower() == "warsaw"
            ]
        if budget and budget[1].upper() == "USD":
            max_usd, _ = budget
            filters_applied.append(f"max_price_{max_usd}_USD_per_day")
            results = [
                i
                for i in results
                if str(i.get("price_period") or "").lower() == "day"
                and _item_matches_budget(i, max_usd, "USD")
            ]
        results = [i for i in results if i.get("available_for_booking") is not False]
    else:
        tokens = [t for t in text.replace(",", " ").split() if len(t) > 2]
        filters_applied.append("token_match")

        def matches(item: dict[str, Any]) -> bool:
            blob = " ".join(
                str(item.get(k, ""))
                for k in (
                    "title",
                    "notes",
                    "category",
                    "city",
                    "provider_name",
                    "area",
                )
            ).lower()
            return any(t in blob for t in tokens)

        results = [i for i in results if matches(i)]

    if limit is not None:
        filters_applied.append(f"limit_{limit}")
        results = results[:limit]

    if not results:
        return ToolCallResult(
            tool_name=ToolName.SEARCH_SERVICE,
            status=ToolStatus.NO_RESULTS,
            error_message="No mock search results matched the query.",
            failure_reason=FailureReason.NO_RESULTS,
            data={
                "query": original,
                "results": [],
                "result_count": 0,
                "filters_applied": filters_applied,
            },
        )

    return ToolCallResult(
        tool_name=ToolName.SEARCH_SERVICE,
        status=ToolStatus.SUCCESS,
        data={
            "query": original,
            "results": results,
            "result_count": len(results),
            "filters_applied": filters_applied,
        },
    )
