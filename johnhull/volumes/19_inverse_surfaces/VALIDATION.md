# Volume 19 Validation — G2

- Gate: **PASS** (`integration_and_reproducibility`)
- Model performance approved: **no**
- Status: reference artifact and executed notebook generated
- Data policy: synthetic-offline
- Network/training/download during notebook execution: none

## Artifact evidence

| Metric | Value |
|---|---:|
| `array_fingerprint` | sha256:4c1cd3f973efda05a09a3fb8917eff7fecf52ff09417d8cca2bee883c17936aa |
| `array_schema` | {'calibration_parameter_dispersion': {'dtype': '<f8', 'shape': [4], 'unit': 'dimensionless'}, 'calibration_parameters': {'dtype': '<f8', 'shape': [4], 'unit': 'dimensionless'}, 'calibration_start_initial': {'dtype': '<f8', 'shape': [4, 4], 'unit': 'dimensionless'}, 'calibration_start_parameters': {'dtype': '<f8', 'shape': [4, 4], 'unit': 'dimensionless'}, 'calibration_start_repricing_rmse': {'dtype': '<f8', 'shape': [4], 'unit': 'annualized_volatility'}, 'calibration_truth': {'dtype': '<f8', 'shape': [4], 'unit': 'dimensionless'}, 'constraint_clean_teacher_price': {'dtype': '<f8', 'shape': [4, 9], 'unit': 'spot_units'}, 'constraint_hard_price': {'dtype': '<f8', 'shape': [4, 9], 'unit': 'spot_units'}, 'constraint_maturities': {'dtype': '<f8', 'shape': [4], 'unit': 'years'}, 'constraint_raw_price': {'dtype': '<f8', 'shape': [4, 9], 'unit': 'spot_units'}, 'constraint_soft_price': {'dtype': '<f8', 'shape': [4, 9], 'unit': 'spot_units'}, 'constraint_strikes': {'dtype': '<f8', 'shape': [9], 'unit': 'spot_units'}, 'direct_inverse_test_prediction': {'dtype': '<f8', 'shape': [8, 4], 'unit': 'dimensionless'}, 'direct_inverse_test_quote': {'dtype': '<f8', 'shape': [8, 12], 'unit': 'dimensionless'}, 'direct_inverse_test_repricing': {'dtype': '<f8', 'shape': [8, 12], 'unit': 'dimensionless'}, 'direct_inverse_test_truth': {'dtype': '<f8', 'shape': [8, 4], 'unit': 'dimensionless'}, 'pareto_fit_parameters': {'dtype': '<f8', 'shape': [3, 2], 'unit': 'dimensionless'}, 'pareto_lambdas': {'dtype': '<f8', 'shape': [3], 'unit': 'dimensionless'}, 'pareto_losses': {'dtype': '<f8', 'shape': [3, 3], 'unit': 'dimensionless'}, 'pareto_nondominated': {'dtype': '|i1', 'shape': [3], 'unit': 'dimensionless'}, 'pareto_predicted_iv': {'dtype': '<f8', 'shape': [3, 3, 4], 'unit': 'annualized_volatility'}, 'pareto_predicted_variance': {'dtype': '<f8', 'shape': [3, 3], 'unit': 'annualized_variance'}, 'pareto_target_iv': {'dtype': '<f8', 'shape': [3, 4], 'unit': 'annualized_volatility'}, 'pareto_target_variance': {'dtype': '<f8', 'shape': [3], 'unit': 'annualized_variance'}, 'teacher_implied_volatility': {'dtype': '<f8', 'shape': [3, 3, 4], 'unit': 'annualized_volatility'}, 'teacher_maturities': {'dtype': '<f8', 'shape': [3], 'unit': 'years'}, 'teacher_model_code': {'dtype': '<i2', 'shape': [3], 'unit': 'dimensionless'}, 'teacher_parameter_mask': {'dtype': '|i1', 'shape': [3, 5], 'unit': 'dimensionless'}, 'teacher_parameter_values': {'dtype': '<f8', 'shape': [3, 5], 'unit': 'dimensionless'}, 'teacher_price': {'dtype': '<f8', 'shape': [3, 3, 4], 'unit': 'spot_units'}, 'teacher_standard_error': {'dtype': '<f8', 'shape': [3, 3, 4], 'unit': 'spot_units'}, 'teacher_strikes': {'dtype': '<f8', 'shape': [4], 'unit': 'spot_units'}} |
| `artifact_kind` | johnhull_frontier_reference |
| `common_teacher_schema` | {'axes': ['model', 'maturity', 'strike'], 'fields': ['price', 'implied_volatility', 'standard_error'], 'same_grid_for_all_models': True} |
| `data_policy` | synthetic_offline_actual_numerical_teachers |
| `direct_inverse` | {'parameter_rmse': 0.11317061477226652, 'repricing_rmse': 0.001329304019867447, 'role': 'ablation_only', 'test_rows': 8, 'train_rows': 24} |
| `execution_profile` | cpu_quick |
| `forward_calibration` | {'all_starts_successful': True, 'evaluations': [16, 11, 24, 27], 'model': 'SABR/Hagan', 'n_starts': 4, 'parameter_mae': 1.9211408013031228e-07, 'parameter_max_abs_error': 4.976756654562209e-07, 'parameter_rmse': 2.66680511214493e-07, 'primary_method': 'multi_start_forward_calibration', 'repricing_rmse': 5.2012449229271927e-11} |
| `joint_variance_refits` | {'actual_refit_per_lambda': True, 'candidate_parameter_unique_count': 3, 'fit_evaluations': [17, 20, 19], 'fixed_parameters': {'kappa': 1.5, 'rho': -0.6, 'xi': 0.3}, 'forward_teacher': 'Heston/COS', 'n_starts_per_lambda': 3, 'optimized_parameters': ['v0', 'theta'], 'points': [{'iv_loss': 6.746682805666861e-07, 'lambda_var': 0.0, 'pareto_nondominated': True, 'total_loss': 6.746682805666861e-07, 'variance_loss': 3.490595925439977e-05}, {'iv_loss': 1.652498181609762e-05, 'lambda_var': 10.0, 'pareto_nondominated': True, 'total_loss': 0.00016347774757961096, 'variance_loss': 1.4695276576351333e-05}, {'iv_loss': 0.00012272360523859574, 'lambda_var': 100.0, 'pareto_nondominated': True, 'total_loss': 0.0003395473746169115, 'variance_loss': 2.1682376937831574e-06}], 'repricing_rmse': [0.002742430760353541, 0.004019830937757005, 0.009930384268981398]} |
| `limitations` | ['rough-Bergomi reference uses a small antithetic Monte Carlo path count', 'direct inverse ridge is diagnostic and is not the primary calibration route', 'quote contamination is deterministic stress data, not observed market data'] |
| `schema_version` | 1 |
| `seed` | 1900 |
| `surface_constraints` | {'hard_arbitrage_label_source': 'complete hullkit hard report', 'reports': {'hard': {'applicable_checks': ['price_bounds', 'strike_monotonicity', 'strike_convexity', 'calendar_monotonicity'], 'arbitrage_free': True, 'check_set_complete': True, 'checks': [{'max_violation': 0.0, 'n_checked': 36, 'n_violations': 0, 'name': 'price_bounds', 'passed': True, 'tolerance': 1e-07, 'violation_rate': 0.0}, {'max_violation': 0.0, 'n_checked': 32, 'n_violations': 0, 'name': 'strike_monotonicity', 'passed': True, 'tolerance': 1e-07, 'violation_rate': 0.0}, {'max_violation': 4.884981308350689e-15, 'n_checked': 28, 'n_violations': 0, 'name': 'strike_convexity', 'passed': True, 'tolerance': 1e-07, 'violation_rate': 0.0}, {'max_violation': 0.0, 'n_checked': 27, 'n_violations': 0, 'name': 'calendar_monotonicity', 'passed': True, 'tolerance': 1e-07, 'violation_rate': 0.0}], 'metadata': {}}, 'raw': {'applicable_checks': ['price_bounds', 'strike_monotonicity', 'strike_convexity', 'calendar_monotonicity'], 'arbitrage_free': False, 'check_set_complete': True, 'checks': [{'max_violation': 0.0, 'n_checked': 36, 'n_violations': 0, 'name': 'price_bounds', 'passed': True, 'tolerance': 1e-07, 'violation_rate': 0.0}, {'max_violation': 0.0, 'n_checked': 32, 'n_violations': 0, 'name': 'strike_monotonicity', 'passed': True, 'tolerance': 1e-07, 'violation_rate': 0.0}, {'max_violation': 0.3874532825396616, 'n_checked': 28, 'n_violations': 4, 'name': 'strike_convexity', 'passed': False, 'tolerance': 1e-07, 'violation_rate': 0.14285714285714285}, {'max_violation': 0.0030000000000000027, 'n_checked': 27, 'n_violations': 1, 'name': 'calendar_monotonicity', 'passed': False, 'tolerance': 1e-07, 'violation_rate': 0.037037037037037035}], 'metadata': {}}, 'soft': {'applicable_checks': ['price_bounds', 'strike_monotonicity', 'strike_convexity', 'calendar_monotonicity'], 'arbitrage_free': False, 'check_set_complete': True, 'checks': [{'max_violation': 0.0, 'n_checked': 36, 'n_violations': 0, 'name': 'price_bounds', 'passed': True, 'tolerance': 1e-07, 'violation_rate': 0.0}, {'max_violation': 0.0, 'n_checked': 32, 'n_violations': 0, 'name': 'strike_monotonicity', 'passed': True, 'tolerance': 1e-07, 'violation_rate': 0.0}, {'max_violation': 3.4373871459214556e-06, 'n_checked': 28, 'n_violations': 4, 'name': 'strike_convexity', 'passed': False, 'tolerance': 1e-07, 'violation_rate': 0.14285714285714285}, {'max_violation': 0.0, 'n_checked': 27, 'n_violations': 0, 'name': 'calendar_monotonicity', 'passed': True, 'tolerance': 1e-07, 'violation_rate': 0.0}], 'metadata': {}}}, 'rmse_to_clean_teacher': {'hard': 0.0030631163078194564, 'raw': 0.003937961394684812, 'soft': 0.0032326269914989595}, 'soft_objective_is_not_an_arbitrage_free_claim': True, 'source': 'Heston/COS prices with deterministic quote contamination'} |
| `teachers` | [{'method': 'heston_cos', 'model': 'heston', 'model_code': 0, 'parameter_names': ['v0', 'kappa', 'theta', 'xi', 'rho'], 'path_count': 0}, {'method': 'hagan_sabr_to_bsm', 'model': 'sabr', 'model_code': 1, 'parameter_names': ['alpha', 'beta', 'rho', 'nu'], 'path_count': 0}, {'method': 'rbergomi_mc_antithetic', 'model': 'rbergomi', 'model_code': 2, 'parameter_names': ['xi0', 'eta', 'hurst', 'rho', 'n_steps'], 'path_count': 2048}] |
| `volume` | 19 |

## Acceptance checks

| Check | Observed | Criterion | Pass |
|---|---:|---|:---:|
| `numerical_teacher_ladder` | 3 | Heston/COS, SABR/Hagan, and rBergomi MC on one uncertainty schema | PASS |
| `multi_start_calibration` | True | all starts successful | PASS |
| `calibration_start_evidence` | 4 | initial/fitted parameters, errors, evaluations, and dispersion align | PASS |
| `forward_repricing_rmse` | 5.2012449229271927e-11 | < 1e-5 | PASS |
| `hard_surface_report` | True | complete and all checks pass | PASS |
| `raw_stress_detected` | False | is false | PASS |
| `joint_variance_refits` | 3 | >= 2 distinct actual refits | PASS |
| `variance_pareto_improvement` | 2.1682376937831574e-06 | < lambda=0 variance loss | PASS |
| `direct_inverse_role` | ablation_only | == ablation_only | PASS |
| `direct_inverse_evidence` | 8 | aligned parameter and repricing ablation arrays | PASS |
| `pareto_evidence` | 3 | each actual refit has losses, parameters, and nondominance status | PASS |

## Negative results

- The soft-constrained stress surface still fails at least one hard arbitrage check.
- The hard repair is a feasible cumulative projection, not a joint-L2 optimum.
- The rough-Bergomi teacher uses a small antithetic Monte Carlo sample for the CPU quick profile.

## Rebuild

```bash
uv run --no-sync python johnhull/scripts/build_frontier_artifacts.py --volume 19
uv run --no-sync --package hullkit python johnhull/volumes/19_inverse_surfaces/build_19_inverse_surfaces_notebook.py
```

## Limitations

- rough-Bergomi reference uses a small antithetic Monte Carlo path count
- direct inverse ridge is diagnostic and is not the primary calibration route
- quote contamination is deterministic stress data, not observed market data
- Research-track models remain optional and cannot fail the core notebook path.
- Core semantic identities are independently recomputed by the release verifier.
