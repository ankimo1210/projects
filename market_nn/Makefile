.PHONY: verify-provenance test smoke lint

verify-provenance:
	uv run --directory .. --no-sync --package lob-paper-reproductions lob-repro evidence build

test:
	uv run --directory .. --no-sync pytest market_nn/tests -q --capture=sys

smoke:
	uv run --directory .. --no-sync --package lob-paper-reproductions python market_nn/scripts/run_reproduction_matrix.py

lint:
	uv run --directory .. --no-sync ruff check market_nn/src market_nn/tests market_nn/scripts
	uv run --directory .. --no-sync ruff format --check market_nn/src market_nn/tests market_nn/scripts
