# johnhull 03_greeks Design — Hull 11e Ch.19

Date: 2026-06-08
Status: Approved (hullkit-module hedging simulator confirmed with user)
Parent spec: `docs/superpowers/specs/2026-06-07-johnhull-full-coverage-design.md`

## Goal

Volume 3: `johnhull/volumes/03_greeks/` covering Ch.19 (the Greek letters),
centered on the delta-hedging simulation (Hull §19.3–19.4, Tables 19.1–19.4).
Two hullkit additions: analytic Greeks in `bsm.py` (deferred from volume 01)
and a new `hedging.py` simulation module.

## hullkit additions

### bsm.py extension (Table 19.6, all with q=0.0 default)

- `gamma(S, K, r, sigma, T, q=0.0)` = e^{−qT} φ(d1) / (S σ √T) — same for calls/puts
- `vega(S, K, r, sigma, T, q=0.0)` = S e^{−qT} φ(d1) √T — per 1.0 vol; same calls/puts
- `call_theta` / `put_theta` — per YEAR (notebook shows /365 conversion)
- `call_rho` / `put_rho`

pytest (`test_greeks.py`): pin the Hull §19 running example
S=49, K=50, r=5%, σ=20%, T=0.3846 (hand-verified exact values, Hull prints in
parens): Δ=0.5216 (0.522), Γ=0.0655 (0.066), V=12.105 (12.1),
Θ=−4.3055/yr (−4.31), ρ=8.9066 (8.91), price 2.4004 (2.40);
BSM PDE identity Θ + rSΔ + ½σ²S²Γ = r·c (tol 1e-9); central finite-difference
cross-checks for gamma/vega/theta/rho against bumped prices; put rho < 0.

### hedging.py (new; q=0 scope, documented)

- `simulate_delta_hedge(S0, K, r, sigma, T, n_rebalance, n_paths, mu=None, rng=None)`
  → array of n_paths discounted hedge costs per share for writing + dynamically
  delta-hedging one European call (Hull §19.4 algorithm: rebalance to Δ at
  equally spaced times, cash carried at r, expiry settlement at K if ITM).
  mu defaults to r; real-world mu only affects dispersion, not the mean.
  Vectorized over paths (internal array d1/N(d1), not per-path scalar calls);
  paths from `mc.simulate_gbm_paths`.
- `simulate_stop_loss_hedge(...)` same interface — naive cover-when-ITM
  strategy (hold 1 share iff S > K, traded at grid prices; Hull §19.3).
- pytest (`test_hedging.py`): (a) mean delta-hedge cost ≈ BSM price 2.4004
  (Hull params, deterministic via mc's default seed); (b) mu-invariance of the
  mean (mu=0.13 vs mu=0.05); (c) performance measure (std/BSM price) improves
  as n_rebalance grows (Table 19.4); (d) stop-loss performance does NOT
  converge — stays well above delta-hedge at high frequency (Table 19.1);
  (e) shape/determinism basics.

## Notebook: `volumes/03_greeks/` (build_greeks_notebook.py → greeks.ipynb)

~30 cells (cap 35), Japanese prose, conventions per parent spec.
All §/eq/Table citations verified against the repo's 11e GE PDF at review time
(volume-02 lesson: section numbers shift between editions, not just figures).

| Sec | ~Cells | Content |
|---|---|---|
| 0 | 3 | intro / `%matplotlib widget` / imports |
| 1 | 5 | Greeks tour: Taylor P&L; interactive 2×3 panel (price, Δ, Γ, Θ, V, ρ vs S; T slider, call/put dropdown); Hull running-example Greeks table vs printed values; Table 19.6 q-generalization + futures delta H_F = e^{−(r−q)T} H_A |
| 2 | 6 | delta hedging (centerpiece): §19.4 mechanics; single-path weekly hedge table (Table 19.2 format, seeded); stop-loss §19.3 and why it fails; frequency-sweep performance table+chart (stop-loss vs delta, Tables 19.1/19.4 analogue); interactive hedge-cost histogram (n_rebalance dropdown, mu slider → mean≈BSM regardless of mu) |
| 3 | 6 | gamma=curvature (delta-approx error + ½Γ(ΔS)² correction chart); theta charts; BSM PDE identity numeric check (eq 19.4); delta-neutral P&L ≈ Θ·dt + ½Γ(ΔS)² scatter demo |
| 4 | 2 | gamma+vega joint neutralization: two-option 2×2 linear solve, verify residual Γ=V=0 |
| 5 | 2 | rho + currency-rho note; rho-vs-T chart |
| 6 | 2 | portfolio insurance = synthetic put (§19.13), equity-fraction-vs-value chart, 1987 lesson |
| 7 | 4 | assertion cell / exercises / summary |

Assertion cell: the six pinned Greeks + price; PDE identity; hedge-sim mean ≈
BSM (seeded); perf(high freq) < perf(low freq); stop-loss perf > 2× delta perf
at high frequency.

## Verification (DoD — same as volumes 01–02)

Build via uv run; headless nbconvert zero errors + 全チェック合格; hullkit
pytest green (30 → ~45); ruff clean (johnhull scope); widget interactivity =
user check; ROADMAP/PROGRESS updated.

## Out of scope

- Higher-order Greeks (vanna/vomma/charm) — markdown mention only; implement
  with volume 05 (vol smile) if needed.
- American Greeks via trees / numerical Greeks (volume 06, Ch.21/27).
- q≠0 hedging simulation; multi-asset portfolios beyond the 2-option solve.
