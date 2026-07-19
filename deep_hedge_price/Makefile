PYTHON ?= python
CONFIG ?= configs/quick.yaml

.PHONY: install test lint train evaluate sensitivity notebook report demo pricing-generate pricing-train pricing-evaluate pricing-report pricing-ablation pricing-demo all clean

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

PRICING_CONFIG ?= configs/pricing_quick.yaml

pricing-generate:
	$(PYTHON) -m deep_hedge_price.cli pricing-generate --config $(PRICING_CONFIG)

pricing-train:
	$(PYTHON) -m deep_hedge_price.cli pricing-train --config $(PRICING_CONFIG)

pricing-evaluate:
	$(PYTHON) -m deep_hedge_price.cli pricing-evaluate --config $(PRICING_CONFIG)

pricing-report:
	$(PYTHON) -m deep_hedge_price.cli pricing-report --config $(PRICING_CONFIG)

pricing-ablation:
	$(PYTHON) -m deep_hedge_price.cli pricing-ablation --config $(PRICING_CONFIG)

pricing-demo:
	$(PYTHON) -m deep_hedge_price.cli pricing-demo --config $(PRICING_CONFIG)

all: test demo

clean:
	@find artifacts/checkpoints artifacts/metrics artifacts/data artifacts/figures -type f ! -name .gitkeep -delete
	@find reports -type f -name '*.html' -delete
	@find notebooks -type d -name .ipynb_checkpoints -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "Generated deep-hedging outputs removed."
