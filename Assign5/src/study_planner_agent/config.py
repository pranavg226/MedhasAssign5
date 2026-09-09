from __future__ import annotations

import os
from dataclasses import dataclass, field

DEFAULT_MODEL = "claude-sonnet-4-5"
APPROVED_MODELS = (DEFAULT_MODEL, "claude-haiku-4-5")
APPROVED_TOOL_NAMES = (
    "mcp__study_planner__search_course_materials",
    "mcp__study_planner__project_course_grade",
)
PLACEHOLDER_KEYS = {"", "replace-me", "replace-with-a-new-key", "your-key"}


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class AgentConfig:
    model: str = field(default_factory=lambda: os.getenv("STUDY_AGENT_MODEL", DEFAULT_MODEL))
    max_turns: int = field(default_factory=lambda: _int_env("STUDY_AGENT_MAX_TURNS", 6))
    max_tokens: int = field(default_factory=lambda: _int_env("STUDY_AGENT_MAX_TOKENS", 2000))
    session_budget_usd: float = field(
        default_factory=lambda: _float_env("STUDY_AGENT_SESSION_BUDGET_USD", 0.25)
    )
    user_id: str = field(default_factory=lambda: os.getenv("STUDY_AGENT_USER_ID", "student-demo"))
    data_dir: str = field(default_factory=lambda: os.getenv("STUDY_AGENT_DATA_DIR", "runtime"))
    approved_models: tuple[str, ...] = APPROVED_MODELS
    approved_tools: tuple[str, ...] = APPROVED_TOOL_NAMES

    def validate(self) -> None:
        if self.model not in self.approved_models:
            raise ValueError(f"Model is not approved: {self.model}")
        if self.max_turns < 1 or self.max_tokens < 1:
            raise ValueError("max_turns and max_tokens must be positive")
        if self.session_budget_usd <= 0:
            raise ValueError("session_budget_usd must be positive")

    @staticmethod
    def validate_api_key() -> None:
        key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if key in PLACEHOLDER_KEYS:
            raise ValueError(
                "ANTHROPIC_API_KEY is missing or still a placeholder. "
                "Add a newly generated key to .env and restart the app."
            )