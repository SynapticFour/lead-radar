"""Reddit search via official OAuth2 API."""

import os
import time
from datetime import datetime, timezone

import requests
from util import get_json, post_json

SUBS = [
    "ExperiencedDevs",
    "programming",
    "startups",
    "SaaS",
    "webdev",
    "cursor",
    "ClaudeAI",
    "Entrepreneur",
]


def fetch(keywords):
    cid, secret = (
        os.environ.get("REDDIT_CLIENT_ID"),
        os.environ.get("REDDIT_CLIENT_SECRET"),
    )
    if not cid or not secret:
        print(
            "[reddit] skipped — REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET not set "
            "(see README / .env.example)",
            flush=True,
        )
        return []
    try:
        tok = post_json(
            "https://www.reddit.com/api/v1/access_token",
            {"grant_type": "client_credentials"},
            auth=(cid, secret),
        )
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        print(
            f"[reddit] OAuth failed: HTTP {status} — check Reddit app credentials",
            flush=True,
        )
        return []
    access = tok.get("access_token")
    if not access:
        print(
            "[reddit] OAuth response missing access_token — check Reddit app type (script)",
            flush=True,
        )
        return []
    hdrs = {"Authorization": f"Bearer {access}"}
    # Prefer tighter search terms — full keyword dump is slow and noisy
    terms = [
        t
        for t in keywords
        if t
        in {
            "vibe coding",
            "vibe-coded",
            "vibecoded",
            "vibe code",
            "claude code",
            "cursor ide",
            "ai slop",
            "technical debt",
            "need help",
            "hire a developer",
            "codebase rescue",
        }
    ] or keywords[:8]
    items, seen = [], set()
    for sub in SUBS:
        for term in terms:
            try:
                children = (
                    get_json(
                        f"https://oauth.reddit.com/r/{sub}/search",
                        headers=hdrs,
                        params={
                            "q": term,
                            "restrict_sr": "on",
                            "sort": "new",
                            "limit": 25,
                            "t": "week",
                        },
                    )
                    .get("data", {})
                    .get("children", [])
                )
            except requests.HTTPError as e:
                status = e.response.status_code if e.response is not None else "?"
                print(
                    f"[reddit] search r/{sub} {term!r} failed: HTTP {status}",
                    flush=True,
                )
                continue
            for post in children:
                p, pid = post["data"], post["data"]["id"]
                if pid in seen:
                    continue
                seen.add(pid)
                text = f"{p.get('title', '')} {p.get('selftext', '')}"
                ts = p.get("created_utc")
                items.append(
                    {
                        "id": f"rd-{pid}",
                        "source": "reddit",
                        "title": p.get("title", "")[:200],
                        "text": text,
                        "author": p.get("author", ""),
                        "url": f"https://reddit.com{p.get('permalink', '')}",
                        "points": p.get("score") or 0,
                        "created_at": datetime.fromtimestamp(ts, tz=timezone.utc)
                        if ts
                        else None,
                    }
                )
            time.sleep(1)
    print(f"[reddit] fetched {len(items)} posts", flush=True)
    return items
