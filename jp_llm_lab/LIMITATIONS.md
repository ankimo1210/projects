# Limitations

This project is an educational lab. Its results make LLM internals *observable*;
they are **not** evidence about competitive-scale models. Read every conclusion
with these limits in mind.

## Scale
- Models are tiny: Model S ≈ 1.1M, Model M ≈ 10M, Model L ≈ 30M parameters.
  Real LLMs are 100–10000× larger.
- Training is short: Model L saw ~98M tokens (<1 epoch of the 108M-token
  snapshot). Most experiments use the 10M-token pilot at <1 epoch.
- Absolute generation quality is low. Model L produces fluent-looking Japanese
  that is frequently **factually wrong** (e.g. "日本の首都は上海") and cannot do
  arithmetic sequences. This is expected and is itself a teaching point, not a
  bug to fix.

## Statistics
- Most runs are a single seed. The ablation chain uses 3 seeds — enough to see
  effect-size-vs-noise, but the confidence intervals are coarse. The sign of
  small effects (e.g. bias-free) is unresolved.
- Reported ± values are sample standard deviations over few seeds, not rigorous
  confidence intervals.

## Comparability
- **Char and BPE losses/perplexities are not comparable** (different vocab, so
  different units: ln V = 7.63 for char-2068 vs 9.01 for BPE-8192). Only compare
  within the same tokenizer.
- Parameter counts across the ablation are only *approximately* equal (±2%;
  SwiGLU width chosen to match GELU).
- The scaling sweep uses a fixed token budget for all sizes, so it is a *slice*
  at fixed compute, not a compute-optimal (Chinchilla) frontier. The largest
  model looks worst there precisely because it is data-starved.

## Interpretation hazards (called out at each figure)
- **Attention weights are not explanations.** High attention weight ≠ high
  causal contribution. The head-ablation and activation-patching experiments
  are the causal counterpart; even they (simple zeroing) under-count head
  redundancy.
- **Next-token calibration is not factual correctness.** Model L is well
  calibrated on next-token prediction (T ≈ 0.98) while still generating false
  statements. Calibration says nothing about hallucination rate.
- **Low validation loss does not prove generalization.** The memorization
  analysis (train-prefix vs val-prefix exact-match) is the direct check.
- **2-D embedding projections (PCA) discard information;** cluster shapes depend
  on the method. Do not over-read distances.
- **Diversity metrics (distinct-n) are proxies, not quality.** Legitimately
  repetitive text (lists, fixed phrases) scores low.
- **Cloze "accuracy" is noisy** for particles (multiple valid answers); the
  number-sequence cloze items are a cleaner probe.

## Environment / engineering
- `torch.compile` could not be benchmarked here: the Inductor backend needs a
  C++ compiler that is absent in this WSL environment. Recorded honestly rather
  than omitted; it may help where the toolchain exists.
- Corpus cleaning is minimal: exact-dedup only (no near-duplicate removal), a
  Japanese-ratio + length filter, and Aozora markup stripping. No toxicity or
  PII filtering.
- Snapshots are prefixes of a single streaming pass over FineWeb-2 / Wikipedia;
  they are reproducible given the same stream order but are not a random sample.

## Not attempted
- Long-context extrapolation tests (where RoPE should widen its lead).
- Compute-optimal scaling (per-size optimal token counts).
- Calibration breakdowns by token frequency / character class.
- Web-vs-Wikipedia training comparison at Model L scale.
- Multi-turn SFT, RLHF, or any preference optimization.
