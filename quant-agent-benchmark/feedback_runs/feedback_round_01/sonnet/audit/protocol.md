# Protocol — feedback_round_01 / sonnet

Written before running any diagnostic experiment (Step A of the process).
Any change to this protocol after experiments begin is appended below with
a timestamp; earlier text is never deleted.

## Assignment (confirmed with user, not self-inferred)

- MODEL_KEY = sonnet
- Baseline submission (read-only): `BENCHMARK_ROOT/output/sonnet`
- ROUND_ID = feedback_round_01
- Additional time budget = 60 minutes
- Round start (actual, recorded before first real work): `2026-09-05T08:10:32Z`
  (epoch 1788595832). Last 10 minutes of the budget (from ~08:50:32Z) are
  reserved for verification/saving only — no new design changes after that.
- REASONING_EFFORT is stated as `xhigh` in the assignment; this session has
  no introspective API to confirm its own active reasoning-effort setting,
  so it is recorded as **unconfirmed / taken as given** in `round_summary.json`,
  not verified independently.
- PYTHON_BIN = `analysis/final-review-20260905/.venv-matched/bin/python`
  (Python 3.12.11; numpy 2.5.2, pandas 2.3.3, scipy 1.18.1, matplotlib
  3.11.1, pytest 8.4.2 — matches the baseline's own `.venv` versions almost
  exactly, pytest differs 8.4.2 vs 9.1.1 originally, immaterial).

## Baseline reproduction (done before any change)

- `audit/baseline_manifest.json`: SHA-256 + size for all 37 tracked files
  (source, tests, config, README/MODEL_RISKS, and the *existing* numerical
  outputs `outputs/` + `reports/`), copied unmodified into both
  `audit/baseline_workspace/` and `submission/` (the latter is the working
  copy that gets modified from here on).
  Exclusion rules: directories named `.venv`, `.pytest_cache`, `__pycache__`,
  `.git`, or ending in `.egg-info`; file `.DS_Store`. These are build/cache
  artifacts, not tracked source or numerical output.
- Reproduced on `audit/baseline_workspace/` (never on the original) using
  PYTHON_BIN, `PYTHONDONTWRITEBYTECODE=1`, `MPLCONFIGDIR`/`PYTHONPYCACHEPREFIX`
  redirected under `audit/tmp_cache/`:
  - `pytest tests/ -v`: 49 passed, 0 failed (`audit/logs/baseline_repro_pytest.log`).
  - Full CLI run into `audit/baseline_repro_outputs/` +
    `audit/baseline_repro_reports/` (`audit/logs/baseline_repro_cli.log`):
    exit 0, model selected = baseline, 73.9s wall.
  - `diagnostics/model_comparison.json` and `diagnostics/cleaning.csv` are
    **byte-identical** to the original submission's own `outputs/` — the
    pipeline is deterministic across machine/pytest-version differences.
- Original `BENCHMARK_ROOT/output/sonnet` hash-verified unchanged after all
  of the above (`ORIGINAL UNCHANGED`, checked against `baseline_manifest.json`).

## Hypotheses to test (from the common feedback + sonnet-specific section)

Framed so each can come back **not supported**, not just confirmed.

- **H1 (sonnet-specific):** short-maturity (deposit/front-end) zero-rate and
  forward-rate repricing errors are larger, in a way that indicates a
  methodological gap, not just genuine short-end data noise.
- **H2 (sonnet-specific):** the baseline's analytic forward
  `f(t) = z(t) + t*z'(t)` (piecewise-linear zero) disagrees with a
  finite-difference forward at knots/boundaries beyond what grid
  refinement should explain (i.e. a bug, not a known kink artifact).
- **H3 (sonnet-specific):** always keeping all deposits in training, and
  screening OIS holdout candidates for local smoothness, means the visible
  holdout never actually tests the hardest/most informative points — i.e.
  the validation is systematically easier than it looks.
- **H4 (sonnet-specific):** baseline winning the internal (visible) holdout
  comparison does not imply it is closer to an unknown true curve; on
  synthetic data with a *known* curve, advanced (or a specific design
  factor) may actually be closer to truth even though baseline won
  in-sample-holdout on the real dataset.
- **H5 (common):** the payment/coupon-schedule convention assumption
  (forward-generated stub for swaps, backward-generated level-coupon stub
  for bonds) is one of several conventions consistent with
  `CONVENTIONS.md`'s text, and the choice may materially affect fitted
  short-end levels; this must be checked directly in pricing, independent
  of curve-fitting.
- **H6 (common):** slope differences at similar rate *levels* inflate
  forward error more than zero-rate error (`f = z + t*z'`), so forward
  diagnostics must be checked separately from zero-rate diagnostics.

## Metrics, splits, and decision criteria (fixed before running experiments)

- **Pricing-only diagnostics (Step B):** independent, hand-written
  reference formulas for deposit/OIS/bond pricing (NOT importing
  `quantcurve.cashflows`, to avoid circular tests) evaluated against several
  self-authored synthetic `D(T)` functions (flat, upward, downward, humped,
  and a deep-negative-rate case) at both integer and fractional maturities.
  Pass criterion: agreement with the package's own pricing functions to
  <1e-8 relative error for well-posed cases; any larger discrepancy is
  logged as a finding with the exact instrument/maturity/amounts, and
  classified as either (a) an implementation bug or (b) a legitimate
  convention-interpretation difference (H5).
- **Short-end error diagnosis (H1):** re-examine the reproduced baseline's
  `diagnostics/repricing.csv`, split by maturity band `T<=2`, `2<T<15`,
  `T>=15`, separately by instrument type, in native units (pct-points for
  deposit/swap, price points for bonds) — no cross-type RMSE averaging.
  A band with zero instruments is reported as "no data", never as zero
  error.
- **Forward consistency (H2):** compare the analytic forward formula
  against a central finite difference on the zero rate at knot points, at
  the two boundary knots, and at a fine grid refined by 10x/100x, both on
  the reproduced baseline curve and on a controlled synthetic curve.
  Decision: a discrepancy that shrinks proportionally to the finite-diff
  step size (i.e. an expected discretisation artifact, worst at kinks by
  construction of a piecewise-linear zero) is not a bug; a discrepancy
  that does NOT shrink, or that appears strictly inside a linear segment
  (no kink), is a bug.
- **Holdout coverage (H3):** for the reproduced baseline run, tabulate
  which maturity bands/instrument types ever appear in `split == holdout`
  in `repricing.csv`; a band that is structurally never eligible (by
  `build_holdout_split`'s own rules) is reported as an explicit coverage
  gap, regardless of whether it happens to reprice well.
- **Baseline vs. advanced vs. truth on synthetic data (H4):** build >=3
  synthetic curve shapes (flat, monotone upward, humped-then-declining)
  with known analytic `z_true(T)`, generate deposit/OIS/bond quotes from
  them (no hidden-market values used or guessed), fit both baseline and
  advanced with the *unmodified* pipeline, and compare each to
  `z_true` (bp RMSE) — not to each other's holdout metric. This measures
  "closeness to a known truth" as a metric distinct from the real
  dataset's internal holdout RMSE.
- **Improvement definition:** `(before - after) / before` computed only
  when both numerator terms are finite, use the same instrument set/split,
  and `before != 0`; otherwise reported as "not computable", never
  defaulted to 0.
- **Adoption rule:** a code change is adopted into `submission/` only if
  (a) it is justified by a experiment result recorded in `experiments.csv`,
  (b) it does not regress synthetic ground-truth bp RMSE for any of the
  >=3 synthetic shapes by more than 0.5bp, and (c) `submission/` still
  passes its full test suite and a full CLI run on the real dataset after
  the change. Changes that only affect report/JSON formatting are tracked
  separately from changes that affect numerical output.

## Time-boxing

- Steps B–D (pricing diagnostics, short-end/forward/holdout investigation,
  synthetic baseline-vs-advanced): target completion by ~08:45Z.
- Step E (adoption decisions + implementation): ~08:45–08:55Z.
- Step F (final verification, hash re-check, audit write-up): ~08:55–09:10Z
  (final 10 minutes — no new design changes).

## Amendments

**2026-09-05T08:35Z** — Steps B-D executed largely as planned; recorded here
are the two deviations from the original wording:

1. H1's original framing ("short-term zero rate AND forward errors are
   prominent") turned out to be two separable claims. The "zero rate"
   half is NOT supported for deposits/swaps (residuals ~2-3bp-equivalent
   at T<=2y); the apparent large short-end error is 2 bonds only (thin
   sample). The "forward" half turned out to be well supported, but not
   as a short-end-specific defect — it is a general property of the
   baseline's piecewise-linear zero curve at any noisy/tightly-clustered
   knot cluster, which happens to sit at the short-to-mid end (1.25-1.5y)
   in this dataset. This is now tracked as EXP-F3/H6, not H1.
2. Given the strength and convergence of the EXP-F3 (real-data forward-jump
   quantification) and EXP-D2 (synthetic humped-shape recovery) evidence,
   a forward-curve-smoothness diagnostic was added to `submission/`
   (`diagnostics.forward_smoothness_check`) as a new, additive
   `sensitivity.json` key and report panel — this was not in the original
   Step E plan as a concrete artifact, but follows directly from the
   protocol's own H6 decision criterion ("forward diagnostics must be
   checked separately from zero-rate diagnostics") and satisfies it with
   a shipped, tested diagnostic rather than only a written finding.

No hidden ground truth, evaluator code, or other models' submissions were
read at any point in this round.
