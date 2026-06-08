# johnhull 08_risk_var Design — Hull 11e Ch.22

Date: 2026-06-08
Status: Approved (recommended allocation auto-applied under the goal directive)
Parent spec: `docs/superpowers/specs/2026-06-07-johnhull-full-coverage-design.md`

## Goal

Volume 8: `johnhull/volumes/08_risk_var/` covering Ch.22 (VaR and Expected
Shortfall). hullkit addition: `risk.py`.

## hullkit addition: `risk.py` (TDD)

- `historical_var_es(pnl, alpha=0.99)` → (var, es): losses = −pnl;
  k = max(1, ceil((1−α)n)); VaR = k-th worst loss, ES = mean of the k worst
  (Hull's 500-scenario convention: 99% → 5th worst / mean of worst 5).
- `normal_var(sigma, alpha=0.99, horizon=1.0, mu=0.0)` = z_α·σ·√h − μ·h.
- `normal_es(sigma, alpha=0.99, horizon=1.0, mu=0.0)` = σ√h·φ(z_α)/(1−α) − μ·h
  (Hull eq. 22.1 form).
- `portfolio_sigma(amounts, vols, corr)` = √(aᵀCa), C_ij = ρ_ij σ_i σ_j
  (Hull eq. 22.3/22.4).

pytest pins (hand-verified; Hull's classic §22 example): $10M Microsoft
σ=2%/day → 10-day 99% VaR = 1,471,311 (Hull prints 1,471,300); $5M AT&T
σ=1%/day → 367,828 (367,800); portfolio ρ=0.3 → σ_P = 220,227 and VaR
1,620,114 (1,620,100); diversification benefit ≈ 219,026; normal ES with
σ=200,000: ES₁d = 2.6652σ; ES > VaR always (normal and historical);
historical VaR/ES on a constructed array with known k-th worst; √10 scaling.

## Notebook: `volumes/08_risk_var/` (build_risk_notebook.py → risk_var.ipynb)

25 cells (cap 35), Japanese prose.

| Sec | Cells | Content |
|---|---|---|
| 0 | 3 | intro / magic / imports |
| 1 | 4 | VaR/ES definitions + loss-distribution chart with both marked; coherence md (subadditivity, Basel FRTB VaR99→ES97.5); subadditivity-violation demo (two independent 0.8%-probability big losses: individual VaR99 = 0, combined > 0) |
| 2 | 6 | variance-covariance method; Hull two-asset example (pins above + diversification benefit); normal ES same example; interactive ρ slider → portfolio VaR/diversification chart; √N scaling + vol-clustering caveat (vol05 link) |
| 3 | 5 | historical simulation md (501 days, v_n·v_i/v_{i−1}); synthetic 2-asset demo with t-distributed fat tails → hist VaR/ES vs normal (hist > normal); P&L histogram with VaR/ES lines; stressed VaR + backtesting md; backtest demo (rolling VaR exceptions vs expected 1%) |
| 4 | 4 | delta vs delta-gamma approximation md (eq 22.7/22.8); option-position VaR three ways (delta-normal / delta-gamma MC / full-revaluation MC, using bsm + mc) — long call: delta-normal overstates downside; Cornish-Fisher / PCA / cash-flow mapping pointers md |
| 5 | 3 | assertion cell / exercises / summary |

Assertion cell: the four Hull pins; ES > VaR (both methods); subadditivity
violation booleans; historical pin on constructed data; delta-gamma VaR <
delta-normal VaR for the long-call demo; hist(fat-tail) VaR > normal VaR.

## Verification (DoD — as previous volumes)

Build; headless zero errors + 全チェック合格; hullkit pytest (68 → ~74);
ruff clean; GE-PDF citation review; ROADMAP/PROGRESS updated (`risk`).

## Out of scope

- EWMA/GARCH-driven VaR (covered conceptually via vol05 link), Cornish-Fisher
  implementation, PCA numerics, Kupiec test statistics, stressed-period
  selection, regulatory capital formulas.
