"""
Agent loop: short-term chat memory + tools (SQL, summary, RAG knowledge).
"""

import json
import re

import ollama

from schema import init_database
from tools import TOOL_SPECS, run_tool

MODEL = "qwen2.5"
MAX_STEPS = 5

SYSTEM_PROMPT = """You are a health diary assistant with tools.

You can:
1) Answer using the user's personal data (mood_logs, food_logs, wearable_daily) via SQL tools.
2) Answer general nutrition/hormone questions using search_health_knowledge (RAG from PDFs/text).

TOOL FORMAT — when you need a tool, reply with ONLY valid JSON (no markdown):
{"tool": "tool_name", "args": {"key": "value"}}

Available tools:
- list_schema — args: {}
- today_summary — args: {}
- query_database — args: {"sql": "SELECT ..."}
- search_health_knowledge — args: {"query": "short search phrase"}

FINAL ANSWER — when you have enough information, reply with ONLY:
ANSWER: <plain English, concise, 2-6 sentences. Mention if advice is general vs from their logs.>

Rules:
- Prefer today_summary for simple "how am I today" questions.
- Use search_health_knowledge for hormones, diet science, food effects (not in SQL).
- Combine both when needed: their logs + general knowledge.
- Never invent personal data; if SQL returns empty, say so.
"""


def _tool_catalog_text() -> str:
    lines = []
    for t in TOOL_SPECS:
        lines.append(f"- {t['name']}: {t['description']}")
    return "\n".join(lines)


def parse_response(text: str) -> tuple[str | None, dict | None]:
    text = text.strip()
    if text.upper().startswith("ANSWER:"):
        return text.split(":", 1)[1].strip(), None

    # JSON tool call
    try:
        data = json.loads(text)
        if "tool" in data:
            return None, {"tool": data["tool"], "args": data.get("args", {})}
    except json.JSONDecodeError:
        pass

    match = re.search(r'\{\s*"tool"\s*:\s*"[^"]+"\s*,\s*"args"\s*:\s*\{.*?\}\s*\}', text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            return None, {"tool": data["tool"], "args": data.get("args", {})}
        except json.JSONDecodeError:
            pass

    # Treat as final answer if model didn't follow format
    return text, None


def run(
    question: str,
    messages: list[dict] | None = None,
    max_steps: int = MAX_STEPS,
) -> dict:
    """
    Returns:
      answer, steps (tool trace), messages (updated short memory), error
    """
    init_database(seed_wearable=False)

    if messages is None:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + _tool_catalog_text()},
        ]

    messages.append({"role": "user", "content": question})
    steps = []

    for _ in range(max_steps):
        response = ollama.chat(model=MODEL, messages=messages)
        content = response["message"]["content"]
        answer, tool_call = parse_response(content)

        if tool_call:
            name = tool_call["tool"]
            args = tool_call.get("args") or {}
            try:
                result = run_tool(name, args)
                err = None
            except Exception as e:
                result = {"error": str(e)}
                err = str(e)

            steps.append({"tool": name, "args": args, "result": result, "error": err})
            messages.append({"role": "assistant", "content": content})
            messages.append(
                {
                    "role": "user",
                    "content": f"Tool `{name}` result:\n{json.dumps(result, default=str)[:4000]}",
                }
            )
            continue

        if answer:
            messages.append({"role": "assistant", "content": f"ANSWER: {answer}"})
            return {
                "question": question,
                "answer": answer,
                "steps": steps,
                "messages": messages,
                "error": None,
            }

    return {
        "question": question,
        "answer": None,
        "steps": steps,
        "messages": messages,
        "error": "Max steps reached without a final answer.",
    }


def run_simple(question: str) -> dict:
    """One-shot wrapper for UI."""
    return run(question, messages=None)
