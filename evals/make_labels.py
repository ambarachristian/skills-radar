"""Pick 50 random October posts and create a pre-filled label file for each.

Usage:  python -m evals.make_labels
"""
import json
import random

from radar.db import DB_PATH, connect
from radar.extract import MODEL, PROMPT_VERSION

LABEL_DIR = DB_PATH.parent / "labels"     # data/labels/ (private: not in git)
SAMPLE_SIZE = 50
SEED = 42                                  # same seed -> same 50 posts every time


def main() -> None:
    conn = connect()
    ids = [r["id"] for r in conn.execute(
        "SELECT id FROM posts WHERE month = '2026-10' ORDER BY id")]
    sample = random.Random(SEED).sample(ids, SAMPLE_SIZE)

    LABEL_DIR.mkdir(exist_ok=True)
    created = 0
    for post_id in sample:
        path = LABEL_DIR / f"{post_id}.json"
        if path.exists():                  # never overwrite your corrections
            continue
        text = conn.execute("SELECT text FROM posts WHERE id = ?", (post_id,)).fetchone()["text"]
        row = conn.execute(
            "SELECT data FROM extractions "
            "WHERE post_id = ? AND model = ? AND prompt_version = ? AND run = 1",
            (post_id, MODEL, PROMPT_VERSION),
        ).fetchone()
        draft = json.loads(row["data"]) if row and row["data"] else {}
        path.write_text(json.dumps({
            "post_id": post_id,
            "post": text.splitlines(),     # one line per item, easy to read
            "label": draft,                # Claude's answer: you correct this
            "checked": False,              # set to true once you've reviewed it
        }, indent=2, ensure_ascii=False), encoding="utf-8")
        created += 1
    print(f"{created} label files created in {LABEL_DIR}")


if __name__ == "__main__":
    main()
