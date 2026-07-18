# Volume 18 Validation — G1

- Gate: **PASS** (`integration_and_reproducibility`)
- Model performance approved: **no**
- Status: reference artifact and executed notebook generated
- Data policy: synthetic-offline
- Network/training/download during notebook execution: none

## Artifact evidence

| Metric | Value |
|---|---:|
| `break_even_batch` | None |
| `delta_mae` | 0.0017494819891811248 |
| `dml_improved_a_greek_without_price_degradation` | True |
| `hard_violation_rate` | 0.0 |
| `heston_bsm_residual_mae` | 0.0006117290429284944 |
| `heston_raw_price_mae` | 0.012620526620790065 |
| `price_mae_normalized` | 0.0005593846268355811 |
| `soft_penalty_improved_hard_checks` | False |
| `split_overlap_count` | 0 |
| `teacher_ci_coverage_20_seeds` | 0.9 |
| `teacher_ci_coverage_20_seeds_by_estimand` | {'delta': 1.0, 'price': 0.9, 'vega': 0.9} |
| `teacher_se_ratio_4x_paths` | 0.5036523091029843 |
| `teacher_se_ratio_4x_paths_by_estimand` | {'delta': 0.5000675502958665, 'price': 0.5036523091029843, 'vega': 0.5018588397313818} |

## Acceptance checks

| Check | Observed | Criterion | Pass |
|---|---:|---|:---:|
| `split_overlap_count` | 0 | == 0 | PASS |
| `price_mae_normalized` | 0.0005593846268355811 | < 0.001 | PASS |
| `delta_mae` | 0.0017494819891811248 | < 0.002 | PASS |
| `hard_check_set` | 8 | exact documented 8-check set | PASS |
| `hard_check_violations` | 0 | == 0 | PASS |
| `residual_baseline` | 0.0006117290429284944 | < raw-price MAE | PASS |
| `mc_ci_coverage` | 0.9 | each estimand in [0.80, 1.00] | PASS |
| `mc_standard_error_scaling` | 0.5036523091029843 | each 4x-path ratio in [0.40, 0.60] | PASS |

## Negative results

- The quick soft-penalty ablation did not improve the hard-check count.
- No neural CPU break-even batch was observed in the measured quick profile.

## Rebuild

```bash
uv run --no-sync --package deep-hedge-price python deep_hedge_price/scripts/export_johnhull_pricing_reference.py --config deep_hedge_price/configs/pricing_quick.yaml
uv run --no-sync --package hullkit python johnhull/volumes/18_ml_surrogates/build_18_ml_surrogates_notebook.py
```

## Limitations

- Synthetic Black-Scholes accuracy is not evidence of market forecasting power.
- The OOD shell remains a stress diagnostic and is not an acceptance claim.
- The 512-path Monte-Carlo benchmark is a latency workload, not a precision result.
- The small ablation may fail absolute main-run thresholds and is used only for relative comparison.
- Research-track models remain optional and cannot fail the core notebook path.
- Core semantic identities are independently recomputed by the release verifier.
