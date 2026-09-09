from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from study_planner_agent.agent import StudyPlannerAgent
from study_planner_agent.config import AgentConfig
from study_planner_agent.data_store import DataStore
from study_planner_agent.tools import project_grade, search_materials

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", override=True)

st.set_page_config(
    page_title="Study Planner",
    page_icon="SP",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    :root { --ink: #17221d; --muted: #66736b; --mint: #b9e8cc; --lime: #d8f36b; --cream: #f6f3e9; --orange: #f28c52; }
    .stApp { background: var(--cream); color: var(--ink); }
    [data-testid="stSidebar"] { background: #20342b; }
    [data-testid="stSidebar"] * { color: #edf6e9; }
    h1, h2, h3 { font-family: 'Space Grotesk', sans-serif; letter-spacing: 0; color: var(--ink); }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: var(--lime); }
    p, label, button, input, textarea, select { font-family: 'DM Sans', sans-serif; }
    .eyebrow { color: #6e7d72; font: 700 0.75rem 'DM Sans', sans-serif; letter-spacing: .08em; text-transform: uppercase; }
    .hero { padding: 1.2rem 0 1rem; border-bottom: 1px solid #d9ded4; margin-bottom: 1.5rem; }
    .hero h1 { font-size: clamp(2.2rem, 5vw, 4.8rem); line-height: .98; margin: .35rem 0 .7rem; max-width: 760px; }
    .hero p { color: var(--muted); font-size: 1.05rem; max-width: 680px; }
    .metric { background: white; border: 1px solid #e0e5dc; border-radius: 8px; padding: 1rem; min-height: 100px; }
    .metric-label { color: var(--muted); font-size: .78rem; text-transform: uppercase; letter-spacing: .06em; }
    .metric-value { color: var(--ink); font: 700 1.65rem 'Space Grotesk', sans-serif; margin-top: .35rem; }
    .course-card { background: white; border-left: 5px solid var(--orange); border-radius: 8px; padding: 1.1rem 1.2rem; margin-bottom: .7rem; }
    .course-code { color: #b65425; font-weight: 700; letter-spacing: .08em; font-size: .78rem; }
    .course-title { color: var(--ink); font: 600 1.15rem 'Space Grotesk', sans-serif; margin: .2rem 0 .35rem; }
    .course-description { color: var(--muted); font-size: .92rem; }
    .stButton > button { border-radius: 6px; border: 1px solid #20342b; background: var(--lime); color: #17221d; font-weight: 700; }
    [data-testid="stSidebar"] .stButton > button,
    [data-testid="stSidebar"] .stButton > button * { color: #17221d !important; background: var(--lime) !important; }
    [data-testid="stSidebar"] input { color: #17221d !important; background: #ffffff !important; }
    [data-testid="stChatInput"] textarea { color: #17221d !important; background: #ffffff !important; caret-color: #17221d !important; }
    [data-testid="stChatInput"] textarea::placeholder { color: #66736b !important; opacity: 1; }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] strong,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] code { color: #17221d !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_store() -> DataStore:
    return DataStore(root=ROOT / os.getenv("STUDY_AGENT_DATA_DIR", "runtime"), catalog_path=ROOT / "data/courses.json")


def initialize_state() -> None:
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"streamlit-{uuid.uuid4().hex[:8]}"
    if "messages" not in st.session_state:
        st.session_state.messages = []


def render_sidebar(config: AgentConfig, store: DataStore) -> None:
    with st.sidebar:
        st.markdown("# Study\nPlanner")
        st.caption("A governed academic co-pilot")
        st.divider()
        st.markdown("### Session")
        session_id = st.text_input("Session ID", value=st.session_state.session_id, label_visibility="collapsed")
        if session_id != st.session_state.session_id:
            st.session_state.session_id = session_id.strip() or st.session_state.session_id
            st.session_state.messages = []
        st.caption(f"User: {config.user_id}")
        st.caption(f"Model: {config.model}")
        st.divider()
        st.markdown("### Guardrails")
        st.write("Approved tools")
        st.code("Course search\nGrade projection", language=None)
        st.write("Blocked tools")
        st.code("Bash · Write · Edit\nWebFetch · WebSearch", language=None)
        st.divider()
        st.markdown("### Budget")
        st.metric("Session cap", f"${config.session_budget_usd:.2f}")
        session = store.load_session(st.session_state.session_id, config.user_id)
        st.metric("Estimated used", f"${session.usage.estimated_cost_usd:.4f}")
        if st.button("Start fresh session", use_container_width=True):
            st.session_state.session_id = f"streamlit-{uuid.uuid4().hex[:8]}"
            st.session_state.messages = []
            st.rerun()


def render_chat(agent: StudyPlannerAgent) -> None:
    st.markdown('<div class="eyebrow">Guided learning workspace</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero"><h1>Make your next study hour count.</h1><p>Ask about course material, project your grade, or build a focused study plan grounded in your catalog.</p></div>', unsafe_allow_html=True)
    if not st.session_state.messages:
        left, right = st.columns(2)
        with left:
            st.markdown('<div class="metric"><div class="metric-label">Try asking</div><div class="metric-value">"Explain trees in CS201"</div></div>', unsafe_allow_html=True)
        with right:
            st.markdown('<div class="metric"><div class="metric-label">Or ask</div><div class="metric-value">"What score do I need on the final?"</div></div>', unsafe_allow_html=True)
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    question = st.chat_input("Ask your study planner...")
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Checking your course context..."):
                try:
                    answer = asyncio.run(agent.ask(st.session_state.session_id, question))
                except Exception as error:
                    answer = f"I could not complete that request: {error}"
                st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})


def render_materials(courses) -> None:
    st.subheader("Course materials")
    course_code = st.selectbox("Course", [course.code for course in courses])
    query = st.text_input("Search topics", placeholder="trees, regression, probability")
    course = next(course for course in courses if course.code == course_code)
    st.markdown(f'<div class="course-card"><div class="course-code">{course.code}</div><div class="course-title">{course.title}</div><div class="course-description">{course.description}</div></div>', unsafe_allow_html=True)
    if query.strip():
        result = search_materials(courses, query, course_code)
        if result["matches"]:
            for match in result["matches"]:
                st.success(match["material"])
        else:
            st.info("No matching material found in this course.")
    else:
        for material in course.materials:
            st.write(f"- {material}")


def render_grade_projection(courses) -> None:
    st.subheader("Grade projection")
    course_code = st.selectbox("Course", [course.code for course in courses], key="grade_course")
    course = next(course for course in courses if course.code == course_code)
    scores: dict[str, float] = {}
    columns = st.columns(2)
    for index, assignment in enumerate(course.assignments):
        with columns[index % 2]:
            current = "" if assignment.score is None else str(assignment.score)
            value = st.text_input(f"{assignment.name} ({assignment.weight:g}%)", value=current, key=f"score_{course_code}_{assignment.name}")
            if value.strip():
                try:
                    scores[assignment.name] = float(value)
                except ValueError:
                    st.error(f"Enter a number for {assignment.name}.")
    if st.button("Calculate projection", type="primary"):
        try:
            result = project_grade(courses, course_code, scores)
            first, second, third = st.columns(3)
            first.metric("Weighted grade", f"{result['weighted_points_earned']:.1f}%")
            second.metric("Completed weight", f"{result['known_weight']:.0f}%")
            third.metric("Remaining weight", f"{result['remaining_weight']:.0f}%")
            st.progress(min(result["weighted_points_earned"] / 100, 1.0))
        except ValueError as error:
            st.error(str(error))


def main() -> None:
    initialize_state()
    config = AgentConfig()
    store = get_store()
    render_sidebar(config, store)
    courses = store.load_courses()
    chat_tab, materials_tab, grades_tab = st.tabs(["Planner chat", "Materials", "Grade projection"])
    with chat_tab:
        render_chat(StudyPlannerAgent(config, store))
    with materials_tab:
        render_materials(courses)
    with grades_tab:
        render_grade_projection(courses)


if __name__ == "__main__":
    main()