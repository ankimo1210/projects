# QuantCurve

QuantCurve validates USD deposit, spot-starting OIS swap, and coupon-bond
observations; fits a continuously compounded zero curve; and produces curve,
diagnostic, risk, chart, and HTML-research-report outputs. It is deterministic
and has no network dependency.

## Environment and installation

Python 3.12 is required. From the project root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## Tests

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Reproducible workflow

Run the end-to-end research workflow with absolute paths:

```bash
PYTHONPATH=src python -m quantcurve.cli run \
  --market-data /absolute/path/to/market_observations.csv \
  --output-dir /absolute/path/to/output_directory \
  --valuation-date 2026-01-15
```

For the supplied benchmark package, the command is:

```bash
PYTHONPATH=src python -m quantcurve.cli run \
  --market-data /Users/ankimo1210/Documents/projects/quant-agent-benchmark/input/market_data/market_observations.csv \
  --output-dir /Users/ankimo1210/Documents/terra/outputs \
  --valuation-date 2026-01-15
```

## Output contract

`curves/curve.csv` contains 361 grid rows from 1/12Y through 30Y and the
continuously compounded zero rate, strictly positive discount factor, and
instantaneous forward rate. `diagnostics/cleaning.csv` is a complete
row-level audit. `repricing.csv`, `risk.csv`, model comparison, sensitivity
JSON, and four PNG charts are written below the selected output directory.
The self-contained report is written to both `<output-dir>/reports/` and the
project-level `reports/research_report.html` when using the standard
`outputs/` directory.

## Approach

The baseline uses linear interpolation of log discount factors. The advanced
estimator uses a natural cubic log-discount spline with a penalty on changes
in local forward rates. It uses bid/ask spread and liquidity-aware weights,
then applies deterministic Huber-style iteratively reweighted least squares.
Model selection uses a maturity-bucket holdout, not a random split. Details,
assumptions, and limitations are in [MODEL_RISKS.md](MODEL_RISKS.md).
