#!/usr/bin/env python3
import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path

import requests

from scoring import load_keywords, score_item
from sources import github, hn, reddit
from storage import init_db, is_seen, mark_seen

ROOT = Path(__file__).parent
DIGESTS = ROOT / "digests"
RAW = ROOT / "raw"
THRESHOLD = 3


def all_keywords(kw):
    return kw["high_intent"] + kw["pain_venting"] + kw["tool_mentions"]


def fetch_all(kw):
    terms = all_keywords(kw)
    items = hn.fetch(terms)
    items.extend(github.fetch())
    items.extend(reddit.fetch(terms))
    return items


def process(items, kw, *, persist=True):
    digest, raw = [], []
    now = datetime.now(timezone.utc).isoformat()
    for item in items:
        score, reasons = score_item(item, kw)
        item["score"] = score
        item["reasons"] = reasons
        if persist and is_seen(item["id"]):
            continue
        if persist:
            mark_seen(item["id"], item["source"], score, item["url"], now)
        (digest if score >= THRESHOLD else raw).append(item)
    digest.sort(key=lambda x: x["score"], reverse=True)
    return digest, raw


def format_digest(digest, date):
    lines = [f"# Lead Radar Digest — {date}", ""]
    if not digest:
        lines.append("_No new leads scoring 3+ today._")
        return "\n".join(lines)
    by_src = {}
    for item in digest:
        by_src.setdefault(item["source"], []).append(item)
    labels = {"hn": "Hacker News", "github": "GitHub", "reddit": "Reddit"}
    for src in ("hn", "reddit", "github"):
        if src not in by_src:
            continue
        lines += [f"## {labels[src]}", ""]
        for item in by_src[src]:
            lines += [f"### Score {item['score']}: {item['title']}", f"- **Link:** {item['url']}",
                      f"- **Author:** {item.get('author', 'n/a')}", f"- **Why:** {'; '.join(item['reasons'])}", ""]
    return "\n".join(lines)


def write_manual_checklist(kw):
    lines = [
        "# Manual Checklist",
        f"_Generated {datetime.now(timezone.utc).date()}_",
        "",
        "Platforms without public APIs — review manually (~2 min):",
        "",
        "## Upwork",
    ]
    for term in kw["high_intent"] + kw["pain_venting"]:
        t = term.replace(" ", "%20")
        lines.append(f"- [{term}](https://www.upwork.com/nx/search/jobs/?q={t})")
    lines += [
        "",
        "## Fiverr Buyer Requests",
        "- [Search buyer requests](https://www.fiverr.com/users/your_username/buyer_requests) _(log in, search manually)_",
        "",
        "## AI App Showcases (human review)",
        "- [Lovable showcase](https://lovable.dev/) — browse recent public projects",
        "- [Bolt.new](https://bolt.new/) — check community/showcase if available",
        "- [Replit Explore](https://replit.com/explore) — filter for recent web apps",
        "",
        "## Suggested search terms",
    ]
    for term in all_keywords(kw):
        lines.append(f"- `{term}`")
    (ROOT / "MANUAL_CHECKLIST.md").write_text("\n".join(lines))


def send_webhook(digest):
    url = os.environ.get("WEBHOOK_URL")
    if not url or not digest:
        return
    top = digest[:5]
    body = "\n".join(f"**[{i['score']}]** {i['title']}\n{i['url']}" for i in top)
    payload = (
        {"content": f"**Lead Radar — top {len(top)}**\n{body}"}
        if "discord" in url
        else {"text": f"Lead Radar — top {len(top)}\n{body}"}
    )
    try:
        requests.post(url, json=payload, timeout=15)
    except requests.RequestException:
        pass


def run(dry_run=False):
    kw = load_keywords()
    init_db()
    items = fetch_all(kw)
    digest, raw = process(items, kw, persist=not dry_run)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    text = format_digest(digest, date)

    if dry_run:
        print(text)
        print(f"\n--- {len(digest)} digest items, {len(raw)} below threshold (not written) ---")
        return

    DIGESTS.mkdir(exist_ok=True)
    RAW.mkdir(exist_ok=True)
    (DIGESTS / f"{date}.md").write_text(text)
    if raw:
        with open(RAW / f"{date}.jsonl", "w") as f:
            for item in raw:
                f.write(json.dumps({k: v for k, v in item.items() if k != "text"}, default=str) + "\n")
    write_manual_checklist(kw)
    send_webhook(digest)
    print(f"Wrote digests/{date}.md ({len(digest)} leads, {len(raw)} raw)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lead Radar")
    parser.add_argument("--dry-run", action="store_true", help="Print digest to stdout, no writes")
    run(dry_run=parser.parse_args().dry_run)
