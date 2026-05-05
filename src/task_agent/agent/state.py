"""Conversation state for planner + executor sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from task_agent.domain.models import AgentStep, ExtractedTask


@dataclass
class ConversationState:
    """Lightweight session memory for multi-turn flows."""

    messages: list[str] = field(default_factory=list)
    last_task: ExtractedTask | None = None
    pending_confirmation_options: list[dict[str, Any]] = field(default_factory=list)
    pending_action: str | None = None
    pending_original_request: str | None = None
    pending_missing_fields: list[str] = field(default_factory=list)
    tool_history: list[AgentStep] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)

    def reset(self) -> None:
        self.messages.clear()
        self.last_task = None
        self.pending_confirmation_options.clear()
        self.pending_action = None
        self.pending_original_request = None
        self.pending_missing_fields.clear()
        self.tool_history.clear()
        self.assumptions.clear()

    def add_user_message(self, text: str) -> None:
        self.messages.append(text)

    def set_pending_options(
        self,
        options: list[dict[str, Any]],
        action: str,
        original_request: str,
    ) -> None:
        self.pending_confirmation_options = list(options)
        self.pending_action = action
        self.pending_original_request = original_request

    def clear_pending_confirmation(self) -> None:
        self.pending_confirmation_options.clear()
        self.pending_action = None
        self.pending_original_request = None

    def has_pending_confirmation(self) -> bool:
        return bool(self.pending_confirmation_options and self.pending_action)
