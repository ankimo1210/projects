# Volume 27 Validation — G9

- Gate: **PASS** (`integration_and_reproducibility`)
- Model performance approved: **no**
- Status: reference artifact and executed notebook generated
- Data policy: synthetic-offline
- Network/training/download during notebook execution: none

## Artifact evidence

| Metric | Value |
|---|---:|
| `alloc_normal_var` | 77.52904630663974 |
| `alpha` | 0.99 |
| `christoffersen_ind_lr_clustered` | 9.894654433330203 |
| `christoffersen_ind_lr_iid` | 0.008064537982836129 |
| `christoffersen_ind_pvalue_clustered` | 0.00165759575466473 |
| `christoffersen_ind_pvalue_iid` | 0.9284439448072724 |
| `clustered_basel_zone` | yellow |
| `desk_report_es` | 89.2145706813487 |
| `desk_report_var` | 77.52904630663974 |
| `euler_additivity_error` | 0.0 |
| `euler_es_additivity_error` | 0.0 |
| `evt_alpha` | 0.999 |
| `evt_es` | 20.753067047383286 |
| `evt_es_identity_error` | 0.0 |
| `evt_threshold` | 5.0 |
| `evt_var` | 15.949662940402645 |
| `fhs_constant_vol_error` | 0.0 |
| `fhs_var_constant` | 0.04886253563711847 |
| `fhs_violation_rate` | 0.01 |
| `gpd_beta_hat` | 0.9332212999765327 |
| `gpd_beta_true` | 1.0 |
| `gpd_n_exceedances` | 500 |
| `gpd_xi_hat` | 0.24567805084324695 |
| `gpd_xi_true` | 0.2 |
| `hs_violation_rate` | 0.0145 |
| `kupiec_size_rejection_rate` | 0.05 |
| `kupiec_size_zscore` | 0.0 |
| `taylor_delta_only` | 29.343901557687268 |
| `taylor_delta_only_half` | 14.671950778843634 |
| `taylor_delta_residual` | 11.690588536237144 |
| `taylor_delta_residual_half` | 5.630239148711208 |
| `taylor_dgv_residual` | 0.3900125643060548 |
| `taylor_dgv_residual_half` | 0.08376719185447001 |
| `taylor_dgv_total` | 41.424502658230466 |
| `taylor_dgv_total_half` | 20.385957119409312 |
| `taylor_full_pnl` | 41.03449009392441 |
| `taylor_full_pnl_half` | 20.302189927554842 |
| `taylor_unexplained_share` | 0.009504506170622559 |
| `total_historical_es` | 89.2145706813487 |

## Acceptance checks

| Check | Observed | Criterion | Pass |
|---|---:|---|:---:|
| `kupiec_size_calibration` | 0.0 | iid rejection rate within z < 3 of nominal 5% (binomial SE, 400 replications) | PASS |
| `christoffersen_detects_clustering` | 0.00165759575466473 | clustered LR_ind p-value < 0.05 and LR_ind statistic exceeds the iid series | PASS |
| `fhs_constant_vol_identity` | 0.0 | <= 1e-12 | PASS |
| `fhs_coverage_improvement` | 0.01 | |FHS violation rate - (1-alpha)| < |plain-HS violation rate - (1-alpha)| | PASS |
| `gpd_parameter_recovery` | 0.04567805084324694 | |xi_hat - xi| <= 0.1 and |beta_hat/beta - 1| <= 0.15 | PASS |
| `evt_var_es_identity` | 0.0 | <= 1e-12 | PASS |
| `euler_additivity_normal` | 0.0 | <= 1e-12 | PASS |
| `marginal_fd_consistency` | 1.027118008182688e-09 | analytic vs central-difference marginals, relative error <= 1e-6 | PASS |
| `euler_es_additivity_sim` | 0.0 | sum(ES components) == total historical ES and matches committed array, <= 1e-12 | PASS |
| `pnl_explain_taylor_ordering` | 0.3900125643060548 | dgv residual < delta-only residual; both shrink when moves halve | PASS |
| `desk_report_reproducible` | 0.0 | desk-report VaR equals Euler component sum and ES equals total historical ES | PASS |

## Negative results

- All P&L, exceedance, and tail samples are synthetic fixed-seed draws, not market data.
- FHS uses the committed EWMA conditional-volatility path; no live model calibration is performed.
- The Basel multiplier schedule is the 250-day BCBS table and is only documented, not re-derived, elsewhere.
- Cross-gamma, vanna, and vomma P&L-explain terms are out of scope (see hullkit.pnl_explain).

## Rebuild

```bash
uv run --no-sync python johnhull/scripts/build_frontier_artifacts.py --volume 27
uv run --no-sync --package hullkit python johnhull/volumes/27_risk_desk/build_27_risk_desk_notebook.py
```

## Limitations

- Synthetic results are not evidence of market forecasting power.
- Research-track models remain optional and cannot fail the core notebook path.
- Core semantic identities are independently recomputed by the release verifier.
