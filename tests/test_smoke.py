"""Smoke tests: imports and config loading."""

from __future__ import annotations

import pytest

from task_agent.config import Config
from task_agent.tools.registry import REGISTRY, get_tool


def test_imports_and_registry() -> None:
    assert "calendar_check" in REGISTRY
    assert get_tool("reminder_create") is REGISTRY["reminder_create"]


def test_config_from_env_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Config loads with safe defaults when env vars are unset."""
    mp = monkeypatch
    mp.delenv("AGENT_LLM_MODE", raising=False)
    mp.delenv("OPENAI_API_KEY", raising=False)
    mp.delenv("OPENAI_MODEL", raising=False)
    mp.setattr("task_agent.config.load_config_env", lambda *_a, **_k: None)
    cfg = Config.from_env()
    assert cfg.agent_llm_mode == "mock"
    assert cfg.openai_api_key is None
    assert cfg.openai_model == "gpt-4.1-mini"
    assert cfg.use_openai is False


def test_config_openai_when_key_and_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    mp = monkeypatch
    mp.setenv("AGENT_LLM_MODE", "openai")
    mp.setenv("OPENAI_API_KEY", "sk-test")
    mp.setenv("OPENAI_MODEL", "gpt-4.1-mini")
    cfg = Config.from_env()
    assert cfg.use_openai is True
