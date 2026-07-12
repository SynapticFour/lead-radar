"""Reddit search via official OAuth2 API."""
import os, time
from datetime import datetime, timezone
from util import get_json, post_json

SUBS = ["ExperiencedDevs", "programming", "startups", "SaaS", "webdev", "cursor", "ClaudeAI", "Entrepreneur"]


def fetch(keywords):
    cid, secret = os.environ.get("REDDIT_CLIENT_ID"), os.environ.get("REDDIT_CLIENT_SECRET")
    if not cid or not secret:
        return []
    tok = post_json("https://www.reddit.com/api/v1/access_token", {"grant_type": "client_credentials"}, auth=(cid, secret))
    hdrs = {"Authorization": f"Bearer {tok.get('access_token')}"}
    items, seen = [], set()
    for sub in SUBS:
        for term in keywords:
            for post in get_json(f"https://oauth.reddit.com/r/{sub}/search", headers=hdrs,
                                 params={"q": term, "restrict_sr": "on", "sort": "new", "limit": 25, "t": "month"}).get("data", {}).get("children", []):
                p, pid = post["data"], post["data"]["id"]
                if pid in seen:
                    continue
                seen.add(pid)
                text = f"{p.get('title', '')} {p.get('selftext', '')}"
                ts = p.get("created_utc")
                items.append({"id": f"rd-{pid}", "source": "reddit", "title": p.get("title", "")[:200], "text": text,
                              "author": p.get("author", ""), "url": f"https://reddit.com{p.get('permalink', '')}",
                              "points": p.get("score") or 0,
                              "created_at": datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None})
            time.sleep(1)
    return items

