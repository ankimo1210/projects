# Volume 26 Validation — G8

- Gate: **PASS** (`integration_and_reproducibility`)
- Model performance approved: **no**
- Status: reference artifact and executed notebook generated
- Data policy: synthetic-offline
- Network/training/download during notebook execution: none

## Artifact evidence

| Metric | Value |
|---|---:|
| `coupon_floor_max_error` | 0.0 |
| `floor_adjusted_breakeven_inflation` | 0.010228827638702365 |
| `floor_decomposition_error` | 0.0 |
| `floor_mc_zscore_max` | 1.1974973083142517 |
| `floor_monotone_in_volatility` | True |
| `hw_curve_fit_max_error` | 0.0 |
| `jy_forward_mc_zscore_max` | 1.4888912714624325 |
| `measure_treatment` | nominal_payment_forward |
| `principal_floor_redemption_only` | True |
| `raw_breakeven_inflation` | 0.00995024875621886 |
| `seasonality_annual_log_sum` | 1.734723475976807e-18 |
| `yoy_convexity_bp` | 0.9818821980900339 |
| `zcis_repricing_max_error` | 0.0 |

## Acceptance checks

| Check | Observed | Criterion | Pass |
|---|---:|---|:---:|
| `hull_white_initial_curve` | 0.0 | <= 1e-12 | PASS |
| `annual_seasonality_normalization` | 1.734723475976807e-18 | <= 1e-12 | PASS |
| `zcis_quote_repricing` | 0.0 | <= 1e-10 | PASS |
| `jy_forward_measure_mc` | 1.4888912714624325 | aligned arrays and maximum analytic/MC z-score < 3 | PASS |
| `jgbi_floor_analytic_mc` | 1.1974973083142517 | aligned arrays and maximum non-degenerate z-score < 3 | PASS |
| `floor_volatility_monotonicity` | True | analytic floor is non-decreasing in inflation volatility | PASS |
| `redemption_only_principal_floor` | 0.0 | coupons identical and floored final principal exceeds unfloored principal | PASS |
| `floor_payoff_decomposition` | 0.0 | <= 1e-12 | PASS |
| `nominal_payment_forward_measure` | nominal_payment_forward | explicit nominal payment-forward measure with non-zero YoY convexity | PASS |
| `raw_and_floor_adjusted_breakeven` | 0.0002785788824835045 | two explicitly different BEI measures | PASS |
| `synthetic_hedge_decomposition` | 2 | nominal-duration and CPI-delta residuals are reported separately | PASS |

## Negative results

- All curves, CPI fixings, option quotes, and hedge ratios are synthetic rather than market calibrated.
- The v1 model uses deterministic seasonality and one-factor nominal/real Gaussian rates.
- Production ISDA disruption fallbacks and live JGBi settlement operations are out of scope.

## Rebuild

```bash
uv run --no-sync python johnhull/scripts/build_frontier_artifacts.py --volume 26
uv run --no-sync --package hullkit python johnhull/volumes/26_inflation_jgbi/build_26_inflation_jgbi_notebook.py
```

## Limitations

- Synthetic results are not evidence of market forecasting power.
- Research-track models remain optional and cannot fail the core notebook path.
- Core semantic identities are independently recomputed by the release verifier.
