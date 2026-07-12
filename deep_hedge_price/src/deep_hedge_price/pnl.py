"""Differentiable discounted hedge accounting."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn

from .black_scholes import call_price
from .config import MarketConfig


@dataclass
class HedgeResult:
    """Pathwise discounted accounting, with positive ``loss`` meaning worse."""

    deltas: torch.Tensor
    payoff: torch.Tensor
    gross_trading_gain: torch.Tensor
    transaction_cost: torch.Tensor
    net_trading_gain: torch.Tensor
    loss_excluding_premium: torch.Tensor
    pnl_including_premium: torch.Tensor
    pnl_before_costs: torch.Tensor
    turnover: torch.Tensor
    meaningful_trades: torch.Tensor
    premium: float


def reporting_premium(config: MarketConfig) -> float:
    """Return the per-option time-zero reporting premium."""
    if config.reporting_premium is not None:
        return config.reporting_premium
    return float(
        call_price(
            config.s0,
            config.strike,
            config.maturity_years,
            config.risk_free_rate,
            config.volatility,
        )
    )


def account_hedge(
    paths: torch.Tensor,
    deltas: torch.Tensor,
    config: MarketConfig,
    *,
    meaningful_trade_threshold: float = 0.001,
) -> HedgeResult:
    """Apply the specified discounted P&L convention to pathwise hedge positions.

    ``deltas[:, t]`` is established at time ``t`` and earns the discounted price
    move to ``t+1``. The initial position is zero. No terminal liquidation trade
    is charged because the supplied project convention ends at ``N-1``.
    """
    expected = (paths.shape[0], config.n_steps)
    if tuple(deltas.shape) != expected:
        raise ValueError(f"deltas must have shape {expected}, got {tuple(deltas.shape)}")
    times = torch.linspace(
        0.0,
        config.maturity_years,
        config.n_steps + 1,
        device=paths.device,
        dtype=paths.dtype,
    )
    discounts = torch.exp(-config.risk_free_rate * times)
    discounted_spot = paths * discounts.unsqueeze(0)
    price_moves = discounted_spot[:, 1:] - discounted_spot[:, :-1]
    gross_by_step = deltas * price_moves

    previous = torch.cat((torch.zeros_like(deltas[:, :1]), deltas[:, :-1]), dim=1)
    trades = deltas - previous
    turnover_by_step = torch.abs(trades)
    cost_by_step = (
        discounts[:-1].unsqueeze(0)
        * config.transaction_cost_rate
        * paths[:, :-1]
        * turnover_by_step
    )
    gross_gain = gross_by_step.sum(dim=1)
    costs = cost_by_step.sum(dim=1)
    net_gain = gross_gain - costs
    payoff = discounts[-1] * torch.clamp(paths[:, -1] - config.strike, min=0.0)
    liability = config.short_quantity * payoff
    loss = liability - net_gain
    premium = config.short_quantity * reporting_premium(config)
    pnl = premium - loss
    pnl_before_costs = premium + gross_gain - liability
    return HedgeResult(
        deltas=deltas,
        payoff=payoff,
        gross_trading_gain=gross_gain,
        transaction_cost=costs,
        net_trading_gain=net_gain,
        loss_excluding_premium=loss,
        pnl_including_premium=pnl,
        pnl_before_costs=pnl_before_costs,
        turnover=turnover_by_step.sum(dim=1),
        meaningful_trades=(turnover_by_step > meaningful_trade_threshold).sum(dim=1),
        premium=premium,
    )


def rollout_policy(
    policy: nn.Module,
    paths: torch.Tensor,
    config: MarketConfig,
    *,
    meaningful_trade_threshold: float = 0.001,
) -> HedgeResult:
    """Roll the shared policy through every hedge date without detaching actions."""
    previous = torch.zeros(paths.shape[0], device=paths.device, dtype=paths.dtype)
    deltas: list[torch.Tensor] = []
    for step in range(config.n_steps):
        time = step * config.dt
        tau_normalized = (config.maturity_years - time) / config.maturity_years
        spot = paths[:, step]
        state = torch.stack(
            (
                torch.log(torch.clamp(spot, min=torch.finfo(paths.dtype).tiny) / config.strike),
                torch.full_like(spot, tau_normalized),
                previous,
                torch.full_like(spot, config.volatility),
                torch.full_like(spot, config.transaction_cost_rate),
            ),
            dim=1,
        )
        current = policy(state)
        deltas.append(current)
        previous = current
    return account_hedge(
        paths,
        torch.stack(deltas, dim=1),
        config,
        meaningful_trade_threshold=meaningful_trade_threshold,
    )
