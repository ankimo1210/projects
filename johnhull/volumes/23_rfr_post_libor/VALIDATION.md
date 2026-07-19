# Volume 23 Validation — G5

- Gate: **PASS** (`integration_and_reproducibility`)
- Model performance approved: **no**
- Status: reference artifact and executed notebook generated
- Data policy: synthetic-offline
- Network/training/download during notebook execution: none

## Artifact evidence

| Metric | Value |
|---|---:|
| `bartlett_hedge_rmse` | 0.0003340079814252839 |
| `continuous_limit_error` | 4.45993810761075e-06 |
| `daily_compounding_handcheck_error` | 0.0 |
| `hagan_calendar_monotone_pass` | True |
| `hagan_high_vol_rmse_bp` | 26.214443819654765 |
| `hagan_long_maturity_rmse_bp` | 26.214443819654765 |
| `hagan_nonnegative_pass` | True |
| `hagan_static_arbitrage_pass` | True |
| `hagan_strike_convex_pass` | True |
| `hagan_strike_monotone_pass` | True |
| `hagan_wing_rmse_bp` | 21.32424980935272 |
| `hagan_worst_error_bp` | 60.63518673342441 |
| `hedge_teacher` | shifted-SABR full-truncation MC with common random numbers |
| `in_advance_coupon` | 10273.128311712791 |
| `in_arrears_coupon` | 10352.53834410721 |
| `lockout_rate` | 0.04142026796545917 |
| `lookback_rate` | 0.04151231072451367 |
| `multi_curve_coupon_pv` | 2.6399144642570382 |
| `observation_shift_rate` | 0.041484401111674174 |
| `quadrature_handcheck_error` | 6.938893903907228e-18 |
| `sabr_teacher` | conditional normal-SABR MC; shifted-SABR full-truncation MC |
| `sabr_teacher_nu` | 0.65 |
| `single_curve_coupon_pv` | 2.631479252266155 |
| `sofr_tona_basis_bp_1y` | 275.96927108916867 |
| `sticky_hedge_rmse` | 0.00036271090191143066 |
| `zero_rate_handcheck_error` | 0.0 |

## Acceptance checks

| Check | Observed | Criterion | Pass |
|---|---:|---|:---:|
| `rfr_conventions` | 4 | four observation conventions and both coupon timings | PASS |
| `daily_compounding_handcheck` | 0.0 | < 1e-12 | PASS |
| `continuous_limit` | 4.45993810761075e-06 | < 1e-5 | PASS |
| `bachelier_quadrature_handcheck` | 6.938893903907228e-18 | < 1e-12 | PASS |
| `multi_curve_policy_collateral` | 3 | SOFR/OIS/TONA curves plus policy and collateral scenarios | PASS |
| `nonzero_nu_teacher` | 0.65 | > 0 with positive SE | PASS |
| `hagan_diagnostics` | 60.63518673342441 | regime errors reported and static checks pass | PASS |
| `independent_hedge_paths` | True | sticky and Bartlett errors differ | PASS |
| `sabr_model_ladder` | 9 | shifted/free-boundary approximations and MC teacher with positive SE | PASS |

## Negative results

- Hagan's quick-grid worst error is 60.6352 bp.
- The free-boundary SABR fixture uses an explicit shift boundary rather than an endogenous boundary solve.
- Monte Carlo standard errors do not include time-discretization bias.

## Rebuild

```bash
uv run --no-sync python johnhull/scripts/build_frontier_artifacts.py --volume 23
uv run --no-sync --package hullkit python johnhull/volumes/23_rfr_post_libor/build_23_rfr_post_libor_notebook.py
```

## Limitations

- Synthetic results are not evidence of market forecasting power.
- Research-track models remain optional and cannot fail the core notebook path.
- Core semantic identities are independently recomputed by the release verifier.
