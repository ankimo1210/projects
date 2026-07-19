"""Classical hedging strategy baselines."""

from __future__ import annotations

import torch

from .black_scholes import torch_call_delta
from .config import MarketConfig


def no_hedge_deltas(paths: torch.Tensor, config: MarketConfig) -> torch.Tensor:
    """Return zero stock positions."""
    return torch.zeros((paths.shape[0], config.n_steps), device=paths.device, dtype=paths.dtype)


def black_scholes_deltas(paths: torch.Tensor, config: MarketConfig) -> torch.Tensor:
    """Return discretely rebalanced Black--Scholes delta positions."""
    positions: list[torch.Tensor] = []
    for step in range(config.n_steps):
        tau = config.maturity_years - step * config.dt
        per_option = torch_call_delta(
            paths[:, step],
            config.strike,
            tau,
            config.risk_free_rate,
            config.volatility,
        )
        positions.append(config.short_quantity * per_option)
    return torch.stack(positions, dim=1)


def no_trade_band_deltas(
    paths: torch.Tensor,
    config: MarketConfig,
    *,
    band: float = 0.05,
) -> torch.Tensor:
    """Trade to the nearest boundary around Black--Scholes delta."""
    if band < 0:
        raise ValueError("band cannot be negative")
    previous = torch.zeros(paths.shape[0], device=paths.device, dtype=paths.dtype)
    positions: list[torch.Tensor] = []
    scaled_band = config.short_quantity * band
    for step in range(config.n_steps):
        tau = config.maturity_years - step * config.dt
        target = config.short_quantity * torch_call_delta(
            paths[:, step],
            config.strike,
            tau,
            config.risk_free_rate,
            config.volatility,
        )
        lower = target - scaled_band
        upper = target + scaled_band
        current = torch.where(
            previous < lower,
            lower,
            torch.where(previous > upper, upper, previous),
        )
        current = torch.clamp(current, min=0.0, max=config.short_quantity)
        positions.append(current)
        previous = current
    return torch.stack(positions, dim=1)
