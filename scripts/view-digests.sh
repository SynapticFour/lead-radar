#!/usr/bin/env bash
# Show daily digests from origin/main without touching the working tree.
# Usage:
#   view-digests.sh           # latest UTC day
#   view-digests.sh 5         # last 5 UTC days
#   view-digests.sh --date YYYY-MM-DD
set -euo pipefail

REF="${VIEW_REF:-origin/main}"
DAYS=1
DATE=

usage() {
	echo "usage: $0 [N] | --date YYYY-MM-DD" >&2
	exit 1
}

while [[ $# -gt 0 ]]; do
	case "$1" in
		--date)
			[[ $# -ge 2 ]] || usage
			DATE="$2"
			shift 2
			;;
		--days)
			[[ $# -ge 2 ]] || usage
			DAYS="$2"
			shift 2
			;;
		-h|--help)
			usage
			;;
		*)
			if [[ "$1" =~ ^[0-9]+$ ]]; then
				DAYS="$1"
			else
				usage
			fi
			shift
			;;
	esac
done

if ! [[ "$DAYS" =~ ^[0-9]+$ ]] || [[ "$DAYS" -lt 1 ]]; then
	echo "error: days must be a positive integer (got: $DAYS)" >&2
	exit 1
fi

echo "Fetching latest digests from GitHub ($REF)..."
git fetch origin main --quiet

if [[ -n "$DATE" ]]; then
	dates="$DATE"
else
	dates="$(
		python3 -c "
from datetime import datetime, timedelta, timezone
n = int('$DAYS')
today = datetime.now(timezone.utc).date()
for i in range(n):
    print((today - timedelta(days=i)).isoformat())
"
	)"
fi

tmpdir=
cleanup() {
	[[ -n "${tmpdir:-}" && -d "$tmpdir" ]] && rm -rf "$tmpdir"
}
trap cleanup EXIT INT TERM

# Stage content under a throwaway dir (never inside the repo) so nothing is staged/committed.
tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/lead-radar-view.XXXXXX")"
shown=0
missing=0

# Oldest → newest for reading chronological order
while IFS= read -r day; do
	[[ -n "$day" ]] || continue
	path="digests/${day}.md"
	if git cat-file -e "${REF}:${path}" 2>/dev/null; then
		out="$tmpdir/${day}.md"
		git show "${REF}:${path}" >"$out"
		shown=$((shown + 1))
	else
		echo "[view] no digest on $REF for $day" >&2
		missing=$((missing + 1))
	fi
done <<<"$(printf '%s\n' $dates | sort)"

if [[ "$shown" -eq 0 ]]; then
	echo "[view] nothing to show" >&2
	exit 1
fi

echo "[view] read-only from $REF — working tree unchanged ($shown day(s))"
echo ""

if [[ "$shown" -eq 1 ]]; then
	file="$(ls "$tmpdir"/*.md)"
else
	# Concatenate with clear separators for multi-day view
	file="$tmpdir/combined.md"
	first=1
	for f in "$tmpdir"/????-??-??.md; do
		if [[ "$first" -eq 1 ]]; then
			first=0
		else
			printf '\n\n---\n\n' >>"$file"
		fi
		cat "$f" >>"$file"
	done
fi

if [[ -t 1 ]] && command -v less >/dev/null 2>&1; then
	LESS="${LESS:--R}" less -F -X "$file"
else
	cat "$file"
fi
