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
| `carbon_model_ladder_complete` | True |
| `hedge_residual` | 40.42651541814297 |
| `market_completeness` | incomplete |
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
| `market_completeness` | incomplete | == incomplete | PASS |
| `premium_principles` | 3 | three explicit non-traded-index principles | PASS |
| `carbon_premium_sensitivity` | 1.1303935436982258 | > 0 | PASS |
| `carbon_model_ladder` | 4 | Black-76 and three MC models with aligned uncertainty | PASS |
| `weather_long_memory` | 0.9661916217361509 | fractional OU lag-1 correlation exceeds OU with finite degree-day moments | PASS |
| `weather_basis_risk` | 5.566902660585961 | increases from zero-distance baseline | PASS |
| `basis_hedge_diagnostics` | 0.9999414442205588 | finite hedge ratios and variance reduction in [0, 1] | PASS |
| `ppa_risk_decomposition` | 3 | finite CVaR/residual and hedge sensitivity | PASS |
| `ppa_cashflow_risk` | 65.69238346389739 | finite aligned CFaR diagnostics and CVaR >= CFaR > 0 | PASS |

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
