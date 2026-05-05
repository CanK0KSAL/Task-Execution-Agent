"""Lightweight checks that submission docs and eval wiring stay intact."""

from __future__ import annotations

from pathlib import Path

import pytest

from task_agent.config import Config
from task_agent.evaluation.runner import mock_eval_config, run_all_scenarios
from task_agent.evaluation.scenarios import ALL_SCENARIOS

ROOT = Path(__file__).resolve().parents[1]


def test_readme_lists_core_commands() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "uv run python main.py" in text
    assert "uv run python main.py demo" in text
    assert "uv run pytest tests/ -q" in text


def test_requirement_mapping_exists() -> None:
    assert (ROOT / "docs" / "requirement-mapping.md").is_file()


def test_env_example_has_no_secret_pattern() -> None:
    raw = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "sk-" not in raw
    assert "AGENT_LLM_MODE" in raw


def test_demo_scenario_count_is_eight() -> None:
    assert len(ALL_SCENARIOS) == 8


def test_mock_eval_config_disables_openai() -> None:
    cfg = mock_eval_config()
    assert cfg.agent_llm_mode == "mock"
    assert cfg.openai_api_key is None


@pytest.mark.parametrize(
    "path",
    [
        "README.md",
        "docs/requirement-mapping.md",
        "docs/architecture.md",
        "docs/failure-handling.md",
    ],
)
def test_key_docs_exist(path: str) -> None:
    assert (ROOT / path).is_file()


def test_run_all_scenarios_passes_under_mock() -> None:
    """Evaluation harness stays green without OpenAI."""
    results = run_all_scenarios()
    assert len(results) == 8
    assert all(r.passed_basic_checks for r in results)


def test_config_default_is_mock_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without env vars and without loading a local .env file, OpenAI stays off."""
    monkeypatch.setattr("task_agent.config.load_config_env", lambda *_a, **_k: None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AGENT_LLM_MODE", raising=False)
    cfg = Config.from_env()
    assert cfg.use_openai is False
