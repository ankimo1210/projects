# Volume 22 Validation — G4

- Gate: **PASS** (`integration_and_reproducibility`)
- Model performance approved: **no**
- Status: reference artifact and executed notebook generated
- Data policy: synthetic-offline
- Network/training/download during notebook execution: none

## Artifact evidence

| Metric | Value |
|---|---:|
| `adjacent_expiry_violations` | 0 |
| `calendar_violations` | 0 |
| `event_count` | 7 |
| `event_greek_mae` | 0.0028003921838527907 |
| `event_greek_rmse` | 0.006149003242174065 |
| `event_price_mae` | 0.0055099021873426125 |
| `event_price_rmse` | 0.01160374776324586 |
| `event_teacher_standard_error` | 0.013281518665180658 |
| `non_event_count` | 6 |
| `non_event_greek_rmse` | 0.010687180266627646 |
| `non_event_price_rmse` | 0.022463991836340305 |
| `session_seconds` | 23400.0 |
| `timezone` | America/New_York |

## Acceptance checks

| Check | Observed | Criterion | Pass |
|---|---:|---|:---:|
| `session_convention` | America/New_York | New York 6.5-hour session with nonnegative settlement clock | PASS |
| `variance_clock` | 1.0 | monotone from 0 to 1 | PASS |
| `expiry_consistency` | 0 | zero violations and nonnegative forward variance | PASS |
| `event_teacher_uncertainty` | 0.013281518665180658 | > 0 | PASS |
| `time_of_day_diagnostics` | 3 | open/midday/close with aligned price and Greek buckets | PASS |
| `event_non_event_split` | 7/6 | mask counts and two-way diagnostics agree | PASS |

## Negative results

- The intraday teacher and event schedule are synthetic fixtures, not causal dealer-flow evidence.

## Rebuild

```bash
uv run --no-sync python johnhull/scripts/build_frontier_artifacts.py --volume 22
uv run --no-sync --package hullkit python johnhull/volumes/22_zero_dte/build_22_zero_dte_notebook.py
```

## Limitations

- Synthetic results are not evidence of market forecasting power.
- Research-track models remain optional and cannot fail the core notebook path.
- Core semantic identities are independently recomputed by the release verifier.
