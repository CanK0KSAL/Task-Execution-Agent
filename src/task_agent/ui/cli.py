"""Interactive CLI for the Task Execution Agent (Rich + Typer)."""

from __future__ import annotations

import json
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from task_agent.agent.executor import AgentExecutor
from task_agent.agent.state import ConversationState
from task_agent.config import Config
from task_agent.domain.models import AgentFinalResponse, IntentType

app = typer.Typer(
    invoke_without_command=True,
    no_args_is_help=False,
    add_completion=False,
)
console = Console()


def build_options_table(found_options: list[dict[str, Any]]) -> Table | None:
    """Build a Rich table for search/option results; returns None if empty."""
    if not found_options:
        return None
    table = Table(title="Options Found", show_lines=False)
    table.add_column("#", justify="right", style="dim")
    table.add_column("Title / Name", overflow="fold")
    table.add_column("Category", overflow="fold")
    table.add_column("City / Dest.", overflow="fold")
    table.add_column("Price", overflow="fold")
    table.add_column("Rating / Avail.", overflow="fold")

    for i, opt in enumerate(found_options):
        title = (
            opt.get("title")
            or opt.get("name")
            or opt.get("provider_name")
            or "-"
        )
        category = str(opt.get("category") or opt.get("trip_subtype") or "-")
        city = str(
            opt.get("city")
            or opt.get("destination")
            or opt.get("area")
            or "-",
        )
        price = opt.get("price")
        currency = opt.get("currency") or ""
        period = opt.get("price_period")
        if price is None:
            price_str = "-"
        else:
            bits = [str(price), str(currency).strip()]
            if period:
                bits.append(f"/{period}")
            price_str = " ".join(b for b in bits if b).strip()

        rating = opt.get("rating")
        avail = (
            opt.get("available_for_booking")
            if "available_for_booking" in opt
            else None
        )
        if avail is None:
            avail = opt.get("availability") or opt.get("available")
        extra_bits: list[str] = []
        if rating is not None:
            extra_bits.append(f"rating {rating}")
        if avail is not None:
            extra_bits.append(f"bookable={avail}")
        rating_avail = " | ".join(extra_bits) if extra_bits else "-"

        table.add_row(str(i + 1), str(title), category, city, price_str, rating_avail)

    return table


def summary_body(response: AgentFinalResponse) -> str:
    """Compose summary text for the final panel."""
    lines: list[str] = []
    primary = (response.summary or "").strip() or (response.message or "").strip()
    if primary:
        lines.append(primary)
    if response.blockers:
        lines.append("[bold red]Blockers[/bold red]")
        for b in response.blockers:
            lines.append(f"  - {b}")
    if response.assumptions:
        lines.append("[bold yellow]Assumptions[/bold yellow]")
        for a in response.assumptions:
            lines.append(f"  - {a}")
    return "\n".join(lines) if lines else "Done."


def render_agent_response(
    response: AgentFinalResponse,
    *,
    debug: bool,
    console_: Console | None = None,
) -> None:
    """Print panels/tables for a single executor response."""
    c = console_ or console

    if response.response_type.value == "CLARIFICATION" or response.missing_fields:
        clar_lines = [response.message]
        if response.missing_fields:
            clar_lines.append("")
            for mf in response.missing_fields:
                clar_lines.append(f"[bold]{mf.name}[/bold]: {mf.question}")
                if mf.reason and mf.reason != mf.question:
                    clar_lines.append(f"  [dim]{mf.reason}[/dim]")
        c.print(
            Panel(
                "\n".join(clar_lines),
                title="Clarification Needed",
                border_style="yellow",
            ),
        )

    if response.found_options:
        tbl = build_options_table(response.found_options)
        if tbl is not None:
            c.print(tbl)

    if response.booked_item:
        bi = response.booked_item
        lines = [
            f"[bold]Booking ID:[/bold] {bi.get('booking_id', '-')}",
            f"[bold]Option:[/bold] {bi.get('title', bi.get('option_id', '-'))}",
        ]
        if bi.get("confirmed_time"):
            lines.append(f"[bold]Confirmed time:[/bold] {bi['confirmed_time']}")
        if bi.get("message"):
            lines.append(f"[dim]{bi['message']}[/dim]")
        c.print(Panel("\n".join(lines), title="Booking Confirmed", border_style="green"))

    if response.reminder:
        rm = response.reminder
        lines = [
            f"[bold]Reminder ID:[/bold] {rm.get('reminder_id', '-')}",
            f"[bold]Title:[/bold] {rm.get('title', '-')}",
            f"[bold]When:[/bold] {rm.get('reminder_time') or rm.get('when', '-')}",
        ]
        if rm.get("message"):
            lines.append(f"[dim]{rm['message']}[/dim]")
        c.print(Panel("\n".join(lines), title="Reminder Created", border_style="cyan"))

    if (
        response.found_options
        and response.booked_item is None
        and (
            any("confirmation" in (b or "").lower() for b in response.blockers)
            or response.intent == IntentType.SCHEDULE_MEETING
        )
    ):
        c.print(
            "[dim]Reply with 'book the first one' or 'select 1' to continue.[/dim]",
        )

    c.print(
        Panel(
            summary_body(response),
            title="Summary",
            border_style="blue",
        ),
    )

    if debug:
        _render_debug(response, c)


def _render_debug(response: AgentFinalResponse, c: Console) -> None:
    dbg_lines = [
        f"[bold]Intent:[/bold] {response.intent.value}",
        f"[bold]Response type:[/bold] {response.response_type.value}",
    ]
    c.print(Panel("\n".join(dbg_lines), title="Debug - routing", border_style="magenta"))

    if response.raw_task is not None:
        try:
            raw_json = json.dumps(
                response.raw_task.model_dump(mode="json"),
                indent=2,
                ensure_ascii=False,
            )
        except Exception:  # noqa: BLE001
            raw_json = str(response.raw_task)
        c.print(
            Panel(
                raw_json[:8000] + ("..." if len(raw_json) > 8000 else ""),
                title="Debug - raw_task (JSON)",
                border_style="magenta",
            ),
        )

    if response.tool_results:
        tbl = Table(title="Debug - tool_results")
        tbl.add_column("tool_name")
        tbl.add_column("status")
        tbl.add_column("failure_reason")
        tbl.add_column("error_message", overflow="fold")
        for tr in response.tool_results:
            tbl.add_row(
                tr.tool_name.value,
                tr.status.value,
                tr.failure_reason.value if tr.failure_reason else "-",
                (tr.error_message or "-")[:500],
            )
        c.print(tbl)

    if response.steps:
        st = Table(title="Debug - steps")
        st.add_column("idx", justify="right")
        st.add_column("description", overflow="fold")
        st.add_column("tool")
        st.add_column("status")
        for step in response.steps:
            name = (
                step.tool_call.tool_name.value
                if step.tool_call
                else "-"
            )
            status = (
                step.tool_result.status.value
                if step.tool_result
                else "-"
            )
            st.add_row(str(step.index), step.description, name, status)
        c.print(st)


def _print_welcome(cfg: Config) -> None:
    mode_label = cfg.agent_llm_mode
    if cfg.use_openai:
        mode_detail = f"openai ({cfg.openai_model})"
    else:
        mode_detail = "mock (no live LLM calls)"

    console.print(
        Panel.fit(
            "[bold green]Task Execution Agent[/bold green]\n\n"
            "I can search, plan, check mock calendar availability, "
            "create mock bookings, and create mock reminders.\n\n"
            f"[dim]LLM mode:[/dim] {mode_label} - {mode_detail}",
            title="Welcome",
            border_style="green",
        ),
    )
    console.print("\n[bold]Try asking:[/bold]")
    examples = [
        "Book me a dentist appointment next week after 5pm.",
        "Find me 3 coworking spaces in Warsaw under $20/day.",
        "Plan a 2-day trip to Prague under 300 EUR.",
        "Schedule a meeting with John next Tuesday afternoon.",
    ]
    for ex in examples:
        console.print(f"  - {ex}")
    console.print(
        "\n[bold]Commands:[/bold] /help | /debug on | /debug off | /reset | /exit\n",
    )


def _print_help() -> None:
    console.print(
        Panel(
            "/help - show this help\n"
            "/debug on|off - toggle planner/tool trace\n"
            "/reset - clear conversation state\n"
            "/exit or /quit - leave the chat\n",
            title="Help",
        ),
    )


def run_interactive_session(
    *,
    config: Config | None = None,
    executor: AgentExecutor | None = None,
    console_: Console | None = None,
) -> None:
    """Run the interactive REPL (used by Typer entry and tests)."""
    c = console_ or console
    cfg = config or Config.from_env()
    exec_ = executor or AgentExecutor(config=cfg)
    state = ConversationState()
    debug = False

    _print_welcome(cfg)

    while True:
        try:
            line = input("You > ").strip()
        except KeyboardInterrupt:
            c.print("\n[yellow]Goodbye.[/yellow]")
            break
        except EOFError:
            c.print("\n[yellow]Goodbye.[/yellow]")
            break

        if not line:
            c.print("[dim]Please enter a request or a command (try /help).[/dim]")
            continue

        low = line.lower()
        if low in {"/exit", "/quit"}:
            c.print("[green]Goodbye.[/green]")
            break
        if low == "/help":
            _print_help()
            continue
        if low == "/reset":
            state.reset()
            c.print("[green]Conversation reset.[/green]")
            continue
        if low == "/debug on":
            debug = True
            c.print("[dim]Debug output ON[/dim]")
            continue
        if low == "/debug off":
            debug = False
            c.print("[dim]Debug output OFF[/dim]")
            continue

        try:
            response = exec_.execute(line, state)
        except Exception as exc:  # noqa: BLE001
            c.print(
                Panel(
                    f"Something went wrong: {type(exc).__name__}: {exc}",
                    title="Error",
                    border_style="red",
                ),
            )
            continue

        render_agent_response(response, debug=debug, console_=c)


def run_cli() -> None:
    """Invoke the Typer application (used by `main.py`)."""
    app()


@app.callback()
def main_callback() -> None:
    """Default command: start interactive chat."""
    run_interactive_session()


if __name__ == "__main__":
    run_cli()
