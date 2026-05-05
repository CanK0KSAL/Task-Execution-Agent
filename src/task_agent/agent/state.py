"""Mutable agent session state (scaffold for planner/executor)."""

from __future__ import annotations

from dataclasses import dataclass, field

from task_agent.domain.models import AgentMessage


@dataclass
class AgentState:
    """Conversation and execution state."""

    messages: list[AgentMessage] = field(default_factory=list)
