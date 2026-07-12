"""Hacker News via Algolia API."""
from datetime import datetime, timezone
from util import get_json

HN = "https://hn.algolia.com/api/v1/search_by_date"


def _hit(hit):
    oid, text = hit["objectID"], hit.get("title") or hit.get("comment_text") or ""
    ts = hit.get("created_at_i")
    return {"id": f"hn-{oid}", "source": "hn", "title": text[:200], "text": text,
            "author": hit.get("author", ""), "url": f"https://news.ycombinator.com/item?id={oid}",
            "points": hit.get("points") or 0,
            "created_at": datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None}


def fetch(keywords):
    items, seen = [], set()
    for term in keywords:
        for tag in ("story", "comment"):
            for hit in get_json(HN, params={"query": term, "tags": tag, "hitsPerPage": 50}).get("hits", []):
                item = _hit(hit)
                if item["id"] not in seen:
                    seen.add(item["id"])
                    items.append(item)
    return items

