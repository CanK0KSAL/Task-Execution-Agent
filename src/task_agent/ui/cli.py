"""Typer-based CLI shell (phase 0: welcome only)."""

from __future__ import annotations

import typer
from rich.console import Console

from task_agent.config import Config

app = typer.Typer(
    invoke_without_command=True,
    no_args_is_help=False,
    add_completion=False,
)
console = Console()


def run_cli() -> None:
    """Invoke the Typer application (used by `main.py`)."""
    app()


@app.callback()
def main_callback() -> None:
    """Task Execution Agent — entry hook for future subcommands."""
    _print_welcome()


def _print_welcome() -> None:
    cfg = Config.from_env()
    console.print(
        "[bold green]Task Execution Agent[/bold green]\n\n"
        "This assistant will help you turn real-world requests into subtasks, "
        "call tools (calendar, search, booking, reminders), and report results. "
        "Full planning and execution are not wired up yet; this is the project shell.\n"
    )
    mode = "mock (no API calls)" if not cfg.use_openai else f"OpenAI model: {cfg.openai_model}"
    console.print(f"[dim]LLM mode:[/dim] {cfg.agent_llm_mode} | {mode}\n")


if __name__ == "__main__":
    run_cli()
