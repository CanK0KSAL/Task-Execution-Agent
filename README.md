# Task Execution Agent

Take-home project: planner, mock tools, executor, and CLI.

## Setup

```bash
uv sync
```

For development (tests, ruff, mypy): `uv sync --extra dev`.

## Interactive CLI

Default entrypoint opens the chat loop (Rich + Typer). No API key required in **mock** mode.

```bash
uv run python main.py
```

Use `/help` for commands (`/debug`, `/reset`, `/exit`). Example prompts also work with `300 EUR` instead of `€300` on narrow Windows consoles.

## Non-interactive demo (evaluation)

Runs all official scenarios with the **mock** planner (deterministic; no OpenAI calls).

```bash
uv run python main.py demo
```

Requirement traceability: `docs/requirement-mapping.md`, scripted scenarios in `src/task_agent/evaluation/`.

## Configuration

- **Default:** `AGENT_LLM_MODE` defaults to mock; no `OPENAI_API_KEY` needed.
- **Optional OpenAI:** set in `.env` (see `.env.example`). The demo command always uses mock mode for evaluation.

## Tests

```bash
uv sync --extra dev
uv run pytest tests/ -q
```
