# Limitations and next steps

## Scientific limitations

This project uses synthetic data and illustrative parameters. It is not
calibrated to an exchange, security, or historical period. Numerical
reproducibility does not imply empirical validity.

The aggregated LOB omits individual price levels beyond a density proxy,
hidden/iceberg liquidity, venue fragmentation, maker priority rules, auctions,
latency, network jitter, message throttles, fees/rebates by venue, and strategic
counterparties. Queue position is a proxy and cancellation ahead is stylized.
The adverse-selection channel shares a latent signal between flow and price,
not a fitted causal model.

Linear impact and constant model coefficients are simplifications. Resilience
can be state-dependent in real markets; permanent and temporary components are
not directly identifiable. The square-root law is diagnostic only. Cross-impact
between assets and manipulation/no-dynamic-arbitrage constraints are absent.

Synthetic latent TCA decomposition is exact by construction but cannot be
observed uniquely in real trades. Implementation shortfall ignores many
operational considerations such as opportunity cost from canceled parent
orders, venue outages, settlement, and capital constraints.

PPO learns the simulator and reward. It may exploit simplifications that do not
survive calibration or distribution shift. The quick profile uses one seed and
a small training budget. Even the three-seed full profile would not establish
production robustness or statistical superiority. Feature ablation measures a
joint retraining effect inside this simulator, not real-world causal value.

## Recommended next implementation steps

1. Calibrate spread, depth, event intensity, fill, and impact distributions to
   strictly held-out order-level data with leakage checks.
2. Add paired confidence intervals for strategy differences and multi-seed RL
   aggregation with preregistered decision thresholds.
3. Enforce no-price-manipulation and no-dynamic-arbitrage conditions for richer
   propagator and cross-impact specifications.
4. Model stochastic, state-dependent resilience and hidden-liquidity regimes.
5. Implement exchange-specific queues, latency, venue routing, auctions, and
   maker/taker economics.
6. Add multi-asset cross-impact for cash/futures/swap portfolio execution.
7. Add synthetic JGB and interest-rate-swap dealer/RFQ markets, including
   hit-ratio and information-leakage models.
8. Build a multi-agent market simulator with adaptive counterparties.
9. Evaluate neural queue-reactive models only after transparent baselines.
10. Add safe constrained and distributionally robust RL with explicit risk
    budgets rather than reward penalties alone.
11. Investigate offline RL with counterfactual correction and behavior-policy
    support diagnostics.
12. Connect execution to deep hedging while preserving separation between hedge
    error and execution cost.
13. Study rough-volatility regimes and Hawkes-style order flow with bounded,
    stable intensities.
14. Add inverse optimal execution and causal impact estimation under explicit
    identifiability assumptions.
15. Provide a quarantined real-data ingestion layer with schema, quality,
    survivorship, timestamp, and leakage validation.

Any empirical extension should preserve the current safeguards: explicit sign
and units, unaffected versus impacted prices, common random numbers where
valid, disjoint train/validation/test data, failure-case reporting, shaped reward
separate from economics, and honest model-risk caveats.
