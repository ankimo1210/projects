# optimal_execution — run from this directory.
# Uses the workspace root venv via `uv run --no-sync` (see repo-root Makefile).

UV      := uv run --no-sync
CONFIG  ?= configs/quick.yaml
CLI     := $(UV) python -m optimal_execution.cli

.PHONY: help install test test-fast classical lob train-rl evaluate notebook \
        report-en report-ja reports demo all clean lint

help:
	@echo "optimal_execution targets (CONFIG=$(CONFIG)):"
	@echo "  make install    - editable install into the workspace venv"
	@echo "  make test       - pytest (all)"
	@echo "  make test-fast  - pytest -m 'not slow'"
	@echo "  make lint       - ruff lint and format checks"
	@echo "  make classical  - Experiments A-E (schedule world)"
	@echo "  make lob        - Experiments F-G (reactive LOB world)"
	@echo "  make train-rl   - train RL policies (residual + unconstrained)"
	@echo "  make evaluate   - Experiments H-J (strategy comparison, stress, ablation)"
	@echo "  make notebook   - execute EN + JA visual-lab notebooks, export both HTML"
	@echo "  make report-en  - English standalone HTML report"
	@echo "  make report-ja  - Japanese standalone HTML report"
	@echo "  make reports    - both reports"
	@echo "  make demo       - quick end-to-end: classical+lob+train-rl+evaluate+notebook+reports"
	@echo "  make all        - same as demo (honours CONFIG)"
	@echo "  make clean      - remove generated artifacts and reports"

install:
	uv pip install -e . --no-deps

test:
	$(UV) pytest tests

test-fast:
	$(UV) pytest tests -m "not slow"

lint:
	$(UV) ruff check src scripts tests
	$(UV) ruff format --check src scripts tests

classical:
	$(CLI) classical --config $(CONFIG)

lob:
	$(CLI) lob --config $(CONFIG)

train-rl:
	$(CLI) train-rl --config $(CONFIG)

evaluate:
	$(CLI) evaluate --config $(CONFIG)

notebook:
	$(UV) python scripts/execute_notebook.py --config $(CONFIG)

report-en:
	$(CLI) report --config $(CONFIG) --locale en

report-ja:
	$(CLI) report --config $(CONFIG) --locale ja

reports: report-en report-ja

demo:
	$(CLI) all --config configs/quick.yaml

all:
	$(CLI) all --config $(CONFIG)

clean:
	rm -rf artifacts/data/* artifacts/metrics/* artifacts/checkpoints/* artifacts/figures/*
	rm -f reports/*.html
	rm -rf notebooks/_executed .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "cleaned."
