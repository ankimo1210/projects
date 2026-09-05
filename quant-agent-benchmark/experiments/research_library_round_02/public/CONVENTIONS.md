# Round 02: canonical pricing contract v2.0

This addendum supersedes conflicting conventions in the inherited project and
the original TASK. It applies only to this new experiment, not to old scores.

- Valuation date: 2026-01-15. USD. `maturity_years = T > 0` is authoritative;
  `maturity_date` is audit metadata. Do not round T to an integer number of days.
- All PVs are at time zero. `settlement_days` is metadata only: no settlement
  discounting, accrued interest, holiday adjustment, or spot-start shift.
- `PERCENT` means percentage points (2.35 = 0.0235). `PRICE_POINTS` means
  currency per face 100. Coupon rates are annual decimals. Units can be corrupt.
- Deposits: simple annual rate r; D(T) = 1 / (1 + r T).
- OIS frequency: annual for T <= 2; semiannual for T > 2. The supplied frequency
  must agree. Bonds use their supplied positive integer payment frequency m.
- Coupon dates: every k/m strictly before T, then T itself. Final short stub;
  alpha_i = t_i - t_(i-1), t_0 = 0. No long first stub or rounding of T*m.
  Example T=1.25, m=1: times [1, 1.25], accruals [1, 0.25].
- OIS par rate: r = (1 - D(T)) / sum(alpha_i D(t_i)).
- Bond price: 100 * coupon_rate * sum(alpha_i D(t_i)) + 100 * D(T).
  Principal is always paid at T; the stub coupon is proportional to its accrual.
- Zero rates: continuous annual decimal, D(T)=exp(-T*z(T)); D(0)=1.
  Forward: f(T)=-d log(D(T))/dT. Negative zero/forward rates are valid.
  D(T)>0 is required, but D(T)<=1 and decreasing D are NOT universal constraints.
- Receiver-fixed PV: deposit N*((1+r*T)*D(T)-1); OIS
  N*(r*sum(alpha_i*D(t_i))-(1-D(T))); bond model price minus trade price.
  N=1,000,000 for deposits/OIS; bond face=100.
- DV01: (PV(z-0.0001)-PV(z+0.0001))/2, in currency, not divided by bump size.
  Use the same cash flows for pricing and risk. Key-rate bumps remain documented
  zero-rate bumps at 2, 5, 10 and 30 years.

Validation must include T shorter than one coupon period, on-grid maturity,
off-grid maturity, zero coupon, and negative rates. Library calendar defaults
are not authoritative for this synthetic contract.
