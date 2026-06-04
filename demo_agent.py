"""
Fallback agent when Ollama is not available (e.g. Streamlit Community Cloud).
Uses tools directly — no LLM orchestration.
"""

import json

from tools import query_database, search_health_knowledge, today_summary


def _answer_from_chunks(chunks: list[dict]) -> str:
    if not chunks:
        return (
            "No knowledge chunks found. Add PDFs under knowledge/pdfs/ "
            "and run ingest_knowledge.py on a machine with Chroma installed."
        )
    parts = [c["text"][:400] for c in chunks[:3]]
    joined = " ".join(parts)
    return (
        "From the health knowledge library (general information, not medical advice):\n\n"
        + joined
        + "\n\nAsk a doctor for personal medical decisions."
    )


def run_demo(question: str) -> dict:
    q = question.lower().strip()
    steps = []

    knowledge_words = (
        "caffeine", "cortisol", "hormone", "nutrition", "protein", "sleep",
        "carb", "fat", "sugar", "meal", "eat", "diet", "stress", "energy",
    )
    data_words = ("my", "i ", "today", "logged", "average", "count", "how many")

    try:
        if any(w in q for w in knowledge_words) and not any(
            w in q for w in ("my log", "i logged", "did i eat", "my mood")
        ):
            r = search_health_knowledge(question)
            steps.append(
                {
                    "tool": "search_health_knowledge",
                    "args": {"query": question},
                    "result": r,
                    "error": None,
                }
            )
            return {
                "question": question,
                "answer": _answer_from_chunks(r.get("chunks") or []),
                "steps": steps,
                "messages": None,
                "error": None,
                "mode": "demo",
            }

        if "eat" in q or "food" in q or "meal" in q or "nutrition log" in q:
            r = query_database(
                """
                SELECT logged_at, meal_type, calories, caffeine_mg, description
                FROM food_logs
                WHERE date(logged_at) = date('now')
                ORDER BY logged_at DESC
                """
            )
            steps.append(
                {
                    "tool": "query_database",
                    "args": {"sql": "food_logs today"},
                    "result": r,
                    "error": None,
                }
            )
            if not r["rows"]:
                answer = "No food logged today in this demo diary. Use Log nutrition to add a meal."
            else:
                lines = [str(row) for row in r["rows"]]
                answer = "Today's food logs:\n" + "\n".join(lines)
            return {
                "question": question,
                "answer": answer,
                "steps": steps,
                "messages": None,
                "error": None,
                "mode": "demo",
            }

        if "mood" in q:
            r = query_database(
                """
                SELECT AVG(mood) AS avg_mood, AVG(energy) AS avg_energy, AVG(stress) AS avg_stress
                FROM mood_logs
                """
            )
            steps.append(
                {
                    "tool": "query_database",
                    "args": {"sql": "mood averages"},
                    "result": r,
                    "error": None,
                }
            )
            row = r["rows"][0] if r["rows"] else (None, None, None)
            answer = f"Mood logs — average mood: {row[0]}, energy: {row[1]}, stress: {row[2]}."
            return {
                "question": question,
                "answer": answer,
                "steps": steps,
                "messages": None,
                "error": None,
                "mode": "demo",
            }

        if "step" in q or "sleep" in q or "wearable" in q or "heart" in q:
            r = query_database(
                """
                SELECT date, steps, sleep_hours, hr_avg, hrv_avg
                FROM wearable_daily
                ORDER BY date DESC
                LIMIT 7
                """
            )
            steps.append(
                {
                    "tool": "query_database",
                    "args": {"sql": "wearable last 7 days"},
                    "result": r,
                    "error": None,
                }
            )
            answer = "Recent demo wearable days:\n" + "\n".join(str(x) for x in r["rows"][:5])
            return {
                "question": question,
                "answer": answer,
                "steps": steps,
                "messages": None,
                "error": None,
                "mode": "demo",
            }

        summary = today_summary()
        steps.append(
            {"tool": "today_summary", "args": {}, "result": summary, "error": None}
        )

        r = search_health_knowledge(question)
        steps.append(
            {
                "tool": "search_health_knowledge",
                "args": {"query": question},
                "result": r,
                "error": None,
            }
        )

        answer = (
            f"Demo mode (no Ollama on this server). Today: {json.dumps(summary)}. "
            f"Knowledge: {_answer_from_chunks(r.get('chunks') or [])[:800]}"
        )
        return {
            "question": question,
            "answer": answer,
            "steps": steps,
            "messages": None,
            "error": None,
            "mode": "demo",
        }

    except Exception as e:
        return {
            "question": question,
            "answer": None,
            "steps": steps,
            "messages": None,
            "error": str(e),
            "mode": "demo",
        }
