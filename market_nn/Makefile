.PHONY: verify-provenance test smoke lint paper-corpus paper-corpus-formulas paper-corpus-verify-sources paper-corpus-check

DOCLING_VERSION := 2.114.0
PAPER_CORPUS_ARGS ?=

verify-provenance:
	uv run --directory .. --no-sync --package lob-paper-reproductions lob-repro evidence build

test:
	uv run --directory .. --no-sync pytest market_nn/tests -q --capture=sys

smoke:
	uv run --directory .. --no-sync --package lob-paper-reproductions python market_nn/scripts/run_reproduction_matrix.py

lint:
	uv run --directory .. --no-sync ruff check market_nn/src market_nn/tests market_nn/scripts
	uv run --directory .. --no-sync ruff format --check market_nn/src market_nn/tests market_nn/scripts

paper-corpus:
	uvx --from docling==$(DOCLING_VERSION) python scripts/build_paper_corpus.py --overwrite $(PAPER_CORPUS_ARGS)

paper-corpus-formulas:
	uvx --from docling==$(DOCLING_VERSION) python scripts/repair_paper_formulas.py

paper-corpus-verify-sources:
	uv run --directory .. --no-sync python market_nn/scripts/verify_arxiv_formulas.py \
		--download \
		--output market_nn/tmp/pdfs/arxiv-formula-report.json \
		--matches-output market_nn/manifests/formula_source_matches.json
	uvx --from docling==$(DOCLING_VERSION) python scripts/repair_paper_formulas.py

paper-corpus-check:
	uvx --from docling==$(DOCLING_VERSION) python scripts/build_paper_corpus.py --check-only
