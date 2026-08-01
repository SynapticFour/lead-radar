#!/usr/bin/env bash
# Copy GEMINI/GROQ/CEREBRAS keys from synaptic-intelligence-engine/.env into
# lead-radar/.env and GitHub Actions secrets — without printing secret values.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SIE_ENV="${SIE_ENV:-$ROOT/../synaptic-intelligence-engine/.env}"
REPO="${LEAD_RADAR_REPO:-SynapticFour/lead-radar}"
ENV_FILE="$ROOT/.env"

if [[ ! -f "$SIE_ENV" ]]; then
  echo "error: SIE .env not found at $SIE_ENV"
  exit 1
fi

touch "$ENV_FILE"
chmod 600 "$ENV_FILE" 2>/dev/null || true

set_kv() {
  local key="$1" value="$2"
  [[ -z "$value" ]] && return 0
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    local tmp
    tmp="$(mktemp)"
    awk -v k="$key" -v v="$value" '
      BEGIN { done=0 }
      $0 ~ ("^" k "=") { print k "=" v; done=1; next }
      { print }
      END { if (!done) print k "=" v }
    ' "$ENV_FILE" >"$tmp"
    mv "$tmp" "$ENV_FILE"
  else
    printf '%s=%s\n' "$key" "$value" >>"$ENV_FILE"
  fi
}

read_sie() {
  local key="$1"
  # shellcheck disable=SC2162
  grep -E "^${key}=" "$SIE_ENV" | head -1 | cut -d= -f2-
}

synced=0
for key in GEMINI_API_KEY GROQ_API_KEY CEREBRAS_API_KEY GEMINI_MODEL GROQ_MODEL CEREBRAS_MODEL; do
  val="$(read_sie "$key" || true)"
  if [[ -n "$val" ]]; then
    set_kv "$key" "$val"
    echo "[ok] .env ← $key"
    synced=1
  else
    echo "[skip] $key not set in SIE .env"
  fi
done

if [[ "$synced" -eq 0 ]]; then
  echo "error: no LLM keys found in $SIE_ENV"
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "[warn] gh not found — local .env updated only"
  exit 0
fi

for key in GEMINI_API_KEY GROQ_API_KEY CEREBRAS_API_KEY; do
  val="$(read_sie "$key" || true)"
  if [[ -n "$val" ]]; then
    if printf '%s' "$val" | gh secret set "$key" -R "$REPO" >/dev/null; then
      echo "[ok] Actions secret $key on $REPO"
    else
      echo "[warn] failed to set Actions secret $key"
    fi
  fi
done

echo "Done. Daily workflow will use --triage cloud when any key is present."
