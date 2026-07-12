"""Keyword-based lead scoring."""
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
RECENT = timedelta(hours=48)


def load_keywords():
    with open(ROOT / "config" / "keywords.yaml") as f:
        return yaml.safe_load(f)["signals"]


def _match(text, terms):
    t = text.lower()
    hits = []
    for term in terms:
        pattern = r"(?<!\w)" + re.escape(term.lower()) + r"(?!\w)"
        if re.search(pattern, t):
            hits.append(term)
    return hits


def score_item(item, kw):
    text = item.get("text", "") or item.get("title", "")

    tools = _match(text, kw["tools"])
    pain = _match(text, kw["pain"])
    intent = _match(text, kw["intent"])

    categories_matched = sum(bool(x) for x in (tools, pain, intent))
    if categories_matched < 2:
        only = "tools" if tools else "pain" if pain else "intent" if intent else "none"
        return 0, [f"below threshold: only '{only}' matched — needs 2+ of tools/pain/intent"]

    score = 0
    reasons = []
    if intent:
        score += 3
        reasons.append(f"intent: {intent[0]}")
    if pain:
        score += 2
        reasons.append(f"pain: {pain[0]}")
    if tools:
        score += 1
        reasons.append(f"tool: {tools[0]}")

    pts = item.get("points") or 0
    if item["source"] == "hn" and pts > 20:
        score += 1
        reasons.append(f"HN points {pts}")
    if item["source"] == "reddit" and pts > 10:
        score += 1
        reasons.append(f"Reddit score {pts}")

    created = item.get("created_at")
    if created:
        dt = created if isinstance(created, datetime) else datetime.fromisoformat(
            str(created).replace("Z", "+00:00")
        )
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - dt < RECENT:
            score += 1
            reasons.append("posted <48h")

    if item["source"] == "github" and not (pain or intent):
        score = max(0, score - 1)
        reasons.append("github weak signal")
    if item["source"] == "devto" and not (pain or intent):
        score = max(0, score - 1)
        reasons.append("devto weak signal")

    return score, reasons
