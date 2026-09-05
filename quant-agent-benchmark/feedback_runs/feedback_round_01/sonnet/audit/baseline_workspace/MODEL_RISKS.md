# Model Risks, Assumptions, and Appropriate Use

## Assumptions

- **Single discount curve.** Deposits, OIS swaps, and bonds are all priced
  off *one* continuously-compounded zero curve. Real markets frequently
  price government/agency bonds at a spread to the OIS/swap curve (issuance,
  liquidity, on/off-the-run effects); this model does not represent that
  basis. It is visible directly in the data: bond repricing residuals are
  consistently larger than deposit/swap residuals in both training and
  holdout (see `diagnostics/model_comparison.json` and the repricing chart).
- **Cash-flow schedule convention.** OIS swaps and bonds pay every
  `1/payment_frequency` years, generated *forward* from the valuation date,
  with any stub inserted as the *final* period (e.g. a 1.25Y annual swap
  pays at 1.0Y and again at 1.25Y; a bond whose maturity is not an exact
  multiple of its period gets one short first coupon period counted
  backward from maturity, but — since the benchmark data states "no
  accrued interest" — every coupon amount, including a stub period, is the
  full level amount `coupon_rate/frequency * face`, not pro-rated). This is
  a simplification for a synthetic dataset with no explicit day-count
  detail per coupon; a production system would need the actual schedule
  dates and accrual conventions.
- **`maturity_years` is authoritative** (per `CONVENTIONS.md`); `maturity_date`
  is not re-derived or used for schedule generation.
- **Deposits/swaps use notional 1,000,000; bonds use face 100** for PV and
  DV01, per `CONVENTIONS.md` — this is why raw DV01 magnitudes differ by
  roughly 10,000x between a bond and a swap of similar maturity; it is a
  units artefact, not a bug (verified in `tests/test_risk.py` and the
  finite-difference bump-size sensitivity check).
- **Unit-scale defects are limited to the two documented patterns**
  (percentage-point-vs-decimal for rates, points-vs-fraction-of-par for
  bond prices, i.e. factors of ×100/×0.01). A different, unanticipated
  corruption pattern in another dataset would not be auto-corrected.

## Numerical risks

- Both models are fit by nonlinear least squares (`scipy.optimize.least_squares`,
  `lm` falling back to `trf`) directly on zero rates (never log- or
  square-transformed), so negative rates are natively supported and the
  discount factor `exp(-z*T)` is strictly positive for any finite `z` by
  construction — verified by an explicit stress test
  (`diagnostics/sensitivity.json: negative_rate_stress`) that shocks all
  deposit/swap quotes down 300bp and confirms every discount factor on the
  output grid stays positive.
- The advanced model's regularisation strength (`lambda`) is chosen by grid
  search over out-of-sample holdout RMSE (`select_lambda`), not fixed a
  priori — but the grid is finite (12 points, `LAMBDA_GRID` in
  `calibration.py`) and log-spaced; the true optimum could fall between
  grid points. The regularisation-sensitivity chart shows the holdout curve
  is fairly flat once past the transition region, so this is a minor risk.
- Iterative robust reweighting (IRLS, Tukey biweight) in the advanced model
  can downweight *genuine* dispersion, not just data errors — observed
  directly on this dataset, where the fully-specified advanced model did
  not beat the simpler baseline on holdout RMSE (see
  `diagnostics/model_comparison.json`). Robust reweighting is not a free
  lunch and should not be assumed to always help; this submission reports
  the honest empirical outcome rather than tuning parameters until
  "advanced wins."
- DV01 and key-rate sensitivities are pure finite differences (per
  `CONVENTIONS.md`'s own definition), verified stable across bump sizes
  from 10bp down to 0.1bp (`bump_size_convergence` check, relative
  deviation < 0.01%). Key-rate DV01s sum to the parallel DV01 to within
  ~2e-5% in aggregate, by construction of the partition-of-unity tent bump
  shapes (`risk.key_rate_bump_shape`).

## Data-quality risks

Cleaning is entirely rule-based and deterministic (no ML, no random
imputation). It found and handled, on the supplied `market_observations.csv`:
stale/duplicate quotes from a backup feed (excluded in favour of the
fresher, spread-consistent quote), missing `quote_value` recovered from the
bid/ask midpoint, crossed bid/ask corrected by reordering, unit-scale
defects (×100 in both directions, for both rates and bond prices) corrected
against a robust local-peer or rolling-YTM-window reference, one bond
outlier only detectable via its own yield-to-maturity (not visible from its
raw price alone), and injected wide-spread/low-liquidity quotes
downweighted rather than excluded. See `diagnostics/cleaning.csv` for the
full per-observation audit trail and `reports/research_report.html` §3 for
a summary table and worked examples.

**Known limitation of the peer-reference method:** it uses a robust median
per maturity bucket (deposits/swaps) or rolling YTM window (bonds), which
has a breakdown point around 50% contamination *within a window*. On this
dataset, contamination per window/bucket is a small minority (at most 1–2
out of 3–7), so this is not observed in practice — confirmed directly by a
synthetic test in `tests/test_cleaning.py` that reproduces the masking
failure mode when a 4-bond window is deliberately given 50% contamination,
which is why that test now uses a realistically-sized (7-bond) window
instead. A dataset with denser corruption per local neighbourhood could
defeat this check.

**The 24 hidden holdout instruments referenced in the benchmark manifest
are never seen** by this model or by its own visible-holdout validation —
by design and by construction (they are not present in the supplied CSV).

## Interpolation and extrapolation behaviour

- Baseline: zero rate is **piecewise-linear** between calibration knots
  (deposit/OIS pillar tenors, 1/12Y–30Y); the instantaneous forward rate is
  therefore **kinked** at every knot (visible in `charts/forward_rate.png`).
- Advanced: zero rate comes from a **natural cubic spline** on cumulative
  log-discount, giving an **analytically smooth** forward curve, further
  shaped by a curvature-penalty regularisation term.
- **Extrapolation beyond the front (1/12Y) and back (30Y) calibration
  pillars is flat in the zero rate** for both models (the spline is
  evaluated with a linear extension using the boundary derivative; the
  piecewise-linear curve is flat by construction). No view on the true
  curve shape beyond the data is expressed or should be inferred from
  either model outside `[1/12Y, 30Y]`.
- One maturity region (~1.25Y–1.5Y) shows a sharp, real local feature
  attested by several independent, mutually consistent quotes (not a data
  error — see the executive summary in the HTML report). Both models
  reproduce it *when it is in the training set*, but it is **not
  recoverable by interpolation** if held out — this is a structural
  property of any smooth curve model, not a defect of either model, and is
  the reason the holdout-bucket selection screens out such points (see
  `calibration.build_holdout_split` and its docstring): testing
  generalisation on a genuinely non-generalisable point would swamp the
  comparison rather than inform it.

## Validation gaps

- The visible holdout is a **single-date cross-section**; there is no
  walk-forward/multi-date backtest (no historical snapshots were supplied).
- Holdout maturities are deliberately restricted to ones that are
  locally smooth relative to their neighbours (see above), so the reported
  holdout RMSE certifies interpolation accuracy at the tested points, not
  at every conceivable maturity.
- The leave-worst-out refit check (`diagnostics/sensitivity.json`) tests
  sensitivity to the single largest-residual training instrument, not to
  arbitrary subsets or combinations of instruments.
- No independent (e.g. broker-composite or exchange-settlement) reference
  curve was available to sanity-check the fitted curve against; validation
  is entirely internal to the supplied instrument quotes.

## Appropriate use

This curve is a **research/diagnostic artefact**, not a production trading
or risk-management curve. It is appropriate for: understanding the shape
and quality of the supplied instrument universe, comparing modelling
choices (baseline vs. regularised/robust), and illustrating standard
curve-construction and risk methodology. It is **not** appropriate for:
live pricing or hedging decisions (no bond-specific basis, no intraday
recalibration, no independent curve validation), or for maturities/dates
outside the calibrated range without an explicit, separately-documented
extrapolation policy.
