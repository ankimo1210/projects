# jp_llm_lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **This session's mode:** inline execution (autonomous session; user not present for handoff question). Git commits are deferred — the workspace branch is shared with parallel sessions and the user commits explicitly. Run metadata records HEAD hash + dirty flag instead.

**Goal:** Build an educational, visualization-first lab that pretrains, instruments, evaluates, and SFTs a small Japanese decoder-only Transformer from scratch in PyTorch, per the project spec (CLAUDE.md).

**Architecture:** A `src/jp_llm_lab` package with explicit (non-abstracted) implementations of tokenizers, attention, Transformer blocks, training/eval/generation loops, and instrumentation hooks; scripts drive reproducible runs into `experiments/runs/<id>/` (config + metrics JSONL + checkpoints + samples); notebooks and a static HTML report consume saved artifacts (no retraining needed for analysis).

**Tech Stack:** Python 3.12, PyTorch 2.11 cu128 (RTX 5080 sm_120, BF16), numpy, matplotlib + plotly, jinja2, PyYAML, pytest; uv workspace member of `/home/kazumasa/projects`.

## Global Constraints (from spec, apply to every task)

- Educational clarity over abstraction: attention/blocks/loops are hand-written; `F.scaled_dot_product_attention` allowed only as the *fast* path next to an explicit path, with parity + speed comparison.
- Visualization-first: every major result ships with 数式 → small example → shape trace → figure → observation → interpretation → caveat.
- Every figure gets What / Why / How to read / Observation / Interpretation / Caveat / Next experiment.
- Reproducibility: each run saves config, seed, git hash, package versions, GPU info, tokenizer version, param count, token count, checkpoints, metrics, samples.
- No hardcoded GPU settings — detect CUDA/VRAM/BF16/SDPA/compile at runtime; CPU-only smoke must work.
- Do not download full datasets; fixed snapshots/streaming only. No checkpoints/large data in git. No fabricated numbers; measured vs illustrative data always labeled.
- Special tokens everywhere: `<BOS> <EOS> <PAD> <UNK> <USER> <ASSISTANT>`.
- Tokenizer invariant: `decode(encode(x)) == x` (for in-vocab text; `<UNK>` caveat documented).
- Notebooks run top-to-bottom; analysis never requires retraining (reads `experiments/runs/`).
- Workspace conventions: `uv run --no-sync`, `uv pip install -e <member> --no-deps`, member registration in root `pyproject.toml` members + testpaths + root `conftest.py` import (dir name == package name).

## Hardware baseline (measured 2026-07-12)

RTX 5080, 15.9 GB VRAM, CC 12.0, BF16 ✓, torch 2.11.0+cu128, CUDA 12.8, CPU RAM 47 GB, Python 3.12.3. All required libs already in workspace venv (missing: none).

---

# Milestone 1 — Educational minimum (THIS SESSION)

## File structure

```text
jp_llm_lab/
├── IMPLEMENTATION_PLAN.md            (this file)
├── README.md                         T17
├── pyproject.toml                    T1
├── Makefile                          T1
├── requirements.lock                 T17
├── configs/smoke/{model_s_char.yaml, bigram_char.yaml}          T11/T6
├── data/{manifests/, samples/}       T4  (samples git-ignored except manifest)
├── src/jp_llm_lab/
│   ├── utils/{env.py, seed.py, runmeta.py, io.py}               T2
│   ├── tokenization/{base.py, char_tokenizer.py}                T3
│   ├── data/{sample_corpus.py, batches.py}                      T4/T5
│   ├── models/{config.py, attention.py, blocks.py, transformer.py, bigram.py}  T6-T8
│   ├── generation/sampler.py                                    T9
│   ├── instrumentation/{activation_stats.py, grad_stats.py}     T10
│   ├── training/{train_config.py, trainer.py}                   T11
│   ├── evaluation/eval_lm.py                                    T11
│   ├── visualization/{style.py, curves.py, attention_viz.py, params_viz.py, shapes_viz.py}  T13-T16
│   └── reporting/{report_m1.py, templates/m1.html.j2}           T16
├── scripts/{diagnose_env.py, fetch_sample_corpus.py, train_lm.py, train_bigram.py,
│            bench_attention.py, build_m1_report.py}             T2,T4,T11,T13,T14,T16
├── tools/{nbkit.py, build_notebooks.py}                         T15
├── notebooks/{00,01,03,04,05,06}_*.ipynb (generated+executed)   T15
├── experiments/{cards/, runs/, comparisons/}                    T11+
├── checkpoints/                      (git-ignored)
├── reports/{env/, figures/, html/}   T2,T16
└── tests/ (14 files, see tasks)      T3-T12
```

### Task 1: Skeleton + packaging + workspace registration

**Files:** Create `jp_llm_lab/pyproject.toml` (hatchling, src layout, name `jp-llm-lab`), `jp_llm_lab/Makefile`, `jp_llm_lab/.gitignore` (checkpoints/, data/samples/*.txt, experiments/runs/, reports/html/assets, `__pycache__`). Modify root `pyproject.toml` (members += `"jp_llm_lab"`, testpaths += `"jp_llm_lab/tests"`), root `conftest.py` (`import jp_llm_lab` — dir name == package name shadow fix).

- [x] Write files; `uv pip install -e jp_llm_lab --no-deps`
- [x] Verify: `uv run --no-sync python -c "import jp_llm_lab; print(jp_llm_lab.__version__)"` → `0.1.0`

### Task 2: Environment diagnostics + recommended setup

**Files:** `src/jp_llm_lab/utils/env.py`, `utils/seed.py`, `utils/runmeta.py`, `utils/io.py`, `scripts/diagnose_env.py`. Test: `tests/test_env.py`.

**Interfaces (produced):**
```python
@dataclass EnvReport: cuda_available, gpu_name, vram_gb, capability, bf16_supported,
    sdpa_backends: list[str], compile_available, torch_version, cuda_version,
    cpu_ram_gb, python_version
collect_env_report() -> EnvReport
recommend_setup(r: EnvReport) -> RecommendedSetup   # micro_batch, grad_accum, model_size, dtype, attn_impl — rule table documented in docstring
set_seed(seed: int, deterministic: bool = False) -> None
collect_run_metadata(extra: dict) -> dict            # git hash+dirty, packages, gpu, timestamps
save_json/load_json/append_jsonl/read_jsonl(path)
```
- [x] test: report fields non-null on CPU; recommend_setup monotone in VRAM (4GB < 16GB micro_batch); run `scripts/diagnose_env.py` → prints table + writes `reports/env/env_report.json`

### Task 3: Character tokenizer

**Files:** `src/jp_llm_lab/tokenization/base.py`, `tokenization/char_tokenizer.py`. Test: `tests/test_char_tokenizer.py`.

**Interfaces:**
```python
SPECIAL_TOKENS = ["<PAD>", "<UNK>", "<BOS>", "<EOS>", "<USER>", "<ASSISTANT>"]  # ids 0..5
class CharTokenizer:
    @classmethod train(cls, texts: Iterable[str], min_freq: int = 1) -> "CharTokenizer"
    encode(text, add_bos=False, add_eos=False) -> list[int]
    decode(ids, skip_special=False) -> str
    vocab_size: int; save(path); load(path); token_to_id/id_to_token
```
- [x] tests: round-trip `decode(encode(x)) == x` on Japanese text incl. 改行・句読点・英数; unknown char → `<UNK>` id 1; specials at ids 0..5; save/load identity; vocab sorted-stable (deterministic)

### Task 4: Sample corpus (Aozora Bunko, public domain)

**Files:** `src/jp_llm_lab/data/sample_corpus.py`, `scripts/fetch_sample_corpus.py`. Manifest: `data/manifests/sample_v1.json`.

- [x] Fetch 夏目漱石『こころ』(+『走れメロス』) from aozora.gr.jp zips (cp932→utf-8, strip ruby 《》/｜/［＃…］, header/footer); save `data/samples/*.txt` + manifest {source_url, license: public domain, sha256, chars}. Fallback if network blocked: skip download, use bundled synthetic paragraphs **clearly labeled synthetic** in manifest.
- [x] `load_sample_corpus(name) -> str`; loader validates sha256 against manifest.

### Task 5: Batch pipeline

**Files:** `src/jp_llm_lab/data/batches.py`. Test: `tests/test_batches.py`.

```python
split_tokens(ids: Tensor, val_frac: float) -> (train, val)          # contiguous split
sample_batch(tokens, batch_size, context_len, generator, device) -> (x[B,T], y[B,T])  # y = x shifted by 1
```
- [x] tests: shapes; `y[:, :-1] == x[:, 1:]`; same generator seed → same batch

### Task 6: Bigram LM (count-based + neural)

**Files:** `src/jp_llm_lab/models/bigram.py`, `scripts/train_bigram.py`, `configs/smoke/bigram_char.yaml`. Test: `tests/test_bigram.py`.

```python
class CountBigramLM: fit(ids, vocab_size, alpha=0.5); log_prob_matrix [V,V]; loss(ids)->float; generate(...)
class NeuralBigramLM(nn.Module): logits = Embedding(V,V)(idx); forward(idx, targets)->(logits, loss)
```
- [x] tests: rows of exp(log_prob_matrix) sum to 1; neural bigram trained 200 steps on tiny text reaches loss ≤ count-model loss + 0.1
- [x] Educational check documented: count model == closed-form optimum the neural one converges to.

### Task 7: Explicit causal self-attention + SDPA twin

**Files:** `src/jp_llm_lab/models/attention.py`. Tests: `tests/test_attention.py`, `tests/test_causal_mask.py`.

```python
class CausalSelfAttention(nn.Module):
    # single qkv Linear; attn_impl: "explicit" | "sdpa" switchable at runtime (same params)
    forward(x[B,T,D], need_weights=False) -> (y[B,T,D], attn[B,H,T,T] | None)  # need_weights forces explicit path
```
- [x] tests: attention rows sum to 1 (post-softmax, all layers/heads); strict upper triangle of weights == 0; explicit vs sdpa `allclose(atol=1e-5)` fp32 CPU & GPU; **no-future-leakage**: changing tokens at positions > t leaves logits[:, :t+1] unchanged (full model test lives in test_causal_mask.py)

### Task 8: ClassicalGPT (Model S) + shape trace + param breakdown

**Files:** `src/jp_llm_lab/models/config.py`, `models/blocks.py`, `models/transformer.py`. Tests: `tests/test_shapes.py`, `tests/test_transformer.py`.

```python
@dataclass ModelConfig: vocab_size, d_model=128, n_heads=4, n_layers=4, context_len=256,
    dropout=0.0, attn_impl="sdpa", tie_weights=True, init_std=0.02, residual_scaled_init=True
class ClassicalGPT(nn.Module):   # pre-LN, learned pos emb, GELU MLP(4x), residual, weight tying
    forward(idx[B,T], targets=None) -> (logits[B,T,V], loss|None)
    trace(idx) -> ForwardTrace     # ordered dict name -> tensor (emb, per-layer q/k/v/scores/weights/attn_out/mlp_out/resid, logits, probs)
    param_breakdown() -> dict[str, int]   # token_emb/pos_emb/attn_qkv/attn_proj/mlp/norms/lm_head/total
    set_attn_impl("explicit"|"sdpa")
```
- [x] tests: logits shape [B,T,V]; trace shapes match spec §8.4 table; param_breakdown sums to `numel`; tied weights share storage; Model S total params in [1M, 2M] for V≈2-4k

### Task 9: Generation sampler

**Files:** `src/jp_llm_lab/generation/sampler.py`. Test: `tests/test_generation.py`.

```python
@dataclass SamplingConfig: max_new_tokens, temperature=1.0, top_k=None, top_p=None, greedy=False, seed=None
generate(model, idx[B,T0], cfg) -> (out[B,T0+N], steps: list[StepRecord])
# StepRecord: chosen id/prob, top10 ids/probs, entropy, logprob cumsum — feeds M5 generation anatomy
```
- [x] tests: greedy deterministic across seeds; same seed → identical sample; temperature=1 top_k=None reproducible with generator; context window trimming at context_len

### Task 10: Instrumentation hooks

**Files:** `src/jp_llm_lab/instrumentation/activation_stats.py`, `instrumentation/grad_stats.py`. Tests: `tests/test_instrumentation.py`, `tests/test_nan_detection.py`.

```python
class ActivationRecorder:  # fwd hooks on chosen module types
    attach(model); detach(); stats() -> {layer_name: {rms, mean, std, absmax, kurtosis, zero_frac, outlier_frac}}
grad_stats(model) -> {group: {grad_norm, param_norm, ...}}     # groups: token_emb/pos_emb/attn/mlp/norm/lm_head
update_ratios(before: dict[str,Tensor], model) -> {group: update_norm/param_norm}
find_nonfinite(model_or_stats) -> list[str]                    # NaN/Inf detection
```
- [x] tests: recorder returns stats for every block; hooks detach cleanly (no leak: second forward without recorder unchanged count); injected NaN in a weight → `find_nonfinite` names the layer

### Task 11: Training loop + eval + checkpoint fractions

**Files:** `src/jp_llm_lab/training/train_config.py`, `training/trainer.py`, `evaluation/eval_lm.py`, `scripts/train_lm.py`, `configs/smoke/model_s_char.yaml`. Tests: `tests/test_checkpoint.py`, `tests/test_grad_accum.py`, `tests/test_smoke_cpu.py`.

```python
@dataclass TrainConfig: seed, steps, batch_size, context_len, grad_accum=1, lr, warmup_frac,
    weight_decay, grad_clip=1.0, dtype="bf16"|"fp32", eval_interval, eval_batches,
    checkpoint_fracs=(0,.01,.05,.10,.25,.50,.75,1.0), fixed_prompts: list[str], out_dir
train_lm(model, train_tokens, val_tokens, cfg, tokenizer) -> RunResult
# per-step JSONL: step, tokens_seen, wallclock, loss, lr, grad_norm(groups), clip_hit,
#   update_ratio(groups, every N), tokens_per_sec, vram; per-eval: val_loss, ppl, entropy, top1_conf,
#   activation RMS (recorder every N); per-checkpoint: model+optim+rng state, fixed-prompt generations
estimate_loss(model, tokens, n_batches, ...) -> {loss, ppl, entropy, top1_conf}
```
- [x] tests: checkpoint save→load → identical logits & optimizer resume matches 1 more step; grad-accum: loss grads of B=8 == 2×B=4 accumulated (fp64 CPU, atol 1e-9); CPU smoke: 5 steps on synthetic tokens, metrics JSONL written, no NaN

### Task 12: 1-batch overfit test

**Files:** `tests/test_overfit.py`.
- [x] Model S small variant (2 layers, d=64) on one fixed batch (B=4,T=64) of real corpus tokens, 300 steps, lr 3e-3 → final loss < 0.15 and < 2% of initial. Runs on GPU if available else CPU. This is spec §28-M1 acceptance.

### Task 13: GPU smoke runs (real artifacts)

- [x] `scripts/train_bigram.py --config configs/smoke/bigram_char.yaml` → run dir + count-vs-neural comparison JSON
- [x] `scripts/train_lm.py --config configs/smoke/model_s_char.yaml` → Model S (~1.3M params) on こころ char tokens, ~200-400 steps ≈ 3-6M tokens, BF16, checkpoints at 8 fracs, 5 fixed Japanese prompts sampled (greedy + T=0.7) at every checkpoint
- [x] Experiment card `experiments/cards/m1_model_s_smoke.yaml` filled with result/observation/interpretation/caveats after the run

### Task 14: Attention microbenchmark

**Files:** `scripts/bench_attention.py` → `reports/figures/attn_bench.json`
- [x] explicit vs SDPA forward+backward, fp32/bf16, T∈{128,256,512}, medians + tokens/sec; feeds notebook 05 and report

### Task 15: Notebooks (generated via nbkit, then executed)

**Files:** `tools/nbkit.py` (md/code cell builders + nbclient executor), `tools/build_notebooks.py`, outputs `notebooks/00_project_overview.ipynb`, `01_environment_and_gpu.ipynb`, `03_tokenizer_anatomy.ipynb` (char part; BPE=M2), `04_bigram_language_model.ipynb`, `05_attention_from_scratch.ipynb`, `06_transformer_forward_pass.ipynb`.

- [x] Each notebook: 学習目標 → 前提 → 数式 → 手計算例 → code → 図 → Observation/Interpretation/Caveat → 確認問題 → 次NBへの接続 (Japanese prose, English code)
- [x] `uv run --no-sync python jp_llm_lab/tools/build_notebooks.py --execute` — all execute cleanly top-to-bottom

### Task 16: Milestone 1 HTML report

**Files:** `src/jp_llm_lab/reporting/report_m1.py`, `reporting/templates/m1.html.j2`, `scripts/build_m1_report.py` → `reports/html/index.html` (+`assets/plotly.min.js` once).
- [x] Sections: Overview / Environment / Tokenizer / Bigram / Attention (init vs trained heatmaps, entropy) / Model S anatomy (params, shapes) / Training dynamics (loss·lr·grad·act-RMS·update-ratio·tokens/sec, x-axis step⇄tokens⇄time) / Checkpoint generations table / Overfit check / Limitations. Every figure carries the 7-part interpretation block. Plotly interactive, static site, no server.

### Task 17: Lock + README + full validation

- [x] `uv pip freeze > jp_llm_lab/requirements.lock` (header: shared workspace venv snapshot)
- [x] `README.md` with the spec-mandated disclaimer ("not designed to build a competitive LLM…"), setup, reproduction guide
- [x] `uv run --no-sync pytest jp_llm_lab/tests -q` all green; `uv run --no-sync ruff check jp_llm_lab` clean
- [x] Root-level check: `uv run --no-sync pytest jp_llm_lab/tests -q` from workspace root collects (conftest shadow fix works)

---

# Milestones 2–6 — roadmap (each gets its own detailed plan at start, per scope-check)

**M2 Instrumented training:** corpus snapshots (smoke/pilot/main/validation/calibration/test; FineWeb2-ja availability+license check, streaming, manifests, corpus viz §4.2), educational BPE trainer + merge-process viz + 2K/4K/8K comparison + fast-tokenizer cross-check, notebook 02, activation/grad hook dashboards over real training, attention viz suite (§9: entropy, distance, prev-token/BOS rates, head similarity, virtual pruning), checkpoint comparison, notebooks 13-17 groundwork.
**M3 Controlled experiments:** LR range test (§14.2), batch-size calibration 8K-64K tokens (§14.4), init calibration (§14.3), Model M; ablation chain Classical→RMSNorm→RoPE→SwiGLU→no-bias→SDPA→Modern (§7.3) with experiment cards, 3 seeds for small runs (§18), notebooks 09-12, 18.
**M4 Main pretraining:** Model L (~30-50M, vocab 8192 BPE) on ~100M tokens with full dashboard, fixed-prompt checkpoint generations, scaling notebook 19, model comparison screen (§17).
**M5 Calibration + SFT + generation anatomy:** probability calibration suite (§15: reliability diagrams equal-width/mass, ECE variants, breakdowns, temperature scaling on calibration split only), generation anatomy notebook/HTML (§16), memorization analysis (§20), SFT with assistant-only vs full loss masks (§21) + SFT loss-mask test, notebooks 20-23.
**M6 Final artifact:** evaluation prompt set ≥200 (§19), all-notebook verification, multi-page static HTML site (§23), final report + limitations + reproduction guide, notebook 24.

## Self-review (done)

- Spec coverage M1: §2 env→T2, §5.1 char→T3, bigram/attention/1M model→T6-8, §8 arch viz→T8/T15/T16, overfit→T12, curves/act/grad→T10/T11/T13, M1 HTML→T16, tests §27 (M1 subset: 15 of 17; SFT-mask & temp-scaling tests belong to M5, ECE/calibration-split to M5)→T3-T12. §31 order preserved.
- Placeholder scan: M2-6 items are roadmap pointers by design (separate plans), not task placeholders. M1 tasks carry interfaces+tests.
- Type consistency: `CharTokenizer.encode/decode`, `CausalSelfAttention.forward` tuple, `ClassicalGPT.trace`, `TrainConfig` names checked against each task's consumers.
