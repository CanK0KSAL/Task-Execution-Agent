# Requirement mapping

Assignment-style expectations mapped to **concrete files / types** (concise).

| Requirement | Where it lives |
|-------------|----------------|
| Understand request / intent | `IntentType`, `ExtractedTask` in `src/task_agent/domain/models.py`; `MockPlanner` / `OpenAIPlanner` in `src/task_agent/agent/planner.py`; `detect_intent()` in `src/task_agent/agent/planner_support.py` |
| Slot / parameter extraction | `ExtractedTask.slots`, helpers in `planner_support.py` (city, budget, dates, reminder payload, …) |
| Break into subtasks | `ToolCallPlan` list on `ExtractedTask`; executed as `AgentStep` in `executor.py` |
| Missing information | `MissingField` on `ExtractedTask`; `_clarification_response` in `executor.py` |
| Clarifying questions | Dentist-without-city flow, `UNKNOWN` blocked copy with examples in `executor.py` |
| Call tools / functions | `ToolRegistry` in `src/task_agent/tools/registry.py` → `calendar_check`, `search_service`, `booking_service`, `reminder_create` |
| Tool success/failure semantics | `ToolStatus`, `FailureReason`, `ToolCallResult` in `domain/models.py`; tool modules under `src/task_agent/tools/` |
| Handle no results / failures | `_tool_failure_response`, booking/reminder branches in `executor.py`; tests in `tests/test_failure_handling.py` |
| Clear final answer | `AgentFinalResponse` (`message`, `summary`, `found_options`, `booked_item`, `reminder`, `blockers`, `tool_results`) |
| Confirmation before booking | `requires_user_confirmation`, `ConversationState` pending options; `_complete_booking` / `_handle_pending_selection` in `executor.py` |
| Stateful follow-up | `ConversationState`, Phase 6 flows (cancel, pivot, constraint merge) in `executor.py` + `planner_support.py` |
| Package / runner | `pyproject.toml`, `uv.lock`; `uv run python main.py`, `uv run python main.py demo` |
| Traceability | `src/task_agent/evaluation/scenarios.py`, `runner.py`; `docs/requirement-mapping.md` |

**OpenAI:** Optional via `.env` (`AGENT_LLM_MODE=openai` + `OPENAI_API_KEY`). **`mock_eval_config()`** in `evaluation/runner.py` and **`main.py demo`** use **mock only**.

**Temporary booking failure:** `tests/test_failure_handling.py`; not one of the eight turn-based demo scenarios.
