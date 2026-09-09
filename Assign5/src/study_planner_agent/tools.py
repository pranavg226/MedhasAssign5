from __future__ import annotations

from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from .data_store import DataStore
from .models import Course


def search_materials(
    courses: list[Course], query: str, course_code: str | None = None
) -> dict[str, Any]:
    normalized_query = query.strip().lower()
    if not normalized_query:
        raise ValueError("query must not be empty")
    matches: list[dict[str, str]] = []
    for course in courses:
        if course_code and course.code.upper() != course_code.upper():
            continue
        for material in course.materials:
            if normalized_query in material.lower():
                matches.append({"course": course.code, "title": course.title, "material": material})
    return {"query": query, "matches": matches, "count": len(matches)}


def project_grade(
    courses: list[Course], course_code: str, projected_scores: dict[str, float] | None = None
) -> dict[str, Any]:
    course = next((item for item in courses if item.code.upper() == course_code.upper()), None)
    if course is None:
        raise ValueError(f"Unknown course: {course_code}")
    projected_scores = projected_scores or {}
    weighted_points = 0.0
    known_weight = 0.0
    details: list[dict[str, Any]] = []
    for assignment in course.assignments:
        score = projected_scores.get(assignment.name, assignment.score)
        if score is not None:
            if not 0 <= score <= 100:
                raise ValueError(f"Score for {assignment.name} must be between 0 and 100")
            weighted_points += score * assignment.weight / 100
            known_weight += assignment.weight
        details.append({"name": assignment.name, "weight": assignment.weight, "score": score})
    remaining_weight = 100 - known_weight
    current_grade = weighted_points / known_weight * 100 if known_weight else 0.0
    return {
        "course": course.code,
        "title": course.title,
        "weighted_points_earned": round(weighted_points, 2),
        "current_grade_on_completed_work": round(current_grade, 2),
        "known_weight": round(known_weight, 2),
        "remaining_weight": round(remaining_weight, 2),
        "details": details,
    }


def build_tools(data_store: DataStore):
    courses = data_store.load_courses()

    @tool(
        "search_course_materials",
        "Search the local course catalog for study materials matching a topic.",
        {"query": str, "course_code": str},
    )
    async def search_course_materials(args: dict[str, Any]) -> dict[str, Any]:
        result = search_materials(courses, args["query"], args.get("course_code"))
        return {"content": [{"type": "text", "text": _as_text(result)}]}

    @tool(
        "project_course_grade",
        "Calculate a weighted course grade from recorded or projected scores.",
        {"course_code": str, "projected_scores": dict},
    )
    async def project_course_grade(args: dict[str, Any]) -> dict[str, Any]:
        result = project_grade(courses, args["course_code"], args.get("projected_scores"))
        return {"content": [{"type": "text", "text": _as_text(result)}]}

    server = create_sdk_mcp_server(
        name="study_planner",
        version="1.0.0",
        tools=[search_course_materials, project_course_grade],
    )
    return server


def _as_text(value: dict[str, Any]) -> str:
    import json

    return json.dumps(value, indent=2, sort_keys=True)