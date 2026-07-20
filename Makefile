# Workspace-wide convenience targets.
#
# Most Python work runs inside a single uv workspace at the repo root
# (members: gto, market-viz, stock, nbody-gpu, line_backup, akinator,
#  autostock, johnhull/hullkit, and the analytics books — see
#  pyproject.toml [tool.uv.workspace] for the canonical list).
#
# `johnhull/hullkit` is a workspace member (used by johnhull notebooks).
# `aisan_lbo_case/` uses requirements.txt; `csharp_calc/` is .NET;
# `rates_volatility_model/`, `notebooks/` have no managed env.

.PHONY: help install sync lint fmt fmt-fix test clean tree report books hull-report hull-book hull-artifacts-check hull-notebooks-check hull-release-check hull-release rough-vol optimal-execution

help:
	@echo "Workspace targets (run from repo root):"
	@echo "  make install  - uv sync --all-packages (creates root .venv)"
	@echo "  make sync     - alias for install"
	@echo "  make lint     - uv run ruff check ."
	@echo "  make fmt      - uv run ruff format --check ."
	@echo "  make fmt-fix  - uv run ruff format ."
	@echo "  make test     - uv run pytest"
	@echo "  make clean    - remove pyc / __pycache__ / .pytest_cache / .ruff_cache"
	@echo "  make tree     - print a project tree (depth 2, ignoring heavy dirs)"
	@echo "  make report   - build the offline analytics portal (analytics/report/site/)"
	@echo "  make books    - build the analytics Jupyter Books"
	@echo "  make hull-report - build the offline johnhull portal (johnhull/report/site/)"
	@echo "  make hull-book   - build the johnhull Jupyter Book (johnhull/book/_build/)"
	@echo "  make hull-artifacts-check - rebuild vol 19-25 in /tmp and compare references"
	@echo "  make hull-notebooks-check - fresh-execute vol 18-25 in /tmp"
	@echo "  make hull-release-check - verify the johnhull A5-A8 release candidate contract"
	@echo "    add HULL_RELEASE_FLAGS=--require-tracked after committing release files"
	@echo "  make hull-release - fresh project tests/lint/notebooks/report/book/release gate"
	@echo "  make rough-vol   - rough_volatility quick demo (experiments + report + notebook)"
	@echo "  make optimal-execution - optimal_execution quick end-to-end visual lab"
	@echo ""
	@echo "Workspace members:"
	@echo "  gto market-viz stock nbody-gpu line_backup akinator autostock"
	@echo "  johnhull/hullkit"
	@echo "  analytics/{linear_algebra,neural_net,bayesian,fourier,laplace,machine_learning}"
	@echo "  analytics/differential_equation/{ode-book,pde-book}"
	@echo "  quantkit deep_hedge_price optimal_execution rough_volatility"
	@echo ""
	@echo "Outside the workspace:"
	@echo "  rates_volatility_model, notebooks, shortest_path, cpp_algo_lab (manual envs)"

install sync:
	uv sync --all-packages

lint:
	uv run --no-sync ruff check .

fmt:
	uv run --no-sync ruff format --check .

fmt-fix:
	uv run --no-sync ruff format .

test:
	uv run --no-sync pytest

report:
	cd analytics/report && PYTHONPATH=. uv run --no-sync python -m report_builder.build
	@echo "Open analytics/report/site/index.html in a browser (works offline)."

books:
	uv run --no-sync jupyter-book build analytics/linear_algebra/book/
	uv run --no-sync jupyter-book build analytics/neural_net/book/
	uv run --no-sync jupyter-book build analytics/bayesian/book/
	uv run --no-sync jupyter-book build analytics/laplace/book/
	uv run --no-sync jupyter-book build analytics/fourier/book/
	uv run --no-sync jupyter-book build analytics/differential_equation/ode-book/book/
	uv run --no-sync jupyter-book build analytics/differential_equation/pde-book/book/
	uv run --no-sync jupyter-book build analytics/machine_learning/book/

hull-report:
	PYTHONPATH=johnhull/report uv run --no-sync python -m report_builder.build
	@echo "Open johnhull/report/site/index.html in a browser (works offline)."

hull-book:
	uv run --no-sync jupyter-book build johnhull/book/

hull-notebooks-check:
	uv run --no-sync --package hullkit python johnhull/scripts/verify_frontier_notebooks.py

hull-artifacts-check:
	uv run --no-sync --package hullkit python johnhull/scripts/verify_frontier_artifacts.py

hull-release-check:
	PYTHONPATH=johnhull/report uv run --no-sync --package hullkit python johnhull/scripts/verify_release.py $(HULL_RELEASE_FLAGS)

hull-release:
	uv run --no-sync --package deep-hedge-price pytest -s -q deep_hedge_price/tests
	uv run --no-sync --package hullkit pytest -s -q johnhull/hullkit/tests johnhull/report/tests
	uv run --no-sync ruff check deep_hedge_price/src deep_hedge_price/tests deep_hedge_price/scripts deep_hedge_price/notebooks/02_neural_pricing_surrogate.ipynb johnhull/hullkit/src johnhull/hullkit/tests johnhull/scripts johnhull/report/report_builder johnhull/report/tests
	uv run --no-sync ruff format --check deep_hedge_price/src deep_hedge_price/tests deep_hedge_price/scripts deep_hedge_price/notebooks/02_neural_pricing_surrogate.ipynb johnhull/hullkit/src johnhull/hullkit/tests johnhull/scripts johnhull/report/report_builder johnhull/report/tests
	$(MAKE) hull-artifacts-check
	$(MAKE) hull-notebooks-check
	$(MAKE) hull-report
	$(MAKE) hull-book
	$(MAKE) hull-release-check

rough-vol:
	cd rough_volatility && $(MAKE) demo

optimal-execution:
	cd optimal_execution && $(MAKE) demo

clean:
	@find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache -o -name .mypy_cache \) \
	  -not -path './.git/*' -not -path '*/.venv/*' -not -path '*/node_modules/*' \
	  -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -name '*.pyc' -not -path './.git/*' -not -path '*/.venv/*' -delete 2>/dev/null || true
	@echo "cleaned."

tree:
	@command -v tree >/dev/null 2>&1 && \
	  tree -L 2 -a -I '.git|.venv|venv|node_modules|__pycache__|_data|_logs|_archive|target|dist|build|.next' || \
	  find . -maxdepth 2 -not -path './.git*' -not -path '*/.venv*' -not -path '*/node_modules*' -not -path './_data*' -not -path './_logs*' -not -path './_archive*' | sort
