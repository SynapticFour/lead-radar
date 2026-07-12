PYTHON ?= python3

.PHONY: install run dry-run local-analysis local-analysis-dry reset-today reset-all

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) main.py

dry-run:
	$(PYTHON) main.py --dry-run

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
