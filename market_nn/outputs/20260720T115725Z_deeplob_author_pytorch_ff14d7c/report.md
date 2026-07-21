# STRUCTURAL REPRODUCTION ON SYNTHETIC DATA

- paper_id: `deeplob`
- implementation_profile: `deeplob_author_pytorch_ff14d7c`
- fidelity_class: `A_AUTHOR_CODE_EXACT`
- paper_version: `arXiv:1808.03668v6`
- source_code_commit: `ff14d7c2fd38bdfc143389786993d0f0236d4eb8`
- dataset_profile: `deterministic_synthetic_smoke_v1`
- random_seed: `{'author': None, 'smoke': 7}`

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
- Unresolved fields: training.adam_epsilon, training.framework_version
