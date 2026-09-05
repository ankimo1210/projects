# Protocol — feedback_round_01 / fable

Written before any experiment was run (08:47 UTC). Later amendments are appended
under "Amendments" with their timestamp; earlier text is never rewritten.

## Assignment and time budget

- MODEL_KEY: `fable`. The prompt carried the unsubstituted placeholder; the value is taken from the
  explicit in-session user statement "you are Fable" and from the original submission directory
  `results/fable` that this session created. Recorded in `round_summary.json` as
  "assignment confirmed from session, placeholder not substituted".
- Round start (first real work): **2026-09-05T08:44:34Z** (epoch 1788597874).
  Hard stop 09:44:34Z. New design changes stop at 09:34:34Z; the last 10 minutes are verification and saving.
- Interpreter: `PYTHON_BIN` (CPython 3.12.11; numpy 2.5.2, pandas 2.3.3, scipy 1.18.1, matplotlib 3.11.1, pytest 8.4.2).
  Executed only; its environment is neither inspected nor modified. `PYTHONDONTWRITEBYTECODE=1`,
  `MPLCONFIGDIR` and `TMPDIR` inside `audit/`, pytest run with `-p no:cacheprovider`.
- Original submission is read-only. All commands run on copies (`audit/baseline_workspace` for reproduction,
  `submission/` for the improved version).

## Scales that are reported separately (never mixed)

| scale | quantity | unit |
|---|---|---|
| S1 synthetic truth | zero-rate and instantaneous-forward RMSE/max vs known curve on the dense grid, per tenor band | bp |
| S2 public observations | in-sample and grouped-holdout repricing error, yield-equivalent (bond price error / dollar duration) | bp |
| S3 pricing/convention | price or par-rate difference between independent pricer and package pricer for a given D(T) | bp (rates) / points (bonds) |
| S4 format/consistency | schema keys, finiteness, DF positivity, forward–zero consistency, determinism | pass/fail |

Tenor bands: short `T<=2`, mid `2<T<15`, long `T>=15`. Empty bands are reported as "missing", not zero.

## Hypotheses (H) and how each can be rejected

- H1 (pricing correctness, integer maturities): for integer-year deposits/OIS/bonds the package price equals an
  independently coded price (explicit cash-flow list, no shared schedule code) to < 1e-9 for any given D(T),
  including negative-rate and humped curves. Rejected if any |diff| > 1e-9 (rates, decimal) or 1e-7 points (bonds).
- H2 (fractional-maturity convention): the public spec does not pin the payment dates of 1.25Y/1.5Y OIS and
  short-stub bonds. The package's `forward` rule is one admissible reading. Test: price the same instrument
  under the four rules on synthetic D(T) and record the spread of prices (S3). Outcome is by construction
  "未確定" (unresolved); the experiment measures the size of the ambiguity and whether it is large enough to
  matter for the curve (compare with S2 residuals). No rule is declared correct from fit quality.
- H3 (unit handling): PERCENT / DECIMAL / BP / PRICE_POINTS conversions round-trip a known quote to the same
  decimal; negative rates keep D(T) > 0. Rejected by any mismatch.
- H4 (tenor-dependent penalty and robust layer generalise): on synthetic markets built from several shapes
  (flat, steep upward, inverted, humped, negative front end) with the *same* schedule convention used for
  fitting, the advanced model's S1 error is not worse than the baseline's in the mid and long bands and not
  more than 2 bp worse in the short band, and remains bounded (< 10 bp zero RMSE) under 20 % missing quotes and
  low-liquidity (wide spread) conditions. Rejected if any shape/condition shows advanced zero RMSE > baseline + 2 bp
  in a band, or a divergence (> 10 bp) that the baseline does not show.
- H5 (forward consistency): the analytic instantaneous forward on the grid equals `-Δlog D/Δt` computed on a
  4× finer grid to < 0.5 bp, and the error halves-or-better when the grid is refined (convergence). Rejected otherwise.
- H6 (format): `sensitivity.json` currently stores a list under `checks`; the round requires ≥3 named
  top-level experiment keys with condition / results / interpretation. `model_comparison.json` must carry units.
  HTML headings must carry the exact English labels. These are S4 items and are not counted as numerical improvement.

## Splits

- Public data: the existing grouped 5-fold split (maturity clusters round-robin, first and last cluster always in
  train). Fold membership is fixed by the cleaning output and is identical before/after any change; re-use
  `outputs/diagnostics/holdout_predictions.csv` definitions. Band-level metrics are computed from the same
  per-instrument holdout predictions.
- Synthetic data: no split needed — the truth curve is known; errors measured on the dense grid.
  Instruments and noise are generated from a fixed seed per scenario (seed = 20260115 + scenario index).

## Adoption criteria (fixed before experiments)

A code change to the numerical pipeline is adopted only if, on the same split/definition:
1. it fixes a confirmed pricing/unit defect (H1/H3), or
2. it improves synthetic S1 zero RMSE in at least two shapes without worsening any band of any shape by more
   than 1 bp AND does not worsen public grouped-holdout precision-weighted RMSE (S2) by more than 0.1 bp, or
3. it is a pure format/diagnostic addition that leaves every numerical output byte-identical (verified by hash).
Anything else is recorded as "not adopted" with the numbers.

Experiment versions (kept as separate runs under `audit/tmp/`): V1 reproduction, V2 pricing-only change (or
"no change" with justification), V3 pricing fixed + one design factor, V4 final validated version.

## Metrics definitions

- RMSE(bp) = sqrt(mean(e²))·1e4 with e in decimal rate units; precision-weighted RMSE uses weights 1/base_scale².
- Improvement rate = (before − after)/before, only when before > 0 and both sides use identical definitions.

## Amendments

(none yet)

- 09:01 UTC — The V3 synthetic run exposed a second failure mode (humped shape + 20 % missing quotes: three lone
  front-end deposits rejected, 23 bp front-end error). Two single-factor candidates were added, each run separately:
  V4a = leave-tenor-out screen exempts the shortest/longest rate cluster (extrapolation is not validation);
  V4b = V4a + singleton rate clusters get Huber (bounded) instead of Tukey (zero) weight in the IRLS stage.
  Adoption criterion unchanged (criterion 2 of the protocol, evaluated on all synthetic cases plus public holdout).
- 09:03 UTC — A fifth synthetic condition `missing20_outliers` (thin clusters plus 5 % gross ±15 bp outliers) and a
  targeted lone-outlier case (single +15 bp 4Y OIS quote) were added to exercise the trade-off of V4b; the V3 code
  was re-run on the same extended set so before/after use identical data (seeds unchanged).
- 09:07 UTC — Report gained a `<!DOCTYPE>`/`<head><meta charset='utf-8'>` wrapper (Japanese headings need it when
  opened from `file://`). Format only; numerical files unaffected (verified by hash).
- 09:12 UTC — Browser check of the rendered report caught a regression introduced by the 09:07 head patch (the
  `<title>`/`<style>` literal had lost its f-string prefix, so `{CSS}` was printed verbatim and the page was
  unstyled). Fixed, regression test added (`test_report_head_is_well_formed`), outputs regenerated from a clean
  state and determinism re-checked. Format only; numerical files unaffected (verified by hash).
