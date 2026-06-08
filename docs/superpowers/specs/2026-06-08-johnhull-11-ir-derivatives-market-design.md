# johnhull 11_ir_derivatives_market Design — Hull 11e Ch.29, 30

Date: 2026-06-08
Status: Approved (recommended allocation auto-applied under the goal directive)
Parent spec: `docs/superpowers/specs/2026-06-07-johnhull-full-coverage-design.md`

## Goal

Volume 11: `johnhull/volumes/11_ir_derivatives_market/` covering Ch.29
(standard market models — bond options, caps/floors, swaptions via Black) and
Ch.30 (convexity, timing, quanto adjustments). hullkit addition:
`ir_options.py`, built on `rates.py`/`swaps.py`. Connects to `ir_models`
(short-rate models) at the curve level.

## hullkit addition: `ir_options.py` (TDD)

- `bond_option_black(P0T, F_B, K, sigma_B, T, kind="call")` — eq 29.1/29.2.
- `caplet_black(L, delta, F, R_K, sigma, t_k, P_pay, kind="caplet")` — eq
  29.7/29.8 (P_pay = P(0, t_{k+1})).
- `cap_black(L, forwards, strikes_or_strike, sigma, accruals, pay_discounts,
  fixing_times, kind="cap")` — sum of caplets/floorlets given per-period
  forwards F_k, accruals δ_k, pay discounts P(0,t_{k+1}), fixing times t_k.
- `swaption_black(L, annuity, s_F, s_K, sigma, T, kind="payer")` — eq
  29.10/29.11.
- `convexity_adjustment(y_F, sigma_y, T, g2_over_g1)` — eq 30.1 form
  E_T(y_T) = y_F − ½ y_F² σ_y² T · (G″/G′); plus a `bond_yield_convexity`
  helper computing G″/G′ for a standard coupon bond.

pytest pins (hand-verified): caplet 519.0046 / floorlet 2823.9125 (L=1e6,
δ=0.25, F=7%, R_K=8%, σ=20%, t_k=1, P=e^{−0.065·1.25}); caplet−floorlet =
L·δ·P·(F−R_K) (1e-9, Black put-call parity); swaption payer−receiver =
L·A·(s_F−s_K) (1e-9); ATM swaption payer=receiver (s_K=s_F); cap−floor = pay-
fixed swap value (sum identity); bond_option call/put parity c−p =
P(0,T)(F_B−K); convexity adjustment positive and ∝ T·σ_y²; kind ValueError.

## Notebook: `volumes/11_ir_derivatives_market/` (build_ir_options_notebook.py → ir_options.ipynb)

27 cells (cap 35), Japanese prose.

| Sec | Ch | Cells | Content |
|---|---|---|---|
| 0 | — | 3 | intro / magic / imports |
| 1 | 29 | 12 | why rates are hard (whole curve moves) md; Black framework md (bond=lognormal price, caplet=lognormal rate, swaption=lognormal swap rate; mutually inconsistent); bond option Black + yield-vol conversion σ_B≈D·y·σ_y; caps/floors md + caplet pricing from a bootstrap curve (uses rates.py forwards) + cap as caplet sum; cap-floor parity = swap (uses swaps.py) demo; flat vol vs spot vol + cap vol stripping (brentq) chart; swaptions md + payer/receiver Black + ATM payer=receiver + annuity from curve; interactive vol-cube slice (option-maturity / strike sliders → swaption price) |
| 2 | 30 | 8 | the 2-step valuation and when it breaks md; convexity adjustment (eq 30.1) — forward yield vs expected yield + magnitude chart (bond-price-yield nonlinearity); eurodollar/SOFR futures convexity ½σ²t₁t₂ recap (vol04 link); timing adjustment md (numeraire P(t,T)→P(t,T*)); quanto adjustment md + Siegel's paradox + diff-swap example; all-three-are-numeraire-change md (vol10 link) |
| 3 | — | 4 | assertion cell / exercises / summary / closing |

Assertion cell: caplet/floorlet pins; Black parity identities (caplet−floorlet,
payer−receiver); ATM payer=receiver; cap−floor=swap; convexity adjustment
sign+monotonicity; stripped spot vol reprices the cap.

## Verification (DoD — as previous volumes)

Build; headless zero errors + 全チェック合格; hullkit pytest (90 → ~98);
ruff clean; GE-PDF citation review; ROADMAP/PROGRESS updated (`ir_options`).

## Out of scope

- Full LMM/BGM (covered in ir_models volume); shifted-lognormal & Bachelier
  normal models for negative rates (md mention); volatility-cube calibration;
  Hull-White swaption analytic formula (ir_models); timing/quanto numerics
  (formula + md only, like vol07's pointers).
