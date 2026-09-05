# Model risks and appropriate use

## Scope and assumptions

The implementation is a single-date research curve for documented USD deposits, spot-start par OIS swaps, and fixed-coupon bonds. It treats `maturity_years` as the authoritative ACT/365F coordinate. Deposits use simple interest, OIS fixed legs pay annually through 2Y and semiannually thereafter, and bonds pay level coupons at the stated frequency with face 100 and no accrued interest.

The input does not include effective dates, issue dates, holiday calendars, business-day adjustments, ex-coupon rules, accrued interest, collateral details, recovery, tax, or security-specific spread curves. Regular coupon times are therefore constructed from the valuation date, with principal at the supplied authoritative maturity. This is defensible for the benchmark conventions but is not a substitute for a production cash-flow engine.

## Data-quality risk

Rates may be in percentage points or incorrectly supplied as decimals under a `PERCENT` label; bond prices may be points or incorrectly scaled currency units. Unit repair compares alternate scales with maturity-local peers for rates and applies a documented range rule for bonds. A genuine isolated low or negative rate could be misclassified if peers are sparse. Every repair appears in `cleaning.csv` and should be reconciled with source metadata before use.

Missing quotes are replaced only when both bid and ask permit an observable midpoint. Bid/ask inversions are swapped. Duplicates retain the newest observation, then higher liquidity and source quality. Stale, incomplete-spread, off-market, and illiquid observations are retained with lower weights. Robust weighting identifies statistical inconsistency; it does not establish that the vendor quote is wrong.

## Statistical and interpolation risk

The baseline PCHIP curve is stable and shape-preserving at its aggregate knots, but bucket aggregation can blur short-lived or sharply localized market structure. Its three-point median stabilizer deliberately sacrifices local fit to prevent isolated securities from producing extreme forwards.

Deterministic synthetic checks in the feedback round confirmed this trade-off: retaining exact tenors reduced short-end known-curve error, but worsened fixed public holdout errors and aggregate synthetic forward stability. That variant was therefore not adopted. A standalone flat yield is exact for deposits and flat curves, but it is only a proxy for the maturity zero rate of coupon-bearing swaps and bonds on sloped curves.

The advanced natural-cubic spline can represent coherent unusual shapes and directly prices all cash flows, but knot placement and the curvature penalty are model choices. Too much smoothing biases short-end humps and inversions; too little can create oscillatory forwards. The supplied sensitivity file shows outcomes for smoothing values 0.2, 2, and 20 and robust thresholds 2, 3, and 4. Results outside that range are not validated.

Repeated maturity/type residuals are centered before Huber downweighting. This avoids rejecting an entire coherent tenor but can leave a common-mode vendor error at that tenor influential. Unique bonds do not receive this group protection.

## Extrapolation and numerical risk

Zero rates are extrapolated flat beyond the fitted knot domain. Discount factors remain positive because they are exponential transforms; they are not constrained to be decreasing. That is intentional for negative-rate regimes, but extreme fitted rates can still create economically implausible discount or forward curves. Parameter bounds and explicit forward-rate guardrails mitigate rather than eliminate this risk.

Natural cubic splines are continuous through the second derivative inside the domain. Instantaneous forward rates are computed analytically as `z(T) + T z'(T)`. At the flat-zero extrapolation boundary, the zero-rate derivative changes to zero, so extrapolated forward behavior is model-dependent.

Nonlinear least squares can converge to a local solution. Deterministic initialization, bounded parameters, strict tolerances, reproducibility tests, finiteness checks, and full-sample refits reduce this risk. A successful optimizer flag is necessary but not sufficient evidence of a good economic curve.

## Validation gaps

The visible holdout uses whole half-year maturity blocks and avoids leakage from same/nearby maturities. It tests interpolation across tenor regions, not forecasting through time. Only one valuation date is available, so there is no historical backtest, stressed-market study, or realized hedge-P&L validation. Hidden instruments are not inspected.

The public split contains no held-out deposit in this sample, so its short-end result is driven by OIS and a small number of bonds. Segment diagnostics are reported rather than treating the aggregate holdout score as universal evidence. Fractional-maturity bond coupon accrual remains ambiguous in the published convention; this implementation pays regular full coupons and principal at maturity, without an extra stub coupon.

DV01 and key rates measure only zero-curve moves. Bond credit/liquidity spread risk, convexity beyond the finite bump, funding effects, and instrument optionality are outside scope. Key-rate hats form a partition of unity, making their aggregate locally consistent with parallel DV01, but the four-key decomposition is coarse.

## Appropriate use

The outputs are appropriate for research, benchmark evaluation, data-quality triage, and preliminary risk analysis under the supplied conventions. They should not be used for financial reporting, collateral valuation, execution, or hedge sizing without production calendars and cash flows, source reconciliation, multi-date backtesting, independent model validation, and portfolio-level P&L checks.
