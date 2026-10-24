"""Talks to the Hacker News API. Uses a cache so we never download an item twice."""
import json
import time

import httpx

# One shared connection to HN, reused for every request.
client = httpx.Client(base_url="https://hacker-news.firebaseio.com/v0/", timeout=20)


def get_user(name: str) -> dict:
    """Download an HN user, e.g. 'whoishiring'. Not cached: their list of posts grows."""
    resp = client.get(f"user/{name}.json")
    resp.raise_for_status()
    return resp.json()


def get_item(conn, item_id: int, use_cache: bool = True) -> dict | None:
    """Return one HN item. Looks in the cache first, unless use_cache=False."""
    # 1. Already downloaded? Return the saved copy.
    if use_cache:
        row = conn.execute("SELECT json FROM hn_items WHERE id = ?", (item_id,)).fetchone()
        if row:
            return json.loads(row["json"])

    # 2. Otherwise, download it from HN.
    resp = client.get(f"item/{item_id}.json")
    resp.raise_for_status()
    item = resp.json()
    if item is None:          # HN answers null for ids that don't exist
        return None

    # 3. Save it in the cache for next time.
    conn.execute(
        "INSERT OR REPLACE INTO hn_items (id, json, fetched_at) VALUES (?, ?, ?)",
        (item_id, json.dumps(item), int(time.time())),
    )
    conn.commit()
    return item
