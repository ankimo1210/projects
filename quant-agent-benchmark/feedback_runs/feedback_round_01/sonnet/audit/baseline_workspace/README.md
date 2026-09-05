# QuantCurve — USD Zero-Curve Research & Engineering

Independently constructs, validates, compares, and reports on a continuously
compounded USD zero curve from deposits, par OIS swaps, and coupon-bearing
bonds, following `market_data/CONVENTIONS.md`.

## Environment

- Python `>=3.12,<3.13` (developed and tested on 3.12.11).
- No network access required at runtime. No personal/absolute paths are
  hard-coded anywhere in `src/`.

```bash
python3.12 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -e .
./.venv/bin/python -m pip install "pytest>=8"   # test runner, not a runtime dependency
```

## Tests

```bash
PYTHONPATH=src ./.venv/bin/python -m pytest tests/ -v
```

49 tests, ~11s. Covers: conventions round-trips, cash-flow schedule
construction (including stub periods), instrument pricing and bond
yield-to-maturity, curve interpolation (piecewise-linear and spline,
including negative-rate / positive-discount-factor guarantees), the full
cleaning pipeline against a synthetic dataset with every injected defect
type, holdout-split leakage checks, calibration recovery of a known curve
and determinism, key-rate partition-of-unity / DV01 reconciliation, and an
end-to-end CLI run (including its required error paths).

## Workflow — reproduce the shipped `outputs/` and `reports/`

Run from the project root, with the real benchmark market data (the exact
command the CLI contract requires):

```bash
PYTHONPATH=src ./.venv/bin/python -m quantcurve.cli run \
  --market-data /absolute/path/to/market_observations.csv \
  --output-dir "$(pwd)/outputs" \
  --report-dir "$(pwd)/reports" \
  --valuation-date 2026-01-15
```

This is exactly how `outputs/` and `reports/research_report.html` in this
project were generated (`--report-dir` is optional; it defaults to
`<output-dir>/reports` so the CLI is fully self-contained for other
datasets — the flag is only used here to place the report at the project
root per the required deliverable layout). The run is deterministic: no
randomness anywhere in cleaning, calibration, or risk. It takes roughly
60–75 seconds, dominated by the advanced model's regularisation-strength
grid search (12 lambda values × 5 IRLS iterations each).

On failure (missing file, malformed `--valuation-date`, missing required
columns, or too few usable instruments to fit a curve) the CLI prints an
actionable message to stderr and exits non-zero.

### Output contract

```text
outputs/
  curves/curve.csv              maturity_years, zero_rate, discount_factor, forward_rate
                                 (400 rows, 1/12Y .. 30Y)
  diagnostics/cleaning.csv       obs_id, instrument_id, action, normalized_quote, weight, reason
  diagnostics/repricing.csv     instrument_id, instrument_type, market_quote, model_quote, residual, weight, split, action
  diagnostics/risk.csv          instrument_id, dv01, key_2y, key_5y, key_10y, key_30y
  diagnostics/model_comparison.json
  diagnostics/sensitivity.json
  charts/curve.png, forward_rate.png, repricing.png, model_comparison.png
reports/research_report.html    self-contained (charts embedded as base64 PNG); open directly in a browser
```

The same source code works unmodified on any other conforming dataset
(different `--market-data` / `--output-dir` / `--valuation-date`); see
`tests/test_cli.py` for an end-to-end run against a synthetic CSV.

## Project layout

```text
src/quantcurve/
  io.py            strict schema loading (supplied, unmodified)
  conventions.py   elementary rate/discount helpers (supplied, unmodified)
  instruments.py   MarketObservation schema (supplied, unmodified)
  cashflows.py     schedules and pricing for deposits/swaps/bonds; bond YTM
  cleaning.py      validation, correction, deduplication, weighting
  curve.py         PiecewiseLinearZeroCurve, SplineZeroCurve, ShiftedCurve
  calibration.py   holdout split, baseline fit, advanced (regularised+IRLS) fit
  risk.py          DV01 and key-rate sensitivities (finite difference)
  diagnostics.py   repricing table, model comparison, sensitivity checks
  charts.py        matplotlib chart generation
  report.py        self-contained HTML report renderer
  cli.py           end-to-end orchestration (the required CLI contract)
tests/             unit + end-to-end tests (see above)
```

See `MODEL_RISKS.md` for assumptions, numerical risks, data-quality risks,
extrapolation behaviour, validation gaps, and appropriate use.
