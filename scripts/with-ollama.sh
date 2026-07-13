#!/bin/sh
# Start ollama serve only if not already running; stop on exit if we started it.
set -e
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
PIDFILE=".ollama.pid"
STARTED=

cleanup() {
	if [ -n "$STARTED" ] && [ -f "$PIDFILE" ]; then
		pid=$(cat "$PIDFILE")
		echo "[ollama] stopping background server (pid $pid)..."
		kill "$pid" 2>/dev/null || true
		rm -f "$PIDFILE"
	fi
}
trap cleanup EXIT INT TERM

if curl -sf "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
	echo "[ollama] already running"
else
	if ! command -v ollama >/dev/null 2>&1; then
		echo "[ollama] not installed — https://ollama.com"
		exit 1
	fi
	echo "[ollama] starting ollama serve..."
	ollama serve >/dev/null 2>&1 &
	echo $! > "$PIDFILE"
	STARTED=1
	i=0
	while [ $i -lt 30 ]; do
		if curl -sf "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
			echo "[ollama] ready"
			break
		fi
		i=$((i + 1))
		sleep 1
	done
	if ! curl -sf "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
		echo "[ollama] failed to start within 30s"
		exit 1
	fi
fi

exec "$@"
