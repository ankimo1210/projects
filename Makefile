# Workspace-wide convenience targets.
# Each sub-project keeps its own toolchain; these targets fan out across them.
# A project failing does not abort the rest (we intentionally trail || true).

UV_PROJECTS := gto re_invest_os market-viz stock nbody-gpu line_backup

.PHONY: help install lint test fmt clean tree

help:
	@echo "Workspace targets:"
	@echo "  make install   - uv sync across uv-managed projects"
	@echo "  make lint      - ruff check across uv-managed projects"
	@echo "  make fmt       - ruff format --check across uv-managed projects"
	@echo "  make test      - pytest -q across uv-managed projects"
	@echo "  make clean     - remove pyc / __pycache__ / .pytest_cache / .ruff_cache"
	@echo "  make tree      - print a project tree (depth 2, ignoring heavy dirs)"
	@echo
	@echo "UV projects: $(UV_PROJECTS)"
	@echo "Other projects (johnhull, rates_volatility_model, notebooks, land_price_api_app)"
	@echo "manage their own envs — run their tooling from inside the project."

install:
	@for p in $(UV_PROJECTS); do \
	  echo "--- uv sync: $$p ---"; \
	  (cd $$p && uv sync) || echo "  (skipped or failed: $$p)"; \
	done

lint:
	@for p in $(UV_PROJECTS); do \
	  echo "--- ruff check: $$p ---"; \
	  (cd $$p && uv run --no-sync ruff check .) || true; \
	done

fmt:
	@for p in $(UV_PROJECTS); do \
	  echo "--- ruff format --check: $$p ---"; \
	  (cd $$p && uv run --no-sync ruff format --check .) || true; \
	done

test:
	@for p in $(UV_PROJECTS); do \
	  echo "--- pytest: $$p ---"; \
	  (cd $$p && uv run --no-sync pytest -q) || true; \
	done

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
