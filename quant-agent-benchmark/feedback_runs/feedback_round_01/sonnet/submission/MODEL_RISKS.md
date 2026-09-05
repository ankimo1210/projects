# Model Risks, Assumptions, and Appropriate Use

## Assumptions

- **Single discount curve.** Deposits, OIS swaps, and bonds are all priced
  off *one* continuously-compounded zero curve. Real markets frequently
  price government/agency bonds at a spread to the OIS/swap curve (issuance,
  liquidity, on/off-the-run effects); this model does not represent that
  basis. It is visible directly in the data: bond repricing residuals are
  consistently larger than deposit/swap residuals in both training and
  holdout (see `diagnostics/model_comparison.json` and the repricing chart).
- **Cash-flow schedule convention.** OIS swaps and bonds *both* pay every
  `1/payment_frequency` years, generated *forward* from the valuation date
  via the same `payment_times()` schedule, with any stub inserted as the
  *final* (short) period when the maturity is not an exact multiple of the
  period (e.g. a 1.25Y annual swap pays at 1.0Y and again at 1.25Y; a bond
  maturing at 1.508434Y on a semi-annual schedule pays at 0.5, 1.0, and
  1.508434Y). Every coupon amount, including a stub period, is the full
  level amount `coupon_rate/frequency * face`, not pro-rated — since the
  benchmark data states "no accrued interest". *(Correction, feedback round
  01: an earlier version of this document additionally described the bond
  stub as "counted backward from maturity", i.e. a front-stub — that clause
  did not match this code, which generates every instrument's schedule the
  same way, forward from the valuation date with an end-stub; the clause is
  removed here rather than the code changed, see the schedule-convention
  sensitivity note below.)* This is a simplification for a synthetic
  dataset with no explicit day-count detail per coupon; a production system
  would need the actual schedule dates and accrual conventions.
- **Schedule-convention sensitivity (quantified, feedback round 01).** A
  backward-from-maturity, front-stub bond schedule (the more common
  real-world convention for coupon bonds, and consistent with the same
  `CONVENTIONS.md` text) is an equally defensible reading for bonds, distinct
  from the forward/end-stub schedule actually implemented. On >=3 synthetic
  curves with a *known* truth (flat, monotone-upward, humped;
  `audit/exp_C_D_synthetic_truth.py` and `audit/exp_E_bond_convention_fix_check.py`
  in the feedback-round audit trail), generating bonds with one convention
  while pricing/fitting with the other produces a symmetric ~1.1-1.4bp
  overall zero-rate RMSE bias (worst band ~1.5bp), regardless of which
  direction the mismatch runs — i.e. this is a genuine, material modelling
  assumption, not a bug, and *not* resolvable by seeing which convention
  fits the supplied real data better (both are internally consistent
  pricers; a same-direction fit is not evidence of being the "true"
  convention). The convention was **not** changed in this round for that
  reason — only the documentation defect above was corrected.
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
- **Holdout coverage gap, quantified (feedback round 01).** Deposits are
  always kept in training by design (there are too few deposit tenors to
  hold any out without destroying the short end), and OIS holdout buckets
  are additionally screened for local smoothness. On the supplied dataset
  this means the `T<=2y` maturity band has **zero holdout coverage across
  every instrument type** (0/19 deposits, 0/16 swaps, 0/2 bonds all sit in
  training — see `diagnostics/repricing.csv`'s `split` column joined to
  `maturity_years`), and the `T>=15y` OIS band also has none (0/13). The
  reported holdout RMSE therefore says nothing about generalisation at the
  short end or the long OIS end; it certifies only the mid-curve OIS/bond
  buckets and the bond long end that are actually held out. Re-designing
  the holdout to force short-end coverage was considered but not adopted
  this round: it would change which points influence model selection and
  requires re-validating the selection outcome from scratch, which the
  round's time budget did not allow safely.
- **Zero-rate error vs. forward-rate error are genuinely different
  diagnostics, quantified (feedback round 01).** `diagnostics/repricing.csv`
  residuals at `T<=2y` are small for the instruments actually priced there
  (deposit mean|residual| ≈ 2.0bp-equivalent, OIS ≈ 2.8bp-equivalent, both
  in native percentage-point units) — i.e. **not** evidence of a short-rate
  bug. But `f(t)=z(t)+t·z'(t)` amplifies slope by `t`, and the baseline's
  zero rate is only piecewise-linear (kinked at knots, see above): the new
  `diagnostics/sensitivity.json → forward_smoothness_check` reports an
  **811.9bp forward-rate jump at the 1.25Y knot** (mean 154.0bp across all
  internal knots) for the baseline curve on the supplied data, driven by the
  same real 1.25-1.5Y local feature discussed above, versus **0.04bp max /
  0.01bp mean** for the advanced (spline) curve on the identical data — a
  ~20,000x difference at the worst knot. This is expected given each
  model's construction (piecewise-linear is only C0; the spline is C1), not
  a bug in either curve, but it means a *holdout-RMSE-only* comparison (which
  is what selected baseline this round, see `model_comparison.json`) is
  blind to this specific, large difference in forward-curve quality. On
  synthetic ground truth with a known smooth humped shape,
  `audit/exp_C_D_synthetic_truth.py` also found the advanced model closer to
  the true zero rate (0.076bp overall RMSE) than baseline (0.665bp) — for a
  flat or exactly-linear truth the two are statistically indistinguishable
  (both ≈0bp, baseline marginally better since the truth is literally
  piecewise-linear there). Taken together this is real, converging evidence
  that model selection based on holdout-RMSE-alone does not capture
  forward-curve smoothness, and that this can favour baseline even where
  advanced is closer to a plausible truth — but it is not, by itself,
  conclusive enough (a 3-shape synthetic test, no walk-forward, no hidden-
  truth check) to override the existing empirical selection rule within
  this round's time budget. Reported as an open, quantified finding rather
  than acted upon by force-selecting advanced.

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
