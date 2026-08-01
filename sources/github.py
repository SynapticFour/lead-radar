"""GitHub code search (weak signal). Requires GITHUB_TOKEN — code search has no unauthenticated tier."""

from __future__ import annotations

import os
import time

import requests
from util import get_json, get_text

API = "https://api.github.com/search/code"


def _token() -> str | None:
    return os.environ.get("LEAD_RADAR_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")


def _readme_snippet(full_name: str, hdrs: dict) -> str:
    """Fetch a short README for scoring text (best-effort)."""
    try:
        return get_text(
            f"https://api.github.com/repos/{full_name}/readme",
            headers={**hdrs, "Accept": "application/vnd.github.raw"},
        )[:2500]
    except Exception:
        return ""


def fetch():
    token = _token()
    if not token:
        print(
            "[github] skipped — no GITHUB_TOKEN / LEAD_RADAR_GITHUB_TOKEN "
            "(code search requires auth)",
            flush=True,
        )
        return []

    hdrs = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    items, seen = [], set()
    queries = (
        "filename:.cursorrules",
        "filename:CLAUDE.md",
        '"vibe coding" OR vibecoded OR "vibe-coded" in:file',
    )
    for q in queries:
        try:
            data = get_json(
                API,
                headers=hdrs,
                params={"q": q, "sort": "indexed", "order": "desc", "per_page": 30},
            )
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            print(f"[github] search failed for {q!r}: HTTP {status}", flush=True)
            continue
        for hit in data.get("items", []):
            repo = hit["repository"]
            rid = str(repo["id"])
            if rid in seen:
                continue
            seen.add(rid)
            full_name = repo["full_name"]
            desc = repo.get("description") or ""
            readme = _readme_snippet(full_name, hdrs)
            text = f"{full_name}\n{desc}\n{readme}".strip()
            items.append(
                {
                    "id": f"gh-{rid}",
                    "source": "github",
                    "title": full_name,
                    "text": text,
                    "author": repo.get("owner", {}).get("login", ""),
                    "url": repo["html_url"],
                    "points": 0,
                    "created_at": None,
                }
            )
        time.sleep(2)
    print(f"[github] fetched {len(items)} repos", flush=True)
    return items
