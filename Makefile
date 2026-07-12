.PHONY: install run dry-run local-analysis local-analysis-dry reset-today reset-all

install:
	pip install -r requirements.txt

run:
	python main.py

dry-run:
	python main.py --dry-run

## Run with local Ollama triage (qwen3:8b). Requires: ollama serve, ollama pull qwen3:8b
local-analysis:
	@echo "Using local Ollama triage — make sure 'ollama serve' is running."
	python main.py --triage local

local-analysis-dry:
	@echo "Using local Ollama triage (dry run, no writes/commits) — make sure 'ollama serve' is running."
	python main.py --dry-run --triage local

## Re-evaluate everything seen today with local triage (useful right after a scoring/config change)
reset-today:
	python main.py --reset-days 1 --triage local

## Re-evaluate the entire ledger with local triage
reset-all:
	python main.py --reset-days 0 --triage local
