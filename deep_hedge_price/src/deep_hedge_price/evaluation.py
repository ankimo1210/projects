"""Common-random-number evaluation and explicit risk metrics."""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np
import pandas as pd
import torch
from torch import nn

from .config import MarketConfig
from .pnl import HedgeResult, account_hedge, rollout_policy


def _to_numpy(tensor: torch.Tensor) -> np.ndarray:
    return tensor.detach().cpu().numpy()


def evaluate_policy_chunks(
    policy: nn.Module,
    paths: torch.Tensor,
    config: MarketConfig,
    *,
    chunk_size: int,
    meaningful_trade_threshold: float,
) -> HedgeResult:
    """Evaluate a policy without gradients and concatenate bounded chunks."""
    parts: list[HedgeResult] = []
    with torch.no_grad():
        for chunk in paths.split(chunk_size):
            parts.append(
                rollout_policy(
                    policy,
                    chunk,
                    config,
                    meaningful_trade_threshold=meaningful_trade_threshold,
                )
            )
    fields = (
        "deltas",
        "payoff",
        "gross_trading_gain",
        "transaction_cost",
        "net_trading_gain",
        "loss_excluding_premium",
        "pnl_including_premium",
        "pnl_before_costs",
        "turnover",
        "meaningful_trades",
    )
    joined = {field: torch.cat([getattr(part, field) for part in parts]) for field in fields}
    return HedgeResult(**joined, premium=parts[0].premium)


def evaluate_delta_strategy(
    paths: torch.Tensor,
    config: MarketConfig,
    delta_function: Callable[[torch.Tensor, MarketConfig], torch.Tensor],
    *,
    meaningful_trade_threshold: float,
) -> HedgeResult:
    """Evaluate a deterministic baseline through the shared accounting engine."""
    with torch.no_grad():
        deltas = delta_function(paths, config)
        return account_hedge(
            paths,
            deltas,
            config,
            meaningful_trade_threshold=meaningful_trade_threshold,
        )


def result_frame(result: HedgeResult, strategy: str, path_ids: np.ndarray) -> pd.DataFrame:
    """Convert pathwise results to a tidy strategy-level frame."""
    return pd.DataFrame(
        {
            "path_id": path_ids,
            "strategy": strategy,
            "discounted_payoff": _to_numpy(result.payoff),
            "gross_trading_gain": _to_numpy(result.gross_trading_gain),
            "net_trading_gain": _to_numpy(result.net_trading_gain),
            "transaction_cost": _to_numpy(result.transaction_cost),
            "turnover_shares": _to_numpy(result.turnover),
            "meaningful_trades": _to_numpy(result.meaningful_trades),
            "terminal_delta": _to_numpy(result.deltas[:, -1]),
            "loss_excluding_premium": _to_numpy(result.loss_excluding_premium),
            "discounted_pnl": _to_numpy(result.pnl_including_premium),
            "discounted_pnl_before_costs": _to_numpy(result.pnl_before_costs),
        }
    )


def _expected_shortfall(loss: np.ndarray, alpha: float) -> tuple[float, float]:
    var = float(np.quantile(loss, alpha))
    tail = loss[loss >= var]
    return var, float(tail.mean())


def summarize_strategy(frame: pd.DataFrame) -> dict[str, float | int | None]:
    """Compute the complete requested metric set for one strategy."""
    pnl = frame["discounted_pnl"].to_numpy(dtype=float)
    loss = -pnl
    payoff = frame["discounted_payoff"].to_numpy(dtype=float)
    gain = frame["net_trading_gain"].to_numpy(dtype=float)
    var95, cvar95 = _expected_shortfall(loss, 0.95)
    var99, cvar99 = _expected_shortfall(loss, 0.99)
    if np.std(payoff) == 0 or np.std(gain) == 0:
        correlation: float | None = None
    else:
        correlation = float(np.corrcoef(payoff, gain)[0, 1])
    terminal = frame["terminal_delta"].to_numpy(dtype=float)
    quantiles = np.quantile(pnl, [0.01, 0.05, 0.25, 0.75, 0.95, 0.99])
    return {
        "n_paths": len(frame),
        "mean_discounted_pnl_after_costs_including_premium": float(pnl.mean()),
        "std_discounted_pnl_after_costs_including_premium": float(pnl.std(ddof=1)),
        "rmse_discounted_hedging_error": float(np.sqrt(np.mean(pnl**2))),
        "mae_discounted_hedging_error": float(np.mean(np.abs(pnl))),
        "median_discounted_pnl": float(np.median(pnl)),
        "minimum_discounted_pnl": float(pnl.min()),
        "maximum_discounted_pnl": float(pnl.max()),
        "pnl_quantile_01": float(quantiles[0]),
        "pnl_quantile_05": float(quantiles[1]),
        "pnl_quantile_25": float(quantiles[2]),
        "pnl_quantile_75": float(quantiles[3]),
        "pnl_quantile_95": float(quantiles[4]),
        "pnl_quantile_99": float(quantiles[5]),
        "var_loss_95": var95,
        "var_loss_99": var99,
        "cvar_loss_95": cvar95,
        "cvar_loss_99": cvar99,
        "average_discounted_transaction_cost": float(frame["transaction_cost"].mean()),
        "average_turnover_shares": float(frame["turnover_shares"].mean()),
        "average_meaningful_trades": float(frame["meaningful_trades"].mean()),
        "terminal_delta_mean": float(terminal.mean()),
        "terminal_delta_std": float(terminal.std(ddof=1)),
        "terminal_delta_min": float(terminal.min()),
        "terminal_delta_q05": float(np.quantile(terminal, 0.05)),
        "terminal_delta_median": float(np.median(terminal)),
        "terminal_delta_q95": float(np.quantile(terminal, 0.95)),
        "terminal_delta_max": float(terminal.max()),
        "payoff_net_gain_correlation": correlation,
    }


def summarize_all(frame: pd.DataFrame) -> dict[str, dict[str, float | int | None]]:
    """Summarize every strategy while preserving frame order."""
    return {
        str(strategy): summarize_strategy(group)
        for strategy, group in frame.groupby("strategy", sort=False)
    }


def policy_distance_to_bs(neural: HedgeResult, bs_deltas: torch.Tensor) -> dict[str, float]:
    """Path-time weighted action distance to Black--Scholes delta."""
    difference = _to_numpy(neural.deltas - bs_deltas).astype(float)
    return {
        "policy_bs_mae": float(np.mean(np.abs(difference))),
        "policy_bs_rmse": float(math.sqrt(np.mean(difference**2))),
    }
