# STRUCTURAL REPRODUCTION ON SYNTHETIC DATA

- paper_id: `tlob_2025`
- implementation_profile: `mlplob_paper_arxiv_2502_15757`
- fidelity_class: `C_PAPER_CONSTRAINED`
- paper_version: `arXiv:2502.15757v3`
- source_code_commit: `None`
- dataset_profile: `deterministic_synthetic_smoke_v1`
- random_seed: `7`

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
- Unresolved fields: model.hidden_dim, model.bin_mode
