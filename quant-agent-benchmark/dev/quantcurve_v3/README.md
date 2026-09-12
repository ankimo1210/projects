# quantcurve — zero-curve research project

Robust construction, validation, risk and reporting of a continuously
compounded USD zero curve from deposits, par OIS swaps and coupon bonds
observed on one valuation date. Built for the zero-curve research benchmark;
the same code runs unchanged on any dataset that follows
`market_data/CONVENTIONS.md` and the public CSV schema.

Everything below was executed on macOS (arm64) with CPython 3.12.11. No
network access is needed at run time; all outputs are deterministic
(byte-identical across runs).

## Environment and installation

Requirements: Python 3.12 (`>=3.12,<3.13`), `numpy`, `pandas`, `scipy`,
`matplotlib` (pinned ranges in `pyproject.toml`); `pytest` for the tests.

Using `uv` (used for the benchmark run):

```bash
cd <project root>
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ".[dev]"
```

Using plain `pip`:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Verify the install:

```bash
.venv/bin/python -c "import quantcurve, numpy, pandas, scipy, matplotlib; print(quantcurve.__version__)"
```

## Tests

```bash
.venv/bin/python -m pytest -q          # 60 tests, ~20 s (RuntimeWarnings are errors)
```

The suite covers conventions and schedules, curve classes (positivity under
negative rates, forward/discount consistency, penalty matrix), analytic
Jacobians against finite differences, the cleaning rules (scale defects,
units, missing quotes, crossed markets, duplicates, stale timestamps, iterated
cross-sectional screen, structural rejections), model recovery of a known
curve (including a negative-rate curve), robust rejection of injected
outliers with a concordant-cluster guard, grouped-fold construction, holdout
scoring, DV01/key-rate verification, and an end-to-end CLI run with
determinism and error-exit checks.

## Workflow (reproduces `outputs/` and `reports/`)

```bash
PYTHONPATH=src .venv/bin/python -m quantcurve.cli run \
  --market-data /absolute/path/to/market_observations.csv \
  --output-dir  "$PWD/outputs" \
  --valuation-date 2026-01-15 \
  --report-dir  "$PWD/reports"
```

Runtime is about 8 s. `--report-dir` is optional; without it the report is
written to `<output-dir>/reports/research_report.html`.

## Required CLI (benchmark contract)

```bash
PYTHONPATH=src python -m quantcurve.cli run \
  --market-data /absolute/path/to/market_observations.csv \
  --output-dir /absolute/path/to/output_directory \
  --valuation-date 2026-01-15
```

Exit codes: `0` success; `2` unrecoverable input error with an actionable
message on stderr (missing file, missing columns, unparseable date, no usable
quotes, every quote stale relative to `--valuation-date`); `1` unexpected
failure (traceback printed).

Optional flags: `--stub-rule {contract_v2,forward,round,linspace,ceil,forward_actual}`
(default `contract_v2`; the others are legacy readings kept for sensitivity),
`--penalty-shape {power,waggoner_steps}` (maturity weighting of the roughness
penalty; default `power`), `--max-knots N` (interior forward-spline knot cap,
default 40; 28 reproduces the round-1 setting), `--no-loo-screen` (disable the leave-tenor-out outlier screen), `--lambda X` (fix the smoothing
parameter instead of cross-validating), `--grid-step` (default 1/48 year; the grid starts at one step and always contains 1/12Y),
`--grid-end` (default 30, extended to the longest instrument), `--folds`
(default 5), `--max-stale-days` (default 0), `--noise-replications`,
`--seed`, `--skip-sensitivity`, `--quiet`. `PYTHONPATH=src` can be dropped
after `pip install -e .`, and the console script `quantcurve run ...` is
equivalent.

## Output contract (`<output-dir>/`)

| File | Content |
|---|---|
| `curves/curve.csv` | selected model on a 1/24-year grid from 1/12Y to 30Y (719 rows): `maturity_years, zero_rate, discount_factor, forward_rate`; rates are annual decimals, zeros continuously compounded, forwards instantaneous |
| `curves/curve_baseline.csv`, `curves/curve_advanced.csv` | both models on the same grid |
| `diagnostics/cleaning.csv` | one row per input observation: `obs_id, instrument_id, action (keep/correct/downweight/exclude), normalized_quote, weight, reason` plus raw quote, bid/ask, spread, liquidity, tenor cluster |
| `diagnostics/repricing.csv` | selected model: `instrument_id, instrument_type, market_quote, model_quote, residual, weight` (percent for rates, points for bonds) plus yield-equivalent residual in bp, standardised residual and robust factor; `repricing_baseline.csv` / `repricing_advanced.csv` for both models |
| `diagnostics/risk.csv` | `instrument_id, dv01, key_2y, key_5y, key_10y, key_30y` for every instrument that survived rule-based cleaning (`usable` flag marks robust-fit rejections), plus PV, key-rate sum, analytic DV01 and verification ratios |
| `diagnostics/model_comparison.json` | baseline/advanced train and holdout metrics, per-fold results, time-aware split, CV tables, selected model and rationale |
| `diagnostics/sensitivity.json` | nine named perturbation/refit checks with numerical outcomes |
| `diagnostics/risk_verification.json`, `holdout_predictions.csv`, `cv_table.csv`, `sensitivity_curve_deltas.csv`, `run_summary.json` | supporting diagnostics (bump shape, FD-vs-analytic checks, held-out predictions, timings, numerical warnings) |
| `charts/*.png` | curve, forward, repricing, model comparison, data quality, sensitivity, risk |
| `reports/research_report.html` | self-contained research report (charts embedded) |

## Project layout

```
pyproject.toml            package metadata, dependencies, pytest config
README.md                 this file
MODEL_RISKS.md            assumptions, numerical/data risks, extrapolation, validation gaps, use
benchmark_summary.json    benchmark process record
src/quantcurve/
  io.py                   CSV loading, schema check, numeric coercion
  cleaning.py             validation, normalisation, duplicates, cross-sectional screen, audit trail
  conventions.py          rate/discount conversions, schedule rules
  instruments.py          observation and instrument (cash-flow) records
  curve.py                piecewise-linear zero curve, B-spline forward curve, bumps
  pricing.py              model quotes, PVs, analytic Jacobians, DV01 derivative
  weights.py              spread/liquidity base scales
  baseline.py             sequential bootstrap (simple baseline)
  advanced.py             penalised spline, leave-tenor-out screen, Tukey IRLS, grouped CV
  validation.py           maturity-grouped holdout and time-aware split
  risk.py                 DV01 and key-rate sensitivities with verification
  sensitivity.py          perturbation, convention, jackknife and noise checks
  charts.py / report.py   PNG charts and the HTML report
  workflow.py / cli.py    orchestration and command line
tests/                    pytest suite (synthetic generator in tests/synthetic.py)
research/                 exploration scripts used while designing the model (audit trail)
outputs/, reports/        results of the workflow on the benchmark data
```

## Method in one paragraph

Quotes are validated and normalised with a full audit trail (peer-based scale
correction, bid/ask mids for missing quotes, deterministic duplicate
resolution, stale-timestamp exclusion, an iterated median/MAD screen inside
tenor clusters). Cash flows follow `CONVENTIONS.md`; for tenors that are not a
whole number of periods the round-02 contract v2.0 applies (`contract_v2`,
default): coupon dates at every `k/m` strictly before `T` then `T`, actual
accruals, stub coupon proportional to accrual, principal at `T`; see
`MODEL_RISKS.md` §1.2, `tests/test_contract_v2.py` and the legacy-reading
sensitivity checks `stub_rule_forward` / `stub_rule_forward_actual`. The baseline is a sequential bootstrap with linear zero
interpolation. The advanced model is a cubic B-spline instantaneous forward
curve (exact integration keeps discount factors positive under negative
rates) with a maturity-weighted roughness penalty, spread/liquidity/type-scale
weights, a leave-tenor-out outlier screen and Tukey IRLS with a
concordant-cluster guard; the smoothing parameter is chosen by maturity-grouped
5-fold cross-validation. Both models are compared on the same grouped holdout
(precision-weighted RMSE), risk is verified analytically, and nine sensitivity
checks quantify convention, weighting, smoothing and data-perturbation risk.
See `reports/research_report.html` and `MODEL_RISKS.md`.

## Feedback round 1 (2026-09-05) — what changed and what did not

Numerical outputs of the default workflow (`curve.csv`, `cleaning.csv`,
`repricing.csv`, `risk.csv`) are byte-identical to the original submission;
the round added verification and robustness, not a new curve:

- `quantcurve.curve.FunctionCurve`: diagnostic curve built from a known
  `D(t)` so every pricing formula can be checked against an independent
  pricer (tests in `tests/test_pricing.py`; integer maturities agree to
  1e-14, DV01 to 2e-10, unit conversions round-trip exactly).
- `--stub-rule forward_actual` (forward dates, actual stub accrual) and a
  corrected `ceil` (actual stub accrual instead of level) so the
  fractional-tenor ambiguity is measured fairly in `sensitivity.json`.
- `advanced.type_scales` falls back to the global scale for a type with no
  active residuals; previously a sparse training fold (e.g. 4 deposits, all
  down-weighted) raised `KeyError` inside the holdout refit.
- `diagnostics/sensitivity.json` is now keyed by check name, each entry with
  `condition`, `results`, `interpretation`; `model_comparison.json` carries
  `units` and holdout metrics by tenor band (`short_T<=2`, `mid_2<T<15`,
  `long_T>=15`); report headings carry the English section labels.

## Round 02 (2026-09-05) — pricing contract v2.0, papers, QuantLib

Run with the approved environment (`requirements.txt`; QuantLib is only needed
by the cross-check tests and is skipped if absent):

```bash
PYTHONPATH=src python -m pytest -q tests
PYTHONPATH=src python -m quantcurve.cli run \
  --market-data /absolute/path/market_observations.csv \
  --output-dir /absolute/path/outputs --valuation-date 2026-01-15
```

What changed and why (details, numbers and rejected variants in `audit/`):

- **Contract v2.0 (default `--stub-rule contract_v2`)**: coupon dates at every
  `k/m` strictly before `T` then `T`, actual accruals, stub coupon `100 c alpha`,
  principal at `T`, OIS annual/semiannual rule enforced. Under the inherited
  legacy reading the new data's short OIS were mispriced by 50-250bp and the
  robust layer discarded them; grouped-holdout weighted RMSE of the advanced
  model went from 8.79bp (before) to 0.26bp (convention only). Verified by
  `tests/test_contract_v2.py` (independent enumeration + QuantLib 1.43).
- **Knot cap 28 -> 40 (`--max-knots`)**: on synthetic truth with the new data's
  unique off-grid tenors the forward RMSE fell from 1.18 to 0.64bp (mean over
  15 shape x condition cases) with zero-rate accuracy unchanged or better and
  the public holdout unchanged (0.256 vs 0.257bp). 60 knots gave no further gain.
- **Not adopted**: Waggoner's three-step penalty (`--penalty-shape
  waggoner_steps`, kept as an option) and the uniform penalty (both slightly
  worse than the existing maturity-weighted power penalty); disabling the
  leave-tenor-out screen (`--no-loo-screen`: synthetic accuracy unchanged, but
  the +/-35bp OIS outliers in the public data survive and the holdout collapses
  to 3.7bp).

## Development version v3 (2026-09-06) — synthetic bench and knot coverage

- `research/synthetic_bench.py` / `research/bench_compare.py`: 30-scenario synthetic validation with hidden
  off-grid instruments (see `research/README_bench.md`); every estimator change is adopted or rejected there
  first, the public holdout is only a guard.
- Output grid step 1/48 starting at 1/48Y (1/12Y always present); 1440 rows for a 30Y curve.
- Bond maturities become spline knots where rate tenors are sparser than `--knot-bond-gap` (default 1.5Y):
  a long end covered only by bonds could not be represented and its bonds were rejected as outliers
  (synthetic `tenor_sparse_long_long_hump`: zero RMSE 10.6 -> 0.33 bp). Public-data outputs unchanged.

