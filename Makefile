PYTHON ?= python3

.PHONY: install run dry-run local-analysis local-analysis-dry reset-today reset-all triage-digest triage-digest-force

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) main.py

dry-run:
	$(PYTHON) main.py --dry-run

## Pull latest keyword digest from GitHub, then LLM-triage it (no re-fetch)
triage-digest:
	@echo "Pulling latest keyword digest from GitHub..."
	@git fetch origin main
	@if [ "$$(git rev-parse HEAD)" = "$$(git rev-parse origin/main)" ]; then \
		echo "[pull] already up to date"; \
	else \
		git pull --ff-only origin main && echo "[pull] updated"; \
	fi
	@echo "LLM triage on keyword digest only (ollama serve must be running)..."
	$(PYTHON) main.py --triage-only --triage local

triage-digest-force:
	@git fetch origin main
	@if [ "$$(git rev-parse HEAD)" != "$$(git rev-parse origin/main)" ]; then \
		git pull --ff-only origin main; \
	fi
	$(PYTHON) main.py --triage-only --triage local --force

## Run with local Ollama triage (qwen3:8b). Requires: ollama serve, ollama pull qwen3:8b
local-analysis:
	@echo "Using local Ollama triage — make sure 'ollama serve' is running."
	$(PYTHON) main.py --triage local

local-analysis-dry:
	@echo "Using local Ollama triage (dry run, no writes/commits) — make sure 'ollama serve' is running."
	$(PYTHON) main.py --dry-run --triage local

## Re-evaluate everything seen today with local triage (useful right after a scoring/config change)
reset-today:
	$(PYTHON) main.py --reset-days 1 --triage local

## Re-evaluate the entire ledger with local triage
reset-all:
	$(PYTHON) main.py --reset-days 0 --triage local
