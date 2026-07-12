# Reinforcement-learning environment

## Purpose

`ExecutionEnv` is a compact Gymnasium-style interface without a Gymnasium
dependency. It is a transparent reactive synthetic market, not an exchange
emulator. The same environment and safety layer serve scripted and learned
policies.

## Observation

The 12-dimensional normalized observation is:

1. elapsed decision fraction;
2. remaining inventory fraction;
3. spread relative to base spread;
4. bid depth relative to target;
5. ask depth relative to target;
6. queue imbalance;
7. recent return;
8. recent signed market-order flow;
9. current volatility state;
10. transient-impact state;
11. recent market volume state;
12. outstanding limit quantity relative to a TWAP slice.

Continuous features are clipped to documented ranges before entering the
network. Ablation masks zero one named feature group both during training and
evaluation.

## Action

The categorical action grid has 15 actions:

\[
\{0,0.5,1,1.5,2\}\times
\{\text{none},\text{join touch},\text{improve one tick}\}.
\]

The first coordinate multiplies the current strategic baseline slice. The
limit directive cancels, joins, or replaces the one outstanding limit order.
Residual RL uses the AC schedule as baseline; free RL uses uniform TWAP-sized
slices. Scripted policies may instead submit an explicit quantity dictionary.

## Transition order

Each decision:

1. decodes the requested market/limit action;
2. applies market-order safety constraints;
3. executes against visible and deeper liquidity;
4. cancels/replaces the outstanding limit order;
5. evolves state-dependent events over sub-steps;
6. applies queue fills and adverse-selection labels;
7. replenishes depth and evolves the unaffected mid;
8. decays transient impact and relaxes spread;
9. forces terminal liquidation at the deadline;
10. records economic cost, shaped reward, diagnostics, and optional trace.

In `reactive=False`, agent orders receive prices but do not consume depth,
widen spread, or update impact. This is the explicit replay-style control.

## Reward and economic cost

Economic implementation shortfall is accumulated directly from cash and fees.
The training reward is separate:

\[
r_k=-c_{\text{scale}}\left(\Delta IS_k
+\lambda_{\text{inv}}x_k^2\sigma_k^2\Delta t
+\lambda_DD_k^2\right)-\lambda_c\mathbf 1_{\text{violation}}.
\]

A normalized terminal-inventory penalty is added if forced liquidation is
required. Reports compare policies only on economic IS, fill/cleanup behavior,
and risk metrics; shaped reward is never called P&L.

## Safety constraints

- nonfinite or negative requested quantities become zero and count a violation;
- quantity cannot exceed free remaining inventory after resting orders;
- nonterminal market orders obey maximum child size;
- participation is capped using recent market-volume state;
- market aggression is blocked beyond the arrival-price collar;
- inventory cannot become negative or over-execute;
- at the final step, resting orders are canceled and remainder is liquidated;
- network parameters are checked for finite values after every PPO update.

Forced liquidation deliberately bypasses normal participation limits so every
episode ends with zero inventory. Cleanup quantity and cost are reported
separately.

## Training protocol

Named seed streams separate training, validation, test, stress, ablation, and
misspecification. Validation uses deterministic actions on a fixed set and
selects the lowest mean economic IS checkpoint. The quick profile trains one
seed for practical CPU execution; the full profile specifies seeds 1210, 2026,
and 31415. One quick seed cannot support a superiority claim.

Liquidity, price, volume, depth, flow, and latent alpha are stochastic within
episodes. Stress tests change volatility, liquidity, volume profile, adverse
alpha, spread, and resilience. The misspecification test freezes the trained
policy and strategic baseline while changing simulator parameters.

Feature ablation retrains one policy per removed feature at the ablation
budget, and the full-feature reference is retrained at that same budget, so
ablation deltas isolate the feature removal rather than training length. The
main (longer-budget) policies never serve as the ablation reference.

## Evaluation outputs

Evaluation records total and decomposed economic cost, shaped reward, risk
penalty, completion time, forced cleanup, market/limit shares, fill rate,
participation, spread paid, transient state, maximum exposure, orders,
cancellations, violations, and optional state/action traces. All strategies in
one regime use the same primitive scenario seeds.
