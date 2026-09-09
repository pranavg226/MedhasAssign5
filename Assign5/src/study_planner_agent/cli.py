from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid

from dotenv import load_dotenv

from .agent import StudyPlannerAgent, demo_governance
from .config import AgentConfig
from .data_store import DataStore
from .spend import estimate_cost
from .tools import project_grade, search_materials


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Governed study-planning Claude agent")
    parser.add_argument("--session", default=None, help="Session ID to resume")
    parser.add_argument("--user", default=None, help="Approved user ID")
    parser.add_argument("--prompt", help="Send one prompt and exit")
    parser.add_argument("--demo", action="store_true", help="Run offline assignment demonstration")
    return parser


def run_demo() -> None:
    store = DataStore()
    courses = store.load_courses()
    search = search_materials(courses, "trees", "CS201")
    grade = project_grade(courses, "CS201", {"Project": 90, "Final Exam": 85})
    config = AgentConfig()
    print(json.dumps({
        "tool_invocations": [
            {"tool": "search_course_materials", "result": search},
            {"tool": "project_course_grade", "result": grade},
        ],
        "session": {
            "session_id": "demo-session",
            "persistence": "runtime/session-demo-session.json",
        },
        "governance_demo": demo_governance(config),
        "spend_demo": {
            "input_tokens": 800,
            "output_tokens": 400,
            "estimated_cost_usd": round(estimate_cost(config.model, 800, 400), 6),
            "session_budget_usd": config.session_budget_usd,
        },
    }, indent=2))


async def run_agent(args: argparse.Namespace) -> None:
    config = AgentConfig()
    agent = StudyPlannerAgent(config)
    session_id = args.session or str(uuid.uuid4())
    if args.prompt:
        print(await agent.ask(session_id, args.prompt, args.user))
        print(f"session_id={session_id}")
        return
    print(f"session_id={session_id}")
    print("Study Planner ready. Type 'exit' to quit.")
    while True:
        question = input("you> ").strip()
        if question.lower() in {"exit", "quit"}:
            return
        if question:
            print(f"agent> {await agent.ask(session_id, question, args.user)}")


def main() -> None:
    load_dotenv(override=True)
    args = build_parser().parse_args()
    try:
        if args.demo:
            run_demo()
        else:
            asyncio.run(run_agent(args))
    except (ValueError, PermissionError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()