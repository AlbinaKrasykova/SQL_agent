"""
Single source of truth for database tables and the SQL agent prompt.

Import from here instead of duplicating CREATE TABLE or column lists elsewhere.
"""

from pathlib import Path

from db import DB_NAME, get_connection

# ---------------------------------------------------------------------------
# Table definitions (one place — DDL and agent prompt are derived from this)
# ---------------------------------------------------------------------------

TABLES: dict[str, dict] = {
    "mood_logs": {
        "purpose": "Manual mood check-ins (Streamlit Log mood).",
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "user_id": "INTEGER DEFAULT 1",
            "logged_at": "TEXT NOT NULL",
            "mood": "INTEGER NOT NULL",
            "energy": "INTEGER",
            "stress": "INTEGER",
            "note": "TEXT",
        },
    },
    "food_logs": {
        "purpose": "Manual nutrition logs (Streamlit Log nutrition).",
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "user_id": "INTEGER DEFAULT 1",
            "logged_at": "TEXT NOT NULL",
            "meal_type": "TEXT NOT NULL",
            "calories": "INTEGER",
            "caffeine_mg": "INTEGER",
            "description": "TEXT",
        },
    },
    "wearable_daily": {
        "purpose": "Daily wearable summary (Apple Health import, one row per day).",
        "columns": {
            "user_id": "INTEGER DEFAULT 1",
            "date": "TEXT NOT NULL",
            "steps": "INTEGER",
            "sleep_hours": "REAL",
            "hr_avg": "INTEGER",
            "hrv_avg": "REAL",
            "calories_burned": "INTEGER",
            "source": "TEXT DEFAULT 'manual'",
            "imported_at": "TEXT",
        },
        "primary_key": "(user_id, date)",
    },
}

JOIN_HINTS = """
Join examples:
- Same calendar day: date(mood_logs.logged_at) = wearable_daily.date
- Same calendar day: date(food_logs.logged_at) = wearable_daily.date
"""


def build_ddl() -> str:
    statements = []
    for name, spec in TABLES.items():
        col_defs = ", ".join(f"{col} {dtype}" for col, dtype in spec["columns"].items())
        pk = spec.get("primary_key")
        if pk:
            col_defs += f", PRIMARY KEY {pk}"
        statements.append(f"CREATE TABLE IF NOT EXISTS {name} ({col_defs});")
    return "\n".join(statements)


def build_agent_schema() -> str:
    lines = ["SQLite database tables:", ""]
    for name, spec in TABLES.items():
        cols = ", ".join(spec["columns"].keys())
        lines.append(f"Table {name} ({cols})")
        lines.append(f"  Purpose: {spec['purpose']}")
        lines.append("")
    lines.append(JOIN_HINTS.strip())
    return "\n".join(lines)


# Convenience aliases used across the project
SCHEMA_DDL = build_ddl()
AGENT_SCHEMA = build_agent_schema()


def seed_fake_wearable_if_empty() -> int:
    """Fill wearable_daily from legacy health_logs or generate demo days."""
    conn = get_connection()
    try:
        count = conn.execute("SELECT COUNT(*) FROM wearable_daily").fetchone()[0]
        if count > 0:
            return 0

        has_legacy = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='health_logs'"
        ).fetchone()
        legacy_rows = 0
        if has_legacy:
            legacy_rows = conn.execute("SELECT COUNT(*) FROM health_logs").fetchone()[0]

        if legacy_rows > 0:
            conn.execute(
                """
                INSERT OR REPLACE INTO wearable_daily (
                    user_id, date, steps, sleep_hours, hr_avg, hrv_avg,
                    calories_burned, source, imported_at
                )
                SELECT
                    1,
                    date(timestamp),
                    CAST(AVG(steps) AS INTEGER),
                    ROUND(AVG(sleep_hours), 1),
                    CAST(AVG(heart_rate) AS INTEGER),
                    ROUND(AVG(hrv), 2),
                    CAST(AVG(calories_burned) AS INTEGER),
                    'demo_health_logs',
                    datetime('now')
                FROM health_logs
                GROUP BY date(timestamp)
                """
            )
        else:
            import random
            from datetime import datetime, timedelta

            base = datetime.now().date()
            rows = []
            for i in range(30):
                day = (base - timedelta(days=i)).isoformat()
                rows.append(
                    (
                        1,
                        day,
                        random.randint(3000, 15000),
                        round(random.uniform(4.0, 9.0), 1),
                        random.randint(60, 110),
                        round(random.uniform(25, 110), 2),
                        random.randint(1800, 3200),
                        "demo_generated",
                        datetime.now().isoformat(timespec="seconds"),
                    )
                )
            conn.executemany(
                """
                INSERT OR REPLACE INTO wearable_daily (
                    user_id, date, steps, sleep_hours, hr_avg, hrv_avg,
                    calories_burned, source, imported_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

        conn.commit()
        return conn.execute("SELECT COUNT(*) FROM wearable_daily").fetchone()[0]
    finally:
        conn.close()


def init_database(seed_wearable: bool = True, quiet: bool = False) -> None:
    conn = get_connection()
    conn.executescript(SCHEMA_DDL)
    conn.commit()
    conn.close()
    if seed_wearable:
        seed_fake_wearable_if_empty()
    if not quiet:
        print(f"Tables ready in {Path(DB_NAME).resolve()}")


if __name__ == "__main__":
    init_database()
