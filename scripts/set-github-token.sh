#!/usr/bin/env bash
# Store a GitHub token for lead-radar without printing it.
# Prefers: LEAD_RADAR_GITHUB_TOKEN env → gh auth token → prompt via gh secret set.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO="${LEAD_RADAR_REPO:-SynapticFour/lead-radar}"
ENV_FILE="$ROOT/.env"

echo "Lead Radar — configure GitHub API token for code search"
echo "Repo: $REPO"
echo ""

if ! command -v gh >/dev/null 2>&1; then
  echo "error: gh CLI not found. Install: https://cli.github.com/"
  exit 1
fi

if ! gh auth status -h github.com >/dev/null 2>&1; then
  echo "GitHub CLI is not logged in (or the keyring token is invalid)."
  echo "Run:  gh auth login -h github.com -s repo"
  echo "Then re-run this script."
  exit 1
fi

TOKEN="${LEAD_RADAR_GITHUB_TOKEN:-}"
if [[ -z "$TOKEN" ]]; then
  TOKEN="$(gh auth token 2>/dev/null || true)"
fi
if [[ -z "$TOKEN" ]]; then
  echo "error: could not read a token. Create a classic PAT with public_repo"
  echo "  https://github.com/settings/tokens"
  echo "then:  LEAD_RADAR_GITHUB_TOKEN=ghp_... $0"
  exit 1
fi

# Local .env (never commit)
touch "$ENV_FILE"
if grep -q '^GITHUB_TOKEN=' "$ENV_FILE" 2>/dev/null; then
  # replace in place without echoing value
  tmp="$(mktemp)"
  awk -v t="$TOKEN" '
    BEGIN { done=0 }
    /^GITHUB_TOKEN=/ { print "GITHUB_TOKEN=" t; done=1; next }
    { print }
    END { if (!done) print "GITHUB_TOKEN=" t }
  ' "$ENV_FILE" >"$tmp"
  mv "$tmp" "$ENV_FILE"
else
  printf 'GITHUB_TOKEN=%s\n' "$TOKEN" >>"$ENV_FILE"
fi
chmod 600 "$ENV_FILE" 2>/dev/null || true
echo "[ok] wrote GITHUB_TOKEN to .env (gitignored)"

# Actions secret (preferred name; workflow falls back to github.token)
if gh secret set LEAD_RADAR_GITHUB_TOKEN -R "$REPO" -b "$TOKEN" 2>/dev/null; then
  echo "[ok] set Actions secret LEAD_RADAR_GITHUB_TOKEN on $REPO"
else
  echo "[warn] could not set Actions secret (permissions?). Set manually:"
  echo "  gh secret set LEAD_RADAR_GITHUB_TOKEN -R $REPO"
fi

echo "Done. Local runs load .env automatically; Actions uses the secret."
