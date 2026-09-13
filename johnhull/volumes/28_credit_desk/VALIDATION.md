# Volume 28 Validation — G10

- Gate: **PASS** (`integration_and_reproducibility`)
- Model performance approved: **no**
- Status: reference artifact and executed notebook generated
- Data policy: synthetic-offline
- Network/training/download during notebook execution: none

## Artifact evidence

| Metric | Value |
|---|---:|
| `base_correlation_max_reprice_error` | 3.737895409861025e-15 |
| `binary_cds_spread_bp` | 205.00429358998645 |
| `bond_bootstrap_hazard_1` | 0.024575329948416012 |
| `bond_bootstrap_hazard_2` | 0.03475777894122982 |
| `bond_bootstrap_hazard_3` | 0.037351228053560705 |
| `cdo_index_hazard` | 0.008296995340469394 |
| `cdo_mezz_accrual` | 0.01869664988180446 |
| `cdo_mezz_annuity` | 4.28464661505203 |
| `cdo_mezz_protection` | 0.14957319905443567 |
| `cdo_mezz_spread_bp` | 347.5744086539548 |
| `cdo_rate` | 0.035 |
| `cdo_rho` | 0.15 |
| `cds_bootstrap_max_reprice_error` | 4.388850394221322e-16 |
| `cds_hazard` | 0.02 |
| `cds_implied_hazard_100bp` | 0.016258868561856883 |
| `cds_mtm_seller_150bp` | 0.011109406541533029 |
| `cds_par_spread_bp` | 123.00257615399185 |
| `cds_protection_pv` | 0.050615408045779915 |
| `cds_rate` | 0.05 |
| `cds_risky_duration` | 4.114987639154196 |
| `credit_var_correlated` | 6.599999999999999 |
| `credit_var_independent` | 3.0 |
| `creditmetrics_bbb_default_threshold` | 2.9290497489376195 |
| `creditmetrics_rho` | 0.2 |
| `cva_general_equivalent` | 0.24458895909902348 |
| `cva_no_default_value` | 7.0 |
| `cva_rate` | 0.05 |
| `cva_special_case` | 0.2445889589461554 |
| `double_t_limit_gap_bp` | 0.006168267563458341 |
| `fixed_coupon_coupon` | 0.004055555555555555 |
| `fixed_coupon_duration` | 4.447404298328079 |
| `fixed_coupon_hazard` | 0.005716736665913349 |
| `fixed_coupon_price` | 100.2705504281483 |
| `fixed_coupon_spread` | 0.0034472222222222217 |
| `gaussian_mezz_spread` | 0.03475744086539548 |
| `gross_exposure` | 40.0 |
| `heterogeneous_binomial_gap` | 5.551115123125783e-16 |
| `heterogeneous_spread_gap` | 5.93275428784068e-15 |
| `hull_bbb_default_threshold` | 2.929 |
| `itraxx_hazard` | 0.003818992392297505 |
| `itraxx_rate` | 0.03 |
| `kth3_accrual` | 0.05239597534667226 |
| `kth3_annuity` | 4.057993117728011 |
| `kth3_payoff` | 0.06287517041600671 |
| `kth3_spread_bp` | 152.96646860498151 |
| `kth_rate` | 0.05 |
| `netting_exposure` | 15.0 |
| `option_expiry` | 1.0 |
| `option_forward_spread` | 0.021130946583698414 |
| `option_risky_annuity` | 3.7743222957665576 |
| `option_sigma` | 0.6 |
| `portfolio_expected_loss` | 0.022380958203668554 |
| `recovery` | 0.4 |

## Acceptance checks

| Check | Observed | Criterion | Pass |
|---|---:|---|:---:|
| `cds_par_spread_hull_pin` | 123.00257615399185 | Σpayoff/(Σpayment+Σaccrual) within 0.5 bp of Hull's 123 bp and 1e-9 bp of the stored metric | PASS |
| `cds_mtm_identity` | 0.011109406541533029 | D·0.015 − protection equals the stored metric and the grid value (1e-10) and Hull's 0.0111 (1e-4) | PASS |
| `cds_bootstrap_round_trip` | 4.388850394221322e-16 | max |repriced − market| <= 1e-10 | PASS |
| `bond_bootstrap_hull_pin` | 0.0019938056124146897 | hazards within 0.0002 of 2.46/3.48/3.74% and loss PVs within 0.01 of 1.50/3.53/5.61 | PASS |
| `fixed_coupon_price_identity` | 100.2705504281483 | 100 − 100·D·(s−c) equals the stored price (1e-10) and Hull's 100.27 (0.01) | PASS |
| `cds_option_parity` | 1.3877787807814457e-17 | max |payer − receiver − A(F−K)| <= 1e-10 | PASS |
| `cdo_mezz_spread_hull_pin` | 347.5744086539548 | re-integrated C/(A+B) within 1 bp of Hull's 348 bp, 1e-9 bp of the stored metric, and 1e-6 bp of an independent numpy repricing; A/B/C within 0.002 of 4.2846/0.0187/0.1496 | PASS |
| `expected_principal_monotone` | 1.1102230246251565e-16 | E_j(F) non-increasing in j and non-decreasing in F (1e-12) | PASS |
| `capital_structure_loss_conservation` | 2.0816681711721685e-17 | Σ width·C_tranche equals the 0–100% expected loss (1e-8) | PASS |
| `kth_to_default_hull_pin_and_ordering` | 152.96646860498151 | re-summed 3rd-to-default spread within 1 bp of Hull's 153 bp and 1e-9 bp of the metric; spreads strictly decrease in k | PASS |
| `implied_correlation_reprices_quotes` | 2.621514116896151e-14 | independent repricing at the committed compound correlations within 1e-6 of the quotes (0.01 bp / 1e-4 upfront points) | PASS |
| `implied_correlation_hull_pin` | 0.000341803712258934 | compound and base correlations within 1.0 point of Table 25.8 | PASS |
| `base_correlation_curve_shape` | -0.0016636335662427392 | 0–X% expected-loss PV increasing in X with strictly decreasing slope ΔEL/ΔX | PASS |
| `double_t_gaussian_limit` | 0.006168267563458341 | ν→∞ double-t spread within 0.5 bp of the Gaussian spread | PASS |
| `heterogeneous_equals_binomial` | 5.551115123125783e-16 | recursion pmf equals the binomial pmf and the committed pmf (1e-12) | PASS |
| `creditmetrics_thresholds_hull_pin` | 4.974893760989474e-05 | thresholds recomputed from Table 24.4 within 0.0002 of Hull and 1e-9 of the stored values; 99.9% credit VaR larger with ρ=0.2 than independent | PASS |
| `netting_collateral_and_cva_special_case` | 1.5286807930614543e-10 | netting 15 <= gross 40 (Hull 24.7); Example 24.4 exposures 5/0/0/5; (1−R)f_nd Σq_i equals the stored CVA (1e-12) and the general CVA on a 2000-step grid (1e-5) | PASS |

## Negative results

- Hull Table 24.4 (S&P 1981–2019) and Table 25.6 (Creditex iTraxx quotes, 2007-01-31) are transcribed textbook constants, not downloaded market data.
- The Table 25.8 implied correlations match Hull to one decimal place; residual differences reflect DerivaGem's integration grid, not calibration quality.
- The double-t copula and ASB recursion are validated only by limits (ν→∞, homogeneous); Hull prints no numeric example for §25.11.
- Random recovery / random factor loadings, the implied copula, dynamic models and KMV EDF mappings are out of scope (documentation only).
- CDS options use the Black-type market formula; the full Hull–White (2003) knock-out treatment is not implemented.

## Rebuild

```bash
uv run --no-sync python johnhull/scripts/build_frontier_artifacts.py --volume 28
uv run --no-sync --package hullkit python johnhull/volumes/28_credit_desk/build_28_credit_desk_notebook.py
```

## Limitations

- Synthetic results are not evidence of market forecasting power.
- Research-track models remain optional and cannot fail the core notebook path.
- Core semantic identities are independently recomputed by the release verifier.
