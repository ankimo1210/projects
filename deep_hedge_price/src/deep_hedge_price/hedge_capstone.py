"""Common-path synthetic hedge comparison for the vol-20 capstone."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import ndtr

DEFAULT_TRANSACTION_COST = 0.0005
DEFAULT_NO_TRADE_WIDTH = 0.04


@dataclass(frozen=True)
class HedgeComparison:
    """Common-path hedge comparison: per-strategy P&L, turnover, and metrics."""

    path_ids: np.ndarray
    pnl: dict[str, np.ndarray]
    turnover: dict[str, np.ndarray]
    metrics: dict[str, dict[str, float]]


def _bsm_call_state(
    spot: np.ndarray,
    strike: float,
    tau: np.ndarray,
    volatility: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Zero-rate BSM price, delta, and gamma on aligned arrays."""

    spot, tau = np.broadcast_arrays(np.asarray(spot, dtype=float), np.asarray(tau, dtype=float))
    safe_tau = np.maximum(tau, np.finfo(float).eps)
    root_tau = np.sqrt(safe_tau)
    d1 = (np.log(spot / strike) + 0.5 * volatility**2 * safe_tau) / (volatility * root_tau)
    d2 = d1 - volatility * root_tau
    density = np.exp(-0.5 * d1**2) / np.sqrt(2 * np.pi)
    live_price = spot * ndtr(d1) - strike * ndtr(d2)
    price = np.where(tau > 0.0, live_price, np.maximum(spot - strike, 0.0))
    delta = np.where(
        tau > 0.0,
        ndtr(d1),
        np.where(spot > strike, 1.0, np.where(spot < strike, 0.0, 0.5)),
    )
    gamma = np.where(tau > 0.0, density / (spot * volatility * root_tau), 0.0)
    return price, delta, gamma


def _risk_metrics(pnl: np.ndarray, turnover: np.ndarray) -> dict[str, float]:
    loss = -pnl
    var = float(np.quantile(loss, 0.95))
    return {
        "mean_pnl": float(np.mean(pnl)),
        "hedging_rmse": float(np.sqrt(np.mean(pnl**2))),
        "var95": var,
        "cvar95": float(np.mean(loss[loss >= var])),
        "turnover": float(np.mean(turnover)),
    }


def synthetic_hedge_capstone(
    *,
    n_paths: int = 2_000,
    n_steps: int = 20,
    seed: int = 0,
    transaction_cost: float = DEFAULT_TRANSACTION_COST,
    no_trade_width: float = DEFAULT_NO_TRADE_WIDTH,
    gamma_hedge_strike: float = 105.0,
    gamma_position_limit: float = 5.0,
    volatility: float = 0.2,
    deep_policy_positions: np.ndarray | None = None,
) -> HedgeComparison:
    """Compare no/delta/delta-gamma/no-trade strategies on common GBM paths.

    Delta-gamma uses a second call, not a stock-only gamma adjustment.  A
    trained Phase-1 neural policy is intentionally not labelled or fabricated
    here; callers must evaluate a real checkpoint through the Phase-1 engine.
    """
    if (
        n_paths < 100
        or n_steps < 2
        or transaction_cost < 0
        or no_trade_width < 0
        or gamma_hedge_strike <= 0
        or gamma_position_limit <= 0
        or volatility <= 0
    ):
        raise ValueError("invalid capstone configuration")
    rng = np.random.default_rng(seed)
    dt = 1 / n_steps
    shocks = rng.standard_normal((n_paths, n_steps))
    increments = (-0.5 * volatility**2) * dt + volatility * np.sqrt(dt) * shocks
    spot = 100 * np.exp(np.column_stack([np.zeros(n_paths), np.cumsum(increments, axis=1)]))
    payoff = np.maximum(spot[:, -1] - 100, 0)
    time = np.arange(n_steps) * dt
    tau = 1 - time
    premium = float(_bsm_call_state(np.array(100.0), 100.0, np.array(1.0), volatility)[0])
    _, delta, gamma = _bsm_call_state(spot[:, :-1], 100.0, tau, volatility)

    secondary_tau = 1.0 - np.arange(n_steps + 1) * dt
    secondary_prices, secondary_delta, secondary_gamma = _bsm_call_state(
        spot,
        gamma_hedge_strike,
        secondary_tau,
        volatility,
    )
    option_units = np.divide(
        gamma,
        secondary_gamma[:, :-1],
        out=np.zeros_like(gamma),
        where=secondary_gamma[:, :-1] > 1e-10,
    )
    option_units = np.clip(option_units, 0.0, gamma_position_limit)
    gamma_stock = delta - option_units * secondary_delta[:, :-1]

    no_trade = delta.copy()
    for index in range(1, n_steps):
        no_trade[:, index] = np.where(
            np.abs(delta[:, index] - no_trade[:, index - 1]) > no_trade_width,
            delta[:, index],
            no_trade[:, index - 1],
        )
    positions = {
        "no hedge": np.zeros_like(delta),
        "delta": delta,
        "no-trade": no_trade,
    }
    if deep_policy_positions is not None:
        deep_positions = np.asarray(deep_policy_positions, dtype=float)
        if deep_positions.shape != delta.shape or np.any(~np.isfinite(deep_positions)):
            raise ValueError("deep_policy_positions must be finite and match [path, trade time]")
        positions["deep-policy"] = deep_positions
    pnl: dict[str, np.ndarray] = {}
    turnover: dict[str, np.ndarray] = {}
    moves = np.diff(spot, axis=1)
    for name, hedge in positions.items():
        trades = np.diff(np.column_stack([np.zeros(n_paths), hedge]), axis=1)
        path_turnover = np.sum(np.abs(trades) * spot[:, :-1], axis=1)
        path_turnover += np.abs(hedge[:, -1]) * spot[:, -1]
        costs = transaction_cost * path_turnover
        gains = np.sum(hedge * moves, axis=1)
        pnl[name] = premium + gains - payoff - costs
        turnover[name] = path_turnover

    stock_trades = np.diff(np.column_stack([np.zeros(n_paths), gamma_stock]), axis=1)
    option_trades = np.diff(np.column_stack([np.zeros(n_paths), option_units]), axis=1)
    gamma_turnover = np.sum(np.abs(stock_trades) * spot[:, :-1], axis=1)
    gamma_turnover += np.abs(gamma_stock[:, -1]) * spot[:, -1]
    gamma_turnover += np.sum(np.abs(option_trades) * secondary_prices[:, :-1], axis=1)
    gamma_gains = np.sum(gamma_stock * moves, axis=1)
    gamma_gains += np.sum(option_units * np.diff(secondary_prices, axis=1), axis=1)
    pnl["delta-gamma"] = premium + gamma_gains - payoff - transaction_cost * gamma_turnover
    turnover["delta-gamma"] = gamma_turnover

    metrics = {name: _risk_metrics(values, turnover[name]) for name, values in pnl.items()}
    metrics["delta-gamma"]["no_change_fraction"] = float(
        np.mean(
            (np.abs(np.diff(gamma_stock, axis=1)) <= 1e-12)
            & (np.abs(np.diff(option_units, axis=1)) <= 1e-12)
        )
    )
    for name, hedge in positions.items():
        metrics[name]["no_change_fraction"] = float(
            np.mean(np.abs(np.diff(hedge, axis=1)) <= 1e-12)
        )
    return HedgeComparison(
        path_ids=np.arange(n_paths),
        pnl=pnl,
        turnover=turnover,
        metrics=metrics,
    )


def _forecast_hedge_case(
    *,
    forecast_volatility,
    path_volatility,
    maturity=1.0,
    n_paths=512,
    n_steps=12,
    seed=0,
    deep_policy_positions=None,
):
    """Private forecast evaluation on common true-vol paths and an oracle fair premium.

    Forecast vol selects primary delta/gamma only. The traded secondary option
    uses observable fair prices/Greeks at true scenario vol. End-point stock
    liquidation is charged, expiry option cash settlement is not a new trade.
    """
    if min(forecast_volatility, path_volatility, maturity) <= 0:
        raise ValueError("positive scenario/forecast vol and maturity required")
    dt = maturity / n_steps
    shocks = np.random.default_rng(seed).standard_normal((n_paths, n_steps))
    increments = -0.5 * path_volatility**2 * dt + path_volatility * np.sqrt(dt) * shocks
    spot = 100 * np.exp(np.column_stack([np.zeros(n_paths), np.cumsum(increments, axis=1)]))
    tau = maturity - np.arange(n_steps) * dt
    premium = float(_bsm_call_state(np.array(100.0), 100.0, np.array(maturity), path_volatility)[0])
    _, delta, gamma = _bsm_call_state(spot[:, :-1], 100, tau, forecast_volatility)
    secondary, secondary_delta, secondary_gamma = _bsm_call_state(
        spot, 105, maturity - np.arange(n_steps + 1) * dt, path_volatility
    )
    units = np.divide(
        gamma,
        secondary_gamma[:, :-1],
        out=np.zeros_like(gamma),
        where=secondary_gamma[:, :-1] > 1e-10,
    )
    units = np.clip(units, 0, 5.0)
    no_trade = delta.copy()
    for t in range(1, n_steps):
        no_trade[:, t] = np.where(
            np.abs(delta[:, t] - no_trade[:, t - 1]) > DEFAULT_NO_TRADE_WIDTH,
            delta[:, t],
            no_trade[:, t - 1],
        )
    positions = {
        "delta": delta,
        "delta-gamma": delta - units * secondary_delta[:, :-1],
        "no hedge": np.zeros_like(delta),
        "no-trade": no_trade,
    }
    if deep_policy_positions is not None:
        positions["deep-policy"] = np.asarray(deep_policy_positions)
    names = sorted(positions)
    stocks = np.stack([positions[name] for name in names])
    options = np.stack([units if name == "delta-gamma" else np.zeros_like(units) for name in names])
    stock_trades = np.diff(
        np.concatenate([np.zeros((len(names), n_paths, 1)), stocks], axis=2), axis=2
    )
    option_trades = np.diff(
        np.concatenate([np.zeros((len(names), n_paths, 1)), options], axis=2), axis=2
    )
    turnover = (np.abs(stock_trades) * spot[:, :-1]).sum(axis=2)
    turnover += (np.abs(option_trades) * secondary[:, :-1]).sum(axis=2)
    turnover += np.abs(stocks[:, :, -1]) * spot[:, -1]
    gains = (stocks * np.diff(spot, axis=1)).sum(axis=2) + (
        options * np.diff(secondary, axis=1)
    ).sum(axis=2)
    pnl = premium + gains - np.maximum(spot[:, -1] - 100, 0) - DEFAULT_TRANSACTION_COST * turnover
    metrics = {name: _risk_metrics(pnl[i], turnover[i]) for i, name in enumerate(names)}
    for i, name in enumerate(names):
        metrics[name]["no_change_fraction"] = float(
            np.mean(
                (np.abs(np.diff(stocks[i], axis=1)) <= 1e-12)
                & (np.abs(np.diff(options[i], axis=1)) <= 1e-12)
            )
        )
    comparison = HedgeComparison(
        np.arange(n_paths),
        dict(zip(names, pnl, strict=True)),
        dict(zip(names, turnover, strict=True)),
        metrics,
    )
    evidence = {
        "spot": spot,
        "shocks": shocks,
        "premium": premium,
        "secondary_price": secondary,
        "stock_positions": stocks,
        "option_positions": options,
        "strategy_names": names,
    }
    return comparison, evidence
