from __future__ import annotations

import uuid
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)

from .config import AgentConfig
from .data_store import DataStore
from .governance import build_governance_hooks, tool_decision, validate_model, validate_user
from .models import SessionState
from .skill import SKILL_INSTRUCTIONS, build_study_request
from .spend import enforce_run_limit, enforce_session_limit, usage_dict, usage_from_result
from .tools import build_tools


class StudyPlannerAgent:
    def __init__(self, config: AgentConfig | None = None, data_store: DataStore | None = None):
        self.config = config or AgentConfig()
        self.config.validate()
        self.data_store = data_store or DataStore(self.config.data_dir)

    async def ask(self, session_id: str, question: str, user_id: str | None = None) -> str:
        checked_user = user_id or self.config.user_id
        self.config.validate_api_key()
        validate_model(self.config)
        validate_user(self.config, checked_user)
        session = self.data_store.load_session(session_id, checked_user)
        tool_events: list[dict[str, Any]] = []
        prompt = build_study_request(question, self._recent_context(session))
        options = ClaudeAgentOptions(
            model=self.config.model,
            max_turns=self.config.max_turns,
            max_budget_usd=self.config.session_budget_usd - session.usage.estimated_cost_usd,
            system_prompt=SKILL_INSTRUCTIONS,
            mcp_servers={"study_planner": build_tools(self.data_store)},
            allowed_tools=list(self.config.approved_tools),
            disallowed_tools=["Bash", "Write", "Edit", "WebFetch", "WebSearch"],
            hooks=build_governance_hooks(self.config, tool_events),
            resume=session.sdk_session_id,
        )
        response_text = ""
        result_message: ResultMessage | None = None
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    response_text += "".join(
                        block.text for block in message.content if isinstance(block, TextBlock)
                    )
                if isinstance(message, ResultMessage):
                    result_message = message
        if result_message is None:
            raise RuntimeError("The SDK did not return a result message")
        usage = usage_from_result(result_message, self.config.model)
        enforce_run_limit(usage, self.config.max_tokens)
        if result_message.total_cost_usd is not None:
            usage.estimated_cost_usd = result_message.total_cost_usd
        enforce_session_limit(session, usage, self.config.session_budget_usd)
        session.sdk_session_id = result_message.session_id
        session.tool_events.extend(tool_events)
        session.add_turn("user", question)
        session.add_turn("assistant", response_text)
        self.data_store.save_session(session)
        self.data_store.append_metric(
            {
                "run_id": str(uuid.uuid4()),
                "session_id": session_id,
                "model": self.config.model,
                "usage": usage_dict(usage),
                "session_usage": usage_dict(session.usage),
                "blocked_actions": result_message.permission_denials or [],
                "sdk_total_cost_usd": result_message.total_cost_usd,
            }
        )
        return response_text.strip()

    @staticmethod
    def _recent_context(session: SessionState) -> str:
        return "\n".join(f"{turn['role']}: {turn['content']}" for turn in session.turns[-4:])


def demo_governance(config: AgentConfig | None = None) -> dict[str, Any]:
    active = config or AgentConfig()
    blocked = tool_decision("Bash", active)
    return {"blocked_tool": "Bash", "decision": blocked}