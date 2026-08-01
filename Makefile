PYTHON ?= python3
WITH_OLLAMA := ./scripts/with-ollama.sh
DAYS ?= 1
DATE ?=

.DEFAULT_GOAL := help

.PHONY: help install run dry-run pull triage-digest triage-digest-force \
        triage-week local-analysis local-analysis-dry reset-today reset-all test

help:
	@echo "Lead Radar — verfügbare Befehle:"
	@echo ""
	@echo "  Täglicher Workflow:"
	@echo "    make triage-digest              git pull + LLM-Triage (heute, UTC)"
	@echo "    make triage-digest DAYS=7       letzte N UTC-Tage triagieren"
	@echo "    make triage-digest DATE=YYYY-MM-DD   einen Tag triagieren"
	@echo "    make triage-digest-force        wie oben, erzwingt erneute Triage"
	@echo "    make triage-week                Alias für DAYS=7"
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
	@echo "    make test                 scoring unit tests"
	@echo ""
	@echo "  Ollama (für triage-* / local-* / reset-*):"
	@echo "    ollama pull qwen3:8b      einmalig, Modell laden"
	@echo ""
	@echo "  GitHub token (nach 'gh auth login'):"
	@echo "    ./scripts/set-github-token.sh"

install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTHON) -m pytest tests/ -q

run:
	$(PYTHON) main.py

dry-run:
	$(PYTHON) main.py --dry-run --debug

pull:
	@echo "Pulling latest keyword digest from GitHub..."
	@git fetch origin main
	@if [ "$$(git rev-parse HEAD)" = "$$(git rev-parse origin/main)" ]; then \
		echo "[pull] already up to date"; \
	else \
		git pull --ff-only origin main && echo "[pull] updated"; \
	fi

# DATE= takes precedence over DAYS=
TRIAGE_ARGS := --triage-only --triage local
ifneq ($(DATE),)
  TRIAGE_ARGS += --date $(DATE)
else
  TRIAGE_ARGS += --days $(DAYS)
endif

triage-digest: pull
	@echo "LLM triage on keyword digest(s)..."
	$(WITH_OLLAMA) $(PYTHON) main.py $(TRIAGE_ARGS)

triage-digest-force: pull
	$(WITH_OLLAMA) $(PYTHON) main.py $(TRIAGE_ARGS) --force

triage-week:
	@$(MAKE) triage-digest DAYS=7

local-analysis:
	$(WITH_OLLAMA) $(PYTHON) main.py --triage local

local-analysis-dry:
	$(WITH_OLLAMA) $(PYTHON) main.py --dry-run --debug --triage local

reset-today:
	$(WITH_OLLAMA) $(PYTHON) main.py --reset-days 1 --triage local

reset-all:
	$(WITH_OLLAMA) $(PYTHON) main.py --reset-days 0 --triage local
