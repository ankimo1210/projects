# Instrument and Curve Conventions

- Valuation date: **2026-01-15**; currency: USD; settlement lag: two calendar days.
- `maturity_years` is the authoritative ACT/365F year fraction used for this synthetic benchmark. `maturity_date` is supplied for auditability.
- Rates in the input use percentage points (`PERCENT`): `2.35` means 2.35%, unless a data-quality defect must be detected and normalized.
- Bond coupons are decimals (`0.025` means 2.5%); prices use points per 100 face value.
- Deposit quotes use simple interest: `D(T) = 1 / (1 + r T)`.
- OIS swaps start at the valuation date. Fixed payments are annual through 2Y and semiannual thereafter. Par rates satisfy `r * sum(alpha_i D(t_i)) = 1 - D(T)`.
- Bonds pay level coupons at `1 / payment_frequency` year intervals, have face value 100, no accrued interest, and repay principal at maturity.
- Candidate zero rates must be continuously compounded annual decimals with `D(T) = exp(-z(T) T)`.
- Forward rates are instantaneous continuously compounded rates, consistent with `-d log(D(T))/dT`.
- Negative zero and forward rates are permitted; discount factors must remain strictly positive.
- DV01 is the central finite-difference change in receiver/fixed-instrument PV for a parallel one-basis-point yield move: `(PV[-1bp] - PV[+1bp]) / 2`. Deposits and swaps use notional 1,000,000; bonds use face 100.
- Key-rate sensitivities use local zero-rate bumps centered at 2Y, 5Y, 10Y, and 30Y; document the bump shape and ensure their aggregate is reasonably consistent with parallel DV01.
