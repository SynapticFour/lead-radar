"""dev.to articles — public API, no auth required."""
from datetime import datetime, timezone
from util import get_json

API = "https://dev.to/api/articles"
TAGS = ["ai", "vibecoding", "webdev", "programming"]


def fetch():
    items, seen = [], set()
    for tag in TAGS:
        for a in get_json(API, params={"tag": tag, "per_page": 30}):
            aid = str(a["id"])
            if aid in seen:
                continue
            seen.add(aid)
            text = f"{a.get('title', '')} {a.get('description', '')}"
            ts = a.get("published_timestamp")
            items.append({
                "id": f"dt-{aid}", "source": "devto", "title": a.get("title", "")[:200],
                "text": text, "author": (a.get("user") or {}).get("username", ""),
                "url": a.get("url", ""), "points": a.get("positive_reactions_count") or 0,
                "created_at": datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None,
            })
    return items
