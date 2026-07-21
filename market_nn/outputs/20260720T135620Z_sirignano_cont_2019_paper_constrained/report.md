# STRUCTURAL REPRODUCTION ON SYNTHETIC DATA

- paper_id: `sirignano_cont_2019`
- implementation_profile: `sirignano_cont_2019_paper_constrained`
- fidelity_class: `C_PAPER_CONSTRAINED`
- paper_version: `arXiv:1803.06917v1`
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
  "runtime": "torch 2.11.0+cu128",
  "audit_metrics": {
    "synthetic_protocol_linear": {
      "asset_specific_linear_accuracy": {
        "0": 0.925,
        "1": 0.8916666666666667,
        "2": 0.9666666666666667,
        "3": 0.95
      },
      "universal_pooled_linear_unseen_accuracy": 0.9116666666666666,
      "universal_pooled_linear_by_unseen_asset": {
        "4": 0.9083333333333333,
        "5": 0.915
      },
      "claim_limit": "synthetic protocol test only"
    },
    "synthetic_protocol_lstm_scaled": {
      "asset_specific_lstm_accuracy": {
        "0": 0.8333333333333334,
        "1": 0.5,
        "2": 0.8333333333333334,
        "3": 0.75
      },
      "universal_pooled_lstm_unseen_accuracy": 0.7807017543859649,
      "universal_pooled_final_training_loss": 0.4344845712184906,
      "configuration": {
        "history": 20,
        "stride": 10,
        "hidden_units": 8,
        "epochs": 15,
        "optimizer": "Adam",
        "learning_rate": 0.02
      },
      "claim_limit": "scaled synthetic LSTM protocol test only"
    }
  }
}
```

## Warnings

- Synthetic structure test; paper-reported accuracy/F1 was not attempted.
- Unresolved fields: model.input_features, training.learning_rate, training.regularization, training.tbptt_reset
