# QuantCurve

Production-oriented research code for cleaning deposit, par OIS swap, and coupon-bond observations; estimating a positive-discount USD zero curve; comparing a simple baseline with a robust smooth model; and producing repricing, risk, sensitivity, chart, and HTML outputs.

## Environment and installation

Python 3.12 is required. From the project root, the exact clean-environment commands are:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --no-cache-dir -e '.[test]'
```

The project uses NumPy, pandas, SciPy, and Matplotlib. No service, credential, private data, or network access is needed after installation.

## Tests

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
```

Tests cover positive discount factors, negative rates, zero/discount/forward consistency, continuity, numerical stability, deterministic fitting, auditable missing data and duplicates, unit conversion, bid/ask inversions, robust outliers, DV01 finite differences, key-rate aggregation, CLI execution, and end-to-end byte reproducibility.

## Full benchmark workflow

Set the market-data path, choose a fresh output directory, and run:

```bash
MARKET_DATA=/absolute/path/to/market_observations.csv
PYTHONPATH=src .venv/bin/python -m quantcurve.cli run \
  --market-data "$MARKET_DATA" \
  --output-dir "$(pwd)/outputs" \
  --valuation-date 2026-01-15 \
  --report-path "$(pwd)/reports/research_report.html" \
  --config "$(pwd)/configs/default.json"
```

The mandatory generic CLI form also works without the optional configuration and report arguments:

```bash
PYTHONPATH=src python -m quantcurve.cli run \
  --market-data /absolute/path/to/market_observations.csv \
  --output-dir /absolute/path/to/output_directory \
  --valuation-date 2026-01-15
```

`examples/run_example.sh` wraps the same command and takes the market CSV as its first argument.

## Outputs

The workflow writes:

- `curves/curve.csv`: 361 ordered points from 1/12Y through 30Y, including continuous zero rates, positive discount factors, and instantaneous forwards;
- `diagnostics/cleaning.csv`: exactly one audit row per input row, with every correction, exclusion, and downweight reason;
- `diagnostics/repricing.csv`: normalized market/model quotes and residuals;
- `diagnostics/risk.csv`: receiver-fixed DV01 and 2Y/5Y/10Y/30Y key-rate sensitivities for every usable instrument;
- model comparison, sensitivity, validation, and run metadata JSON;
- four PNG charts; and
- a self-contained HTML report with embedded chart images.

## Model design

The baseline solves a standalone flat continuously compounded yield for each instrument, takes liquidity/spread-weighted medians by half-year maturity bucket, applies a three-point median stabilizer, and interpolates with PCHIP. It is deliberately simple and stable.

The advanced model fits natural-cubic zero-rate knots directly to every documented cash-flow equation. The objective combines bid/ask residual scales, liquidity confidence, a zero-curve second-derivative penalty, and iterative Huber weights. Residuals at repeated type/maturity tenors are centered within the tenor before Huber weighting so a coherent unusual shape is not mislabeled as many outliers. Rates may be negative; discount factors are always `exp(-z(T)T)` and are not forced to be monotone.

Visible validation holds out entire half-year maturity blocks (`bucket mod 5 == 3`). Model selection requires numerical guardrails and either a baseline stability failure or more than 2% improvement in holdout spread-normalized RMSE. Thus the advanced model is not selected merely for being more complex.

## Risk convention

Receiver-fixed DV01 is `(PV[-1bp] - PV[+1bp]) / 2`, exactly as specified. Key-rate bumps are piecewise-linear hats centered at 2Y, 5Y, 10Y, and 30Y, with flat endpoint tails. The hats form a partition of unity, so their sum is checked against parallel DV01. Deposits and swaps use notional USD 1,000,000; bonds use face 100.

## Data assumptions

`maturity_years` is authoritative. OIS fixed schedules are annual through 2Y and semiannual thereafter, including a terminal stub. Bonds pay full level coupons on regular dates measured from valuation and principal at authoritative maturity; no accrued interest is used. `MODEL_RISKS.md` explains the production limitations of these assumptions.
