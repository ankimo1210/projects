CONFIG ?= configs/quick.yaml
UV_RUN ?= uv run --no-sync

.PHONY: help install test test-slow lint paths options microstructure all notebook report demo full clean

help:
	@echo "rough_volatility targets (CONFIG=$(CONFIG)):"
	@echo "  make install         - sync the uv workspace (editable install of all members)"
	@echo "  make test            - run the fast test suite"
	@echo "  make test-slow       - run the slow stochastic integration tests"
	@echo "  make lint            - ruff check on src/tests/scripts"
	@echo "  make paths           - run path experiments A-C"
	@echo "  make options         - run option experiments D-E"
	@echo "  make microstructure  - run microstructure experiments F-G"
	@echo "  make all             - run all experiments + static figures + standalone report"
	@echo "  make notebook        - build, execute and export the notebook"
	@echo "  make report          - build static figures + standalone HTML report"
	@echo "  make demo            - quick end-to-end: experiments, figures, report, notebook"
	@echo "  make full            - end-to-end with configs/full.yaml"
	@echo "  make clean           - remove generated artifacts and reports"

install:
	uv sync --all-packages

test:
	$(UV_RUN) pytest tests -q -m "not slow"

test-slow:
	$(UV_RUN) pytest tests -q -m slow

lint:
	$(UV_RUN) ruff check src tests scripts

paths:
	$(UV_RUN) python -m rough_volatility.cli paths --config $(CONFIG)

options:
	$(UV_RUN) python -m rough_volatility.cli options --config $(CONFIG)

microstructure:
	$(UV_RUN) python -m rough_volatility.cli microstructure --config $(CONFIG)

all:
	$(UV_RUN) python -m rough_volatility.cli all --config $(CONFIG)
	$(UV_RUN) python -m rough_volatility.cli report --config $(CONFIG)

notebook:
	$(UV_RUN) python scripts/execute_notebook.py --config $(CONFIG)

report:
	$(UV_RUN) python -m rough_volatility.cli report --config $(CONFIG)

demo: all notebook

full:
	$(MAKE) all CONFIG=configs/full.yaml
	$(MAKE) notebook CONFIG=configs/full.yaml

clean:
	find artifacts -type f ! -name ".gitkeep" -delete
	rm -f reports/*.html
	rm -rf notebooks/.ipynb_checkpoints
