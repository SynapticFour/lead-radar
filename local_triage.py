"""Optional local LLM triage pass via Ollama — a zero-cost alternative to the
Anthropic API triage. Runs only on items that already cleared the numeric
threshold. Requires `ollama serve` running locally with the model pulled.
Fails open (keeps the item) if Ollama isn't reachable."""
import json

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3:8b"

PROMPT = """You are screening a forum post for a consultant who helps fix broken AI-generated ("vibe coded") codebases.

Post:
\"\"\"{text}\"\"\"

Does this post indicate the AUTHOR currently has a problem with an AI-generated codebase that they might realistically pay someone to help fix? Answer "false" for success stories, general discussion, unrelated topics (security policy, recruiting, company drama, etc.), or praise for a tool — even if it happens to mention a relevant keyword out of context.

Respond with strict JSON only, nothing else: {{"is_lead": true or false, "reason": "one short sentence"}}"""


def triage(items):
    kept = []
    for item in items:
        text = (item.get("text") or item.get("title") or "")[:1500]
        try:
            r = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "prompt": PROMPT.format(text=text),
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0},
                },
                timeout=60,
            )
            r.raise_for_status()
            reply = r.json().get("response", "").strip()
            verdict = json.loads(reply)
        except Exception as e:
            item["reasons"].append(f"local triage skipped ({type(e).__name__}: is 'ollama serve' running?)")
            kept.append(item)
            continue

        is_lead = verdict.get("is_lead", True)
        item["llm_reason"] = verdict.get("reason", "")
        if is_lead:
            item["reasons"].append(f"local llm confirmed: {item['llm_reason']}")
            kept.append(item)
    return kept
