import re

import ollama

from db import get_connection

MODEL = "qwen2.5"  # must match `ollama list` (e.g. qwen2.5:latest)

SCHEMA = """
Table: health_logs

Columns:
timestamp, heart_rate, hrv, sleep_hours, steps,
calories_burned, mood, energy, stress,
calories_intake, caffeine_mg, meal_type
"""


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

Convert the question into one SELECT query on table health_logs.

RULES:
- Return ONLY the SQL statement (no markdown, no explanation)
- Use only these columns: timestamp, heart_rate, hrv, sleep_hours, steps,
  calories_burned, mood, energy, stress, calories_intake, caffeine_mg, meal_type
- SELECT queries only
{extra}
Schema:
{SCHEMA}

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
        return cursor.fetchall()
    finally:
        conn.close()


def ask(question: str, max_retries: int = 1):
    print("\nQuestion:", question)

    sql = clean_sql(generate_sql(question))
    print("\nGenerated SQL:\n", sql)

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            results = run_sql(sql)
            print("\nResults:")
            for row in results:
                print(row)
            return results
        except Exception as e:
            last_error = str(e)
            print("SQL Error:", e)
            if attempt >= max_retries:
                break
            sql = clean_sql(generate_sql(question, error_hint=last_error))
            print("\nRetry SQL:\n", sql)

    return None


if __name__ == "__main__":
    while True:
        q = input("\nAsk your health data (empty to quit): ").strip()
        if not q:
            break
        ask(q)
