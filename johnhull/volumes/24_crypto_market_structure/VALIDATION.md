# Volume 24 Validation — G6

- Gate: **PASS** (`integration_and_reproducibility`)
- Model performance approved: **no**
- Status: reference artifact and executed notebook generated
- Data policy: synthetic-offline
- Network/training/download during notebook execution: none

## Artifact evidence

| Metric | Value |
|---|---:|
| `auction_socialized_loss` | 6.443163968193039 |
| `cashflow_conservation_error` | 7.105427357601002e-15 |
| `contract_long_short_sign_error` | 0.0 |
| `contract_zero_move_error` | 0.0 |
| `dynamic_fee_compensation` | 24.658350911738395 |
| `dynamic_fee_gross_lvr_reduction` | 0.0 |
| `ending_adl_notional` | 3.0 |
| `ending_insurance_fund` | 0.0 |
| `ending_socialized_loss` | 6.443163968193039 |
| `ending_uncovered_loss` | 0.0 |
| `forced_sale_socialized_loss` | 8.22316396819304 |
| `funding_absolute_cap` | 0.005 |
| `funding_interval_hours` | 8.0 |
| `insurance_identity_error` | 0.0 |
| `oracle_dislocated_count` | 1 |
| `oracle_stale_count` | 5 |
| `solvency_identity_error` | 0.0 |
| `solvent` | True |
| `synthetic_cascade` | True |

## Acceptance checks

| Check | Observed | Criterion | Pass |
|---|---:|---|:---:|
| `perpetual_contract_identities` | 3 | linear/inverse/quanto long-short and zero-move identities | PASS |
| `cashflow_conservation` | 7.105427357601002e-15 | funding long+short+venue, waterfall equity+absorbers-trader-fee (both rebuilt from the committed legs), AMM and CPMM identities all < 1e-12; stored error < 1e-12 | PASS |
| `funding_cap_interval` | 8.0 | positive interval and absolute cap; settled intervals == floor(elapsed / interval); long+short+venue == 0 and cumulative funding == cumsum(long) rebuilt from the arrays | PASS |
| `solvency_identity` | 0.0 | auction insurance identity (after - before - fee + used) rebuilt from the legs and uncovered loss both < 1e-12; equals the stored error (1e-12) | PASS |
| `insurance_identity` | 0.0 | insurance_after == insurance_before + fee - insurance_used for every liquidation method (1e-12); stored auction error matches (1e-12) | PASS |
| `stress_waterfall` | 6.443163968193039 | ending ADL/social/uncovered/insurance path equals the auction waterfall legs and the stored metrics; ADL and social loss > 0 with zero uncovered loss | PASS |
| `liquidation_method_waterfalls` | 0.0 | forced sale and auction: equity + absorbers - trader return - fee == 0, absorbers == max(-equity, 0), trader return == max(equity - fee, 0), fee <= max(equity, 0) (all rebuilt from the legs, 1e-12); auction socialized loss < forced sale; metrics match | PASS |
| `amm_identity` | 0.0 | gross LVR == max(0, rebalanced - LP value) for the fixed and dynamic fee ledgers and gross - dynamic fee - net == 0, all rebuilt from the committed arrays (1e-12) | PASS |
| `amm_lvr_fee_variants` | 0.0 | CPMM identity; net LVR == gross - cumulative fee for the fixed and dynamic ledgers (1e-12); fee income non-decreasing; gross-LVR reduction and fee compensation metrics match the arrays; finite concentrated LVR | PASS |
| `oracle_staleness_dislocation` | 5/1 | both explicit flags agree with their counts | PASS |

## Negative results

- The liquidation cascade is deliberately synthetic and is not a reconstruction of a market event.
- The dynamic fee does not reduce gross LVR in this fixture; fee compensation is reported separately.

## Rebuild

```bash
uv run --no-sync python johnhull/scripts/build_frontier_artifacts.py --volume 24
uv run --no-sync --package hullkit python johnhull/volumes/24_crypto_market_structure/build_24_crypto_market_structure_notebook.py
```

## Limitations

- Synthetic results are not evidence of market forecasting power.
- Research-track models remain optional and cannot fail the core notebook path.
- Core semantic identities are independently recomputed by the release verifier.
