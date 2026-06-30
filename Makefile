.PHONY: setup run dashboard test eval load-test demo clean compile

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn
PYTEST := $(VENV)/bin/pytest
STREAMLIT := $(VENV)/bin/streamlit

setup:
	@if [ -d .venv ] && [ -L .venv ]; then \
		echo "Using existing .venv symlink"; \
	elif echo "$$PWD" | grep -q ':'; then \
		mkdir -p $(HOME)/.venvs; \
		python3 -m venv $(HOME)/.venvs/routewise-gateway; \
		ln -sfn $(HOME)/.venvs/routewise-gateway .venv; \
	else \
		python3 -m venv $(VENV); \
	fi
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run:
	$(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

dashboard:
	$(STREAMLIT) run ui/dashboard.py --server.port 8501

test:
	$(PYTEST) -v

eval:
	$(PYTHON) scripts/run_eval.py

load-test:
	$(PYTHON) scripts/load_test.py

demo:
	$(PYTHON) scripts/demo_requests.py

compile:
	$(PYTHON) -m compileall app

clean:
	rm -rf $(VENV) __pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -f data/routewise.db data/routewise.db-journal
