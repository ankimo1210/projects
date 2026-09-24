# §26.16 Volatility and Variance Swaps — M8 design

Date: 2026-09-25. The user asked to continue the section-quality workflow with the next unreviewed section. Source: Hull 11e Global Edition §26.16, physical/printed pp.629–632 (the section ends where §26.17 starts on p.632). Unlike §26.14–§26.15, the section prints two worked examples (26.4 and 26.5), so printed anchors exist.

## Goal and contract

Complete requirements, independent numerics, implementation, teaching, figures and real-screen verification for §26.16. The ledger row is `unreviewed`; vol10 carries one uncommented code cell (strip replication under a flat smile) and `hullkit.variance_swaps` already implements eqs. 26.6–26.10 with Example 26.4/26.5 pins. The existence of that code is not acceptance evidence by itself. Do not claim other sections complete.

Contracts, as printed:

- Realized volatility over n daily observations with zero mean: `sigma = sqrt(252/(n-2) * sum_{i=1}^{n-1} ln(S_{i+1}/S_i)^2)`; Hull notes `n-1` sometimes replaces `n-2`. Realized variance rate `V = sigma^2`.
- Volatility swap pays `L_vol (sigma - sigma_K)` to the payer of the fixed volatility; variance swap pays `L_var (V - V_K)`; the conventional notional link is `L_var = L_vol / (2 sigma_K)`.
- Eq. 26.6 (from Technical Note 22): for any `S*`, `E(V) = (2/T) ln(F0/S*) - (2/T)(F0/S* - 1) + (2/T) ∫_0^{S*} e^{rT} p(K)/K^2 dK + (2/T) ∫_{S*}^∞ e^{rT} c(K)/K^2 dK`.
- Eq. 26.7: value of receiving realized variance against `V_K` is `L_var (E(V) - V_K) e^{-rT}`.
- Eq. 26.8: the strip `sum_i ΔK_i/K_i^2 e^{rT} Q(K_i)` with Hull's `ΔK_i`, `S*` = first strike below `F0`, and `Q` = put below, call above, average at `S*`.
- Eq. 26.9: `E(sigma) ≈ sqrt(E(V)) (1 - var(V)/(8 E(V)^2))`; the volatility swap is worth `L_vol (E(sigma) - sigma_K) e^{-rT}`.
- Eq. 26.10 (VIX): `E(V)T = -(F0/S* - 1)^2 + 2 sum_i ΔK_i/K_i^2 e^{rT} Q(K_i)`; interpolate the cumulative variance between the maturities around 30 days, multiply by 365/30, take the square root.

Units: prices and strikes in currency, `T` in years, `r`, `q` continuously compounded annual, volatilities annualized decimals, variance rates per year, `E(V)T` dimensionless cumulative variance, notionals in currency per unit of volatility or variance. Replication assumes a continuous-path diffusion observed continuously (the TN22 derivation); Hull's realized-volatility contract is daily and discrete. Jumps, discrete-monitoring corrections beyond the measured GBM case, dividends paid in cash, and the full CBOE VIX procedure (listed-strike selection, minute-level interpolation, forward determination) are outside this milestone.

## Requirements (VS01–VS06)

- VS01 contracts and units: realized volatility formula and its `n-2`/`n-1` variants, the two payoffs, `V = sigma^2`, and the notional link; a variance swap is convex in realized volatility where a volatility swap is linear.
- VS02 static replication: eq. 26.6 as an integral, why the log contract appears, and that the result does not depend on `S*`; validated beyond a flat smile against a model whose expected variance is known.
- VS03 discretization and Example 26.4: eq. 26.8, `ΔK_i`, `S*`, `Q(K_i)`; Hull's printed `Q` values, 0.008139, `E(V)=0.0621`, value 1.69 ($m); measured grid and truncation error of the strip against the continuous integral.
- VS04 volatility swaps and Example 26.5: eq. 26.9, 0.2484, 1.82 ($m); the approximation measured against an exact `E(sqrt V)` and MC; `E(sigma) < sqrt(E(V))`.
- VS05 VIX: the two-term truncation of `ln(F0/S*)` (eq. 26.10), its size on Example 26.4, and the 30-day interpolation/annualization Hull describes (not the full CBOE rulebook).
- VS06 teaching: six subsections in vol10 §4.6 and four shared figures on Book and portal, with the domain and limits stated.

## Numerics (M8a, independent of the library)

`scripts/build_variance_swap_reference.py` imports only NumPy/SciPy. It re-derives Example 26.4/26.5 with its own BSM; evaluates eq. 26.6 as a continuous integral with `quad` for flat-volatility BSM (answer `sigma^2`, checked at several `S*`) and for Heston prices from its own characteristic-function integral (answer `theta + (v0-theta)(1-e^{-kappa T})/(kappa T)`); measures the discrete strip against those integrals over grid spacing and strike range; computes the exact `var(V)` of continuously monitored Heston variance by `var = xi^2 ∫_0^T b(s)^2 E[v_s] ds`, `b(s) = (1-e^{-kappa(T-s)})/kappa`, and exact `E(sqrt V)` from the CIR Laplace transform `E[sqrt X] = (2 sqrt(pi))^{-1} ∫_0^∞ (1 - E[e^{-sX}]) s^{-3/2} ds`, cross-checked by a fixed-seed MC; and checks the daily realized-variance estimator's exact expectation under GBM. Outputs: `docs/validation/section-26-16/{reference,numerical-check}.json`, byte-reproducible via `--check`. Errors are reported with their method (quadrature estimate, MC standard error); no universal error bound.

## Implementation and delivery (M8b)

Public additions to `hullkit.variance_swaps` (not `exotics.py`, so earlier lesson hashes stay valid): `realized_variance(prices, periods_per_year=252, denominator="n-2")`, `realized_volatility(...)`, `variance_notional(volatility_notional, volatility_strike)`, and `vix_index(near_term, near_cumulative_variance, next_term, next_cumulative_variance, target_term=30/365)`. Existing functions keep their contracts.

Four saved-data figures in `hullkit._variance_swap_lesson`: `varswap_payoff` (linear vs convex payoff with the notional link, and their difference), `varswap_strip` (Example 26.4 `Q(K_i)` and strip contributions), `varswap_replication` (strip error against the continuous integral over grid spacing and strike range), `volswap_convexity` (eq. 26.9 against exact `E(sqrt V)` and MC ±4SE over vol-of-vol). Lesson JSON pins source hashes; notebook and report builds do no quadrature or MC. vol10 §4.6 gets six subsections; the existing variance-swap code cell is kept (the notebook's assertion cell reads its variables). Book and portal are checked at 1440/1000 px across all menu states with a numeric mutation that must be rejected.

Changing the shared vol10 notebook, builder, portal registry and stylesheet invalidates the hashes that the seven accepted sections (§26.9–§26.15) pin, so their tests and browser checks are rerun on the final build and recorded as M8 rechecks; historical records stay untouched.

## Review

Independent review has been part of every earlier milestone. This session does not spawn review agents unless the user asks, so the ledger row stays `pending_validation` after delivery and moves to `accepted` only after an independent review or an explicit user waiver (the §26.13 precedent).
