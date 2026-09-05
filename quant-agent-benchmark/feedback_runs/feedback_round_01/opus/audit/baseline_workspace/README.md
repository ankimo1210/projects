# quantcurve — zero-curve construction, validation and model risk

A production-shaped research project that turns one file of imperfect USD market
observations (deposits, par OIS swaps, coupon bonds) into a published,
continuously compounded zero curve, together with the diagnostics a desk needs
before trusting it: a per-observation cleaning audit, repricing residuals, a
maturity-blocked holdout, stability and sensitivity studies, DV01 and key-rate
risk, and a self-contained HTML research report.

The published curve is a **penalised, robust cubic spline in the instantaneous
forward rate**. A sequential bootstrap of consensus pillars is fitted alongside
it as the baseline, and both are scored by a rule fixed before any number was
looked at. On the benchmark data the bootstrap reprices its own pillars exactly
and still loses, because its instantaneous forward curve runs from −1.8% to
+5.9% against a quoted rate range of 1.21%–2.58%: that is exact interpolation of
quote noise between nearly coincident maturities, not information.

---

## 1. Environment

Python **3.12** (the project pins `>=3.12,<3.13`). No network access is needed at
run time. Dependencies: `numpy`, `pandas`, `scipy`, `matplotlib`; `pytest` is
optional (the suite also runs on the standard-library `unittest`).

Exact commands, from the project root (`.../results/opus`):

```bash
python3.12 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
```

With [uv](https://docs.astral.sh/uv/) instead:

```bash
uv venv --python 3.12 .venv
```

## 2. Installation

Editable install, including the optional test dependency:

```bash
./.venv/bin/python -m pip install -e ".[dev]"
```

With uv:

```bash
VIRTUAL_ENV=$PWD/.venv uv pip install -e ".[dev]"
```

Verify that the package installs and imports:

```bash
./.venv/bin/python -c "import quantcurve; print(quantcurve.__version__)"
# 1.0.0
```

Nothing in the codebase requires the install: every command below also works
from a bare checkout with `PYTHONPATH=src`.

## 3. Tests

```bash
./.venv/bin/python -m pytest -q
```

or, with no third-party test runner at all:

```bash
PYTHONPATH=src:tests ./.venv/bin/python -m unittest discover -s tests -q
```

203 tests. Expect **about 110 seconds**: roughly 80 of them are one end-to-end
test that runs the mandated CLI on the real 143-row data set in a subprocess.
That test skips itself, with a message, if the benchmark input file is not
present; everything else runs on synthetic data generated from a known
Nelson–Siegel curve in `tests/synthetic.py`, so the suite is self-contained and
its expected values are analytic rather than golden-file snapshots.

`pyproject.toml` promotes `FutureWarning` and `RuntimeWarning` to errors under
pytest, so a silently degraded numerical path fails the suite rather than
printing to a log nobody reads.

## 4. Running the workflow

The mandated invocation, exactly as specified:

```bash
PYTHONPATH=src ./.venv/bin/python -m quantcurve.cli run \
  --market-data /Users/ankimo1210/Documents/projects/quant-agent-benchmark/input/market_data/market_observations.csv \
  --output-dir  /Users/ankimo1210/Documents/projects/quant-agent-benchmark/results/opus/outputs \
  --valuation-date 2026-01-15
```

About 40 seconds. It is deterministic — no random number is drawn anywhere, and
two runs of the same input produce byte-identical CSV, JSON, PNG and HTML — and
it works unchanged on any other file with the same schema. Unrecoverable input
problems exit non-zero (`2` bad input, `3` unwritable output, `4` unexpected)
with a message that names the problem and what to do about it.

The copy of the report checked in at `reports/research_report.html` is the same
run with the report redirected:

```bash
PYTHONPATH=src ./.venv/bin/python -m quantcurve.cli run \
  --market-data /Users/ankimo1210/Documents/projects/quant-agent-benchmark/input/market_data/market_observations.csv \
  --output-dir  /Users/ankimo1210/Documents/projects/quant-agent-benchmark/results/opus/outputs \
  --valuation-date 2026-01-15 \
  --report-path  /Users/ankimo1210/Documents/projects/quant-agent-benchmark/results/opus/reports/research_report.html
```

If the package was installed, `quantcurve run ...` is equivalent and needs no
`PYTHONPATH`.

### Optional flags

| Flag | Effect |
|---|---|
| `--report-path PATH` | write the HTML report somewhere other than `<output-dir>/reports/` |
| `--grid-points N` | rows in `curves/curve.csv` (minimum 361, default 601) |
| `--grid-max-years T` | longest published maturity (default 30) |
| `--compact-report` | shorten the long tables in the HTML report |
| `--no-report`, `--no-charts`, `--no-sensitivity` | skip those stages |
| `--quiet` | suppress the progress summary |

## 5. What is produced

```
outputs/curves/curve.csv                    601 rows, 1/12Y … 30Y
outputs/diagnostics/cleaning.csv            one row per input observation
outputs/diagnostics/repricing.csv           one row per calibrating instrument
outputs/diagnostics/risk.csv                DV01 and 2Y/5Y/10Y/30Y key rates
outputs/diagnostics/model_comparison.json   both fits, the holdout, the rule
outputs/diagnostics/sensitivity.json        six named checks
outputs/diagnostics/validation_summary.json flag counts and provenance
outputs/charts/*.png                        seven figures
outputs/reports/research_report.html        self-contained report
reports/research_report.html                the same report, checked in
```

`curve.csv` carries `maturity_years, zero_rate, discount_factor, forward_rate`.
Rates are **annual decimals, continuously compounded**; `discount_factor` is
`exp(-zero_rate * maturity_years)` to machine precision and `forward_rate` is
the instantaneous forward `-d log D / dT`, whose running average reproduces
`zero_rate` (both relations are asserted in the test suite against the published
columns alone).

The grid is geometric below 2Y and uniform above it, so linear interpolation
between published rows costs under 0.01bp anywhere on the curve; a uniform grid
of the same size would cost 0.55bp at the front, where the curve bends most.

`cleaning.csv` gives every input row an `action` from `keep / correct /
downweight / exclude`, the quote actually used, the calibration weight, and a
sentence saying why. It is the audit trail: no observation is dropped or altered
anywhere else in the pipeline.

## 6. Headline result on the benchmark data

| | |
|---|---|
| Observations in / instruments calibrated | 143 / 119 |
| Cleaning actions | 90 keep, 15 correct, 14 downweight, 24 exclude |
| Published model | penalised robust forward spline, 21 knots, λ = 1e-5, penalty power 2 |
| Repricing RMSE (weighted, yield-equivalent) | 0.09bp deposits (n=16), 0.89bp OIS swaps (n=59), 2.55bp bonds (n=44) |
| Maturity-blocked holdout | 19 instruments withheld from 44 blocks; 1.15bp weighted RMSE |
| Estimated instrument noise | 0.25bp deposits, 0.56bp swaps, 2.14bp bonds |
| Sensitivity envelope | 0.03bp to 7.41bp of zero-rate movement across six checks |
| Zero rates | 1.21% (1M), 1.95% (1Y), 2.22% (2Y), 2.28% (5Y), 2.10% (10Y), 2.06% (30Y) |

The bond repricing RMSE is deliberately not driven to zero: it is the same size
as the measured bond idiosyncratic spread, which is a property of the bonds, not
an error in the curve. Read `MODEL_RISKS.md` before using any of these numbers.

## 7. Layout

```
src/quantcurve/
  io.py           strict schema load, audit of unparseable and blank cells
  validation.py   27 read-only defect flags; changes nothing
  cleaning.py     the audited corrections, exclusions and calibration weights
  conventions.py  schedules and elementary rate/discount conversions
  instruments.py  the immutable calibration instrument
  pricing.py      cash flows and model quotes, scalar and vectorised
  curve.py        piecewise-flat-forward and spline-forward discount curves
  models.py       bootstrap baseline, penalised robust spline, outlier screen
  holdout.py      maturity-blocked split, admissibility gate, selection rule
  risk.py         DV01, key rates, and the analytic cross-check
  sensitivity.py  stability and perturbation studies
  workflow.py     the end-to-end run
  outputs.py      the machine-readable output contract and its assertions
  charts.py       the seven figures
  report.py       the self-contained HTML report
  cli.py          the mandated entry point
tests/            203 tests; synthetic.py generates data from a known curve
MODEL_RISKS.md    assumptions, numerical and data risks, appropriate use
benchmark_summary.json
```

## 8. Method in one page

**Conventions.** Inferred from the data, not assumed: swap and bond schedules run
backwards from maturity in `1/frequency` steps with
`n = max(1, round(T × frequency))` periods. `ceil` mis-prices the 1.25Y annual
OIS and `floor` mis-prices the 2.44Y semiannual bond; only this rule reprices
every quoted instrument consistently. OIS fixed legs pay annually to 2Y and
semiannually beyond. Deposits are simple-interest, `D(T) = 1/(1 + rT)`. Bonds
are bullet, face 100, no accrued interest.

**Validation then cleaning.** `validation.py` only *observes* — 27 flags covering
schema, units, staleness, crossed and wide markets, duplicates, liquidity, and
maturity-date consistency. `cleaning.py` is the only module that changes a
number, and every change lands in `cleaning.csv` with its reason.

**Weights.** `σ_i² = σ_quote,i² + σ_model,type²`. The first term is the
yield-equivalent half-spread, floored at 0.1bp, capped at 20bp and divided by
`√liquidity`. The second is estimated from a preliminary robust fit's residual
MAD per instrument type — 2.14bp for bonds against 0.56bp for swaps, which is
the bonds' idiosyncratic spread and is why a bid/ask-only weighting scheme would
be badly overconfident about them. Data-quality penalties multiply on top.

**Estimator.** Cubic spline in the instantaneous forward `f`, so
`D = exp(-∫f)` is positive by construction and negative rates need no special
case. The objective is `Σ wᵢ ρ(rᵢ) + λ∫(T/T_ref)^p f''(T)² dT`; the
maturity-weighted roughness penalty stops a flat penalty from over-smoothing the
steep money-market end. `λ` and `p` are chosen by maturity-blocked
cross-validation on training data only. Robustness is a convex Huber warm-up
followed by Tukey-biweight IRLS — the warm-up matters: starting the redescending
stage from a non-robust fit lets it converge onto the wrong cluster of quotes.

**Selection.** (1) Reject any curve whose instantaneous forward leaves the quoted
rate range by more than 200bp. (2) Among admissible curves take the lower
maturity-blocked holdout weighted RMSE, requiring the advanced estimator to beat
the baseline by 5% before its extra complexity is accepted. The holdout is
blocked by maturity, never random: the file contains four venues quoting the
same 10Y swap and bonds maturing days apart, and a random split would leave a
near-identical instrument in the training set and measure quote dispersion
instead of curve quality.

**Risk.** DV01 is `(PV[−1bp] − PV[+1bp]) / 2` under a parallel zero-rate bump,
receiver-fixed, on 1,000,000 notional for deposits and swaps and face 100 for
bonds. Key rates use triangular tent bumps at 2/5/10/30Y that sum to 1 at every
maturity, so the four buckets add back to the parallel DV01 — they agree to
5×10⁻⁷ relative. Every finite difference is checked against an analytic
cash-flow derivative; that check is what caught a sign error in the OIS floating
leg.
