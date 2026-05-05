"""Agent planner: mock rules and optional OpenAI with safe fallback."""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol, runtime_checkable

from task_agent.agent import planner_support as S
from task_agent.agent.prompts import PLANNER_SYSTEM_PROMPT
from task_agent.config import Config
from task_agent.domain.models import (
    ExtractedTask,
    IntentType,
    MissingField,
    Money,
    ToolCallPlan,
    ToolName,
)
from task_agent.domain.schemas import UserRequest

logger = logging.getLogger(__name__)


@runtime_checkable
class Planner(Protocol):
    """Produces an `ExtractedTask` from a structured user request."""

    def plan(self, request: UserRequest) -> ExtractedTask: ...


def _strip_booking_plans(task: ExtractedTask) -> ExtractedTask:
    kept = [p for p in task.tool_plan if p.tool_name != ToolName.BOOKING_SERVICE]
    if len(kept) == len(task.tool_plan):
        return task
    return task.model_copy(update={"tool_plan": kept})


class MockPlanner:
    """Deterministic, rule-based planner for demos and tests."""

    def plan(self, request: UserRequest) -> ExtractedTask:
        text = request.text
        scenario = S.detect_intent(text)
        builders: dict[str, Any] = {
            "unknown": self._build_unknown,
            "reminder": self._build_reminder,
            "meeting": self._build_meeting,
            "trip": self._build_trip,
            "coworking": self._build_coworking,
            "appointment": self._build_appointment,
        }
        builder = builders.get(scenario, self._build_unknown)
        return builder(text)

    def _build_unknown(self, text: str) -> ExtractedTask:
        return ExtractedTask(
            intent=IntentType.UNKNOWN,
            confidence=0.28,
            original_request=text,
            missing_fields=[
                MissingField(
                    name="task",
                    reason="The request does not describe a concrete task.",
                    question="What would you like me to help you with?",
                )
            ],
            tool_plan=[],
            requires_user_confirmation=False,
        )

    def _build_reminder(self, text: str) -> ExtractedTask:
        payload = S.extract_reminder_payload(text)
        if not payload:
            return self._partial_reminder(text)
        title, when = payload
        return ExtractedTask(
            intent=IntentType.CREATE_REMINDER,
            confidence=0.93,
            original_request=text,
            slots={
                "title": title,
                "task": title,
                "date_range": when,
            },
            tool_plan=[
                ToolCallPlan(
                    tool_name=ToolName.REMINDER_CREATE,
                    arguments={"details": {"title": title, "when": when}},
                    reason="Create a reminder with the requested title and time.",
                    requires_confirmation=False,
                )
            ],
            requires_user_confirmation=False,
        )

    def _partial_reminder(self, text: str) -> ExtractedTask:
        return ExtractedTask(
            intent=IntentType.CREATE_REMINDER,
            confidence=0.55,
            original_request=text,
            missing_fields=[
                MissingField(
                    name="reminder_time",
                    reason="Reminder time could not be parsed reliably.",
                    question="What time should I remind you?",
                )
            ],
            requires_user_confirmation=True,
        )

    def _build_meeting(self, text: str) -> ExtractedTask:
        person = S.extract_person_name(text) or "John"
        dr = S.extract_date_range_phrase(text) or "next Tuesday afternoon"
        assumptions: list[str] = []
        if "minute" not in S.normalize_text(text) and "hour" not in S.normalize_text(
            text,
        ):
            assumptions.append("Assumed a 30-minute meeting duration.")
        slots: dict[str, Any] = {
            "person": person,
            "date_range": dr,
            "duration_minutes": 30,
        }
        return ExtractedTask(
            intent=IntentType.SCHEDULE_MEETING,
            confidence=0.9,
            original_request=text,
            slots=slots,
            tool_plan=[
                ToolCallPlan(
                    tool_name=ToolName.CALENDAR_CHECK,
                    arguments={"date_range": dr},
                    reason="Check calendar availability for the proposed meeting window.",
                    requires_confirmation=True,
                ),
                ToolCallPlan(
                    tool_name=ToolName.SEARCH_SERVICE,
                    arguments={
                        "query": (
                            f"schedule meeting with {person} {dr} availability contact"
                        ),
                    },
                    reason="Look up mock availability hints for the attendee.",
                    requires_confirmation=True,
                ),
            ],
            requires_user_confirmation=True,
            assumptions=assumptions,
        )

    def _build_trip(self, text: str) -> ExtractedTask:
        destination = S.extract_destination(text) or "Prague"
        days = S.extract_duration_days(text) or 2
        budget = S.extract_trip_budget(text) or Money(amount=300, currency="EUR")
        slots = {
            "destination": destination,
            "duration_days": days,
            "budget": budget.model_dump(),
        }
        query = f"{destination} {days}-day trip under {int(budget.amount)} EUR"
        return ExtractedTask(
            intent=IntentType.PLAN_TRIP,
            confidence=0.94,
            original_request=text,
            slots=slots,
            tool_plan=[
                ToolCallPlan(
                    tool_name=ToolName.SEARCH_SERVICE,
                    arguments={"query": query},
                    reason="Find mock itinerary options that fit the destination and budget.",
                    requires_confirmation=False,
                )
            ],
            requires_user_confirmation=False,
        )

    def _build_coworking(self, text: str) -> ExtractedTask:
        city = S.extract_city(text) or "Warsaw"
        budget = S.extract_coworking_budget(text) or Money(
            amount=20,
            currency="USD",
            period="day",
        )
        count = S.extract_result_count(text) or 3
        slots = {
            "category": "coworking space",
            "city": city,
            "budget": budget.model_dump(),
            "result_count": count,
        }
        return ExtractedTask(
            intent=IntentType.FIND_OPTIONS,
            confidence=0.95,
            original_request=text,
            slots=slots,
            tool_plan=[
                ToolCallPlan(
                    tool_name=ToolName.SEARCH_SERVICE,
                    arguments={"query": text},
                    reason="Search mock inventory for coworking spaces matching filters.",
                    requires_confirmation=False,
                )
            ],
            requires_user_confirmation=False,
        )

    def _build_appointment(self, text: str) -> ExtractedTask:
        city = S.extract_city(text)
        dr = S.extract_date_range_phrase(text) or "next week after 5pm"
        slots: dict[str, Any] = {
            "service_type": "dentist",
            "date_range": dr,
        }
        if city:
            slots["city"] = city
        missing: list[MissingField] = []
        if not city:
            missing.append(
                MissingField(
                    name="city",
                    reason="City is required to search for providers.",
                    question="What city should I search in?",
                ),
            )
            return ExtractedTask(
                intent=IntentType.BOOK_APPOINTMENT,
                confidence=0.9,
                original_request=text,
                slots=slots,
                missing_fields=missing,
                tool_plan=[],
                requires_user_confirmation=True,
            )

        search_query = (
            f"dentist {city} next week after 5pm evening appointments available"
        )
        return ExtractedTask(
            intent=IntentType.BOOK_APPOINTMENT,
            confidence=0.92,
            original_request=text,
            slots=slots,
            tool_plan=[
                ToolCallPlan(
                    tool_name=ToolName.CALENDAR_CHECK,
                    arguments={"date_range": dr},
                    reason="Verify availability in the requested window before search.",
                    requires_confirmation=True,
                ),
                ToolCallPlan(
                    tool_name=ToolName.SEARCH_SERVICE,
                    arguments={"query": search_query},
                    reason="Find dentist options matching city and time preferences.",
                    requires_confirmation=True,
                ),
            ],
            requires_user_confirmation=True,
        )


class OpenAIPlanner:
    """LLM-backed planner; falls back to `MockPlanner` on any failure."""

    def __init__(self, config: Config, fallback: MockPlanner) -> None:
        self._config = config
        self._fallback = fallback

    def plan(self, request: UserRequest) -> ExtractedTask:
        try:
            content = self._call_openai(request)
            payload = json.loads(content)
            task = ExtractedTask.model_validate(payload)
            task = _strip_booking_plans(task)
            return task
        except Exception as exc:  # noqa: BLE001
            logger.debug("OpenAI planner failed: %s", type(exc).__name__)
            base = self._fallback.plan(request)
            warning = "OpenAI planner failed; used mock planner fallback."
            return base.model_copy(update={"warnings": [*base.warnings, warning]})

    def _call_openai(self, request: UserRequest) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self._config.openai_api_key)
        user_prompt = json.dumps(
            {
                "instruction": "Return ONLY JSON for ExtractedTask matching the user request.",
                "user_request": request.text,
                "locale": request.locale,
            },
        )
        response = client.chat.completions.create(
            model=self._config.openai_model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        choice = response.choices[0].message.content
        if not choice:
            msg = "Empty response from OpenAI planner"
            raise RuntimeError(msg)
        return choice


def get_planner(config: Config | None = None) -> Planner:
    """Planner factory: mock by default; OpenAI when configured with API key."""
    cfg = config or Config.from_env()
    mock = MockPlanner()
    if cfg.agent_llm_mode == "openai" and cfg.openai_api_key:
        return OpenAIPlanner(cfg, mock)
    return mock
