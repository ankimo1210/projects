# Model risks and appropriate use

## Assumptions

- The input follows the supplied USD, ACT/365F, spot-start, two-day-settlement
  conventions. `maturity_years` is authoritative; maturity dates are audited
  but not used to rebuild a holiday calendar.
- Deposit rates are simple annual rates. OIS fixed-leg dates use the provided
  frequency with a final stub. Bonds use clean price, level coupons, no
  accrued interest, face 100, and final principal repayment.
- Quotes tagged `PERCENT` are divided by 100. Bond coupons are already
  decimals and bond prices remain points per 100.

## Data-quality handling and risks

- Missing or structurally inconsistent observations are excluded; duplicate
  instruments keep the freshest valid observation. A quote outside bid/ask is
  corrected to its midpoint, and stale records have reduced quality weight.
- Bid/ask and liquidity are useful but not guarantees of correctness. A
  mutually consistent bad quote can survive static checks; robust IRLS only
  reduces its influence after residual review.
- All actions and final weights are visible in `diagnostics/cleaning.csv`.
  Users should review every correction and downweight before relying on the
  curve.

## Numerical and interpolation risk

- Calibration occurs in log-discount space, guaranteeing positive discount
  factors. Negative zero and forward rates are allowed by design.
- The baseline has discontinuous instantaneous forwards at knots. The advanced
  natural cubic spline is smoother but can still produce local forward-rate
  artifacts where observations are sparse. Regularisation strength is reported
  and perturbed in the sensitivity file.
- Optimisation is bounded to a broad but finite log-discount range to prevent a
  malformed observation from causing numerical overflow. A bound hit should be
  investigated, not treated as economic information.

## Extrapolation and validation gaps

- The published grid ends at 30Y. Beyond the final knot, any spline evaluation
  is a mathematical continuation and is not a validated market extrapolation.
- The visible holdout is blocked by maturity to prevent same-maturity leakage;
  it is not a historical out-of-time validation. It cannot establish future
  performance or protect against a market-regime change.
- Key-rate bumps form a 2Y/5Y/10Y/30Y partition of unity, including a flat
  front and long-end extension, so key sums approximate the parallel DV01.
  They are risk-reporting approximations rather than desk-specific hedging
  bucket definitions.

## Appropriate use

Use this output as transparent research and a controlled pricing diagnostic,
not as an independently governed production curve. Before production use,
validate source entitlements, calendars, business-day adjustment, accrual and
stub rules, collateral conventions, historical backtests, independent-price
checks, long-end extrapolation policy, and model-governance thresholds.
