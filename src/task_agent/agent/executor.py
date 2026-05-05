"""Agent executor: orchestrate planner output, tools, confirmations, and responses."""

from __future__ import annotations

import re
from typing import Any

from task_agent.agent.planner import Planner, get_planner
from task_agent.agent.planner_support import extract_city
from task_agent.agent.state import ConversationState
from task_agent.config import Config
from task_agent.domain.models import (
    AgentFinalResponse,
    AgentResponseType,
    AgentStep,
    ExtractedTask,
    IntentType,
    MissingField,
    ToolCallPlan,
    ToolCallResult,
    ToolName,
    ToolStatus,
)
from task_agent.domain.schemas import UserRequest
from task_agent.tools.registry import ToolRegistry


def parse_selection_index(message: str) -> int | None:
    """Parse a 0-based selection index from short confirmation utterances."""
    t = message.strip().lower()
    if re.search(r"\bthird\b|\b3rd\b", t):
        return 2
    if re.search(r"\bsecond\b|\b2nd\b", t):
        return 1
    m = re.search(r"\boption\s+(\d+)\b", t)
    if m:
        return int(m.group(1)) - 1
    m = re.search(r"\bselect\s+(\d+)\b", t)
    if m:
        return int(m.group(1)) - 1
    m = re.match(r"^\s*(\d+)\s*$", t)
    if m:
        return int(m.group(1)) - 1
    if "first" in t or re.search(r"\b1st\b", t):
        return 0
    if re.search(r"\bchoose\b", t) and re.search(r"\b1\b", t) and "2" not in t:
        return 0
    if re.search(r"\b1\b", t) and "2" not in t and "3" not in t and "option" not in t:
        return 0
    if re.search(r"\b2\b", t) and "1" not in t and "3" not in t:
        return 1
    if re.search(r"\b3\b", t) and "1" not in t and "2" not in t:
        return 2
    return None


class AgentExecutor:
    """Runs planned tools, handles clarifications, and manages confirmations."""

    def __init__(
        self,
        planner: Planner | None = None,
        tool_registry: ToolRegistry | None = None,
        config: Config | None = None,
    ) -> None:
        self._config = config or Config.from_env()
        self._planner = planner or get_planner(self._config)
        self._registry = tool_registry or ToolRegistry()

    def execute(
        self,
        user_message: str,
        state: ConversationState | None = None,
    ) -> AgentFinalResponse:
        state = state or ConversationState()
        state.add_user_message(user_message)

        if state.has_pending_confirmation():
            selection = parse_selection_index(user_message)
            if selection is not None:
                return self._handle_pending_selection(selection, state)
            return AgentFinalResponse(
                response_type=AgentResponseType.CLARIFICATION,
                message=(
                    "I already have options ready. "
                    "Tell me which to use (for example, “book the first one”)."
                ),
                blockers=["Awaiting confirmation for pending options."],
            )

        selection = parse_selection_index(user_message)
        if selection is not None:
            return AgentFinalResponse(
                response_type=AgentResponseType.BLOCKED,
                message="There is nothing on hold to select. Please start a request first.",
                intent=IntentType.UNKNOWN,
                blockers=["No pending options to book or schedule."],
            )

        merged = self._try_merge_city_clarification(user_message, state)
        text_for_planner = merged if merged else user_message

        task = self._planner.plan(UserRequest(text=text_for_planner))
        state.last_task = task
        state.pending_missing_fields = [m.name for m in task.missing_fields]
        state.assumptions = list(
            dict.fromkeys([*state.assumptions, *task.assumptions]),
        )

        if task.missing_fields:
            return self._clarification_response(task)

        if task.intent == IntentType.UNKNOWN:
            return AgentFinalResponse(
                response_type=AgentResponseType.BLOCKED,
                message=task.missing_fields[0].question
                if task.missing_fields
                else "I need more detail to proceed.",
                intent=IntentType.UNKNOWN,
                missing_fields=list(task.missing_fields),
                assumptions=list(task.assumptions),
                raw_task=task,
                blockers=["Unsupported or unclear request."],
            )

        return self._run_planned_tools(task, state)

    def _clarification_response(self, task: ExtractedTask) -> AgentFinalResponse:
        first = task.missing_fields[0]
        return AgentFinalResponse(
            response_type=AgentResponseType.CLARIFICATION,
            message=first.question,
            intent=task.intent,
            summary="More information is required before running tools.",
            missing_fields=list(task.missing_fields),
            assumptions=list(task.assumptions),
            raw_task=task,
        )

    def _try_merge_city_clarification(
        self,
        message: str,
        state: ConversationState,
    ) -> str | None:
        lt = state.last_task
        if lt is None or not lt.missing_fields:
            return None
        if not any(m.name == "city" for m in lt.missing_fields):
            return None
        city = extract_city(message)
        if city is None:
            token = message.strip().lower()
            if token in {"warsaw", "prague", "krakow", "berlin", "london"}:
                city = message.strip().title()
        if city is None:
            return None
        orig = lt.original_request.strip()
        if " in " in orig.lower():
            return None
        lower = orig.lower()
        needle = "dentist appointment "
        if needle in lower:
            idx = lower.index(needle) + len(needle)
            return f"{orig[:idx]}in {city} {orig[idx:]}".replace("  ", " ")
        return orig.replace("appointment ", f"appointment in {city} ", 1)

    def _run_planned_tools(
        self,
        task: ExtractedTask,
        state: ConversationState,
    ) -> AgentFinalResponse:
        steps: list[AgentStep] = []
        results: list[ToolCallResult] = []

        for idx, plan in enumerate(task.tool_plan):
            if plan.tool_name == ToolName.BOOKING_SERVICE:
                continue
            result = self._registry.execute(plan.tool_name, plan.arguments)
            step = AgentStep(
                index=idx,
                description=plan.reason,
                tool_call=plan,
                tool_result=result,
            )
            steps.append(step)
            state.tool_history.append(step)
            results.append(result)

            if result.status in (
                ToolStatus.FAILURE,
                ToolStatus.TEMPORARY_FAILURE,
                ToolStatus.NO_RESULTS,
            ):
                return self._tool_failure_response(task, steps, results, result)

        return self._success_branch(task, state, steps, results)

    def _tool_failure_response(
        self,
        task: ExtractedTask,
        steps: list[AgentStep],
        results: list[ToolCallResult],
        failed: ToolCallResult,
    ) -> AgentFinalResponse:
        blocker = failed.error_message or "Tool execution failed."
        rtype = AgentResponseType.BLOCKED
        if failed.status == ToolStatus.TEMPORARY_FAILURE:
            rtype = AgentResponseType.FAILURE
        elif failed.status == ToolStatus.NO_RESULTS:
            rtype = AgentResponseType.PARTIAL_SUCCESS
        return AgentFinalResponse(
            response_type=rtype,
            message="I could not complete the search with the current plan.",
            summary="Tool execution stopped after a failure or empty result set.",
            intent=task.intent,
            steps=steps,
            tool_results=results,
            blockers=[blocker],
            assumptions=list(task.assumptions),
            raw_task=task,
        )

    def _success_branch(
        self,
        task: ExtractedTask,
        state: ConversationState,
        steps: list[AgentStep],
        results: list[ToolCallResult],
    ) -> AgentFinalResponse:
        if task.intent == IntentType.CREATE_REMINDER:
            return self._finalize_reminder(task, steps, results)

        if task.intent == IntentType.BOOK_APPOINTMENT and task.requires_user_confirmation:
            options = self._collect_search_results(results)
            if not options:
                return AgentFinalResponse(
                    response_type=AgentResponseType.BLOCKED,
                    message="No dentist options were found to book.",
                    intent=task.intent,
                    steps=steps,
                    tool_results=results,
                    blockers=["Search returned no bookable options."],
                    raw_task=task,
                )
            state.set_pending_options(options, "book_option", task.original_request)
            return AgentFinalResponse(
                response_type=AgentResponseType.PARTIAL_SUCCESS,
                message=(
                    "I found dentist options matching your request. "
                    "Reply with which option to book (for example, “book the first one”)."
                ),
                summary="Search completed; booking requires your confirmation.",
                intent=task.intent,
                steps=steps,
                tool_results=results,
                found_options=options,
                blockers=["User confirmation required before booking."],
                assumptions=list(task.assumptions),
                raw_task=task,
            )

        if task.intent == IntentType.FIND_OPTIONS:
            options = self._collect_search_results(results)
            return AgentFinalResponse(
                response_type=AgentResponseType.SUCCESS,
                message=f"Found {len(options)} matching options.",
                summary=f"Located {len(options)} options for your search.",
                intent=task.intent,
                steps=steps,
                tool_results=results,
                found_options=options,
                assumptions=list(task.assumptions),
                raw_task=task,
            )

        if task.intent == IntentType.PLAN_TRIP:
            options = self._collect_search_results(results)
            dest = task.slots.get("destination", "your destination")
            days = task.slots.get("duration_days", "?")
            budget = task.slots.get("budget", {})
            amount = budget.get("amount", "")
            cur = budget.get("currency", "")
            summary = (
                f"Candidate activities, food, and stays for {dest} "
                f"across {days} day(s) within {amount} {cur} (mock data)."
            )
            return AgentFinalResponse(
                response_type=AgentResponseType.SUCCESS,
                message="Here are candidate items that fit your trip constraints.",
                summary=summary,
                intent=task.intent,
                steps=steps,
                tool_results=results,
                found_options=options,
                assumptions=list(task.assumptions),
                raw_task=task,
            )

        if task.intent == IntentType.SCHEDULE_MEETING:
            cal_slots = self._collect_calendar_slots(results)
            search_hits = self._collect_search_results(results)
            options = cal_slots or search_hits
            state.set_pending_options(
                options,
                "schedule_meeting",
                task.original_request,
            )
            return AgentFinalResponse(
                response_type=AgentResponseType.PARTIAL_SUCCESS,
                message=(
                    "Available slots and attendee hints are ready. "
                    "Confirm a slot (for example, “book the first one”) to set a reminder."
                ),
                summary="Calendar data retrieved; meeting is not finalized yet.",
                intent=task.intent,
                steps=steps,
                tool_results=results,
                found_options=options,
                blockers=["User confirmation required before scheduling."],
                assumptions=list(task.assumptions),
                raw_task=task,
            )

        return AgentFinalResponse(
            response_type=AgentResponseType.SUCCESS,
            message="Request processed.",
            intent=task.intent,
            steps=steps,
            tool_results=results,
            raw_task=task,
        )

    def _finalize_reminder(
        self,
        task: ExtractedTask,
        steps: list[AgentStep],
        results: list[ToolCallResult],
    ) -> AgentFinalResponse:
        if not results or results[-1].status != ToolStatus.SUCCESS:
            return AgentFinalResponse(
                response_type=AgentResponseType.FAILURE,
                message="Reminder could not be created.",
                intent=task.intent,
                steps=steps,
                tool_results=results,
                blockers=["Reminder tool did not succeed."],
                raw_task=task,
            )
        reminder_data = results[-1].data
        return AgentFinalResponse(
            response_type=AgentResponseType.SUCCESS,
            message="Reminder created (mock).",
            summary=reminder_data.get("message", "Reminder stored."),
            intent=task.intent,
            steps=steps,
            tool_results=results,
            reminder=reminder_data,
            raw_task=task,
        )

    def _handle_pending_selection(
        self,
        index: int,
        state: ConversationState,
    ) -> AgentFinalResponse:
        options = state.pending_confirmation_options
        if index < 0 or index >= len(options):
            return AgentFinalResponse(
                response_type=AgentResponseType.BLOCKED,
                message="That selection is not available.",
                intent=IntentType.UNKNOWN,
                blockers=["Selection out of range for pending options."],
            )

        selected = options[index]
        if state.pending_action == "book_option":
            return self._complete_booking(selected, state)
        if state.pending_action == "schedule_meeting":
            return self._complete_meeting_reminder(selected, state)
        return AgentFinalResponse(
            response_type=AgentResponseType.BLOCKED,
            message="Unsupported pending action.",
            blockers=["Unknown pending action state."],
        )

    def _complete_booking(
        self,
        option: dict[str, Any],
        state: ConversationState,
    ) -> AgentFinalResponse:
        option_id = option.get("id")
        book_res = self._registry.execute(
            ToolName.BOOKING_SERVICE,
            {"option": str(option_id)},
        )
        step_book = AgentStep(
            index=0,
            description="Confirm and create booking for selected option.",
            tool_call=ToolCallPlan(
                tool_name=ToolName.BOOKING_SERVICE,
                arguments={"option": str(option_id)},
                reason="User confirmed a specific search result.",
            ),
            tool_result=book_res,
        )
        state.tool_history.append(step_book)

        if book_res.status != ToolStatus.SUCCESS:
            blocker = book_res.error_message or "Booking failed."
            return AgentFinalResponse(
                response_type=AgentResponseType.FAILURE
                if book_res.status == ToolStatus.TEMPORARY_FAILURE
                else AgentResponseType.BLOCKED,
                message="Booking could not be completed.",
                intent=IntentType.BOOK_APPOINTMENT,
                steps=[step_book],
                tool_results=[book_res],
                blockers=[blocker],
            )

        title = str(option.get("title") or option_id)
        confirmed = book_res.data.get("confirmed_time") or option.get(
            "available_slot_id",
            "the scheduled time",
        )
        reminder_details = {
            "title": f"Reminder for {title}",
            "when": f"2 hours before {confirmed}",
        }
        rem_res = self._registry.execute(
            ToolName.REMINDER_CREATE,
            {"details": reminder_details},
        )
        step_rem = AgentStep(
            index=1,
            description="Create reminder ahead of the booking.",
            tool_call=ToolCallPlan(
                tool_name=ToolName.REMINDER_CREATE,
                arguments={"details": reminder_details},
                reason="Post-booking reminder per workflow.",
            ),
            tool_result=rem_res,
        )
        state.tool_history.append(step_rem)

        state.clear_pending_confirmation()

        if rem_res.status == ToolStatus.SUCCESS:
            return AgentFinalResponse(
                response_type=AgentResponseType.SUCCESS,
                message="Booking and reminder are set (mock).",
                summary="Booking confirmed and reminder created.",
                intent=IntentType.BOOK_APPOINTMENT,
                steps=[step_book, step_rem],
                tool_results=[book_res, rem_res],
                booked_item=dict(book_res.data),
                reminder=dict(rem_res.data),
            )

        return AgentFinalResponse(
            response_type=AgentResponseType.PARTIAL_SUCCESS,
            message="Booking succeeded but reminder failed.",
            summary="Booking is confirmed; reminder was not created.",
            intent=IntentType.BOOK_APPOINTMENT,
            steps=[step_book, step_rem],
            tool_results=[book_res, rem_res],
            booked_item=dict(book_res.data),
            reminder=None,
            blockers=[rem_res.error_message or "Reminder creation failed."],
        )

    def _complete_meeting_reminder(
        self,
        slot: dict[str, Any],
        state: ConversationState,
    ) -> AgentFinalResponse:
        when = f"{slot.get('date', '')} {slot.get('start_time', '')}".strip()
        if not when:
            when = str(slot.get("id", "selected slot"))
        details = {
            "title": f"Meeting reminder: {slot.get('label', slot.get('id'))}",
            "when": when,
        }
        rem_res = self._registry.execute(
            ToolName.REMINDER_CREATE,
            {"details": details},
        )
        step = AgentStep(
            index=0,
            description="Create reminder for chosen meeting slot.",
            tool_call=ToolCallPlan(
                tool_name=ToolName.REMINDER_CREATE,
                arguments={"details": details},
                reason="User confirmed a meeting slot.",
            ),
            tool_result=rem_res,
        )
        state.tool_history.append(step)
        state.clear_pending_confirmation()
        if rem_res.status != ToolStatus.SUCCESS:
            return AgentFinalResponse(
                response_type=AgentResponseType.FAILURE,
                message="Could not set meeting reminder.",
                steps=[step],
                tool_results=[rem_res],
                blockers=[rem_res.error_message or "Reminder failed."],
            )
        return AgentFinalResponse(
            response_type=AgentResponseType.PARTIAL_SUCCESS,
            message="Meeting reminder stored; calendar event not created (mock).",
            summary="Reminder captured for the chosen slot.",
            intent=IntentType.SCHEDULE_MEETING,
            steps=[step],
            tool_results=[rem_res],
            reminder=dict(rem_res.data),
        )

    @staticmethod
    def _collect_search_results(results: list[ToolCallResult]) -> list[dict[str, Any]]:
        for res in reversed(results):
            if res.tool_name == ToolName.SEARCH_SERVICE and res.status == ToolStatus.SUCCESS:
                data = res.data.get("results")
                if isinstance(data, list):
                    return list(data)
        return []

    @staticmethod
    def _collect_calendar_slots(results: list[ToolCallResult]) -> list[dict[str, Any]]:
        slots: list[dict[str, Any]] = []
        for res in results:
            if res.tool_name == ToolName.CALENDAR_CHECK and res.status == ToolStatus.SUCCESS:
                slots.extend(res.data.get("available_slots", []))
        return slots
