from __future__ import annotations

SKILL_NAME = "study_planning_skill"
SKILL_INSTRUCTIONS = """You are a careful study-planning assistant.

Ground answers in the course catalog and use the available course tools for factual
material searches and grade calculations. Never invent course content or scores.
When creating a plan, identify the course, target, available time, and weak topics.
Break work into measurable sessions, recommend retrieval practice, and state any
assumptions. Grade projections are estimates, not guarantees.
"""


def build_study_request(question: str, session_context: str = "") -> str:
    context = f"\nExisting session context:\n{session_context}\n" if session_context else ""
    return f"{SKILL_INSTRUCTIONS}\n{context}\nStudent request:\n{question}"


def export_skill() -> dict[str, str]:
    return {"name": SKILL_NAME, "instructions": SKILL_INSTRUCTIONS}