"""GitHub code search (weak signal). Requires GITHUB_TOKEN — code search has no unauthenticated tier."""
import os
import time

import requests
from util import get_json

API = "https://api.github.com/search/code"


def fetch():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return []

    hdrs = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    items, seen = [], set()
    for q in ("filename:.cursorrules", "filename:CLAUDE.md"):
        try:
            data = get_json(API, headers=hdrs, params={"q": q, "sort": "indexed", "order": "desc", "per_page": 30})
        except requests.HTTPError:
            continue
        for hit in data.get("items", []):
            repo = hit["repository"]
            rid = str(repo["id"])
            if rid in seen:
                continue
            seen.add(rid)
            items.append({
                "id": f"gh-{rid}", "source": "github", "title": repo["full_name"],
                "text": f"{repo['full_name']} {repo.get('description') or ''}",
                "author": repo.get("owner", {}).get("login", ""),
                "url": repo["html_url"], "points": 0,
                "created_at": None,
            })
        time.sleep(2)
    return items
