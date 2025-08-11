.PHONY: help setup-3.12 install run run-nmap clean distclean

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

# Default output dir and args can be overridden:
OUT ?= out
INPUT ?=
ARGS ?= -out $(OUT)

help:
	@echo ""
	@echo "aquapy — Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  make setup-3.12     Create virtualenv with Python 3.12 (via Homebrew path or python3.12 in PATH)"
	@echo "  make install         Install/upgrade deps into $$(VENV) and install Chromium via Playwright (always runs)"
	@echo "  make run             Run aquapy with $$(ARGS). If $$(INPUT) is set, it's passed via -i; otherwise read STDIN."
	@echo "  make run-nmap        Same as run, but adds -nmap."
	@echo "  make clean           Remove build artifacts"
	@echo "  make distclean       Remove venv and output dir"
	@echo ""
	@echo "Variables:"
	@echo "  OUT=out              Output directory (default: out)"
	@echo "  INPUT=targets.txt    Optional: file to use as input instead of STDIN"
	@echo "  ARGS='...'           Extra CLI arguments for aquapy"
	@echo ""
	@echo "Examples:"
	@echo "  make setup-3.12 install"
	@echo "  cat hosts.txt | make run ARGS='-out out -profile mobile -full-page'"
	@echo "  make run INPUT=hosts.txt ARGS='-out out -redirect -ports large'"
	@echo "  make run-nmap INPUT=scan.xml ARGS='-out out'"
	@echo ""

setup-3.12:
	@set -e; \
	if command -v python3.12 >/dev/null 2>&1; then PY=$$(command -v python3.12); \
	elif [ -x /opt/homebrew/bin/python3.12 ]; then PY=/opt/homebrew/bin/python3.12; \
	else echo "python3.12 not found. On macOS: brew install python@3.12"; exit 1; fi; \
	echo "Using $$PY"; \
	"$$PY" -m venv "$(VENV)"; \
	echo "✅ Virtualenv created at $(VENV)"

install:
	@set -e; \
	if [ ! -x "$(PYTHON)" ]; then echo "❌ Missing venv. Run: make setup-3.12"; exit 1; fi; \
	echo "Installing dependencies into $(VENV) ..."; \
	"$(PYTHON)" -m pip install --upgrade pip wheel; \
	"$(PYTHON)" -m pip install -r requirements.txt; \
	"$(PYTHON)" -m playwright install chromium; \
	echo "✅ Dependencies installed"

run:
	@set -e; \
	if [ ! -x "$(PYTHON)" ]; then echo "❌ Missing venv. Run: make setup-3.12 install"; exit 1; fi; \
	if [ -n "$(INPUT)" ]; then IN="-i $(INPUT)"; else IN=""; fi; \
	"$(PYTHON)" -m aquapy $$IN $(ARGS)

run-nmap:
	@set -e; \
	if [ ! -x "$(PYTHON)" ]; then echo "❌ Missing venv. Run: make setup-3.12 install"; exit 1; fi; \
	if [ -n "$(INPUT)" ]; then IN="-i $(INPUT)"; else IN=""; fi; \
	"$(PYTHON)" -m aquapy -nmap $$IN $(ARGS)

clean:
	@rm -rf out __pycache__ aquapy/__pycache__ */__pycache__

distclean: clean
	@rm -rf "$(VENV)"
