"""GitHub repository search (weak signal)."""
import os
from datetime import datetime, timedelta, timezone
from util import get_json

API = "https://api.github.com/search/repositories"


def fetch():
    since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    hdrs = {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"} if os.environ.get("GITHUB_TOKEN") else {}
    items, seen = [], set()
    for q in (f"filename:.cursorrules pushed:>{since}", f"filename:CLAUDE.md pushed:>{since}"):
        for repo in get_json(API, headers=hdrs, params={"q": q, "sort": "updated", "order": "desc", "per_page": 30}).get("items", []):
            rid = str(repo["id"])
            if rid in seen:
                continue
            seen.add(rid)
            desc = repo.get("description") or ""
            pushed = repo.get("pushed_at", "")
            items.append({"id": f"gh-{rid}", "source": "github", "title": repo["full_name"],
                          "text": f"{repo['full_name']} {desc}", "author": repo.get("owner", {}).get("login", ""),
                          "url": repo["html_url"], "points": 0,
                          "created_at": datetime.fromisoformat(pushed.replace("Z", "+00:00")) if pushed else None})
    return items

