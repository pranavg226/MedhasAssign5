from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Assignment:
    name: str
    weight: float
    score: float | None
    topic: str


@dataclass(frozen=True)
class Course:
    code: str
    title: str
    description: str
    materials: tuple[str, ...]
    assignments: tuple[Assignment, ...]


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    estimated_cost_usd: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class SessionState:
    session_id: str
    user_id: str
    sdk_session_id: str | None = None
    turns: list[dict[str, str]] = field(default_factory=list)
    tool_events: list[dict[str, Any]] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def add_turn(self, role: str, content: str) -> None:
        self.turns.append({"role": role, "content": content})
        self.updated_at = utc_now()

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["usage"] = asdict(self.usage)
        return result

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SessionState":
        usage = Usage(**value.get("usage", {}))
        return cls(
            session_id=value["session_id"],
            user_id=value["user_id"],
            sdk_session_id=value.get("sdk_session_id"),
            turns=value.get("turns", []),
            tool_events=value.get("tool_events", []),
            usage=usage,
            created_at=value.get("created_at", utc_now()),
            updated_at=value.get("updated_at", utc_now()),
        )