# johnhull 09_credit_xva Design — Hull 11e Ch.9, 24, 25

Date: 2026-06-08
Status: Approved (recommended allocation auto-applied under the goal directive)
Parent spec: `docs/superpowers/specs/2026-06-07-johnhull-full-coverage-design.md`

## Goal

Volume 9: `johnhull/volumes/09_credit_xva/` covering Ch.24 (credit risk —
hazard rates, Merton, copula), Ch.25 (credit derivatives — CDS, indices,
CDOs), Ch.9 (XVAs — CVA/DVA/FVA family, lighter). hullkit addition:
`credit.py`.

## hullkit addition: `credit.py` (TDD)

- `survival_prob(t, hazard)` / `default_prob(t, hazard)` — constant or
  piecewise hazard via cumulative ∫λ; S(t)=exp(−∫λ).
- `hazard_from_spread(spread, recovery)` = spread/(1−R) (Hull eq. 24.2 approx).
- `cds_spread(hazard, recovery, r, maturity, freq=4)` — discrete protection
  leg (period default ≈ (S_{i−1}−S_i) paid mid-period with (1−R)) over
  premium leg + accrual; constant hazard.
- `merton_default_prob(E0, sigma_E, D, r, T)` → (V0, sigma_V, Q): solve the
  two-equation system (Hull eq. 24.3/24.4) by 2-D Newton/fsolve; Q=N(−d2).
- `gaussian_copula_conditional(Q, a, F)` — N((N⁻¹(Q)−aF)/√(1−a²)) (eq 24.8).
- `vasicek_credit_var(Q, rho, conf)` — N((N⁻¹(Q)+√ρ·N⁻¹(conf))/√(1−ρ)) (eq 24.10).

pytest pins (hand-verified): constant-hazard S(2)=e^{−0.04}, default consistency;
hazard_from_spread(0.012, 0.4)=0.02; cds_spread(0.02, 0.4, 0.05, 5, 4) ≈ 0.0119
(≈ λ(1−R)=0.012 first order, slightly below); Merton Example 24.3 (E0=3,
σE=80%, D=10, r=5%, T=1) → V0≈12.40, σV≈0.2123, Q≈0.127 (Hull 12.7%);
gaussian copula monotonic in F (Q(F) decreasing); vasicek_credit_var increases
with rho and conf and exceeds Q at high conf.

## Notebook: `volumes/09_credit_xva/` (build_credit_notebook.py → credit_xva.ipynb)

27 cells (cap 35), Japanese prose.

| Sec | Ch | Cells | Content |
|---|---|---|---|
| 0 | — | 3 | intro / magic / imports |
| 1 | 24 | 7 | hazard/survival md + curve chart; real vs risk-neutral PD (5–10×) md; spread↔hazard (eq 24.2) + bond-implied; Merton structural model (equity = call on assets) + Example 24.3 solve + distance-to-default; interactive Merton explorer (leverage/σ sliders → Q) |
| 2 | 25 | 7 | CDS mechanics + protection/premium legs md; CDS spread vs hazard demo + bootstrap from term structure; index (CDX/iTraxx) + s≈mean; Gaussian copula one-factor (eq 24.7/24.8) + conditional-PD chart; CDO tranche loss waterfall demo (equity/mezz/senior expected loss via copula MC) + correlation effect; correlation-smile md |
| 3 | 9 | 6 | XVA family table (CVA/DVA/FVA/MVA/KVA) md; CVA = Σ q_i v_i worked example on a swap-like exposure profile; netting/collateral effect chart; wrong-way risk md; DVA + own-credit paradox md |
| 4 | — | 4 | assertion cell / exercises / summary / closing |

Assertion cell: hazard/survival; spread↔hazard; cds_spread ≈ λ(1−R) band;
Merton Q ≈ 0.127 + V0/σV pins; copula monotonicity boolean; vasicek > Q at
99.9%; CVA worked value reproduces.

## Verification (DoD — as previous volumes)

Build; headless zero errors + 全チェック合格; hullkit pytest (75 → ~82);
ruff clean; GE-PDF citation review; ROADMAP/PROGRESS updated (`credit`).

## Out of scope

- KMV EDF mapping, CreditMetrics transition-matrix MC, base-correlation
  calibration, full CVA with netting sets/CSA, FVA/MVA/KVA numerics
  (md/conceptual only); Big-Bang fixed-coupon upfront conversion (md).
