"""Application configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def load_config_env(dotenv_path: str | Path | None = None) -> None:
    """Load `.env` if present; does not override existing process env."""
    load_dotenv(dotenv_path=dotenv_path, override=False)


@dataclass(frozen=True)
class Config:
    """Runtime configuration for LLM mode and OpenAI settings."""

    agent_llm_mode: str
    openai_api_key: str | None
    openai_model: str

    @classmethod
    def from_env(cls) -> Config:
        load_config_env()
        mode = os.getenv("AGENT_LLM_MODE", "mock").strip().lower()
        key = os.getenv("OPENAI_API_KEY")
        key = key.strip() if key else None
        if key == "":
            key = None
        model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
        return cls(agent_llm_mode=mode, openai_api_key=key, openai_model=model)

    @property
    def use_openai(self) -> bool:
        """True when OpenAI-backed features are configured (explicit openai mode + key)."""
        return self.agent_llm_mode == "openai" and bool(self.openai_api_key)
