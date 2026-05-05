# Architecture

## Flow

1. **User input** enters the **CLI** (`cli.py`) or the **evaluation runner** (`evaluation/runner.py`).
2. **Planner** (`planner.py`) produces an **`ExtractedTask`**: intent, slots, optional `missing_fields`, ordered **`tool_plan`**, and flags such as `requires_user_confirmation`.
3. **Executor** (`executor.py`) either returns clarification/unknown responses or runs the plan via **`ToolRegistry`**.
4. **Tools** (`tools/*.py`) read **local JSON** under `data/` and return **`ToolCallResult`**.
5. The executor assembles **`AgentFinalResponse`** (message, summary, options, booking/reminder payloads, blockers).

## Planner vs executor

| Component | Responsibility |
|-----------|----------------|
| **Planner** | Natural-language → structured task: intent, slots, which tools to call, with what arguments; surface missing fields. Does not call `booking_service` for exploratory searches (booking plans are stripped where applicable). |
| **Executor** | Run tools in order, stop on hard failures, set **pending confirmation** when options need user choice, complete booking/reminder only after confirmation, merge follow-up utterances (cancel, constraint update, new task). |

## Why mock tools

- **Deterministic** evaluation without credentials or network flakiness.
- **Explicit** `ToolStatus` / `FailureReason` for teaching and tests.
- Same **interfaces** (`ToolCallResult`, argument shapes) a real integration would implement behind the registry.

## Confirmation flow

For dentist booking and meeting scheduling, search/calendar steps run first; **`booking_service`** (or meeting reminder completion) runs only after the user picks an option (`parse_selection_index` / explicit phrasing). Pending state lives in **`ConversationState`**.

## Failure handling

See **`docs/failure-handling.md`**. Short version: failures and empty results become **`AgentFinalResponse`** blockers and appropriate **`AgentResponseType`** values; the agent avoids claiming success when tools did not succeed.

## OpenAI (optional)

When `AGENT_LLM_MODE=openai` and a key is set, **`OpenAIPlanner`** parses JSON into **`ExtractedTask`**. On any error, it **falls back to `MockPlanner`** and records a warning on the task. **Demo scenarios** do not use this path.
