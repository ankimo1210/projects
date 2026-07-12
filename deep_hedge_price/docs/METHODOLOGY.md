# Methodology

## Simulation measure

Paths are simulated under the physical measure with drift `mu`, not the risk-neutral drift. Exact GBM increments are used on a uniform grid. Antithetic mode draws half the shocks and appends their negatives before truncating to the requested even or odd path count.

## Discounted hedge accounting

All price changes, payoff, costs, P&L, VaR, and CVaR are reported in time-zero discounted units. The stock position established at date `t` earns the move from `t` to `t+1`. Turnover includes the initial move from zero. Transaction cost is `exp(-r*t) * lambda * S_t * abs(delta_t-delta_{t-1})`.

There is no terminal liquidation trade because the project-specified sum ends at `N-1`. Adding liquidation is a different economic convention and would require an explicit config option and new tests.

For short quantity `q = -option_position`,

- liability: `q * discounted_call_payoff`;
- training loss: `liability - net_trading_gain`;
- economic P&L: `q * premium + net_trading_gain - liability`.

The default premium is the Black–Scholes time-zero price. It has no direct derivative with respect to policy parameters. For translation-invariant risk measures such as entropic risk and CVaR, a constant premium does not change the optimizer. MSE is not translation invariant, so this Phase 1 implementation follows the requested premium-excluded MSE definition exactly and discloses the distinction.

## Policy

The state is `[log(S/K), normalized time to maturity, previous total stock position, sigma, lambda]`. Fixed economically meaningful scales normalize these features. The shared MLP has three 64-unit SiLU layers. A Tanh transformation smoothly bounds the per-option hedge ratio to `[-0.25, 1.25]`; the total position scales with short option quantity.

The previous position makes costs endogenous to the policy and provides an extension point for no-transaction-band behavior. The package keeps policy rollout separate from accounting so recurrent policies and multiple instruments can be added later.

## Risk measures

- MSE is the mean squared dollar loss specified by the project.
- Entropic risk applies stable log-sum-exp to `loss / S0`.
- CVaR applies the Rockafellar–Uryasev representation to `loss / S0`; its threshold is a trainable parameter saved in the checkpoint.

## Baselines

- No hedge holds zero stock.
- Black–Scholes delta rebalances at every hedge date and pays the same transaction costs.
- The no-trade band keeps the previous position inside `BS delta ± band`; outside, it trades to the nearest boundary.

All strategies use the same accounting code and identical test paths.

## Evaluation protocol

Training receives new paths every optimizer update. A separate fixed validation set selects the best checkpoint and drives early stopping. A third, larger test set is used once for strategy comparisons. Path IDs and discounted payoff must match across strategies.

Economic-loss VaR at level `alpha` is the empirical `alpha` quantile of `-P&L`. CVaR is the mean loss at or above that quantile. P&L quantiles retain the P&L sign. Turnover is in shares; transaction cost and P&L are in discounted currency units.

## Known limitations

The model has one underlying, one European payoff, constant parameters, exact GBM, proportional cost, and no market impact or liquidity constraint. It does not estimate an option price. A quick-profile 99% tail contains only about 200 observations. Sanity checks are descriptive diagnostics rather than mathematical guarantees.
