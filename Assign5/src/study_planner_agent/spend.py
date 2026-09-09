from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .models import SessionState, Usage

MODEL_PRICES_PER_MILLION: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-5": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}


class SpendLimitError(RuntimeError):
    pass


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    input_price, output_price = MODEL_PRICES_PER_MILLION.get(model, (3.0, 15.0))
    return (input_tokens * input_price + output_tokens * output_price) / 1_000_000


def usage_from_result(result: Any, model: str) -> Usage:
    raw: dict[str, Any] = getattr(result, "usage", None) or {}
    input_tokens = int(raw.get("input_tokens", 0))
    output_tokens = int(raw.get("output_tokens", 0))
    usage = Usage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_input_tokens=int(raw.get("cache_read_input_tokens", 0)),
        cache_creation_input_tokens=int(raw.get("cache_creation_input_tokens", 0)),
    )
    usage.estimated_cost_usd = estimate_cost(model, input_tokens, output_tokens)
    return usage


def enforce_run_limit(usage: Usage, max_tokens: int) -> None:
    if usage.total_tokens > max_tokens:
        raise SpendLimitError(f"Run token limit exceeded: {usage.total_tokens} > {max_tokens}")


def enforce_session_limit(session: SessionState, additional: Usage, budget_usd: float) -> None:
    projected = session.usage.estimated_cost_usd + additional.estimated_cost_usd
    if projected > budget_usd:
        raise SpendLimitError(f"Session budget exceeded: ${projected:.6f} > ${budget_usd:.6f}")
    session.usage.input_tokens += additional.input_tokens
    session.usage.output_tokens += additional.output_tokens
    session.usage.cache_read_input_tokens += additional.cache_read_input_tokens
    session.usage.cache_creation_input_tokens += additional.cache_creation_input_tokens
    session.usage.estimated_cost_usd = projected


def usage_dict(usage: Usage) -> dict[str, Any]:
    return asdict(usage) | {"total_tokens": usage.total_tokens}