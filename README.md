# Lead Radar

A low-maintenance monitoring tool that finds businesses struggling with AI-generated ("vibe-coded") codebases — potential clients for AI-codebase-rescue consulting. Runs on a schedule, checks public APIs, scores results, deduplicates, and writes a daily digest.

**No servers. No paid infra.** A GitHub Actions cron job runs daily and commits digests to this repo.

## What it checks

| Source | API | Signal strength |
|--------|-----|-----------------|
| Hacker News | [Algolia HN API](https://hn.algolia.com/) (free, no key) | Strong |
| dev.to | [Articles API](https://developers.forem.com/api) (free, no key) | Weak–medium |
| GitHub | [Code Search API](https://docs.github.com/en/rest/search) (**requires** `GITHUB_TOKEN`) | Weak |
| Reddit | [Official API](https://www.reddit.com/dev/api/) (OAuth2) | Strong |
| Upwork / Fiverr | None — see `MANUAL_CHECKLIST.md` | Manual |

**Source setup:** dev.to requires no setup and is active immediately. GitHub and Reddit need their respective credentials — both sources fail silently (return empty) rather than erroring when a key is missing. Check **Settings → Secrets** to see which are configured.

## 5-minute setup

### 1. Clone and install

```bash
git clone <your-repo-url> lead-radar && cd lead-radar
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit CONTACT_EMAIL at minimum
```

### 2. Register a Reddit script app (~2 min)

1. Log in to Reddit → [prefs/apps](https://www.reddit.com/prefs/apps)
2. Click **create another app…**
3. Choose **script**, name it `LeadRadar`, redirect URI `http://localhost:8080`
4. Copy the **client ID** (under the app name) and **secret**
5. Add to `.env`:
   ```
   REDDIT_CLIENT_ID=your_id
   REDDIT_CLIENT_SECRET=your_secret
   ```

Reddit is optional — the tool skips it silently if credentials are missing.

### 3. GitHub token (required for GitHub source)

The GitHub source uses `/search/code`, which **has no unauthenticated access** — without `GITHUB_TOKEN`, GitHub is skipped entirely (like Reddit without credentials).

Create a [Personal Access Token](https://github.com/settings/tokens) with **`public_repo` scope only** (classic token) or fine-grained read access to public repos.

```
GITHUB_TOKEN=ghp_...
```

In GitHub Actions, the workflow passes the built-in `${{ github.token }}` automatically — no extra secret needed for scheduled runs.

### 4. LLM triage (optional)

Set `ANTHROPIC_API_KEY` to enable a Claude Haiku pass on digest items only — filters semantic false positives (success stories, general discussion) that keyword scoring can't catch. Without it, numeric scoring is used as-is.

```
ANTHROPIC_API_KEY=sk-ant-...
```

### 5. Webhook (optional)

Set `WEBHOOK_URL` to a Slack incoming webhook or Discord webhook URL. Top 5 leads are posted after each run.

### 6. Test locally

```bash
python main.py --dry-run
python main.py --dry-run --debug   # also show score distribution + near-misses
```

Prints today's digest to stdout without writing files, touching the database, or sending webhooks. `--debug` explains why the digest is empty (score distribution, top near-misses at score 2).

### 7. GitHub Actions secrets

In your repo → **Settings → Secrets and variables → Actions**, add:

| Secret | Value |
|--------|-------|
| `REDDIT_CLIENT_ID` | Reddit app client ID |
| `REDDIT_CLIENT_SECRET` | Reddit app secret |
| `ANTHROPIC_API_KEY` | Claude API key for LLM triage (optional) |
| `WEBHOOK_URL` | Slack/Discord webhook (optional) |

The workflow in `.github/workflows/lead-radar.yml` runs daily at 13:00 UTC and commits `digests/`, `data/seen.db`, and `MANUAL_CHECKLIST.md`.

Give the workflow **write** permission to push commits (repo Settings → Actions → General → Workflow permissions → Read and write).

## Configuration

Edit `config/keywords.yaml` to tune search terms without touching code. Three tiers:

- **intent** — actively looking for help (+3)
- **pain** — describing a problem (+2)
- **tools** — AI tool mentions (+1 only when paired with pain or intent)

Items scoring **3+** appear in the digest. Lower scores go to `raw/` for manual review.

## Output

```
digests/YYYY-MM-DD.md   # daily digest, grouped by source, sorted by score
raw/YYYY-MM-DD.jsonl    # below-threshold items for tuning
MANUAL_CHECKLIST.md     # Upwork/Fiverr/showcase links (regenerated each run)
data/seen.db            # dedup ledger (IDs only, never deleted)
```

## Ethics & constraints

- Official public APIs only — no scraping of auth-walled platforms
- No vulnerability scanning or probing of live apps
- Descriptive `User-Agent` on every request (set `CONTACT_EMAIL`)
- Exponential backoff on HTTP 429 responses
- Stores only IDs needed for deduplication

## License

Personal research tool — use responsibly and in accordance with each platform's Terms of Service.
