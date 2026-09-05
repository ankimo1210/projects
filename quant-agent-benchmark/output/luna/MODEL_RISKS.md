# Model risks and appropriate use

## Assumptions

The model uses the supplied ACT/365F year fraction as authoritative, USD valuation date 2026-01-15, two-calendar-day settlement, annual OIS fixed payments through 2Y, semiannual OIS payments thereafter, and level coupon cash flows for bonds. Quotes are normalized from percentage points to annual decimals; bonds remain in price points. No accrued interest, business-day adjustment, collateral, or calendar logic is inferred beyond the supplied conventions.

Discount factors are represented as `exp(-z(T)T)`, so they remain strictly positive even when zero or instantaneous forward rates are negative. The dense-grid forward rate is the analytical `-d log(D)/dT` within each piecewise-linear zero-rate segment; at interior knots the reporting value is the deterministic midpoint of the left/right derivative, and beyond 30Y the constant-zero extrapolation implies a constant terminal forward.

## Numerical risks

The advanced fit is a nonlinear, weighted least-squares problem over piecewise-linear zero rates. Curvature regularisation stabilizes gaps but can smooth through genuine market discontinuities. Robust residual weights are updated four times; they reduce the influence of gross prints but do not prove a quote is wrong. Bounds are intentionally broad (`-25%` to `25%`) but still constitute a failure boundary for extreme datasets.

The baseline bootstraps using log-linear discount interpolation when a cash-flow date is not an observed pillar. The preferred curve is selected from visible whole-maturity holdout error, with a 5% tolerance before retaining the simpler baseline. Risk is a local central finite-difference result around the fitted curve and does not include re-hedging or stochastic scenario effects.

## Data-quality risks

The input is intentionally imperfect. Deterministic decimal-fraction scaling, missing quote midpoint recovery, and crossed bid/ask reordering are recorded as `correct`. Backup duplicates are excluded in favor of a fresh non-backup observation. Stale observations and low-liquidity observations are retained with lower weights. Gross same-maturity rate outliers are excluded only where at least two peers provide a defensible comparison. Every raw row is preserved in `diagnostics/cleaning.csv`.

This is a single synthetic snapshot. It cannot establish source reliability, historical stability, or dealer consensus. A production pipeline should add source lineage, calendar validation, independent stale-price rules, and human review for any exclusion affecting a risk limit.

## Interpolation and extrapolation

Zero rates are linearly interpolated between fixed knots. The zero rate is held constant beyond 30Y; therefore the long-end tail is deterministic and not an economic forecast. Key-rate sensitivities use four triangular basis functions that sum to one at every maturity, with nearest-key clamping outside the first and last key.

## Validation gaps and failure modes

Visible validation uses whole maturity clusters near 2Y, 5Y, 10Y, 20Y, and 30Y. This prevents same-maturity quote leakage but remains a single-snapshot test. It does not replace rolling backtests, regime-shift tests, independent reference curves, or bid/ask P&L validation. Failure modes include too few front-end deposits, no valid instrument after cleaning, a long-end regime change, malformed cash-flow metadata, or a dataset whose units are not covered by the documented schema.

The HTML report shows repricing, sensitivity, risk finite-difference checks, and the model comparison. If those diagnostics materially deteriorate on a new dataset, use the actionable CLI error or investigate the row-level audit before relying on the curve.

## Appropriate use

Use this project for reproducible research, curve-shape inspection, and scenario-risk prototyping on data conforming to the supplied conventions. Do not use it as a production pricing service without validating instrument-specific calendars, collateral/discounting, market-data governance, independent reference prices, and operational controls.
