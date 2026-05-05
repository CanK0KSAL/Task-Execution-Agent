"""Rule-based text helpers for MockPlanner (readable, deterministic)."""

from __future__ import annotations

import re
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
    m = re.search(r"under\s+(\d+(?:\.\d+)?)\s*usd(?:\s*/\s*day)?", t)
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


def is_cancel_message(text: str) -> bool:
    """User wants to drop the current pending confirmation."""
    t = normalize_text(text.strip())
    phrases = (
        "cancel",
        "never mind",
        "nevermind",
        "abort",
        "forget it",
        "başka bir şey",
        "iptal",
    )
    if t in phrases:
        return True
    if t == "stop" or t.startswith("stop "):
        return True
    return any(t.startswith(p + " ") for p in phrases if p != "stop")


def is_constraint_update(text: str) -> bool:
    """Short follow-up that adjusts budget, time, or city (not a full new task)."""
    raw = text.strip()
    t = normalize_text(raw)
    prefixes = (
        "actually ",
        "instead ",
        "make it ",
        "change it to ",
        "switch to ",
    )
    if any(t.startswith(p) for p in prefixes):
        return True
    task_markers = (
        "find me",
        "book me",
        "plan a",
        "remind me",
        "schedule a",
        "schedule meeting",
    )
    if any(m in t for m in task_markers):
        return False
    if extract_coworking_budget(raw) or re.search(
        r"under\s*\$?\s*\d+(?:\.\d+)?\s*/\s*day",
        t,
    ):
        return True
    if extract_trip_budget(raw) or re.search(
        r"under\s*(?:€\s*)?\d+(?:\.\d+)?\s*eur",
        t,
    ):
        return len(t) < 80
    if extract_date_range_phrase(raw):
        return len(t) < 80
    if re.match(r"^in\s+[a-z]+$", t):
        return True
    return False


def merge_constraint_update(previous_request: str, update_text: str) -> str | None:
    """Merge a constraint tweak into the prior utterance; None if unsure."""
    prev = previous_request.strip()
    if not prev:
        return None
    body = update_text.strip()
    low = normalize_text(body)
    for prefix in (
        "actually ",
        "instead ",
        "make it ",
        "change it to ",
        "switch to ",
    ):
        if low.startswith(prefix):
            body = body[len(prefix) :].strip()
            low = normalize_text(body)
            break

    prev_low = normalize_text(prev)

    # Coworking budget
    if "coworking" in prev_low or (
        "space" in prev_low and "warsaw" in prev_low
    ):
        bud = extract_coworking_budget(body) or extract_coworking_budget(update_text)
        if bud and bud.currency == "USD":
            new_phrase = f"under ${int(bud.amount)}/day" if bud.amount == int(bud.amount) else f"under ${bud.amount}/day"
            m = re.search(
                r"under\s*\$?\s*\d+(?:\.\d+)?\s*/\s*day",
                prev,
                flags=re.IGNORECASE,
            )
            if m:
                return re.sub(
                    r"under\s*\$?\s*\d+(?:\.\d+)?\s*/\s*day",
                    new_phrase,
                    prev,
                    count=1,
                    flags=re.IGNORECASE,
                )
        return None

    # Trip budget (EUR)
    if "trip" in prev_low:
        tb = extract_trip_budget(body) or extract_trip_budget(update_text)
        if tb:
            return re.sub(
                r"under\s*(?:€\s*)?\d+(?:\.\d+)?(?:\s*eur)?",
                f"under {int(tb.amount)} EUR",
                prev,
                count=1,
                flags=re.IGNORECASE,
            )

    # Dentist / appointment time
    if "dentist" in prev_low or "appointment" in prev_low:
        new_date = extract_date_range_phrase(body) or extract_date_range_phrase(
            update_text,
        )
        if not new_date:
            return None
        replaced = False
        merged = prev
        for needle, _canonical in (
            ("next week after 5pm", "next week after 5pm"),
            ("next week after 5 pm", "next week after 5pm"),
            ("next tuesday afternoon", "next Tuesday afternoon"),
            ("tomorrow morning", "tomorrow morning"),
        ):
            if needle in normalize_text(merged):
                merged = re.sub(
                    re.escape(needle),
                    new_date,
                    merged,
                    count=1,
                    flags=re.IGNORECASE,
                )
                replaced = True
                break
        if replaced:
            return merged
        return f"{prev.rstrip('.')} {new_date}."

    # City swap
    city = extract_city(body) or extract_city(update_text)
    if city and re.search(r"\bin\s+[A-Za-zÀ-ÿ]+\b", prev):
        return re.sub(
            r"in\s+[A-Za-zÀ-ÿ]+",
            f"in {city}",
            prev,
            count=1,
        )

    return None


def is_new_standalone_task(text: str) -> bool:
    """Full new request (replaces pending confirmation)."""
    key = detect_intent(text)
    t = normalize_text(text)
    if key == "reminder" and "remind me" in t:
        return True
    if key == "trip" and ("plan" in t or "trip to" in t):
        return True
    if key == "coworking" and ("find" in t or "coworking" in t):
        return True
    if key == "meeting" and (
        "schedule" in t or "meeting with" in t
    ):
        return True
    if key == "appointment" and (
        "book" in t or "appointment" in t
    ):
        return True
    return False


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
