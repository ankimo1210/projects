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
| `cashflow_conservation` | 7.105427357601002e-15 | < 1e-12 | PASS |
| `funding_cap_interval` | 8.0 | positive interval, absolute cap, and conserved transfers | PASS |
| `solvency_identity` | 0.0 | < 1e-12 | PASS |
| `insurance_identity` | 0.0 | < 1e-12 | PASS |
| `stress_waterfall` | 6.443163968193039 | ADL/social loss tracked with zero uncovered loss | PASS |
| `liquidation_method_waterfalls` | 2 | forced sale and auction conserve their stress waterfalls | PASS |
| `amm_identity` | 0.0 | < 1e-12 | PASS |
| `amm_lvr_fee_variants` | 7.105427357601002e-15 | CPMM identity plus finite fixed/dynamic/concentrated LVR | PASS |
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
