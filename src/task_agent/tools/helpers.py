"""Small helpers for mock tools: paths, JSON loading, query parsing."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

BudgetFilter = tuple[float, str] | None


def project_root() -> Path:
    """Repository root (contains `data/` and `src/`)."""
    return Path(__file__).resolve().parents[3]


def data_dir() -> Path:
    return project_root() / "data"


def load_json_data(filename: str) -> Any:
    path = data_dir() / filename
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def normalize_query(query: str | dict[str, Any]) -> str:
    if isinstance(query, dict):
        for key in ("query", "text", "q"):
            val = query.get(key)
            if val is not None and str(val).strip():
                return str(val).strip().lower()
        return ""
    return str(query).strip().lower()


def extract_budget_filter(text: str) -> BudgetFilter:
    """Parse simple 'under $20/day', 'under 300 EUR', etc."""
    t = text.lower()
    m = re.search(r"under\s*\$?\s*(\d+(?:\.\d+)?)\s*/\s*day", t)
    if m:
        return float(m.group(1)), "USD"

    t_norm = t.replace("€", " eur ").replace("$", " usd ")
    m = re.search(
        r"under\s+(\d+(?:\.\d+)?)\s*(?:eur|euros?|€)",
        t_norm,
        re.IGNORECASE,
    )
    if m:
        return float(m.group(1)), "EUR"
    m = re.search(
        r"under\s+(\d+(?:\.\d+)?)\s*(?:usd|dollars?|\$)",
        t_norm,
        re.IGNORECASE,
    )
    if m:
        return float(m.group(1)), "USD"
    m = re.search(r"under\s+(\d+(?:\.\d+)?)\s*usd", t_norm)
    if m:
        return float(m.group(1)), "USD"
    return None


def extract_result_limit(text: str) -> int | None:
    if re.search(r"\b3\b", text):
        return 3
    return None


def normalize_date_range_key(date_range: str | dict[str, Any]) -> str:
    if isinstance(date_range, dict):
        raw = str(
            date_range.get("date_range")
            or date_range.get("raw")
            or date_range.get("range")
            or "",
        )
    else:
        raw = str(date_range)
    collapsed = re.sub(r"\s+", " ", raw.strip().lower())
    return collapsed


def calendar_pattern_key(normalized: str) -> str | None:
    """Map free text to a calendar group key in mock data."""
    aliases = {
        "next week after 5pm": "next_week_after_5pm",
        "next week after 5 pm": "next_week_after_5pm",
        "next tuesday afternoon": "next_tuesday_afternoon",
        "tomorrow morning": "tomorrow_morning",
    }
    return aliases.get(normalized)
