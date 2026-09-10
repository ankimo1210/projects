# MODEL_RISKS.md — assumptions, risks and appropriate use

This document is the candid model-risk statement for the `quantcurve`
zero-curve project. Numbers quoted refer to the benchmark run in `outputs/`
(valuation date 2026-01-15); rerun the workflow to refresh them.

## 1. Assumptions

1. **Conventions as documented.** `maturity_years` (ACT/365F) is authoritative;
   deposits are simple-interest from the valuation date; OIS fixed legs are
   annual to 2Y and semi-annual beyond with level accrual `1/f`; bonds pay
   level coupons at `1/f` intervals, principal at maturity, clean = dirty
   (no accrued interest). Settlement lag is informational only.
2. **Cash-flow schedule = round-02 canonical pricing contract v2.0.** Coupon
   dates at every `k/m` strictly before `T` and then `T` itself (final short
   stub, no long stub, no rounding of `T·m`), `alpha_i = t_i - t_{i-1}` with
   `t_0 = 0`; OIS par `r = (1 - D(T)) / sum(alpha_i D(t_i))` with annual
   payments for `T <= 2` and semiannual beyond (a supplied frequency that
   disagrees is corrected to the rule and flagged); bond price
   `100 c sum(alpha_i D(t_i)) + 100 D(T)` (stub coupon proportional to its
   accrual, principal at `T`); `settlement_days` is metadata only. Verified in
   `tests/test_contract_v2.py` against an explicit enumeration of the contract
   text and against QuantLib 1.43 discount factors on continuous year
   fractions (T shorter than one period, on/off grid, zero coupon, negative
   rates with `D > 1`). The legacy readings of the first two rounds
   (`forward`, `forward_actual`, ...) are kept only as `--stub-rule`
   alternatives for sensitivity; under the inherited default the new data
   mispriced short OIS by 50-250bp (see `audit/before`).
3. **One curve for all instrument types.** Deposits, OIS and bonds are
   assumed to discount off the same curve; bond deviations are treated as
   noise (down-weighted through a per-type robust scale), not as a credit or
   liquidity spread.
4. **Quote noise model.** The noise scale of a quote is
   `sqrt(half_spread² + (0.5bp)²) / sqrt(liquidity × rule_factor)`, times a
   per-type robust factor estimated from residuals. The 0.5bp floor and the
   liquidity mapping are judgement calls, not calibrated from history.
5. **Smoothness prior.** The forward curve is assumed smooth; curvature is
   penalised with weight `((t+0.5)/5.5)^1`, i.e. the long end is smoothed
   roughly five times harder than the 5Y area and the front end is nearly
   free. The exponent is fixed a priori (the uniform penalty scores slightly
   better in CV but breaks the front end when the smoothing parameter is
   tripled: 34bp error at 1M versus 1.4bp with the weighted penalty).

## 2. Numerical risks

- **Optimiser.** Each penalised fit is a Levenberg–Marquardt solve with
  analytic Jacobians (verified against finite differences to 1e-9 relative);
  the IRLS outer loop converged (relative step < 1e-6) on the benchmark data.
  Convergence is reported in `model_comparison.json`; a non-converged flag
  should be treated as a warning, not an error.
- **Penalty matrix.** Exact Gauss quadrature per knot interval; the eigen
  square root drops modes below 1e-12 of the largest eigenvalue (the two
  linear modes are unpenalised by construction).
- **Discount factors are strictly positive** for any coefficient vector
  because `log D` is the integral of the spline; zero and forward rates may be
  negative (tested with a −1.2% curve). The baseline's flat-zero
  extrapolation is also positivity-safe.
- **Finite differences.** DV01 uses ±1bp central differences on the zero
  curve; agreement with the analytic derivative is 1.3e-6 relative and the
  half-step estimate agrees to 1e-6, so truncation error is negligible.
  Key-rate tents sum to the parallel bump, and the key-rate sum matches DV01
  to 5e-7 relative (second-order convexity only).
- **Warnings are surfaced, not silenced.** Any `RuntimeWarning` raised in the
  workflow is listed in `run_summary.json` and the report (none on the
  benchmark data); the test suite turns them into errors.

## 3. Data-quality risks

- **Detected and handled on the benchmark data** (see
  `diagnostics/cleaning.csv`): 7 backup-feed duplicates (stale, outside their
  own bid/ask), 7 ×100 scale defects (3 OIS, 1 deposit, 3 bond prices),
  4 missing quotes (bid/ask mid used), 4 crossed markets, 5 quotes dated 13
  days before the valuation date, 6 very wide-spread/illiquid quotes,
  6 cross-sectional outliers in replicated tenors (−15 to −170bp), and 4
  model-based rejections (a 9M deposit 16bp high that was the only liquid
  9M quote, a bond 121bp rich, two bonds 5–10bp off).
- **Residual risk.** The scale-defect rule is peer based: a defect at a tenor
  with no comparable peers, or a defect of a factor other than 100, is not
  corrected (the plausibility range then excludes it). Two independent
  errors in a two-quote cluster cannot be resolved cross-sectionally; the
  leave-tenor-out screen handles the single-liquid-quote case only when the
  neighbours are clean.
- **Concordant deviations.** The 7Y OIS quotes (three sources within 0.3bp)
  sit ~3bp above the smooth curve and the 1.25Y/1.5Y clusters ~1–2bp off in
  opposite directions; the model keeps them with bounded Huber weight rather
  than rejecting them. Whether these are genuine curve features or convention
  artefacts cannot be decided from one snapshot.
- **Stale-quote policy.** Quotes older than `--max-stale-days` (default 0)
  are excluded outright; with a single snapshot there is no basis for an
  age-decay weight.
- **Bond noise.** Bond yield-equivalent residuals are ~4bp RMSE versus
  <1bp for OIS; bonds therefore contribute little to the curve level and
  mostly inform shape between swap tenors. If bonds carry a genuine spread,
  the single-curve assumption biases the curve slightly towards bonds
  between tenors (the rates-only refit moves the curve by up to 1.1bp).

## 4. Interpolation and extrapolation behaviour

Knot coverage (dev v3): interior knots sit at rate tenors and, where rate tenors
are sparser than `--knot-bond-gap` (1.5Y), at bond maturities. Without this a
long end covered only by bonds cannot be represented by the spline, the
misfit is attributed to the bonds and the robust layer rejects them
(synthetic `tenor_sparse_long_long_hump`: 10.6 bp zero error, 6 clean bonds
excluded). Regions with no instruments at all (e.g. nothing beyond 5Y) are
still extrapolated with a flat forward and can be tens of bp wrong; the
synthetic bench keeps that case as an informational failure.

- **Interior.** The advanced curve interpolates in the instantaneous forward
  with a smoothness penalty; it does not reprice every quote exactly (that is
  the point), and its forward rates can show curvature between sparse long
  tenors (12Y–30Y) that is only weakly identified — the jackknife shows the
  30Y cluster alone moves the curve by up to 3.3bp and the quote-noise
  bootstrap gives ~1bp standard deviation at 20Y+ versus 0.15–0.3bp inside
  10Y. The baseline interpolates linearly in the zero rate, which implies
  jump discontinuities in the forward at every knot.
- **Below 1M.** Neither model is informed below the shortest deposit; the
  spline's forward at 0 is an extrapolated boundary value and the grid
  therefore starts at 1/12Y.
- **Beyond the last instrument.** The spline forward is held flat beyond the
  domain end; the baseline holds the zero rate flat. Neither is a forecast of
  long-dated rates; if the longest instrument is shorter than 30Y the grid
  still extends to 30Y and that segment must be read as extrapolation.
- **Other datasets.** Knots are placed at the rate-instrument tenors that
  the data contains (capped at 28); a dataset with very few tenors yields a
  correspondingly stiff curve, and a dataset without deposits/OIS is refused
  (bonds alone are not used to anchor the curve).

## 5. Validation gaps

- Hyper-parameters (smoothing parameter, and the fixed penalty exponent that
  was reviewed against CV) were selected on the same grouped folds used to
  report holdout performance; the advanced model's holdout numbers are
  mildly optimistic. The baseline has no tuned parameter.
- The holdout scores interpolation at held-out tenor clusters; extrapolation
  beyond the anchors is deliberately not scored. Instruments rejected by the
  full-data robust fit are not scored either, so the metrics describe
  performance on plausible quotes only.
- The time-aware split spans two hours of one day and shares tenors across
  train and test; it checks consistency with later quotes, not stability
  across days.
- Robust rejections rely on the smoothness prior; a genuine isolated market
  feature at a tenor with a single quote would be treated as an error.
- No comparison against an external reference curve was possible (none is
  supplied); the hidden-holdout evaluation of the benchmark is the only
  independent check.

## 6. Appropriate use

- Suitable for: marking a single-currency discount curve from a clean-ish
  snapshot, repricing and risk (DV01, key rates) of linear instruments,
  and as a research baseline for curve-construction choices.
- Not suitable for: pricing instruments beyond 30Y or below 1M without
  additional data, bonds with material credit/liquidity spreads, forward
  starting or cross-currency instruments, or any use that requires the
  curve to reprice every input quote exactly (use the baseline or reduce
  `--lambda` with the understanding that forward rates become jagged).
- Operational guidance: review `diagnostics/cleaning.csv` for every
  `exclude`/`correct`, read the sensitivity table before relying on the long
  end, and rerun with `--stub-rule` alternatives whenever the counterparty
  convention is uncertain.
