.PHONY: verify-provenance test smoke lint

verify-provenance:
	uv run --directory .. --no-sync --package lob-paper-reproductions lob-repro evidence build

test:
	uv run --directory .. --no-sync pytest lob-paper-reproductions/tests -q --capture=sys

smoke:
	uv run --directory .. --no-sync --package lob-paper-reproductions python lob-paper-reproductions/scripts/run_reproduction_matrix.py

lint:
	uv run --directory .. --no-sync ruff check lob-paper-reproductions/src lob-paper-reproductions/tests lob-paper-reproductions/scripts
	uv run --directory .. --no-sync ruff format --check lob-paper-reproductions/src lob-paper-reproductions/tests lob-paper-reproductions/scripts
