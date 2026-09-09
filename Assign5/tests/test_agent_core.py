from types import SimpleNamespace

import pytest

from study_planner_agent.config import AgentConfig
from study_planner_agent.data_store import DataStore
from study_planner_agent.governance import GovernanceError, validate_model, validate_user
from study_planner_agent.models import SessionState, Usage
from study_planner_agent.skill import SKILL_NAME, export_skill
from study_planner_agent.spend import SpendLimitError, enforce_run_limit, enforce_session_limit
from study_planner_agent.tools import project_grade, search_materials


@pytest.fixture
def courses():
    return DataStore().load_courses()


def test_search_tool_returns_matching_material(courses):
    result = search_materials(courses, "trees")
    assert result["count"] == 1
    assert result["matches"][0]["course"] == "CS201"


def test_grade_tool_projects_all_assignments(courses):
    result = project_grade(courses, "CS201", {"Project": 90, "Final Exam": 85})
    assert result["weighted_points_earned"] == 85
    assert result["remaining_weight"] == 0


def test_reusable_skill_is_exported():
    skill = export_skill()
    assert skill["name"] == SKILL_NAME
    assert "course catalog" in skill["instructions"]


def test_session_round_trip(tmp_path):
    store = DataStore(tmp_path)
    session = SessionState(session_id="abc", user_id="student")
    session.add_turn("user", "Help with trees")
    session.usage.output_tokens = 12
    store.save_session(session)
    restored = store.load_session("abc", "student")
    assert restored.turns == [{"role": "user", "content": "Help with trees"}]
    assert restored.usage.output_tokens == 12


def test_session_rejects_different_user(tmp_path):
    store = DataStore(tmp_path)
    store.save_session(SessionState(session_id="abc", user_id="owner"))
    with pytest.raises(PermissionError):
        store.load_session("abc", "other")


def test_governance_rejects_model_and_user():
    config = AgentConfig(user_id="student")
    with pytest.raises(GovernanceError):
        validate_model(AgentConfig(model="unapproved-model"))
    with pytest.raises(GovernanceError):
        validate_user(config, "other")


def test_run_and_session_spend_limits():
    with pytest.raises(SpendLimitError):
        enforce_run_limit(Usage(input_tokens=10, output_tokens=5), max_tokens=10)
    session = SessionState(session_id="abc", user_id="student")
    usage = Usage(estimated_cost_usd=0.30)
    with pytest.raises(SpendLimitError):
        enforce_session_limit(session, usage, budget_usd=0.25)


def test_usage_limit_accepts_under_budget():
    session = SessionState(session_id="abc", user_id="student")
    usage = Usage(input_tokens=10, output_tokens=5, estimated_cost_usd=0.02)
    enforce_session_limit(session, usage, budget_usd=0.25)
    assert session.usage.total_tokens == 15


def test_usage_normalization_shape():
    from study_planner_agent.spend import usage_from_result

    result = SimpleNamespace(usage={"input_tokens": 20, "output_tokens": 10})
    usage = usage_from_result(result, "claude-haiku-4-5")
    assert usage.total_tokens == 30
    assert usage.estimated_cost_usd > 0