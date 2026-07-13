PYTHON ?= python3
WITH_OLLAMA := ./scripts/with-ollama.sh

.DEFAULT_GOAL := help

.PHONY: help install run dry-run pull triage-digest triage-digest-force \
        local-analysis local-analysis-dry reset-today reset-all

help:
	@echo "Lead Radar — verfügbare Befehle:"
	@echo ""
	@echo "  Täglicher Workflow:"
	@echo "    make triage-digest        git pull + LLM-Triage (Ollama start/stop automatisch)"
	@echo "    make triage-digest-force  wie oben, erzwingt erneute Triage"
	@echo ""
	@echo "  Vollständiger Lauf (fetch + score, lokal):"
	@echo "    make run                  keyword-Digest schreiben"
	@echo "    make dry-run              preview, keine Dateien"
	@echo "    make local-analysis       fetch + score + LLM-Triage"
	@echo "    make local-analysis-dry   preview mit LLM-Triage"
	@echo ""
	@echo "  Nach Scoring-/Config-Änderung:"
	@echo "    make reset-today          ledger (1 Tag) leeren + fetch + LLM"
	@echo "    make reset-all            gesamtes ledger leeren + fetch + LLM"
	@echo ""
	@echo "  Setup:"
	@echo "    make install              pip install -r requirements.txt"
	@echo ""
	@echo "  Ollama (für triage-* / local-* / reset-*):"
	@echo "    ollama pull qwen3:8b      einmalig, Modell laden"

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) main.py

dry-run:
	$(PYTHON) main.py --dry-run

pull:
	@echo "Pulling latest keyword digest from GitHub..."
	@git fetch origin main
	@if [ "$$(git rev-parse HEAD)" = "$$(git rev-parse origin/main)" ]; then \
		echo "[pull] already up to date"; \
	else \
		git pull --ff-only origin main && echo "[pull] updated"; \
	fi

triage-digest: pull
	@echo "LLM triage on keyword digest only..."
	$(WITH_OLLAMA) $(PYTHON) main.py --triage-only --triage local

triage-digest-force: pull
	$(WITH_OLLAMA) $(PYTHON) main.py --triage-only --triage local --force

local-analysis:
	$(WITH_OLLAMA) $(PYTHON) main.py --triage local

local-analysis-dry:
	$(WITH_OLLAMA) $(PYTHON) main.py --dry-run --triage local

reset-today:
	$(WITH_OLLAMA) $(PYTHON) main.py --reset-days 1 --triage local

reset-all:
	$(WITH_OLLAMA) $(PYTHON) main.py --reset-days 0 --triage local
