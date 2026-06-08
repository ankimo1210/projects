# johnhull 10_exotics_martingales Design — Hull 11e Ch.26, 28

Date: 2026-06-08
Status: Approved (recommended allocation auto-applied under the goal directive)
Parent spec: `docs/superpowers/specs/2026-06-07-johnhull-full-coverage-design.md`

## Goal

Volume 10: `johnhull/volumes/10_exotics_martingales/` covering Ch.26 (exotic
options) and Ch.28 (martingales and measures). hullkit addition: `exotics.py`.
Ch.28 is shown numerically (numeraire invariance, market price of risk,
forward measure) rather than via new module functions.

## hullkit addition: `exotics.py` (TDD)

Closed forms (all with continuous yield q, Hull Ch.26):
- `gap_call(S, K1, K2, r, sigma, T, q=0.0)` — eq 26.1.
- `cash_or_nothing(S, K, r, sigma, T, q=0.0, kind="call", payout=1.0)` and
  `asset_or_nothing(S, K, r, sigma, T, q=0.0, kind="call")` — §26.10.
- `barrier_call(S, K, H, r, sigma, T, q=0.0, barrier="down-and-in")` — the
  four call barrier types via the λ/y/x₁/y₁ closed forms (§26.9), with
  in+out=vanilla used for the "-out" complements.
- `lookback_floating_call(S, S_min, r, sigma, T, q=0.0)` — §26.11.
- `asian_call_turnbull_wakeman(S, K, r, sigma, T, q=0.0)` — moment-matching
  M1/M2 into Black-76 (eq 26.3/26.4).
- `exchange_option(U0, V0, sigma_u, sigma_v, rho, T, q_u=0.0, q_v=0.0)` —
  Margrabe (eq 26.5), r-independent.

pytest pins (hand-verified): binary decomposition aon(K)−K·con(K) = vanilla
call (1e-12); barrier in+out = vanilla (c_di+c_do, 1e-12); barrier monotonic
(c_di increases as H→K from below); Margrabe r-independence (price unchanged
across r) and value 7.965567 (U0=V0=100, σ=0.2, ρ=0.5, T=1); gap call
13.112208 (S=100,K1=95,K2=100,r=5%,σ=20%,T=1); Turnbull-Wakeman Asian ≈
terminal-average MC (abs 0.1 at 200k paths) and < vanilla call (averaging
lowers vol); lookback floating ≥ ATM call value; cash-or-nothing put-call
(con call + con put = Q·e^{−rT}); kind/barrier ValueError.

## Notebook: `volumes/10_exotics_martingales/` (build_exotics_notebook.py → exotics.ipynb)

28 cells (cap 35), Japanese prose.

| Sec | Ch | Cells | Content |
|---|---|---|---|
| 0 | — | 3 | intro / magic / imports |
| 1 | 26 | 11 | exotics taxonomy md (15 types); binary options + decomposition (digital = aon − K·con; discontinuous payoff chart); barrier options 8-type md + in/out=vanilla identity + barrier-vs-H chart + knock-out payoff intuition; lookback (floating) + path demo; Asian Turnbull-Wakeman vs MC (averaging reduces vol → cheaper) + path-average chart; exchange/Margrabe (r-independence demo) + rainbow md; variance swap = log-contract static replication (md + discrete VIX-style strip demo); interactive barrier explorer (H/σ sliders → price + knock-out probability) |
| 2 | 28 | 11 | numeraire & martingale md (f/g is a martingale); market price of risk λ=(μ−r)/σ same across derivatives — numeric demo with two derivatives on one θ; risk-neutral measure (money-market numeraire) as λ=0; T-forward measure (P(t,T) numeraire) → F(t,T)=E^T[S_T] + Black-76 justification under stochastic rates; numeraire-invariance demo (price a forward-start/option three ways under different numeraires → same value); Girsanov (drift changes, vol invariant) + GBM-under-two-measures path demo (same σ, different drift); swap measure pointer (→ volume 11) |
| 3 | — | 3 | assertion cell / exercises / summary |

Assertion cell: binary decomposition identity; barrier in+out=vanilla; Margrabe
r-independence + value 7.9656; gap 13.1122; Asian < vanilla and ≈ MC;
numeraire-invariance (two numeraires give same price within tol); market-price-
of-risk equality across two derivatives.

## Verification (DoD — as previous volumes)

Build; headless zero errors + 全チェック合格; hullkit pytest (81 → ~89);
ruff clean; GE-PDF citation review; ROADMAP/PROGRESS updated (`exotics`).

## Out of scope

- Compound (Geske bivariate-normal), chooser, cliquet, perpetual American
  closed forms (md/formula only); fixed-strike lookback; Parisian/shout;
  full variance-swap replication integral (discrete strip demo only);
  measure-theory proofs (numerical illustration only).
