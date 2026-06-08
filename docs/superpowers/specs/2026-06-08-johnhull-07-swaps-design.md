# johnhull 07_swaps Design — Hull 11e Ch.7, 34

Date: 2026-06-08
Status: Approved (recommended allocation auto-applied under the goal directive)
Parent spec: `docs/superpowers/specs/2026-06-07-johnhull-full-coverage-design.md`

## Goal

Volume 7: `johnhull/volumes/07_swaps/` covering Ch.7 (interest-rate and
currency swaps) and Ch.34 (nonstandard swaps). hullkit addition: `swaps.py`
built on `rates.py` curves.

## hullkit addition: `swaps.py` (TDD)

Curve = `(times, zero_rates)` tuple, continuous compounding, interpolated via
`rates.zero_interp`; `P(0,t)=e^{−z(t)t}`.

- `discount(t, curve)` — P(0, t).
- `swap_rate(pay_times, curve)` — par rate s = (1 − P(0,t_n)) / Σ τ_i P(0,t_i).
- `irs_value_bonds(notional, s_fixed, pay_times, curve, next_float_rate,
  accrual_to_next=None)` — receive-fixed V = B_fix − B_fl with
  B_fl = (L + L·r*·τ₁)·P(0,t₁) (floating bond worth par after reset).
- `irs_value_fras(notional, s_fixed, pay_times, curve, next_float_rate=None)`
  — FRA decomposition: per-period simple forwards from the curve,
  V = Σ L(s − f_i)τ_i P(0,t_i) (Hull's preferred approach).
- `currency_swap_value(domestic_times, domestic_cfs, domestic_curve,
  foreign_times, foreign_cfs, foreign_curve, spot)` — B_D − S₀·B_F.

pytest: par identity (s = swap_rate ⇒ BOTH valuation approaches ≈ 0 when the
preset first floating rate is curve-consistent); bonds ≡ FRA equality for
off-market fixed rates (1e-10); swap_rate hand value on a flat curve;
currency-swap pin = Hull 11e Example 7.2/7.3 (pay $4%/$10M vs receive ¥3%/¥1,200M, 2.5%/1.5% flat cc, S0=1/110 → receive-yen V ≈ 0.9628; Hull prints 0.9629); receive-fixed
value decreases as curve shifts up.

## Notebook: `volumes/07_swaps/` (build_swaps_notebook.py → swaps.ipynb)

25 cells (cap 35), Japanese prose, equation/chapter-first citations.

| Sec | Ch | Cells | Content |
|---|---|---|---|
| 0 | — | 3 | intro / magic / imports |
| 1 | 7 | 3 | IRS mechanics + cashflow-table demo (fixed vs floating legs); comparative advantage worked table (total gain a−b) and its critique |
| 2 | 7 | 6 | two valuation approaches md; swap rate from the volume-04 bootstrap curve; both-approaches-agree demo (at-par ≈ 0 and off-market equality); DV01/parallel-shift sensitivity chart; interactive curve-shift slider → swap value |
| 3 | 7 | 4 | currency swap mechanics + decomposition md; B_D − S₀·B_F valuation demo; forwards-view md; OIS/SOFR transition note |
| 4 | 34 | 6 | nonstandard zoo table (step-up/amortizing/compounding/basis/accrual/cancellable); compounding-swap forward-realized demo; LIBOR-in-arrears convexity formula F̂ = F + F²σ²τT/(1+Fτ) + magnitude chart; CMS/quanto pointers (Ch.30 → volume 11); equity swap + cancellable = swap + swaption md |
| 5 | — | 3 | assertion cell / exercises / summary |

Assertion cell: par identity both approaches; bonds≡FRA off-market; currency
currency pin 0.9628; in-arrears adjustment > 0 and matches the formula; receive-fixed
loses value when rates shift +100bp.

## Verification (DoD — as previous volumes)

Build; headless zero errors + 全チェック合格; hullkit pytest (62 → ~68);
ruff clean; GE-PDF citation review; ROADMAP/PROGRESS updated (module list
gains `swaps`).

## Out of scope

- OIS-vs-LIBOR dual-curve machinery (single OIS-style curve only, per Hull's
  post-2010 simplification); day-count calendars (year fractions direct)
- Swaption pricing (volume 11); CMS/quanto adjustment numerics (volume 11)
- Accrual-swap binary decomposition implementation (md only)
