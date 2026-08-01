"""Cloud LLM triage — filters keyword-scored digest items.

Same role as local_triage.py (Ollama), but uses the cloud providers Synaptic
Intelligence Engine already uses: Gemini → Groq → Cerebras (+ optional Anthropic).

Fails open (keeps the item) on per-item API errors. If no provider key is
configured, returns items unchanged.
"""

from __future__ import annotations

import json
import os
import re
from typing import Callable

import requests

PROMPT = """You are screening a forum post for a consultant who helps fix broken AI-generated ("vibe coded") codebases.

Post:
\"\"\"{text}\"\"\"

Does this post indicate the AUTHOR currently has a problem with an AI-generated codebase that they might realistically pay someone to help fix? Answer "false" for success stories, general discussion, unrelated topics (security policy, recruiting, company drama, etc.), or praise for a tool — even if it happens to mention a relevant keyword out of context.

Respond with strict JSON only, nothing else: {{"is_lead": true or false, "reason": "one short sentence"}}"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(0))


def _call_gemini(prompt: str) -> str:
    key = os.environ["GEMINI_API_KEY"]
    model = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    r = requests.post(
        url,
        params={"key": key},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 150},
        },
        timeout=45,
    )
    r.raise_for_status()
    parts = r.json()["candidates"][0]["content"]["parts"]
    return parts[0].get("text", "")


def _call_openai_compat(
    base_url: str, key_env: str, model_env: str, default_model: str, prompt: str
) -> str:
    key = os.environ[key_env]
    model = os.environ.get(model_env, default_model)
    r = requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "temperature": 0,
            "max_tokens": 150,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=45,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _call_groq(prompt: str) -> str:
    return _call_openai_compat(
        "https://api.groq.com/openai/v1",
        "GROQ_API_KEY",
        "GROQ_MODEL",
        "llama-3.3-70b-versatile",
        prompt,
    )


def _call_cerebras(prompt: str) -> str:
    return _call_openai_compat(
        "https://api.cerebras.ai/v1",
        "CEREBRAS_API_KEY",
        "CEREBRAS_MODEL",
        "gemma-4-31b",
        prompt,
    )


def _call_anthropic(prompt: str) -> str:
    key = os.environ["ANTHROPIC_API_KEY"]
    model = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": 150,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=45,
    )
    r.raise_for_status()
    return r.json()["content"][0]["text"]


# Prefer Gemini (SIE default for reasoning), then fast OpenAI-compat, then Anthropic.
_PROVIDERS: list[tuple[str, str, Callable[[str], str]]] = [
    ("gemini", "GEMINI_API_KEY", _call_gemini),
    ("groq", "GROQ_API_KEY", _call_groq),
    ("cerebras", "CEREBRAS_API_KEY", _call_cerebras),
    ("anthropic", "ANTHROPIC_API_KEY", _call_anthropic),
]


def _pick_provider() -> tuple[str, Callable[[str], str]] | None:
    preferred = os.environ.get("LEAD_RADAR_LLM_PROVIDER", "").strip().lower()
    if preferred:
        for name, key_env, fn in _PROVIDERS:
            if name == preferred and os.environ.get(key_env):
                return name, fn
        print(
            f"[triage] LEAD_RADAR_LLM_PROVIDER={preferred!r} unavailable — falling back",
            flush=True,
        )
    for name, key_env, fn in _PROVIDERS:
        if os.environ.get(key_env):
            return name, fn
    return None


def triage(items):
    picked = _pick_provider()
    if not picked:
        print(
            "[triage] no GEMINI_API_KEY / GROQ_API_KEY / CEREBRAS_API_KEY / ANTHROPIC_API_KEY "
            "— keeping keyword digest as-is",
            flush=True,
        )
        return items

    provider_name, call = picked
    kept = []
    total = len(items)
    if total:
        print(
            f"[triage] screening {total} digest items via {provider_name}...",
            flush=True,
        )
    for i, item in enumerate(items, 1):
        title = (item.get("title") or "")[:60]
        print(f"[triage {i}/{total}] {title}", flush=True)
        text = (item.get("text") or item.get("title") or "")[:1500]
        prompt = PROMPT.format(text=text)
        try:
            reply = call(prompt)
            verdict = _extract_json(reply)
        except Exception as e:
            item["reasons"].append(
                f"llm triage skipped ({provider_name}/{type(e).__name__})"
            )
            kept.append(item)
            continue

        is_lead = verdict.get("is_lead", True)
        item["llm_reason"] = verdict.get("reason", "")
        if is_lead:
            item["reasons"].append(f"{provider_name} confirmed: {item['llm_reason']}")
            kept.append(item)
    if total:
        print(
            f"[triage] done — {len(kept)}/{total} kept via {provider_name}", flush=True
        )
    return kept
