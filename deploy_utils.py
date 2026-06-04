"""Hosting helpers: detect cloud, Ollama, seed public demo data."""

import os
from datetime import datetime, timedelta

from db import get_connection


def is_streamlit_cloud() -> bool:
    return os.environ.get("STREAMLIT_RUNTIME_ENV") == "cloud"


def ollama_is_available() -> bool:
    try:
        import ollama

        ollama.list()
        return True
    except Exception:
        return False


def seed_demo_logs_if_empty() -> None:
    """Sample mood/food rows so public demo charts are not empty."""
    conn = get_connection()
    try:
        mood_n = conn.execute("SELECT COUNT(*) FROM mood_logs").fetchone()[0]
        food_n = conn.execute("SELECT COUNT(*) FROM food_logs").fetchone()[0]
        if mood_n > 0 and food_n > 0:
            return

        now = datetime.now()
        if mood_n == 0:
            moods = [
                (6, 5, 7, "Tired morning"),
                (7, 6, 5, None),
                (8, 7, 4, "Good walk"),
                (5, 4, 8, "Work stress"),
                (7, 6, 5, None),
            ]
            for i, (mood, energy, stress, note) in enumerate(moods):
                ts = (now - timedelta(days=i, hours=2)).isoformat(timespec="seconds")
                conn.execute(
                    """
                    INSERT INTO mood_logs (logged_at, mood, energy, stress, note)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (ts, mood, energy, stress, note),
                )

        if food_n == 0:
            meals = [
                ("breakfast", 420, 80, "Oatmeal, coffee"),
                ("lunch", 650, 0, "Salad, chicken"),
                ("dinner", 720, 0, "Fish, rice, vegetables"),
                ("snack", 180, 40, "Yogurt"),
            ]
            for i, (meal, cal, caf, desc) in enumerate(meals):
                ts = (now - timedelta(days=i % 3, hours=8 + i)).isoformat(timespec="seconds")
                conn.execute(
                    """
                    INSERT INTO food_logs (logged_at, meal_type, calories, caffeine_mg, description)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (ts, meal, cal, caf, desc),
                )
        conn.commit()
    finally:
        conn.close()


def ensure_knowledge_indexed() -> None:
    try:
        from rag import ingest

        ingest()
    except Exception:
        pass
