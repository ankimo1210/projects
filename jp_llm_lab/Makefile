# jp_llm_lab — run everything from the workspace root with `uv run --no-sync`.
# Usage: make -C jp_llm_lab <target>   (or `make <target>` inside jp_llm_lab/)

UV := uv run --no-sync
ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

.PHONY: env corpus test train-bigram train-smoke bench report m1 lint \
        snapshots tokenizers train-m calibrations ablation train-l scaling \
        m5-analysis eval site notebooks-all all

# ---- Milestone 1 (char, sample corpus) ----
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

report:
	$(UV) python $(ROOT)scripts/build_m1_report.py

lint:
	$(UV) ruff check $(ROOT)

m1: env test train-bigram train-smoke bench report
	$(UV) python $(ROOT)tools/build_notebooks.py --execute

# ---- Milestone 2 (snapshots, BPE, Model M) ----  (needs network for snapshots)
snapshots:
	$(UV) python $(ROOT)scripts/fetch_snapshots.py --source all

tokenizers:
	$(UV) python $(ROOT)scripts/train_tokenizers.py

train-m:
	$(UV) python $(ROOT)scripts/run_experiment.py --config $(ROOT)configs/pilot/model_m_classical.yaml
	$(UV) python -m jp_llm_lab.reporting.analysis_artifacts $(ROOT)experiments/runs/m2_model_m_classical_seed42
	$(UV) python $(ROOT)scripts/corpus_report.py

# ---- Milestone 3 (calibrations, ablation) ----
calibrations:
	$(UV) python $(ROOT)scripts/run_calibrations.py

ablation:
	$(UV) python $(ROOT)scripts/run_ablation.py --seeds 3 --steps 300

# ---- Milestone 4 (Model L, scaling) ----
train-l:
	$(UV) python $(ROOT)scripts/run_experiment.py --config $(ROOT)configs/main/model_l_modern.yaml
	$(UV) python -m jp_llm_lab.reporting.analysis_artifacts $(ROOT)experiments/runs/m4_model_l_modern_seed42

scaling:
	$(UV) python $(ROOT)scripts/run_scaling.py --steps 500

# ---- Milestone 5 (calibration, generation, memorization, SFT) ----
m5-analysis:
	$(UV) python $(ROOT)scripts/run_m5_analysis.py

# ---- Milestone 6 (eval, site) ----
eval:
	$(UV) python $(ROOT)scripts/run_eval.py

site:
	$(UV) python $(ROOT)scripts/build_site.py

notebooks-all:
	$(UV) python $(ROOT)tools/build_notebooks.py --execute
	$(UV) python $(ROOT)tools/build_notebooks_m2.py --execute
	$(UV) python $(ROOT)tools/build_notebooks_m3.py --execute
	$(UV) python $(ROOT)tools/build_notebooks_m4m5.py --execute
	$(UV) python $(ROOT)tools/build_notebooks_m6.py --execute

# Full pipeline (long — trains all models). Assumes `make corpus snapshots tokenizers`.
all: m1 train-m calibrations ablation train-l scaling m5-analysis eval site notebooks-all report
