# johnhull 04_futures_forwards_rates Design — Hull 11e Ch.2–6

Date: 2026-06-08
Status: Approved (rates-centric allocation confirmed with user)
Parent spec: `docs/superpowers/specs/2026-06-07-johnhull-full-coverage-design.md`

## Goal

Volume 4: `johnhull/volumes/04_futures_forwards_rates/` covering Ch.2 (futures
markets/margining), Ch.3 (hedging with futures), Ch.4 (interest rates — the
centerpiece), Ch.5 (forward/futures pricing), Ch.6 (interest rate futures).
One hullkit addition: `rates.py` — the curve/bond utility module that
volumes 07 (swaps) and 11 (IR derivatives) depend on.

## hullkit addition: `rates.py` (TDD)

Functions (continuous compounding throughout, Hull's book standard):
- `to_continuous(rate, m)` / `from_continuous(rate, m)` — eq (4.3)/(4.4)
- `bond_price(times, cashflows, zero_rates)` — zero_rates scalar or per-time array
- `bond_yield(times, cashflows, price)` — continuous YTM via brentq
- `macaulay_duration(times, cashflows, y)` / `convexity(times, cashflows, y)` — eq (4.8)/(4.14)
- `forward_rate(r1, t1, r2, t2)` — eq (4.5)
- `fra_value(notional, rate_fixed, rate_forward, t1, t2, r2)` — fixed-receiver FRA
- `bootstrap_zero_curve(instruments)` — instruments = list of
  `(maturity_years, annual_coupon, price)` on face 100, semiannual coupons
  (zero-coupon when annual_coupon=0), sorted-by-maturity sequential solve with
  linear interpolation on already-solved nodes; returns (times, zero_rates)
- `zero_interp(t, times, rates)` — linear interp, flat extrapolation

pytest reference pins (hand-verified; Hull prints in parens):
Table 4.3 bootstrap → zeros 1.6032% / 2.0101% / 2.2245% / 2.2845% / 2.4162%
(1.603/2.010/2.225/2.284/2.416); Table 4.2 bond price 98.385 (98.39) and
YTM 6.76%; Table 4.6 duration example B=94.213, D=2.653, ΔB≈−BDΔy check +
convexity improvement; compounding round-trips + 10% semi = 9.758% cc;
forward_rate(3%@1y, 4%@2y) = 5% exact; FRA(L=100M, RK=5.8%, RF=5.0%,
T1=1.5, T2=2, R2=4%) = 369,247 (Hull ≈369,200).

## Notebook: `volumes/04_futures_forwards_rates/` (build_futures_rates_notebook.py → futures_rates.ipynb)

34 cells (cap 35), Japanese prose, conventions per parent spec. All §/eq/Table
citations verified against the repo's 11e GE PDF at review time.

| Sec | Ch | Cells | Content |
|---|---|---|---|
| 0 | — | 3 | intro / `%matplotlib widget` / imports |
| 1 | 2 | 2 | mechanics digest incl. forward-vs-futures table + margin-account simulation (Table 2.1 format: 2 gold contracts ×100oz, seeded path, margin calls; invariant: cumulative gain = (F_T−F_0)×200) |
| 2 | 3 | 4 | hedge basics/basis risk; optimal hedge ratio h*=ρσ_S/σ_F with simulated ΔS/ΔF (ρ=0.928, σ_S=0.0263, σ_F=0.0313 → h*≈0.78, jet-fuel N*≈37; variance-vs-h curve); beta hedging (V_A=$5.05M, F=1010×250, β=1.5 → N*=30; β→β* changes) |
| 3 | 4 | 10 | centerpiece: compounding conversions; bond price/YTM/par yield (Table 4.2); bootstrap (Table 4.3) with curve chart; forward rates + FRA; duration/convexity (approximation-vs-actual chart) |
| 4 | 5 | 6 | cost of carry (eq 5.1–5.3, FX 5.9, asset-type table); forward valuation f=(F₀−K)e^{−rT} (5.4–5.7 identity checks); interactive term-structure F₀(T)=S e^{(r+u−q−y)T} (contango/backwardation) |
| 5 | 6 | 6 | day counts + accrued interest (actual/actual vs 30/360); T-bond futures CF/CTD selection table; eurodollar-SOFR futures + convexity adjustment ½σ²t₁t₂ chart + duration-based hedge N*=P·D_P/(V_F·D_F) (=79.42 for the classic P=$10M, D_P=6.8, V_F=93,062.50, D_F=9.2) |
| 6 | — | 3 | assertion cell / exercises / summary |

Assertion cell: compounding pin + round trip; Table 4.2 price/YTM; all five
bootstrap zeros; forward_rate exact 5%; FRA 369,247; duration B/D pins +
linear-approx check; F=40e^{0.05·0.25}=40.5031 (40.50); forward-value identity
(5.4)≡(5.5) to 1e-12; h* 0.7798 and N* 30.0; duration hedge 79.42; margin-sim
invariant.

## Verification (DoD — same as volumes 01–03)

Build via uv run; headless nbconvert zero errors + 全チェック合格; hullkit
pytest green (39 → ~51); ruff clean (johnhull); GE-PDF citation review;
widget interactivity = user check; ROADMAP/PROGRESS updated.

## Out of scope

- Sample yield-curve patterns from `interest_rate_models/market_data.py`
  (notebooks generate their own; revisit if volume 07/11 needs them)
- Eurodollar-futures-based bootstrap (eq 6.2) — markdown mention only
- Tailing the hedge beyond a markdown note; stack-and-roll simulation
- Day-count date arithmetic with real calendars (fractional-period
  approximation only)
