"""Run evaluation scenarios against the agent (mock planner, deterministic)."""

from __future__ import annotations

from dataclasses import dataclass, field

from task_agent.agent.executor import AgentExecutor
from task_agent.agent.state import ConversationState
from task_agent.config import Config
from task_agent.domain.models import AgentFinalResponse, ToolName
from task_agent.evaluation.scenarios import ALL_SCENARIOS, DemoScenario
from task_agent.tools.registry import ToolRegistry


def mock_eval_config() -> Config:
    """Config that never selects OpenAI (for demos and CI)."""
    return Config(
        agent_llm_mode="mock",
        openai_api_key=None,
        openai_model="gpt-4.1-mini",
    )


@dataclass
class TurnResult:
    user: str
    response_type: str
    intent: str
    message: str
    summary: str | None
    found_option_count: int
    booked: bool
    reminder_created: bool
    blockers: list[str]
    tool_names_called: list[str]


@dataclass
class ScenarioResult:
    scenario_id: str
    title: str
    turn_results: list[TurnResult] = field(default_factory=list)
    passed_basic_checks: bool = True
    warnings: list[str] = field(default_factory=list)


def _turn_from_response(user: str, response: AgentFinalResponse) -> TurnResult:
    tools = [t.tool_name.value for t in response.tool_results]
    return TurnResult(
        user=user,
        response_type=response.response_type.value,
        intent=response.intent.value,
        message=response.message,
        summary=response.summary,
        found_option_count=len(response.found_options),
        booked=response.booked_item is not None,
        reminder_created=response.reminder is not None,
        blockers=list(response.blockers),
        tool_names_called=tools,
    )


def _scenario_checks(
    scenario: DemoScenario,
    turns: list[TurnResult],
) -> list[str]:
    warnings: list[str] = []

    for i, turn in enumerate(scenario.turns):
        exp = turn.expected_response_type
        if exp is None or i >= len(turns):
            continue
        actual = turns[i].response_type
        if actual != exp:
            warnings.append(
                f"Turn {i + 1}: expected response_type {exp!r}, got {actual!r}",
            )

    if scenario.id == "dentist_clarification_booking" and len(turns) >= 3:
        if turns[0].tool_names_called:
            warnings.append("Dentist turn 1: expected no tools to run.")
        t1_tools = set(turns[1].tool_names_called)
        if ToolName.CALENDAR_CHECK.value not in t1_tools:
            warnings.append("Dentist turn 2: expected calendar_check.")
        if ToolName.SEARCH_SERVICE.value not in t1_tools:
            warnings.append("Dentist turn 2: expected search_service.")
        if ToolName.BOOKING_SERVICE.value in t1_tools:
            warnings.append("Dentist turn 2: booking_service must not run yet.")
        t2_tools = turns[2].tool_names_called
        if ToolName.BOOKING_SERVICE.value not in t2_tools:
            warnings.append("Dentist turn 3: expected booking_service.")
        if ToolName.REMINDER_CREATE.value not in t2_tools:
            warnings.append("Dentist turn 3: expected reminder_create.")

    if scenario.id == "coworking_search" and turns:
        if turns[-1].found_option_count != 3:
            warnings.append(
                f"Coworking: expected 3 options, got {turns[-1].found_option_count}.",
            )

    if scenario.id == "unknown_request" and turns:
        if turns[0].tool_names_called:
            warnings.append("Unknown request: expected no tool calls.")

    if scenario.id == "cancel_pending_booking" and len(turns) >= 2:
        if turns[1].booked:
            warnings.append("Cancel scenario: booking should not be created.")

    if scenario.id == "new_task_pivots_pending" and len(turns) >= 2:
        if turns[1].booked:
            warnings.append("Pivot scenario: second turn should not book dentist.")
        if turns[1].found_option_count != 3:
            warnings.append(
                f"Pivot: expected 3 coworking options, got {turns[1].found_option_count}.",
            )

    return warnings


def run_scenario(
    scenario: DemoScenario,
    executor: AgentExecutor | None = None,
) -> ScenarioResult:
    """Execute one scenario with a fresh `ConversationState`, all turns in order."""
    cfg = mock_eval_config()
    exec_ = executor or AgentExecutor(
        config=cfg,
        tool_registry=ToolRegistry(),
    )
    state = ConversationState()
    turn_results: list[TurnResult] = []

    for demo_turn in scenario.turns:
        resp = exec_.execute(demo_turn.user, state)
        turn_results.append(_turn_from_response(demo_turn.user, resp))

    warnings = _scenario_checks(scenario, turn_results)
    passed = len(warnings) == 0

    return ScenarioResult(
        scenario_id=scenario.id,
        title=scenario.title,
        turn_results=turn_results,
        passed_basic_checks=passed,
        warnings=warnings,
    )


def run_all_scenarios(
    executor: AgentExecutor | None = None,
) -> list[ScenarioResult]:
    """Run every defined scenario."""
    return [run_scenario(s, executor=executor) for s in ALL_SCENARIOS]
