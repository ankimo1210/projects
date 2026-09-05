# QuantCurve Luna candidate

This project builds and validates a USD continuously compounded zero curve from the supplied deposits, par OIS swaps, and coupon-bearing bonds. It is deterministic, uses no network data, and preserves a row-level cleaning audit.

## Environment and installation

The benchmark requires Python `>=3.12,<3.13`. The commands below assume Python 3.12 is available as `python3.12`.

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

The runtime dependencies are declared in `pyproject.toml`: NumPy, pandas, SciPy, and Matplotlib. No external market-data or AI service is required.

## Tests

```bash
. .venv/bin/activate
python -m unittest discover -s tests -v
```

## Reproducible workflow

From the project root:

```bash
PYTHONPATH=src python -m quantcurve.cli run \
  --market-data /Users/ankimo1210/Documents/projects/quant-agent-benchmark/input/market_data/market_observations.csv \
  --output-dir /Users/ankimo1210/Documents/projects/quant-agent-benchmark/output/luna/outputs \
  --valuation-date 2026-01-15
```

The command creates `outputs/curves`, `outputs/diagnostics`, and `outputs/charts`, plus `reports/research_report.html` and `benchmark_summary.json` at the project root. The code accepts other conforming CSV files through the same CLI without manual edits.

## Methods at a glance

- Data validation checks schema, types, ranges, dates, units, bid/ask integrity, duplicates, missing quotes, liquidity, stale timestamps, and documented conventions.
- The baseline is a weighted-median deposit/OIS bootstrap with log-linear discount interpolation.
- The advanced estimator fits all usable instruments on a piecewise-linear continuous zero-rate grid with spread/liquidity weights, curvature regularisation, and four robust residual reweighting iterations.
- The visible holdout removes entire maturity clusters near 2Y, 5Y, 10Y, 20Y, and 30Y; it is not a random row split.
- All risk uses central finite differences. Key-rate bumps are local triangular partition-of-unity shapes at 2Y, 5Y, 10Y, and 30Y.

See [MODEL_RISKS.md](MODEL_RISKS.md) and the generated HTML report for assumptions, validation, sensitivity results, and limitations.
