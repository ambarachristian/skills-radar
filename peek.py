import httpx

BASE = "https://hacker-news.firebaseio.com/v0"

# 1. Ask HN for the "whoishiring" account.
user = httpx.get(f"{BASE}/user/whoishiring.json").json()
print("whoishiring has posted", len(user["submitted"]), "threads")

# 2. Look at its 4 most recent posts.
for item_id in user["submitted"][:4]:
    item = httpx.get(f"{BASE}/item/{item_id}.json").json()
    n_comments = len(item.get("kids", []))
    print(item_id, "|", item.get("title"), "|", n_comments, "top-level comments")
