PYTHON ?= python
CONFIG ?= configs/quick.yaml

.PHONY: install test lint train evaluate sensitivity notebook report demo all clean

install:
	@if command -v uv >/dev/null 2>&1; then uv pip install -e ".[dev]"; else $(PYTHON) -m pip install -e ".[dev]"; fi

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check src tests scripts

train:
	$(PYTHON) -m deep_hedge_price.cli train --config $(CONFIG)

evaluate:
	$(PYTHON) -m deep_hedge_price.cli evaluate --config $(CONFIG)

sensitivity:
	$(PYTHON) -m deep_hedge_price.cli sensitivity --config $(CONFIG)

report:
	$(PYTHON) -m deep_hedge_price.cli report --config $(CONFIG)

notebook: report
	$(PYTHON) scripts/execute_notebook.py --config $(CONFIG)

demo:
	$(PYTHON) scripts/run_demo.py --config $(CONFIG)

all: test demo

clean:
	@find artifacts/checkpoints artifacts/metrics artifacts/data artifacts/figures -type f ! -name .gitkeep -delete
	@find reports -type f -name '*.html' -delete
	@find notebooks -type d -name .ipynb_checkpoints -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "Generated deep-hedging outputs removed."
