"""Answer eval: ask the agent 20 questions and check its answers against the SQL truth.

Usage:  python -m evals.answer_eval            (all 20 questions, about $0.70)
        python -m evals.answer_eval --only q06 q18
"""
import argparse
import asyncio
import json
import re

import anthropic
from dotenv import load_dotenv
from mcp import Client

from evals.answer_questions import QUESTIONS
from radar.agent import SERVER, answer
from radar.db import DB_PATH

# Phrases that mean "the data can't answer this".
NO_DATA_PHRASES = [
    "no data", "no posts", "no job posts", "none of the", "not in the data", "zero",
    "don't have", "do not have", "doesn't have", "does not have", "no information",
    "not available", "isn't available", "is not available", "not tracked", "doesn't track",
    "does not track", "doesn't include", "does not include", "not included", "no mention",
    "can't answer", "cannot answer", "can't tell", "cannot tell", "only covers", "only has",
]


def numbers_in(text: str) -> list[float]:
    """'$186K, 9.0% and 1,200 posts' -> [186000.0, 9.0, 1200.0]"""
    found = []
    for digits, k in re.findall(r"(\d[\d,]*(?:\.\d+)?)\s*([kK])?(?!\w)", text):
        value = float(digits.replace(",", ""))
        found.append(value * 1000 if k else value)
    return found


def close(found: float, expected: float, tolerance: float) -> bool:
    return abs(found - expected) <= tolerance * max(abs(expected), 1)


def grade(q: dict, text: str) -> tuple[bool, str]:
    """Return (passed, what was expected)."""
    low = text.lower().replace("\u2019", "'")          # curly apostrophe -> straight
    if q.get("no_data"):
        said_none = re.search(r"\b(no|0|zero)\b(\s+\w+){0,3}\s+(posts?|jobs?|data)\b", low)
        return bool(said_none) or any(p in low for p in NO_DATA_PHRASES), "says the data can't answer"
    if "numbers" in q:
        expected = q["numbers"]()
        found = numbers_in(text)
        tolerance = q.get("tolerance", 0)
        ok = all(any(close(f, e, tolerance) for f in found) for e in expected)
        return ok, f"numbers {expected}"
    expected = q["words"]()
    return all(w.lower() in low for w in expected), f"words {expected}"


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="*", help="question ids to run, e.g. q01 q18")
    args = parser.parse_args()

    load_dotenv(override=True)
    claude = anthropic.AsyncAnthropic()
    questions = [q for q in QUESTIONS if not args.only or q["id"] in args.only]

    results, passed, cost = [], 0, 0.0
    async with Client(SERVER) as mcp_client:
        for q in questions:
            r = await answer(q["question"], mcp_client, claude)
            ok, expected = grade(q, r["answer"])
            if not q.get("no_data") and not r["tool_calls"]:
                ok, expected = False, expected + " (but answered without using a tool)"
            passed += ok
            cost += r["cost_usd"]
            tools = ", ".join(c["tool"] for c in r["tool_calls"]) or "none"
            print(f"{'PASS' if ok else 'FAIL'}  {q['id']}  expected {expected}   tools: {tools}")
            results.append({"id": q["id"], "question": q["question"], "expected": expected,
                            "passed": ok, **r})

    print(f"\nScore: {passed}/{len(questions)}   cost ${cost:.2f}")
    out = DB_PATH.parent / "answer_eval.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Full answers saved to {out}")


if __name__ == "__main__":
    asyncio.run(main())
