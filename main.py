#!/usr/bin/env python3
import argparse, hashlib, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

import requests

from scoring import load_keywords, score_item
from sources import devto, github, hn, reddit
from storage import init_db, is_seen, mark_seen, reset_recent

ROOT = Path(__file__).parent
DIGESTS = ROOT / "digests"
RAW = ROOT / "raw"
THRESHOLD = 3


def _digest_jsonl(date):
    return DIGESTS / f"{date}.jsonl"


def _triage_state(date):
    return DIGESTS / f"{date}.triage-state"


def _jsonl_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_digest_jsonl(digest, date):
    """Save keyword-scored digest (with full text) for later triage-only runs."""
    DIGESTS.mkdir(exist_ok=True)
    with open(_digest_jsonl(date), "w") as f:
        for item in digest:
            f.write(json.dumps(item, default=str) + "\n")


def load_digest_jsonl(date):
    path = _digest_jsonl(date)
    if not path.exists():
        return None, path
    items = []
    with open(path) as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items, path


def already_triaged(date, jsonl_path):
    state = _triage_state(date)
    return state.exists() and state.read_text().strip() == _jsonl_hash(jsonl_path)


def mark_triaged(date, jsonl_path):
    _triage_state(date).write_text(_jsonl_hash(jsonl_path))


def run_triage_only(triage_backend="local", *, force=False):
    if triage_backend == "none":
        print("[triage-only] requires --triage local or --triage anthropic")
        return 1

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    digest, jsonl_path = load_digest_jsonl(date)

    if digest is None:
        print(f"[triage-only] no keyword digest at {jsonl_path}")
        print("[triage-only] run after GitHub Actions commits, or: git pull")
        return 0

    if not digest:
        print(f"[triage-only] keyword digest empty for {date} — nothing to triage")
        return 0

    if not force and already_triaged(date, jsonl_path):
        md = DIGESTS / f"{date}.md"
        print(f"[triage-only] already triaged — digest unchanged since last LLM pass")
        print(f"[triage-only] see {md} (use --force to re-run)")
        return 0

    n_before = len(digest)
    print(f"[triage-only] {n_before} keyword leads from {jsonl_path.name}", flush=True)

    if triage_backend == "local":
        from local_triage import triage as run_triage
    else:
        from llm_triage import triage as run_triage
    digest = run_triage(digest)

    DIGESTS.mkdir(exist_ok=True)
    md_path = DIGESTS / f"{date}.md"
    md_path.write_text(format_digest(digest, date))
    mark_triaged(date, jsonl_path)
    print(f"[triage-only] wrote {md_path} ({len(digest)}/{n_before} kept after triage)")
    return 0


def all_keywords(kw):
    return kw["tools"] + kw["pain"] + kw["intent"]


def fetch_all(kw):
    terms = all_keywords(kw)
    items = hn.fetch(terms)
    items.extend(github.fetch())
    items.extend(reddit.fetch(terms))
    items.extend(devto.fetch())
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
    labels = {"hn": "Hacker News", "github": "GitHub", "reddit": "Reddit", "devto": "dev.to"}
    for src in ("hn", "reddit", "devto", "github"):
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
    for term in kw["intent"] + kw["pain"]:
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


def print_debug(digest, raw):
    from collections import Counter
    dist = Counter(item["score"] for item in (digest + raw))
    print(f"[debug] score distribution: {dict(sorted(dist.items()))}")
    near_misses = sorted((i for i in raw if i["score"] == THRESHOLD - 1), key=lambda x: x["score"], reverse=True)[:10]
    if near_misses:
        print(f"[debug] top {len(near_misses)} near-misses (score {THRESHOLD - 1}):")
        for i in near_misses:
            print(f"  [{i['score']}] {i['title'][:80]}  ({'; '.join(i['reasons'])})")


def run(dry_run=False, debug=False, reset_days=None, triage_backend="none"):
    kw = load_keywords()
    init_db()
    if reset_days is not None:
        n = reset_recent(reset_days if reset_days > 0 else None)
        scope = "entire ledger" if reset_days == 0 else f"last {reset_days} day(s)"
        print(f"[reset] cleared {n} entries from dedup ledger ({scope})")
    print("[fetch] querying sources...", flush=True)
    items = fetch_all(kw)
    digest, raw = process(items, kw, persist=not dry_run)
    print(f"[score] {len(digest)} digest items, {len(raw)} below threshold", flush=True)

    if debug:
        print_debug(digest, raw)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if not dry_run and digest:
        save_digest_jsonl(digest, date)

    if triage_backend == "local":
        from local_triage import triage as run_triage
        digest = run_triage(digest)
    elif triage_backend == "anthropic":
        from llm_triage import triage as run_triage
        digest = run_triage(digest)

    text = format_digest(digest, date)

    if dry_run:
        print(text)
        print(f"\n--- {len(digest)} digest items, {len(raw)} below threshold (not written) ---")
        return

    DIGESTS.mkdir(exist_ok=True)
    RAW.mkdir(exist_ok=True)
    (DIGESTS / f"{date}.md").write_text(text)
    if triage_backend != "none" and digest:
        mark_triaged(date, _digest_jsonl(date))
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
    parser.add_argument("--debug", action="store_true", help="Print score distribution and top near-misses")
    parser.add_argument(
        "--reset-days", type=int, default=None, metavar="N",
        help="Clear dedup ledger entries from the last N days (0 = entire ledger) before running.",
    )
    parser.add_argument(
        "--triage", choices=["none", "local", "anthropic"], default="none",
        help="Optional LLM triage pass: 'local' (Ollama, free) or 'anthropic' (Claude API).",
    )
    parser.add_argument(
        "--triage-only", action="store_true",
        help="LLM-triage existing digests/YYYY-MM-DD.jsonl only — no fetch, no dedup changes.",
    )
    parser.add_argument("--force", action="store_true", help="Re-run triage even if digest already triaged")
    args = parser.parse_args()
    if args.triage_only:
        sys.exit(run_triage_only(args.triage, force=args.force))
    run(dry_run=args.dry_run, debug=args.debug, reset_days=args.reset_days, triage_backend=args.triage)
