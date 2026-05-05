"""Rule-based text helpers for MockPlanner (readable, deterministic)."""

from __future__ import annotations

import re
from typing import Any

from task_agent.domain.models import Money


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def is_vague_request(text: str) -> bool:
    t = normalize_text(text)
    if "can you handle" in t and "for me" in t:
        return True
    if t in {"help", "help me", "do it", "please"}:
        return True
    return False


def extract_city(text: str) -> str | None:
    t = normalize_text(text)
    mapping = (
        ("warsaw", "Warsaw"),
        ("prague", "Prague"),
        ("praha", "Prague"),
        ("krakow", "Krakow"),
        ("kraków", "Krakow"),
    )
    for needle, city in mapping:
        if needle in t:
            return city
    return None


def extract_date_range_phrase(text: str) -> str | None:
    """Return a canonical calendar/search phrase if recognized."""
    t = normalize_text(text)
    matches: tuple[tuple[str, str], ...] = (
        ("next week after 5pm", "next week after 5pm"),
        ("next week after 5 pm", "next week after 5pm"),
        ("next tuesday afternoon", "next Tuesday afternoon"),
        ("tomorrow morning", "tomorrow morning"),
    )
    for needle, canonical in matches:
        if needle in t:
            return canonical
    if "next week" in t and "after 5" in t:
        return "next week after 5pm"
    return None


def extract_result_count(text: str) -> int | None:
    if re.search(r"\b3\b", text):
        return 3
    return None


def extract_trip_budget(text: str) -> Money | None:
    t = normalize_text(text)
    m = re.search(r"under\s*€\s*(\d+(?:\.\d+)?)", t)
    if m:
        return Money(amount=float(m.group(1)), currency="EUR")
    m = re.search(r"under\s+(\d+(?:\.\d+)?)\s*(?:eur|€)", t)
    if m:
        return Money(amount=float(m.group(1)), currency="EUR")
    m = re.search(r"under\s+(\d+(?:\.\d+)?)\s*eur\b", t)
    if m:
        return Money(amount=float(m.group(1)), currency="EUR")
    return None


def extract_coworking_budget(text: str) -> Money | None:
    t = normalize_text(text)
    m = re.search(r"under\s*\$?\s*(\d+(?:\.\d+)?)\s*/\s*day", t)
    if m:
        return Money(amount=float(m.group(1)), currency="USD", period="day")
    m = re.search(r"under\s+(\d+(?:\.\d+)?)\s*usd", t)
    if m:
        return Money(amount=float(m.group(1)), currency="USD", period="day")
    return None


def extract_duration_days(text: str) -> int | None:
    t = normalize_text(text)
    m = re.search(r"(\d+)(?:-| )day", t)
    if m:
        return int(m.group(1))
    return None


def extract_destination(text: str) -> str | None:
    t = normalize_text(text)
    if "prague" in t or "praha" in t:
        return "Prague"
    m = re.search(r"trip to\s+([a-záéíóúñç]+)", t)
    if m:
        return m.group(1).title()
    return None


def extract_person_name(text: str) -> str | None:
    m = re.search(
        r"meeting with\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        text.strip(),
    )
    if m:
        return m.group(1).split()[0]
    m = re.search(
        r"with\s+([A-Z][a-z]+)\s+next",
        text.strip(),
    )
    if m:
        return m.group(1)
    return None


def extract_reminder_payload(text: str) -> tuple[str, str] | None:
    """Return (title, when_phrase) for reminder utterances."""
    raw = text.strip()
    low = normalize_text(raw)
    needle = "remind me to "
    if needle not in low:
        return None
    start = low.index(needle) + len(needle)
    rest = raw[start:]
    rest_low = low[start:]
    when: str | None = None
    title = ""
    for phrase in ("tomorrow morning", "tomorrow afternoon", "next week"):
        if phrase in rest_low:
            when = phrase
            cut = rest_low.index(phrase)
            title = rest[:cut].strip(" .,")
            break
    if when is None or not title:
        return None
    return title, when


def detect_intent(text: str) -> str:
    """Return a scenario key for routing (not always final IntentType)."""
    t = normalize_text(text)
    if is_vague_request(text):
        return "unknown"
    if "remind me" in t or t.startswith("remind "):
        return "reminder"
    if ("schedule" in t and "meeting" in t) or "meeting with" in t:
        return "meeting"
    if ("plan" in t and "trip" in t) or "trip to" in t:
        return "trip"
    if "coworking" in t or ("find" in t and "space" in t):
        return "coworking"
    if ("book" in t and "appointment" in t) or ("dentist" in t and "book" in t):
        return "appointment"
    if "dentist" in t:
        return "appointment"
    return "unknown"
