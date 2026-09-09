from __future__ import annotations

from typing import Any

from claude_agent_sdk import HookMatcher

from .config import AgentConfig


class GovernanceError(PermissionError):
    pass


def validate_model(config: AgentConfig) -> None:
    if config.model not in config.approved_models:
        raise GovernanceError(f"Blocked model: {config.model}")


def validate_user(config: AgentConfig, user_id: str) -> None:
    if not user_id or user_id != config.user_id:
        raise GovernanceError("User identity check failed")


def tool_decision(tool_name: str, config: AgentConfig) -> dict[str, Any]:
    if tool_name not in config.approved_tools:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Tool is not approved: {tool_name}",
            }
        }
    return {}


def build_governance_hooks(
    config: AgentConfig, tool_events: list[dict[str, Any]] | None = None
) -> dict[str, list[HookMatcher]]:
    async def enforce_tool_allowlist(
        input_data: dict[str, Any], tool_use_id: str | None, context: Any
    ) -> dict[str, Any]:
        del tool_use_id, context
        return tool_decision(input_data.get("tool_name", ""), config)

    async def record_tool_result(
        input_data: dict[str, Any], tool_use_id: str | None, context: Any
    ) -> dict[str, Any]:
        del tool_use_id, context
        if tool_events is not None:
            tool_events.append(
                {
                    "tool_name": input_data.get("tool_name", ""),
                    "tool_input": input_data.get("tool_input", {}),
                    "tool_response": input_data.get("tool_response", {}),
                }
            )
        return {}

    return {
        "PreToolUse": [HookMatcher(matcher=None, hooks=[enforce_tool_allowlist])],
        "PostToolUse": [HookMatcher(matcher=None, hooks=[record_tool_result])],
    }