# Volume 21 Validation — G4

- Gate: **PASS** (`integration_and_reproducibility`)
- Model performance approved: **no**
- Status: reference artifact and executed notebook generated
- Data policy: synthetic-offline
- Network/training/download during notebook execution: none

## Artifact evidence

| Metric | Value |
|---|---:|
| `in_domain_greek_rmse` | 25.349173063933875 |
| `in_domain_price_rmse` | 0.4256623957319136 |
| `joint_spx_rmse` | 0.03640612872286824 |
| `joint_variance_rmse` | 0.012136360789840171 |
| `joint_vix_option_rmse` | 1.7147112919089407 |
| `joint_vix_rmse` | 4.139354595392237 |
| `ood_count` | 4 |
| `ood_greek_rmse` | 25.41046863034563 |
| `ood_price_rmse` | 0.3381758958670694 |
| `surrogate_delta_rmse` | 5.043078088519851 |
| `surrogate_gamma_rmse` | 35.50726161092219 |
| `surrogate_greek_rmse` | 25.359399280280453 |
| `surrogate_price_rmse` | 0.4123722655252687 |
| `surrogate_speedup_1024` | 914.2897131825704 |
| `teacher` | hullkit.spx_vix.nested_vix_teacher |
| `timing_method` | perf_counter_ns warm-cache median of 5 |
| `timing_nondeterministic` | True |

## Acceptance checks

| Check | Observed | Criterion | Pass |
|---|---:|---|:---:|
| `joint_model_ladder` | 4 | exact four-model ladder with all joint components | PASS |
| `teacher_surrogate_pairing` | True | price/delta/gamma shapes match | PASS |
| `teacher_uncertainty` | 16 | aligned, nonnegative, and nontrivial standard errors | PASS |
| `ood_shell` | 4 | > 0 flagged observations | PASS |
| `measured_cpu_timing` | perf_counter_ns warm-cache median of 5 | positive measured samples | PASS |
| `surrogate_speedup` | 914.2897131825704 | > 1 at batch 1024 | PASS |
| `joint_objective_components` | True | all four component errors finite | PASS |
| `in_domain_ood_diagnostics` | True | price and Greek RMSE finite in both domains | PASS |

## Negative results

- The polynomial surrogate Greek RMSE is 25.3594; this is a reported negative result, not a Greek-accuracy approval.
- The manufactured joint target has SPX RMSE 0.0364061 and VIX RMSE 4.13935.

## Rebuild

```bash
uv run --no-sync python johnhull/scripts/build_frontier_artifacts.py --volume 21
uv run --no-sync --package hullkit python johnhull/volumes/21_spx_vix/build_21_spx_vix_notebook.py
```

## Limitations

- Synthetic results are not evidence of market forecasting power.
- Research-track models remain optional and cannot fail the core notebook path.
- Core semantic identities are independently recomputed by the release verifier.
