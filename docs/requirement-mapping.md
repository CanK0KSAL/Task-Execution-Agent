# Requirement mapping

Concise map from assignment-style expectations to this codebase.

| Assignment expectation | Implementation |
|------------------------|----------------|
| Understand request / identify intent | `MockPlanner` / `OpenAIPlanner`, `IntentType`, `ExtractedTask`, `planner_support.detect_intent` |
| Break task into subtasks | `tool_plan: list[ToolCallPlan]`, executed steps as `AgentStep` |
| Determine missing information | `MissingField` on `ExtractedTask`, executor clarification branch |
| Ask clarifying questions | Dentist missing city flow, `UNKNOWN` / blocked copy with examples |
| Use tools / functions | `ToolRegistry` → `calendar_check`, `search_service`, `booking_service`, `reminder_create` |
| Handle failures, no results, missing data | `ToolStatus`, `FailureReason`, `AgentFinalResponse.blockers`, Phase 6 executor behavior |
| Return clear final result | `AgentFinalResponse` (`message`, `summary`, `found_options`, `booked_item`, `reminder`, `tool_results`) |
| Package / workflow | `uv` (`pyproject.toml`, `uv.lock`), `uv run python main.py` |
| Traceability / demo | `src/task_agent/evaluation/scenarios.py`, `runner.py`, `uv run python main.py demo` |

**OpenAI:** Optional via `.env` (`AGENT_LLM_MODE=openai` and `OPENAI_API_KEY`). Default and demo runner use **mock** only (no live LLM, no key required).

**Temporary booking failures:** Covered in `tests/test_failure_handling.py`, not in the turn-based demo scenarios (see scenario notes in code).
