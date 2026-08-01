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
    """Match terms as substrings with loose word boundaries.

    Multi-word / punctuated phrases (e.g. ``vibe coding``, ``.cursorrules``)
    match literally after lowercasing. Single tokens still avoid mid-word hits.
    """
    t = text.lower()
    hits = []
    for term in terms:
        needle = term.lower()
        if " " in needle or "." in needle or "-" in needle:
            if needle in t:
                hits.append(term)
            continue
        pattern = r"(?<!\w)" + re.escape(needle) + r"(?!\w)"
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
        return 0, [
            f"below threshold: only '{only}' matched — needs 2+ of tools/pain/intent"
        ]

    # GitHub /dev.to need intent (or strong pain+tool) — name/readme alone is weak
    source = item.get("source")
    if source in ("github", "devto") and not intent and not (pain and tools):
        return 0, ["weak source without intent (or pain+tool)"]

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
    if source == "hn" and pts > 20:
        score += 1
        reasons.append(f"HN points {pts}")
    if source == "reddit" and pts > 10:
        score += 1
        reasons.append(f"Reddit score {pts}")

    created = item.get("created_at")
    if created:
        dt = (
            created
            if isinstance(created, datetime)
            else datetime.fromisoformat(str(created).replace("Z", "+00:00"))
        )
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - dt < RECENT:
            score += 1
            reasons.append("posted <48h")

    return score, reasons
