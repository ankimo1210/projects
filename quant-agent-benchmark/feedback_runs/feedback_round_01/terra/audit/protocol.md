# feedback_round_01 protocol — Terra

## Fixed scope and timing

- Model key: `terra` (assigned in the round instruction).
- Declared reasoning effort: `xhigh`; the task runtime's underlying model setting is not independently machine-verifiable here.
- Start: `2026-09-05T07:54:44Z`.
- Time limit: 60 minutes; new design changes stop at `2026-09-05T08:44:44Z` to reserve ten minutes for final validation and preservation.
- Authoritative research inputs: public `input/` and the Terra initial project only. No evaluator, analysis, other-model, network, or external-model material is used.

## Preservation and reproducibility

Initial project files are SHA-256 recorded in `baseline_manifest.json`; the same rules will create `original_manifest_after.json`. Excluded from both manifests are VCS metadata, virtual environments, build/cache files, and the pre-round `submission/` directory accidentally created before the complete improvement instruction was available. That incident is documented in `feedback_response.md`; it is not read or used. The original project is not executed.

All baseline and final executions use the supplied Python executable with `PYTHONDONTWRITEBYTECODE=1`, deterministic NumPy seed `20260905`, and a round-local Matplotlib cache. The submission must not depend on audit files, the baseline directory, prior output files, or personal absolute paths.

## Pre-registered comparisons

The baseline is the copied initial project. Every published-data comparison uses its deterministic maturity-bucket split: every fifth sorted exact maturity bucket is holdout, with all same-maturity observations assigned together. This prevents duplicated or same-maturity observations from leaking across the split.

Metrics are retained separately:

1. **Synthetic truth:** zero-rate RMSE and instantaneous-forward RMSE, in bp, against known independently specified discount curves; reported overall and for short (`T <= 2`), medium (`2 < T < 15`), and long (`T >= 15`) bands.
2. **Public data:** model-minus-market residuals in native units (decimal rates for deposits/OIS, price points for bonds), plus a type-normalized residual using fixed denominators of 0.5 bp for rate instruments and 0.05 price points for bonds. Weighted normalized RMSE is computed within each product/band only; native-unit RMSEs are never added across products.
3. **Stability:** extrema of zero/forward grids, strictly positive discount factors, finite risk values, sensitivity refit impact, and key-rate-sum versus parallel-DV01 finite-difference gap.
4. **Convention checks:** independent formulas for deposits, OIS, and bonds under flat, rising, falling, curved, and negative-rate discount functions; integer and fractional maturities are both tested.

## Pre-registered hypotheses and decision rules

| ID | Hypothesis | Decision rule |
|---|---|---|
| H1 | Current unit, inverted bid/ask, and exclusion labels may not match actual normalized values/weights. | Retain the current implementation only if audit rows, normalized quotes, actions, and final weights agree in an independent check; otherwise repair the computation and label. |
| H2 | Long-end curvature/endpoint regularisation can improve known-curve long-band error or stability without damaging pricing/holdout accuracy. | Change only the long-end penalty/endpoint treatment. Adopt only if all convention tests pass, long-band synthetic zero or forward RMSE improves by at least 5%, no public product/band weighted RMSE worsens by more than 5%, and forward extrema do not become less stable. |
| H3 | The current public fractional-bond convention needs an independent pricing check, not an observation-fit-based choice. | Do not change conventions merely because public fit changes. Record both interpretations if public text is ambiguous; adopt only an implementation defect correction proven against an independent formula. |
| H4 | Smoothing selection based solely on one aggregate holdout can hide product/band deterioration. | Preserve a selected smoothing choice only if its pre-defined band/product checks meet H2-style guardrails; otherwise retain the baseline setting and report the failed condition. |

No interaction of a pricing-convention change and a curvature change will be claimed unless separately tested. A rejected experiment remains in `experiments.csv` and is not mixed into the final version.

## Planned experiments

1. `E0`: reproduce baseline copy exactly: tests and full CLI.
2. `E1`: convention/unit audit and independent-pricer synthetic checks; no estimator change unless a defect is demonstrated.
3. `E2`: fixed-pricer, one-factor long-end endpoint/curvature experiment, compared with `E0` on the same synthetic suite and public split.
4. `E3`: final selected submission validation in a fresh output directory; no new modelling change.

## Changes to this protocol

登録後、H1の実査で「反転を補正した後にIRLSダウンウェイトも受けた行」は最終単一 `action` が `downweight` となり、補正の事実が理由文にのみ残ることを確認した。推定器・採用条件を変えず、実処理に対応する `unit_normalization`、`bid_ask_inverted`、`quote_midpoint_corrected` の構造化監査列を追加した。この訂正はE2の長期曲率実験とは別であり、両者の交互作用を検証済みとは扱わない。
