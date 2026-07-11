# jp_llm_lab — run everything from the workspace root with `uv run --no-sync`.
# Usage: make -C jp_llm_lab <target>   (or `make <target>` inside jp_llm_lab/)

UV := uv run --no-sync
ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

.PHONY: env corpus test train-bigram train-smoke bench notebooks report m1 lint

env:
	$(UV) python $(ROOT)scripts/diagnose_env.py

corpus:
	$(UV) python $(ROOT)scripts/fetch_sample_corpus.py

test:
	$(UV) pytest $(ROOT)tests -q

train-bigram:
	$(UV) python $(ROOT)scripts/train_bigram.py --config $(ROOT)configs/smoke/bigram_char.yaml

train-smoke:
	$(UV) python $(ROOT)scripts/train_lm.py --config $(ROOT)configs/smoke/model_s_char.yaml

bench:
	$(UV) python $(ROOT)scripts/bench_attention.py

notebooks:
	$(UV) python $(ROOT)tools/build_notebooks.py --execute

report:
	$(UV) python $(ROOT)scripts/build_m1_report.py

lint:
	$(UV) ruff check $(ROOT)

# Milestone 1 end-to-end (after `make corpus`)
m1: env test train-bigram train-smoke bench notebooks report
