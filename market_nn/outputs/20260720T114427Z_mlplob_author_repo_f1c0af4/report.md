# STRUCTURAL REPRODUCTION ON SYNTHETIC DATA

- paper_id: `tlob_2025`
- implementation_profile: `mlplob_author_repo_f1c0af4`
- fidelity_class: `A_AUTHOR_CODE_EXACT`
- paper_version: `arXiv:2502.15757v3`
- source_code_commit: `f1c0af4d81067978914361766db0457a7d8b6a46`
- dataset_profile: `deterministic_synthetic_smoke_v1`
- random_seed: `1`

This output verifies structure/protocol on a deterministic synthetic fixture.
It is not a numerical replication of paper-reported market-data results.

## Metrics

```json
{
  "architecture_verified": true,
  "output_rows": 2,
  "probability_rows_sum_to_one": true,
  "numerical_benchmark_attempted": false,
  "runtime": "torch 2.11.0+cu128"
}
```

## Warnings

- Synthetic structure test; paper-reported accuracy/F1 was not attempted.
- This smoke validates the clean-room target; it did not execute fetched reference code side-by-side.
- Pinned repository specifies torch_2.5.0_cu121; clean-room smoke used torch 2.11.0+cu128.
