# Lead Radar

A low-maintenance monitoring tool that finds businesses struggling with AI-generated ("vibe-coded") codebases — potential clients for AI-codebase-rescue consulting. Runs on a schedule, checks public APIs, scores results, deduplicates, and writes a daily digest.

**No servers. No paid infra.** A GitHub Actions cron job runs daily and commits digests to this repo.

## What it checks

| Source | API | Signal strength | Notes |
|--------|-----|-----------------|-------|
| Hacker News | [Algolia HN API](https://hn.algolia.com/) (free, no key) | Strong | Primary source today |
| Reddit | [Official API](https://www.reddit.com/dev/api/) (OAuth2) | Strong | Skipped with a log line if secrets missing |
| GitHub | [Code Search API](https://docs.github.com/en/rest/search) (**requires** token) | Weak | Scores README + description; needs intent or pain+tool |
| dev.to | [Articles API](https://developers.forem.com/api) (free, no key) | Weak | Same weak-source gate as GitHub |
| Upwork / Fiverr | None — see `MANUAL_CHECKLIST.md` | Manual | |

Missing credentials **log a clear skip message** (they no longer fail silently without a trace).

## 5-minute setup

### 1. Clone and install

```bash
git clone <your-repo-url> lead-radar && cd lead-radar
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit CONTACT_EMAIL at minimum
```

### 2. GitHub token (required for GitHub source)

Code search has **no unauthenticated access**. Your local `gh` session must be valid:

```bash
gh auth login -h github.com -s repo
./scripts/set-github-token.sh   # writes .env + Actions secret LEAD_RADAR_GITHUB_TOKEN
```

Or create a [classic PAT](https://github.com/settings/tokens) with `public_repo` and put `GITHUB_TOKEN=ghp_...` in `.env`.

In Actions, the job token is always available as a fallback; a PAT in `LEAD_RADAR_GITHUB_TOKEN` is preferred for reliable code search.

### 3. Reddit script app (recommended)

1. Log in to Reddit → [prefs/apps](https://www.reddit.com/prefs/apps)
2. **create another app…** → type **script**, name `LeadRadar`, redirect `http://localhost:8080`
3. Put client ID + secret in `.env` and as Actions secrets `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET`

Without Reddit credentials the source is skipped (logged).

### 4. LLM triage (optional)

```bash
python main.py --triage cloud    # Gemini → Groq → Cerebras (SIE keys); no Ollama
python main.py --triage local    # Ollama on your machine
```

**Local `make triage-digest`** still uses **Ollama** (`--triage local`). That is not the same as SIE’s cloud stack.

**GitHub Actions** uses **`--triage cloud`** when any of `GEMINI_API_KEY` / `GROQ_API_KEY` / `CEREBRAS_API_KEY` is set (same providers/keys as synaptic-intelligence-engine). Keyword `.jsonl` is still saved pre-triage.

### 5. Webhook (optional)

Set `WEBHOOK_URL` for Slack/Discord top-5 alerts.

### 6. Test locally

```bash
python main.py --dry-run --debug
make test
```

### 7. GitHub Actions secrets

| Secret | Value |
|--------|-------|
| `LEAD_RADAR_GITHUB_TOKEN` | PAT for code search (optional; job token is fallback) |
| `REDDIT_CLIENT_ID` | Reddit app client ID |
| `REDDIT_CLIENT_SECRET` | Reddit app secret |
| `GEMINI_API_KEY` | Preferred cloud triage (SIE) |
| `GROQ_API_KEY` | Fallback cloud triage |
| `CEREBRAS_API_KEY` | Fallback cloud triage |
| `WEBHOOK_URL` | Slack/Discord webhook (optional) |

Copy keys from SIE without printing: `./scripts/sync-llm-secrets-from-sie.sh`

Workflow: daily 13:00 UTC → commits `digests/`, `data/seen.db`, `MANUAL_CHECKLIST.md`, `raw/`.

## Scoring

Edit `config/keywords.yaml`. Three tiers:

- **intent** — looking for help (+3) — phrases, not bare `hire` / `audit`
- **pain** — problem language (+2) — not bare `mess` / `duplicate`
- **tools** — AI coding tools (+1) — `vibe coding`, `cursor ide`, not bare `cursor`

Needs **2+ categories**. Digest threshold is **4** (so tools+pain alone = 3 stays in `raw/` unless boosted). GitHub/dev.to also require intent **or** pain+tool.

## Local triage

```bash
ollama pull qwen3:8b
make triage-digest              # today (UTC)
make triage-digest DAYS=7       # last week
make triage-digest DATE=2026-07-30
make triage-week                # alias for DAYS=7
make triage-digest-force DAYS=7
```

`make triage-digest` pulls, then LLM-filters existing `digests/*.jsonl` — it does **not** re-fetch APIs.

## Output

```
digests/YYYY-MM-DD.md      # human-readable (keyword and/or LLM-triaged)
digests/YYYY-MM-DD.jsonl   # keyword-scored items with full text
raw/YYYY-MM-DD.jsonl       # below-threshold items for tuning
MANUAL_CHECKLIST.md
data/seen.db               # dedup ledger (IDs; clearable via --reset-days)
```

## Ethics & constraints

- Official public APIs only — no scraping of auth-walled platforms
- No vulnerability scanning or probing of live apps
- Descriptive `User-Agent` on every request (set `CONTACT_EMAIL`)
- Exponential backoff on HTTP 429 responses
- Stores only IDs needed for deduplication

## License

MIT — see [LICENSE](LICENSE).

Personal research tool — use responsibly and in accordance with each platform's Terms of Service.
