# Zero-Curve Research and Engineering Benchmark

You are the senior quantitative researcher and quantitative developer responsible for delivering a production-quality zero-curve research project. Work only with the files in this input package and write the completed project directly into your assigned result directory. Do not seek, infer, or access evaluator material or another candidate's work.

## Objective

From `market_data/market_observations.csv`, independently construct, validate, compare, and report on a continuously compounded zero curve. The observations contain deposits, par OIS swaps, and coupon-bearing bonds. The data are intentionally realistic and imperfect. Follow every convention in `market_data/CONVENTIONS.md`; do not rely on undocumented market conventions.

Your submission must demonstrate quantitative judgment, not merely code execution. Build a simple baseline first, then an advanced method. Use empirical evidence to choose or qualify the preferred model; complexity is not evidence of superiority.

## Required work

Implement all of the following:

1. schema, type, range, timestamp, unit, bid/ask, duplicate, and missing-data validation;
2. defensible correction, exclusion, deduplication, or downweighting decisions, with an audit trail;
3. cash-flow construction and discounting for every documented instrument type;
4. a simple baseline zero-curve model;
5. an advanced zero-curve estimator with appropriate smoothing or regularisation;
6. spread- and liquidity-aware weights and iterative robust residual treatment;
7. support for negative rates without forcing discount factors below zero;
8. zero rates, discount factors, and instantaneous forward rates on a dense grid from the front end through 30Y;
9. instrument repricing diagnostics, visible holdout validation, stability checks, and sensitivity analysis;
10. receiver-fixed DV01 and 2Y/5Y/10Y/30Y key-rate sensitivities, with finite-difference verification;
11. automated tests, a reproducible command-line workflow, charts, and an HTML research report;
12. a candid discussion of model risk, data limitations, extrapolation, and failure modes.

Use a time-aware, maturity-aware, or otherwise defensible visible holdout methodology. Avoid a random split that leaks near-duplicate instruments across train and validation sets. Inspect numerical outputs and rendered charts, identify weaknesses, make corrective iterations, and rerun your tests after corrections.

## Required command-line interface

Your package must support this command from the project root:

```bash
PYTHONPATH=src python -m quantcurve.cli run \
  --market-data /absolute/path/to/market_observations.csv \
  --output-dir /absolute/path/to/output_directory \
  --valuation-date 2026-01-15
```

The same source code must work for other conforming datasets without manual edits. The command must be deterministic. It may accept additional options, but these arguments and semantics are mandatory. It must exit nonzero with an actionable message for unrecoverable input errors.

## Machine-readable output contract

The CLI output directory must contain:

- `curves/curve.csv`: at least 361 ordered grid rows, spanning no less than 1/12Y to 30Y, with columns `maturity_years`, `zero_rate`, `discount_factor`, and `forward_rate`. Rates are annual decimals and zero rates are continuously compounded.
- `diagnostics/cleaning.csv`: one row per input observation with `obs_id`, `instrument_id`, `action`, `normalized_quote`, `weight`, and `reason`. `action` must be one of `keep`, `correct`, `downweight`, or `exclude`.
- `diagnostics/repricing.csv`: `instrument_id`, `instrument_type`, `market_quote`, `model_quote`, `residual`, and `weight`, using normalized input units.
- `diagnostics/risk.csv`: risk for every usable instrument, with `instrument_id`, `dv01`, `key_2y`, `key_5y`, `key_10y`, and `key_30y`.
- `diagnostics/model_comparison.json`: baseline and advanced train/holdout metrics, model selected, and selection rationale.
- `diagnostics/sensitivity.json`: at least three named perturbation or refit checks with numerical outcomes.
- `charts/`: non-empty curve, forward-rate, repricing, and model-comparison charts in PNG or SVG format.

The main completed project must additionally contain `reports/research_report.html`. When the CLI is run on a fresh alternative dataset, it is acceptable to generate a compact version of the same report, but the curve and diagnostic files remain mandatory.

## Required project deliverables

Place the project directly in your assigned result directory with this shape (you may add files and choose your own internal design):

```text
pyproject.toml
README.md
MODEL_RISKS.md
benchmark_summary.json
src/
tests/
reports/research_report.html
outputs/curves/
outputs/diagnostics/
outputs/charts/
```

`README.md` must contain exact environment, installation, test, workflow, and CLI commands. `MODEL_RISKS.md` must cover assumptions, numerical risks, data-quality risks, interpolation and extrapolation behavior, validation gaps, and appropriate use.

The HTML report must be self-contained enough to open locally and must visibly cover:

- executive summary;
- methodology;
- data-quality findings;
- baseline-versus-advanced model comparison;
- sensitivity analysis;
- validation and repricing;
- charts;
- limitations;
- recommended next steps.

## `benchmark_summary.json`

Provide valid JSON with these fields:

```json
{
  "schema_version": "1.0",
  "model_name": "string",
  "reasoning_effort": "string or null",
  "start_time": "ISO-8601 timestamp",
  "finish_time": "ISO-8601 timestamp",
  "wall_time_seconds": 0.0,
  "test_runs": 0,
  "failed_test_runs": 0,
  "corrective_iterations": 0,
  "tests_passed": 0,
  "tests_failed": 0,
  "files_created": ["relative/path"],
  "unresolved_limitations": ["string"],
  "quota_percentage_consumed": null,
  "credits_consumed": null,
  "estimated_usd_cost": null,
  "human_interventions": 0
}
```

The timing and process fields must be honest observations, not estimates manufactured after the fact. Nullable cost and quota fields may be completed externally.

## Completion standard

Before finishing:

1. run all of your tests;
2. run the complete workflow from the supplied data into `outputs/`;
3. inspect all numerical files for finiteness, units, curve coverage, and economic plausibility;
4. inspect every generated chart and the HTML report;
5. record and correct any failures or weaknesses you find;
6. rerun the relevant tests and workflow after corrections;
7. confirm the project has no dependency on prior runs, personal absolute paths, external network access, or unavailable private data.

Document unresolved limitations rather than hiding them.
