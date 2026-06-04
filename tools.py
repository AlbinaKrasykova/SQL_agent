"""Agent tools: your SQLite data + RAG health knowledge."""

from schema import AGENT_SCHEMA, init_database

from db import get_connection

# SQL helpers (shared with lama_agent)
from lama_agent import clean_sql, is_read_only_sql, run_sql

from rag import search as rag_search


def list_schema() -> str:
    return AGENT_SCHEMA


def today_summary() -> dict:
    conn = get_connection()
    cur = conn.cursor()
    mood = cur.execute(
        "SELECT COUNT(*) FROM mood_logs WHERE date(logged_at) = date('now')"
    ).fetchone()[0]
    food = cur.execute(
        "SELECT COUNT(*) FROM food_logs WHERE date(logged_at) = date('now')"
    ).fetchone()[0]
    wear = cur.execute(
        """
        SELECT steps, sleep_hours, hr_avg
        FROM wearable_daily
        WHERE date = date('now')
        """
    ).fetchone()
    conn.close()
    return {
        "mood_logs_today": mood,
        "food_logs_today": food,
        "wearable_today": wear,
    }


def query_database(sql: str) -> dict:
    init_database(seed_wearable=False)
    sql = clean_sql(sql)
    if not is_read_only_sql(sql):
        raise ValueError("Only read-only SELECT queries are allowed.")
    columns, rows = run_sql(sql)
    return {
        "columns": columns,
        "rows": rows[:30],
        "row_count": len(rows),
        "truncated": len(rows) > 30,
    }


def search_health_knowledge(query: str, n_results: int = 4) -> dict:
    chunks = rag_search(query, n_results=n_results)
    return {
        "query": query,
        "chunks": chunks,
        "chunk_count": len(chunks),
    }


TOOL_SPECS = [
    {
        "name": "list_schema",
        "description": "Get database table and column descriptions for writing SQL.",
        "args": {},
    },
    {
        "name": "today_summary",
        "description": "Counts of today's mood and food logs plus wearable row for today.",
        "args": {},
    },
    {
        "name": "query_database",
        "description": "Run one read-only SELECT on mood_logs, food_logs, wearable_daily.",
        "args": {"sql": "string"},
    },
    {
        "name": "search_health_knowledge",
        "description": "Search PDF/text library about nutrition, hormones, eating (RAG). Not personal data.",
        "args": {"query": "string"},
    },
]


def run_tool(name: str, args: dict) -> dict:
    if name == "list_schema":
        return {"schema": list_schema()}
    if name == "today_summary":
        return today_summary()
    if name == "query_database":
        return query_database(args.get("sql", ""))
    if name == "search_health_knowledge":
        return search_health_knowledge(args.get("query", ""))
    raise ValueError(f"Unknown tool: {name}")
