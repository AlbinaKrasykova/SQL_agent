"""Minimal Streamlit health diary: mood, nutrition, and SQL agent."""

from datetime import datetime

import pandas as pd
import streamlit as st

from db import get_connection
from agent import run as agent_run
from schema import init_database

# ---------------------------------------------------------------------------
# Page config and minimal styling
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Health Diary",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #f7f6f3; }
    h1, h2, h3 {
        font-weight: 500;
        letter-spacing: -0.02em;
        color: #1a1a1a;
    }
    .diary-tagline {
        color: #5c5c5c;
        font-size: 0.95rem;
        margin-top: -0.5rem;
        margin-bottom: 1.5rem;
    }
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e8e6e1;
        padding: 0.75rem 1rem;
        border-radius: 4px;
    }
    .stButton > button {
        background: #1a1a1a;
        color: #f7f6f3;
        border: none;
        border-radius: 4px;
        font-weight: 500;
    }
    .stButton > button:hover {
        background: #333333;
        color: #ffffff;
    }
    section[data-testid="stSidebar"] {
        background-color: #efeee9;
        border-right: 1px solid #e0ddd6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

EXAMPLE_QUESTIONS = [
    "What did I eat today?",
    "What is my average mood?",
    "How does my mood relate to caffeine today?",
    "What were my steps on days I logged low mood?",
]


def ensure_tables():
    init_database(seed_wearable=True, quiet=True)


def insert_mood(mood: int, energy: int, stress: int, note: str | None):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO mood_logs (logged_at, mood, energy, stress, note)
        VALUES (?, ?, ?, ?, ?)
        """,
        (datetime.now().isoformat(timespec="seconds"), mood, energy, stress, note),
    )
    conn.commit()
    conn.close()


def insert_food(
    meal_type: str,
    calories: int | None,
    caffeine_mg: int | None,
    description: str | None,
):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO food_logs (logged_at, meal_type, calories, caffeine_mg, description)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            datetime.now().isoformat(timespec="seconds"),
            meal_type,
            calories,
            caffeine_mg,
            description,
        ),
    )
    conn.commit()
    conn.close()


def load_mood_df(limit: int = 60) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        f"""
        SELECT logged_at, mood, energy, stress, note
        FROM mood_logs
        ORDER BY logged_at DESC
        LIMIT {limit}
        """,
        conn,
    )
    conn.close()
    return df


def load_food_df(limit: int = 30) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        f"""
        SELECT logged_at, meal_type, calories, caffeine_mg, description
        FROM food_logs
        ORDER BY logged_at DESC
        LIMIT {limit}
        """,
        conn,
    )
    conn.close()
    return df


def load_wearable_df(limit: int = 14) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        f"""
        SELECT date, steps, sleep_hours, hr_avg, hrv_avg, calories_burned, source
        FROM wearable_daily
        ORDER BY date DESC
        LIMIT {limit}
        """,
        conn,
    )
    conn.close()
    return df


def render_ask_panel():
    st.subheader("Ask your data")
    st.caption(
        "Agent uses your SQLite logs (SQL tools) and nutrition/hormone PDFs (RAG). "
        "Add PDFs to knowledge/pdfs/ then run: python ingest_knowledge.py"
    )

    if "agent_q" not in st.session_state:
        st.session_state["agent_q"] = ""
    if "agent_messages" not in st.session_state:
        st.session_state["agent_messages"] = None

    cols = st.columns(len(EXAMPLE_QUESTIONS))
    for col, example in zip(cols, EXAMPLE_QUESTIONS):
        with col:
            if st.button(example, width="stretch", key=f"ex_{example[:12]}"):
                st.session_state["agent_q"] = example
                st.rerun()

    question = st.text_input(
        "Question",
        key="agent_q",
        placeholder="e.g. What did I eat today? How does caffeine affect cortisol?",
        label_visibility="collapsed",
    )

    col_run, col_clear = st.columns([1, 1])
    with col_run:
        run = st.button("Ask agent", type="primary")
    with col_clear:
        if st.button("Clear chat"):
            st.session_state["agent_messages"] = None
            st.session_state.pop("last_agent_result", None)
            st.rerun()

    if run and question.strip():
        with st.spinner("Thinking (tools + knowledge)..."):
            result = agent_run(
                question.strip(),
                messages=st.session_state.get("agent_messages"),
            )
        st.session_state["agent_messages"] = result.get("messages")
        st.session_state["last_agent_result"] = result

    result = st.session_state.get("last_agent_result")
    if not result:
        return

    if result.get("error") and not result.get("answer"):
        st.error(result["error"])
        return

    if result.get("answer"):
        st.markdown(result["answer"])

    for step in result.get("steps") or []:
        with st.expander(f"Tool: {step['tool']}", expanded=False):
            if step.get("args"):
                st.json(step["args"])
            if step["tool"] == "query_database" and step.get("result", {}).get("rows"):
                r = step["result"]
                st.code(
                    step["args"].get("sql", ""),
                    language="sql",
                )
                st.dataframe(
                    pd.DataFrame(r["rows"], columns=r.get("columns") or None),
                    width="stretch",
                    hide_index=True,
                )
            elif step["tool"] == "search_health_knowledge":
                for ch in step.get("result", {}).get("chunks") or []:
                    st.caption(ch.get("source", ""))
                    st.write(ch.get("text", "")[:500])
            else:
                st.json(step.get("result", {}))
            if step.get("error"):
                st.error(step["error"])


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


def page_overview():
    st.title("Health Diary")
    st.markdown(
        '<p class="diary-tagline">Mood, nutrition, and demo wearable data in one place.</p>',
        unsafe_allow_html=True,
    )

    render_ask_panel()
    st.divider()

    mood_df = load_mood_df(30)
    food_df = load_food_df(15)
    wearable_df = load_wearable_df(14)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if mood_df.empty:
            st.metric("Latest mood", "—")
        else:
            st.metric("Latest mood", f"{int(mood_df.iloc[0]['mood'])}/10")
    with col2:
        st.metric("Meals logged", len(food_df) if not food_df.empty else 0)
    with col3:
        if wearable_df.empty:
            st.metric("Steps (latest day)", "—")
        else:
            val = wearable_df.iloc[0]["steps"]
            st.metric("Steps (latest day)", int(val) if pd.notna(val) else "—")
    with col4:
        if wearable_df.empty:
            st.metric("Sleep (latest day)", "—")
        else:
            val = wearable_df.iloc[0]["sleep_hours"]
            st.metric("Sleep (latest day)", f"{val}h" if pd.notna(val) else "—")

    st.caption(
        "Wearable rows are demo data until you import Apple Health. "
        "Mood and food come from your Streamlit logs."
    )

    left, right = st.columns(2)
    with left:
        st.subheader("Mood trend")
        if mood_df.empty:
            st.caption("No mood entries yet.")
        else:
            chart_df = mood_df.copy()
            chart_df["logged_at"] = pd.to_datetime(chart_df["logged_at"])
            chart_df = chart_df.sort_values("logged_at")
            st.line_chart(chart_df.set_index("logged_at")[["mood", "energy", "stress"]])
    with right:
        st.subheader("Steps (demo wearable)")
        if wearable_df.empty:
            st.caption("No wearable data.")
        else:
            wdf = wearable_df.copy()
            wdf["date"] = pd.to_datetime(wdf["date"])
            wdf = wdf.sort_values("date")
            st.line_chart(wdf.set_index("date")[["steps"]])

    st.subheader("Recent nutrition")
    if food_df.empty:
        st.caption("No meals logged yet.")
    else:
        st.dataframe(food_df, width="stretch", hide_index=True)


def page_mood():
    st.title("Log mood")
    st.caption("Saved to mood_logs in health.db.")

    with st.form("mood_form", clear_on_submit=True):
        mood = st.slider("Mood", 1, 10, 5)
        energy = st.slider("Energy", 1, 10, 5)
        stress = st.slider("Stress", 1, 10, 5)
        note = st.text_area("Note", placeholder="Optional", height=80)
        save = st.form_submit_button("Save entry")

    if save:
        ensure_tables()
        insert_mood(mood, energy, stress, note.strip() or None)
        st.success("Saved to database.")
        st.rerun()

    st.divider()
    st.subheader("Recent entries")
    df = load_mood_df(20)
    if df.empty:
        st.caption("No entries.")
    else:
        st.dataframe(df, width="stretch", hide_index=True)


def page_nutrition():
    st.title("Log nutrition")
    st.caption("Saved to food_logs in health.db.")

    with st.form("food_form", clear_on_submit=True):
        meal_type = st.selectbox("Meal", ["breakfast", "lunch", "dinner", "snack"])
        calories = st.number_input("Calories", min_value=0, max_value=10000, value=0, step=50)
        caffeine = st.number_input("Caffeine (mg)", min_value=0, max_value=1000, value=0, step=25)
        description = st.text_input("Description", placeholder="What you ate")
        save = st.form_submit_button("Save entry")

    if save:
        ensure_tables()
        insert_food(
            meal_type,
            calories if calories > 0 else None,
            caffeine if caffeine > 0 else None,
            description.strip() or None,
        )
        st.success("Saved to database.")
        st.rerun()

    st.divider()
    st.subheader("Recent entries")
    df = load_food_df(20)
    if df.empty:
        st.caption("No entries.")
    else:
        st.dataframe(df, width="stretch", hide_index=True)


# ---------------------------------------------------------------------------
# App entry
# ---------------------------------------------------------------------------

ensure_tables()

# Sidebar header (above navigation)
st.sidebar.image("assets/health_diary_concept.png", width="stretch")
st.sidebar.markdown("### Health Diary")
st.sidebar.markdown(
    "A quiet place to log mood and meals, review demo wearable data, "
    "and ask questions about your day."
)
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    ["Overview", "Log mood", "Log nutrition"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.caption("Wearable data is demo until Apple Health import.")

if page == "Overview":
    page_overview()
elif page == "Log mood":
    page_mood()
else:
    page_nutrition()
