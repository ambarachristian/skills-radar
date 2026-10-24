"""Download "Who is hiring?" threads and save each job post in the database.

Usage:  python -m radar.ingest 2026-09 2026-10
"""
import html
import re
import sys
from datetime import datetime

from radar import hn
from radar.db import connect

TITLE_RE = re.compile(r"^Ask HN: Who is hiring\? \((\w+) (\d{4})\)$")


def month_key(title: str | None) -> str | None:
    """'Ask HN: Who is hiring? (October 2026)' -> '2026-10'. Any other title -> None."""
    match = TITLE_RE.match(title or "")
    if not match:
        return None
    month_name, year = match.groups()
    return datetime.strptime(f"{month_name} {year}", "%B %Y").strftime("%Y-%m")


def html_to_text(raw: str) -> str:
    """HN sends posts as HTML. Turn them into plain text for the LLM."""
    text = raw.replace("<p>", "\n\n")      # HN puts <p> between paragraphs
    text = re.sub(r"<[^>]+>", "", text)    # remove the other tags, like <a href=...>
    return html.unescape(text).strip()     # &#x2F; -> /    &amp; -> &

def find_threads(conn, wanted: set[str]) -> dict[str, dict]:
    """Find the "Who is hiring?" thread for each wanted month, e.g. {'2026-10': {...}}."""
    user = hn.get_user("whoishiring")
    oldest = min(wanted)
    found = {}
    for item_id in user["submitted"]:              # newest first
        item = hn.get_item(conn, item_id, use_cache=False) or {}
        month = month_key(item.get("title"))
        if month in wanted:
            found[month] = item
        if month and month < oldest:               # older than anything we want: stop
            break
    return found


def ingest_thread(conn, month: str, thread: dict) -> None:
    """Save one thread and every job post in it."""
    conn.execute(
        "INSERT OR REPLACE INTO threads (id, month, title) VALUES (?, ?, ?)",
        (thread["id"], month, thread["title"]),
    )
    kids = thread.get("kids", [])
    saved = skipped = 0
    for i, post_id in enumerate(kids, start=1):
        print(f"\r  {month}: {i}/{len(kids)}", end="", flush=True)
        post = hn.get_item(conn, post_id)          # cached: posts rarely change
        if not post or post.get("deleted") or post.get("dead") or not post.get("text"):
            skipped += 1
            continue
        conn.execute(
            "INSERT OR REPLACE INTO posts (id, thread_id, month, author, posted_at, text) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (post["id"], thread["id"], month, post.get("by"), post.get("time"),
             html_to_text(post["text"])),
        )
        saved += 1
    conn.commit()
    print(f"\n  {month}: saved {saved} posts, skipped {skipped} deleted or dead")


def main() -> None:
    wanted = set(sys.argv[1:]) or {"2026-09", "2026-10"}
    conn = connect()
    threads = find_threads(conn, wanted)
    for month in sorted(wanted):
        if month in threads:
            ingest_thread(conn, month, threads[month])
        else:
            print(f"  {month}: no thread found")
    total = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    print(f"Done. {total} posts in the database.")


if __name__ == "__main__":
    main()
