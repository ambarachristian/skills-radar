"""Compare Claude's answers with your labels, field by field.

Usage:  python -m evals.grade [--model ...] [--prompt-version ...] [--show FIELD]
"""
import argparse
import json
import re

from evals.make_labels import LABEL_DIR
from radar.db import connect
from radar.extract import MODEL, PROMPT_VERSION

RUNS = [1, 2, 3]


def norm(text):
    """'Acme, Inc.' -> 'acme'. Lowercase, no punctuation, no legal suffix."""
    if text is None:
        return None
    text = re.sub(r"[^\w\s]", "", text.lower())
    text = re.sub(r"\b(inc|ltd|llc|gmbh|corp)\b", "", text)
    return " ".join(text.split())


# One rule per field: turn an answer into a value we can compare with ==.
FIELDS = {
    "is_job_post":     lambda d: d["is_job_post"],
    "company":         lambda d: norm(d["company"]),
    "role_count":      lambda d: len(d["roles"]),
    "seniorities":     lambda d: frozenset(r["seniority"] for r in d["roles"]),
    "work_modes":      lambda d: frozenset(d["work_modes"]),
    "cities":          lambda d: frozenset(norm(c) for c in d["cities"]),
    "countries":       lambda d: frozenset(c.upper() for c in d["countries"]),
    "salary_min":      lambda d: d["salary_min"],
    "salary_max":      lambda d: d["salary_max"],
    "salary_currency": lambda d: d["salary_currency"],
    "skills_exact":    lambda d: frozenset(d["skills"]),
    "ai_work":         lambda d: d["ai_work"],
}


def fmt(value):
    return sorted(value) if isinstance(value, frozenset) else value


def load_labels() -> dict:
    labels = {}
    for path in sorted(LABEL_DIR.glob("*.json")):
        obj = json.loads(path.read_text(encoding="utf-8"))
        if obj.get("checked"):
            labels[obj["post_id"]] = obj["label"]
    return labels


def load_runs(conn, post_id, model, prompt_version) -> list:
    rows = conn.execute(
        "SELECT run, data FROM extractions WHERE post_id = ? AND model = ? "
        "AND prompt_version = ? AND data IS NOT NULL ORDER BY run",
        (post_id, model, prompt_version),
    ).fetchall()
    return [json.loads(r["data"]) for r in rows if r["run"] in RUNS]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--prompt-version", default=PROMPT_VERSION)
    parser.add_argument("--show", help="print run-1 mistakes for one field, e.g. skills_exact")
    args = parser.parse_args()

    conn = connect()
    labels = load_labels()
    correct = dict.fromkeys(FIELDS, 0)   # right answers, counted over all runs
    answers = dict.fromkeys(FIELDS, 0)   # all answers, counted over all runs
    agreed = dict.fromkeys(FIELDS, 0)    # posts where the 3 runs gave the same value
    graded = dict.fromkeys(FIELDS, 0)    # posts graded on this field
    tp = fp = fn = 0                     # for skills precision and recall

    for post_id, gold in labels.items():
        runs = load_runs(conn, post_id, args.model, args.prompt_version)
        if not runs:
            continue
        # Not a job post? Then only is_job_post is meaningful.
        fields = FIELDS if gold["is_job_post"] else {"is_job_post": FIELDS["is_job_post"]}
        for name, get in fields.items():
            expected = get(gold)
            values = [get(run) for run in runs]
            correct[name] += sum(v == expected for v in values)
            answers[name] += len(values)
            agreed[name] += len(set(values)) == 1
            graded[name] += 1
            if args.show == name and values[0] != expected:
                print(f"post {post_id}: label={fmt(expected)}  claude={fmt(values[0])}")
        if gold["is_job_post"]:
            for run in runs:
                pred, true = set(run["skills"]), set(gold["skills"])
                tp += len(pred & true)
                fp += len(pred - true)
                fn += len(true - pred)

    print(f"\nModel {args.model}, prompt {args.prompt_version}, {len(labels)} labeled posts\n")
    print(f"{'field':<16} {'accuracy':>9} {'agreement':>10}")
    for name in FIELDS:
        if answers[name]:
            print(f"{name:<16} {correct[name] / answers[name]:>9.0%} "
                  f"{agreed[name] / graded[name]:>10.0%}")
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
    print(f"\nskills: precision {precision:.0%}, recall {recall:.0%}, F1 {f1:.0%}")


if __name__ == "__main__":
    main()
