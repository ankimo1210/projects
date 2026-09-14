# Volume 25 Validation — G7

- Gate: **PASS** (`integration_and_reproducibility`)
- Model performance approved: **no**
- Status: reference artifact and executed notebook generated
- Data policy: synthetic-offline
- Network/training/download during notebook execution: none

## Artifact evidence

| Metric | Value |
|---|---:|
| `carbon_atm_black76_price` | 9.750668398221954 |
| `carbon_atm_heston_price` | 9.293620958236868 |
| `carbon_atm_jump_price` | 9.77883384942297 |
| `carbon_atm_standard_error` | 0.17495521242041653 |
| `carbon_black76_volatility` | 0.25 |
| `carbon_forward` | 100.0 |
| `carbon_maturity` | 1.0 |
| `carbon_model_ladder_complete` | True |
| `carbon_rate` | 0.02 |
| `hedge_residual` | 40.42651541814297 |
| `market_completeness` | incomplete |
| `ppa_alpha` | 0.95 |
| `ppa_cash_flow_at_risk95` | 65.69238346389739 |
| `ppa_cvar95` | 82.3691062150823 |
| `ppa_hedge_residual` | 40.42651541814297 |
| `premium_principle` | standard_deviation |
| `price_generation_correlation` | -0.5927276785284812 |
| `weather_basis_rmse_100km` | 2.4258099230251826 |
| `weather_fou_lag1_autocorrelation` | 0.9661916217361509 |
| `weather_ou_lag1_autocorrelation` | 0.8306188484659933 |
| `weather_premium_principle` | standard_deviation |

## Acceptance checks

| Check | Observed | Criterion | Pass |
|---|---:|---|:---:|
| `market_completeness` | 731.4813189586184 | label == incomplete; premium principles disagree (ptp > 0) and off-site basis hedges leave residual variance (variance reduction < 1) | PASS |
| `premium_principles` | 3 | three explicit non-traded-index principles | PASS |
| `carbon_premium_sensitivity` | 1.1303935436982258 | > 0 | PASS |
| `carbon_model_ladder` | 1.0865168682003306 | Black-76 rebuilt from (F, r, T, sigma) matches the committed row (1e-10); the ladder stacks the four committed price rows; constant-variance GBM MC within 4 SE of Black-76 at every strike; zero SE for Black-76, positive for the MC rows | PASS |
| `weather_long_memory` | 0.9661916217361509 | fractional OU lag-1 correlation exceeds OU with finite degree-day moments | PASS |
| `weather_basis_risk` | 5.566902660585961 | increases from zero-distance baseline | PASS |
| `basis_hedge_diagnostics` | 0.9999414442205588 | finite hedge ratios and variance reduction in [0, 1] | PASS |
| `ppa_risk_decomposition` | 3.552713678800501e-15 | fair value == mean(hedged - merchant) == sum of period settlement means; unhedged std == merchant std; hedge-ratio ladder spans unhedged std (h=0) to hedged residual (h=1) (all rebuilt from the samples, 1e-9) | PASS |
| `ppa_cashflow_risk` | 0.0 | expected cash flow, CFaR = mean - q(1-alpha), CVaR = mean - mean(tail <= q) and residual std rebuilt from the hedged samples match the committed arrays (1e-9); CVaR >= CFaR > 0; pay-as-produced metrics match | PASS |

## Negative results

- Weather and PPA values are premium-principle dependent because the underlying market is incomplete.

## Rebuild

```bash
uv run --no-sync python johnhull/scripts/build_frontier_artifacts.py --volume 25
uv run --no-sync --package hullkit python johnhull/volumes/25_climate_energy/build_25_climate_energy_notebook.py
```

## Limitations

- Synthetic results are not evidence of market forecasting power.
- Research-track models remain optional and cannot fail the core notebook path.
- Core semantic identities are independently recomputed by the release verifier.
