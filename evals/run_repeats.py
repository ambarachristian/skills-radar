"""Run Claude 3 times on each labeled post, to measure consistency.

Usage:  python -m evals.run_repeats [--model claude-sonnet-5-5]
"""
import argparse
import json

import anthropic
from dotenv import load_dotenv

from evals.make_labels import LABEL_DIR
from radar.db import connect
from radar.extract import MODEL, PROMPT_VERSION, extract_one, save

RUNS = [1, 2, 3]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=MODEL)
    args = parser.parse_args()

    load_dotenv(override=True)
    client = anthropic.Anthropic()
    conn = connect()
    post_ids = [json.loads(p.read_text(encoding="utf-8"))["post_id"]
                for p in sorted(LABEL_DIR.glob("*.json"))]

    total = 0.0
    for run in RUNS:
        for post_id in post_ids:
            done = conn.execute(
                "SELECT 1 FROM extractions WHERE post_id = ? AND model = ? "
                "AND prompt_version = ? AND run = ? AND data IS NOT NULL",
                (post_id, args.model, PROMPT_VERSION, run),
            ).fetchone()
            if done:                       # already have this run: skip
                continue
            text = conn.execute("SELECT text FROM posts WHERE id = ?", (post_id,)).fetchone()["text"]
            result = extract_one(client, text, model=args.model)
            save(conn, post_id, result, model=args.model, run=run)
            total += result["cost_usd"]
            print(f"run {run} post {post_id}: {result['stop_reason']}, ${result['cost_usd']:.4f}")
    print(f"Done. Spent ${total:.4f}")


if __name__ == "__main__":
    main()
