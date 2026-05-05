# Task Execution Agent

A **uv-based** Python assistant agent that interprets user requests, asks clarifying questions when information is missing, plans tool usage, executes **mock** tools, manages a confirmation flow before bookings, and returns structured final responses.

The project uses **deterministic mock services by default**, so it can be evaluated **without API keys or external HTTP services**. An **optional OpenAI** planning mode can be enabled via environment variables; validated LLM output falls back to the rule-based planner on failure.

---

## Features

- **Intent detection** and **slot extraction** (mock rules + optional LLM planner)
- **Missing-information** handling with clarifying questions (`MissingField`)
- **Tool planning** (`ToolCallPlan`) and **orchestration** (`AgentExecutor`, `ToolRegistry`)
- **Confirmation-before-booking** for dentist appointments and meeting slots
- **Stateful follow-ups** (selection, cancel, pivot to a new task, budget/time constraint updates)
- **No-results** and **temporary failure** handling with explicit blockers (no false success claims)
- **Interactive CLI** (Rich + Typer)
- **Deterministic demo runner** (`main.py demo`) for evaluators
- **Optional OpenAI planner** with **MockPlanner fallback** (`OpenAIPlanner`)

---

## Supported example requests

Try these in the interactive CLI:

- Book me a dentist appointment next week after 5pm.
- Find me 3 coworking spaces in Warsaw under $20/day.
- Plan a 2-day trip to Prague under 300 EUR.
- Schedule a meeting with John next Tuesday afternoon.
- Remind me to call John tomorrow morning.

(You can use `300 EUR` instead of `€300` on consoles with limited Unicode support.)

---

## Quick start

```bash
uv sync
uv run python main.py
```

Chat commands: `/help`, `/debug on|off`, `/reset`, `/exit`.

---

## Run the deterministic demo

```bash
uv run python main.py demo
```

This runs all built-in evaluation scenarios with the **mock** planner only: **no OpenAI calls**, **no API key**. You should see **8/8 scenarios passed** basic checks (at the time of submission, **`uv run pytest tests/ -q`** reports **89 passed** — re-run after changes).

Details: `docs/requirement-mapping.md`, `docs/architecture.md`, `src/task_agent/evaluation/`.

---

## Run tests

```bash
uv sync
uv run pytest tests/ -q
```

At submission time this reports **89 passed** (run locally to confirm after any change).

---

## Configuration

Copy `.env.example` to `.env` if you need to override defaults. **Never commit `.env`.**

| Variable | Role |
|----------|------|
| `AGENT_LLM_MODE` | `mock` (default, recommended for evaluation) or `openai` if a key is set |
| `OPENAI_API_KEY` | Optional; required only for OpenAI planning mode |
| `OPENAI_MODEL` | Optional model name when using OpenAI |

- **Mock mode** is default and **recommended for grading**.
- **OpenAI mode** is optional; the **demo runner always uses mock mode**.
- The demo and mock tools do **not** call external booking or calendar APIs.

---

## Architecture

High-level flow:

```text
User request
  → Planner (MockPlanner or OpenAIPlanner)
  → ExtractedTask (intent, slots, tool_plan, missing_fields)
  → Executor
  → ToolRegistry
  → mock tools (JSON-backed data)
  → AgentFinalResponse
```

| Area | Module(s) |
|------|-----------|
| Planning | `src/task_agent/agent/planner.py`, `planner_support.py` |
| Execution / confirmations | `src/task_agent/agent/executor.py` |
| Session state | `src/task_agent/agent/state.py` |
| Tool implementations | `src/task_agent/tools/*`, `registry.py` |
| Domain types | `src/task_agent/domain/models.py` |
| CLI + demo command | `src/task_agent/ui/cli.py` |
| Evaluation scenarios | `src/task_agent/evaluation/*` |

More detail: **`docs/architecture.md`**.

---

## Tool contracts

Mock tools match the assignment-style surface area:

| Tool | Role |
|------|------|
| `calendar_check(date_range)` | Mock availability windows |
| `search_service(query)` | Mock search over local JSON index |
| `booking_service(option)` | Mock booking by option id |
| `reminder_create(details)` | Mock reminder record |

Each returns a **`ToolCallResult`** with `status`, optional `failure_reason`, and `error_message` / `data` as appropriate.

---

## Safety and reliability

- **`booking_service` is not invoked** until the user **confirms** a concrete option (dentist / meeting flows).
- **OpenAI** output is validated as **`ExtractedTask`**; on any failure the code **falls back to `MockPlanner`**.
- The **demo / evaluation harness** forces **mock** configuration (no key required).
- **Mock tools** read local **`data/*.json`** only — **no network** calls in the default path.
- **Failures** are communicated via **`blockers`** and response types; the agent does **not** claim booking or reminder success when tools fail.

---

## Demo scenarios (8)

Run via `uv run python main.py demo`:

1. **dentist_clarification_booking** — missing city → search → confirm → book + reminder  
2. **coworking_search** — budget + limit  
3. **prague_trip** — trip intent, budget/duration  
4. **meeting_schedule** — calendar + lookup → confirm → reminder  
5. **constraint_update** — coworking budget follow-up  
6. **cancel_pending_booking** — abort pending confirmation  
7. **new_task_pivots_pending** — new request clears pending dentist flow  
8. **unknown_request** — vague prompt, no tools  

*(Simulated **temporary booking** failures are covered in tests, not in this scripted demo.)*

---

## Limitations

- **Mock data only** — not real dentists, calendars, or booking providers.
- **Trip planning** returns **candidate items** from the index, not a full itinerary optimizer.
- **NLP** beyond the planner is **intentionally narrow** (keyword/heuristic helpers) for stable demos.
- **OpenAI** is **optional** and **not required** for evaluation or tests.

---

## Submission checklist

```bash
uv sync
uv run python main.py
uv run python main.py demo
uv run pytest tests/ -q
```

Expected: interactive CLI starts; demo reports **8/8**; pytest reports **89 passed** (verify locally).

---

## Documentation

- `docs/requirement-mapping.md` — assignment expectations ↔ code  
- `docs/architecture.md` — design overview  
- `docs/failure-handling.md` — edge-case behavior  
- `docs/demo-transcript.md` — sample dialogue
