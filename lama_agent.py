import re

import ollama

from db import get_connection
from schema import AGENT_SCHEMA, init_database

MODEL = "qwen2.5"  # must match `ollama list` (e.g. qwen2.5:latest)


def clean_sql(sql: str) -> str:
    sql = re.sub(r"```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
    sql = sql.replace("```", "")
    return sql.strip().rstrip(";")


def is_read_only_sql(sql: str) -> bool:
    normalized = re.sub(r"\s+", " ", sql.strip().upper())
    if not normalized.startswith("SELECT"):
        return False
    forbidden = ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "ATTACH", "DETACH")
    return not any(word in normalized for word in forbidden)


def generate_sql(question: str, error_hint: str | None = None) -> str:
    extra = ""
    if error_hint:
        extra = f"\nPrevious SQL failed with: {error_hint}\nReturn corrected SQL only.\n"

    prompt = f"""
You are a SQL expert for SQLite.

Convert the question into one SELECT query using only the tables below.

RULES:
- Return ONLY SQL (no markdown, no explanation)
- SELECT queries only
- Use only tables and columns from the schema
- For mood or food over time, use mood_logs or food_logs
- For steps, sleep, heart rate by day, use wearable_daily
- For "today", filter with date(logged_at) = date('now') or date = date('now')
- To compare mood and food on the same day, JOIN on date(logged_at) = date(food_logs.logged_at)
{extra}
Schema:
{AGENT_SCHEMA}

Question:
{question}
"""

    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response["message"]["content"].strip()


def run_sql(sql: str):
    if not is_read_only_sql(sql):
        raise ValueError("Only read-only SELECT queries are allowed.")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        columns = [d[0] for d in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        return columns, rows
    finally:
        conn.close()


def ask(question: str, max_retries: int = 1) -> dict:
    """
    Returns {"question", "sql", "columns", "rows", "error"} for UI or CLI.
    """
    init_database(seed_wearable=False)

    sql = clean_sql(generate_sql(question))
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            columns, rows = run_sql(sql)
            return {
                "question": question,
                "sql": sql,
                "columns": columns,
                "rows": rows,
                "error": None,
            }
        except Exception as e:
            last_error = str(e)
            if attempt >= max_retries:
                break
            sql = clean_sql(generate_sql(question, error_hint=last_error))

    return {
        "question": question,
        "sql": sql,
        "columns": [],
        "rows": [],
        "error": last_error,
    }


def ask_cli(question: str, max_retries: int = 1):
    init_database()
    print("\nQuestion:", question)
    result = ask(question, max_retries=max_retries)
    print("\nGenerated SQL:\n", result["sql"])
    if result["error"]:
        print("SQL Error:", result["error"])
        return None
    print("\nResults:")
    for row in result["rows"]:
        print(row)
    return result["rows"]


if __name__ == "__main__":
    while True:
        q = input("\nAsk your health data (empty to quit): ").strip()
        if not q:
            break
        ask_cli(q)
