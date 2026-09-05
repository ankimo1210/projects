# Sol feedback_round_01 protocol

## Fixed execution frame

- Model assignment: `sol` (explicitly supplied in this conversation).
- Round: `feedback_round_01`.
- Start UTC: `2026-09-05T07:58:29Z`; hard stop: `2026-09-05T08:58:29Z`.
- Design-change freeze: `2026-09-05T08:48:29Z`; after this point only validation and saving are allowed.
- Reasoning effort: requested `xhigh`; runtime setting could not be independently verified.
- Seed: `1729`.
- Python: prescribed Python 3.12.11; numpy 2.5.2, pandas 2.3.3, scipy 1.18.1, matplotlib 3.11.1, pytest 8.4.2.
- Public input SHA-256: `dd96a259f44c81c272f048c3600dc5f7df686ea77a1c192d2c4aa3a306654d01`.
- Original-manifest exclusions: `.git`, `.venv`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `build`, `dist`, `*.pyc`, `*.pyo`.
- No external search, API, network access, other model output, evaluator, generator, hidden truth, review database, or analysis material will be accessed.

## Baseline reproduction

- Workspace: `audit/baseline_workspace`, never the original directory.
- Tests: 20 passed in 10.38 seconds.
- Fresh CLI: succeeded; 136 usable observations, 7 exclusions, 55 robust downweights; selected `baseline`.
- Baseline full-sample repricing RMSE: deposit 16.5808 bp, OIS 47.2374 bp, bond 1.14148 price points. This is public-observation fit, not truth error.
- Baseline numerical checks: 361 points from 1/12Y to 30Y, finite, positive discount factors, forward range 0.464742% to 4.128747%, risk checks passed.

## Frozen diagnostic questions and factual starting point

Facts verified in the copied source: the baseline (a) solves a flat curve per instrument, (b) interprets that yield as a maturity zero, (c) aggregates into 0.5Y buckets, (d) applies a centered three-point rolling median, and (e) uses PCHIP. The advanced model prices cash flows directly on a natural-cubic zero curve. The original visible holdout is deterministic 0.5Y maturity blocks.

Hypotheses to test, not assume:

1. `H_PRICE`: pricing implementation or percent/decimal/price-point conversion is wrong, especially for fractional maturities.
2. `H_PROXY`: a flat single-instrument yield is biased relative to the maturity zero rate for coupon instruments on non-flat curves.
3. `H_AGG`: half-year aggregation removes useful short-end tenor information.
4. `H_MEDIAN`: the subsequent rolling median removes useful short-end shape beyond any robustness benefit.
5. `H_HOLDOUT`: baseline wins aggregate public holdout because of particular tenor/product/convention slices; the result need not imply lower known-truth error.

## Fixed splits and metrics

- Public split `public_maturity_blocks_v1`: original deterministic 0.5Y bucket rule, held bucket index modulo 5 equals 3. The split is unchanged for all before/after public comparisons.
- Public tenor bands: short `T <= 2`, medium `2 < T < 15`, long `T >= 15`; empty groups are missing, never zero error.
- Public metrics: spread-normalized weighted RMSE (dimensionless, scale=max(half bid/ask spread, 1 bp for rates or 0.05 price points for bonds)); rate-instrument RMSE in bp; bond RMSE in price points. Units are never pooled without normalization.
- Synthetic suite `synthetic_v1`: deterministic flat, rising, falling, and humped continuously compounded zero curves; instruments are priced independently from direct discount functions. Report zero and forward RMSE in bp on a dense truth grid, overall and by tenor band.
- Convention checks compare independent formulas against implementation under the same direct `D(T)`; price/rate differences retain native units.
- Improvement rate is `(before - after) / before`; it is omitted for zero, missing, or non-comparable denominators.

## Predeclared adoption gates

Priority order is strict: pricing and units; unseen-condition accuracy; stability and reproducibility.

1. All independent pricing/unit checks, original tests, full CLI checks, schema checks, and finite/positive-discount/risk guardrails must pass.
2. A candidate model must improve synthetic short-end (`T <= 2`) zero RMSE by at least 10% versus the reproduced baseline on the aggregate suite.
3. No individual synthetic shape may worsen overall zero RMSE or forward RMSE by more than 5%; no public holdout tenor/product slice with at least 3 rows may worsen normalized RMSE by more than 5% when the absolute increase exceeds 0.25 normalized units.
4. Public aggregate holdout normalized RMSE must not worsen by more than 2%.
5. Repeated fresh CLI runs must select the same model and produce byte-identical CSV/JSON numerical outputs after excluding timestamps and report paths.
6. Only one-factor effects demonstrated under the fixed protocol may justify adoption. If multiple accepted changes are combined, an integration experiment must pass all gates; untested interactions are not claimed.

## Planned one-factor sequence

- `E00`: reproduce baseline tests and CLI.
- `E01`: direct-discount independent pricing and unit/convention tests, including negative, integer, and fractional maturities.
- `E02`: quantify flat-yield proxy bias by product, tenor, and synthetic shape; no implementation change.
- `E03`: remove rolling median only; keep 0.5Y aggregation and PCHIP.
- `E04`: retain exact maturities only; keep standalone-yield proxy and PCHIP, with no rolling median.
- `E05`: compare baseline and advanced under fixed public split and synthetic truth, by tenor/product.
- `E06`: final integration and reproducibility check for any adopted candidate.

## Protocol changes

- `2026-09-05T08:12:53Z`: added a regular-half-year-grid versus fractional-maturity reporting slice to `E05` because the fixed hypothesis already required pricing-convention diagnosis. This is a measurement-only extension; no split, model, metric definition, or adoption threshold changed. The first diagnostic run remains in `logs/03_diagnostics.log`, and the extended rerun is in `logs/04_diagnostics_with_convention_slice.log`.
