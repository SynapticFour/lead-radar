"""Optional LLM triage pass — filters numerically-scored items using Claude's
judgment, to catch cases keyword matching structurally can't: success stories,
sarcasm, discussion-not-distress, etc. Runs only on items that already cleared
the numeric threshold, to keep API cost minimal. Skips silently without a key."""
import json
import os

import requests

API = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5-20251001"

PROMPT = """You are screening a forum post for a consultant who helps fix broken AI-generated ("vibe coded") codebases.

Post:
\"\"\"{text}\"\"\"

Does this post indicate the AUTHOR currently has a problem with an AI-generated codebase that they might realistically pay someone to help fix? Answer "false" if it is a success story, general discussion, someone else's problem being described secondhand, or praise for a tool.

Respond with strict JSON only, nothing else: {{"is_lead": true or false, "reason": "one short sentence"}}"""


def triage(items):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return items

    kept = []
    for item in items:
        text = (item.get("text") or item.get("title") or "")[:1500]
        try:
            r = requests.post(
                API,
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": MODEL,
                    "max_tokens": 150,
                    "messages": [{"role": "user", "content": PROMPT.format(text=text)}],
                },
                timeout=30,
            )
            r.raise_for_status()
            reply = r.json()["content"][0]["text"].strip()
            verdict = json.loads(reply)
        except Exception as e:
            item["reasons"].append(f"llm triage skipped ({type(e).__name__})")
            kept.append(item)
            continue

        is_lead = verdict.get("is_lead", True)
        item["llm_reason"] = verdict.get("reason", "")
        if is_lead:
            item["reasons"].append(f"llm confirmed: {item['llm_reason']}")
            kept.append(item)
    return kept
