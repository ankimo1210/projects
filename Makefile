# Workspace-wide convenience targets.
#
# Most Python work runs inside a single uv workspace at the repo root
# (members: gto, market-viz, stock, nbody-gpu, line_backup,
#  land_price_api_app, re_invest_os/apps/api,
#  re_invest_os/packages/financial-engine).
#
# `land_price_api_app/` keeps requirements.txt for legacy reference, but
# pyproject.toml is canonical and it is a uv workspace member.
# `johnhull/hullkit` is a workspace member (used by johnhull notebooks).
# `rates_volatility_model/`, `notebooks/` have no managed env.

.PHONY: help install sync lint fmt fmt-fix test clean tree

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
	@echo ""
	@echo "Workspace members:"
	@echo "  gto market-viz stock nbody-gpu line_backup land_price_api_app"
	@echo "  re_invest_os/apps/api re_invest_os/packages/financial-engine"
	@echo "  akinator johnhull/hullkit"
	@echo ""
	@echo "Outside the workspace:"
	@echo "  rates_volatility_model, notebooks (manual envs)"

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
