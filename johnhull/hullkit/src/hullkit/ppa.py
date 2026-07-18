"""Synthetic renewable-PPA payoffs, valuation, and cash-flow risk.

Merchant revenue and PPA settlement are kept separate.  This makes volume,
shape/profile, and price-generation correlation risks visible even when the
contract fixes part of the realized power price.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np

PPAKind = Literal["fixed", "pay_as_produced", "floor_collar"]


def _scenario_arrays(spot_prices, generation) -> tuple[np.ndarray, np.ndarray]:
    spot = np.asarray(spot_prices, dtype=float)
    generated = np.asarray(generation, dtype=float)
    if spot.shape != generated.shape or spot.ndim not in (1, 2) or spot.size == 0:
        raise ValueError("spot_prices and generation must be aligned 1-D or 2-D arrays")
    if np.any(~np.isfinite(spot)) or np.any(~np.isfinite(generated)):
        raise ValueError("spot_prices and generation must be finite")
    # Power markets can clear at negative prices; only physical generation is
    # constrained to be non-negative.
    if np.any(generated < 0.0):
        raise ValueError("generation must be non-negative")
    return spot, generated


def ppa_settlement(
    kind: PPAKind,
    spot_prices,
    generation,
    *,
    fixed_price: float | None = None,
    contracted_volume=None,
    floor: float | None = None,
    cap: float | None = None,
) -> np.ndarray:
    """Settlement cash flow to the renewable generator.

    ``fixed`` is a fixed-volume contract-for-difference;
    ``pay_as_produced`` applies the fixed price to actual generation; and
    ``floor_collar`` clips the realized price for actual generation.
    """

    spot, generated = _scenario_arrays(spot_prices, generation)
    if kind in ("fixed", "pay_as_produced"):
        if fixed_price is None or not np.isfinite(fixed_price) or fixed_price < 0.0:
            raise ValueError("fixed_price must be finite and non-negative")
    if kind == "fixed":
        if contracted_volume is None:
            raise ValueError("fixed contract requires contracted_volume")
        volume = np.asarray(contracted_volume, dtype=float)
        try:
            volume = np.broadcast_to(volume, spot.shape)
        except ValueError as exc:
            raise ValueError("contracted_volume must broadcast to spot_prices") from exc
        if np.any(~np.isfinite(volume)) or np.any(volume < 0.0):
            raise ValueError("contracted_volume must be finite and non-negative")
        settlement = (float(fixed_price) - spot) * volume
    elif kind == "pay_as_produced":
        settlement = (float(fixed_price) - spot) * generated
    elif kind == "floor_collar":
        if floor is None and cap is None:
            raise ValueError("floor_collar requires floor or cap")
        lower = -np.inf if floor is None else float(floor)
        upper = np.inf if cap is None else float(cap)
        if not lower <= upper:
            raise ValueError("floor cannot exceed cap")
        protected_price = np.clip(spot, lower, upper)
        settlement = (protected_price - spot) * generated
    else:
        raise ValueError("unknown PPA kind")
    return np.asarray(settlement, dtype=float)


@dataclass(frozen=True)
class PriceGenerationScenarios:
    spot_prices: np.ndarray
    generation: np.ndarray
    target_correlation: float
    realized_correlation: float


def simulate_price_generation(
    n_scenarios: int,
    n_periods: int,
    *,
    base_price=60.0,
    base_generation=1.0,
    price_volatility: float = 0.25,
    generation_volatility: float = 0.20,
    correlation: float = -0.40,
    seed: int = 0,
) -> PriceGenerationScenarios:
    """Synthetic correlated electricity-price and renewable-output paths."""

    if not isinstance(n_scenarios, int) or n_scenarios < 2:
        raise ValueError("n_scenarios must be an integer >= 2")
    if not isinstance(n_periods, int) or n_periods < 1:
        raise ValueError("n_periods must be a positive integer")
    if not np.isfinite(correlation) or not -1.0 <= correlation <= 1.0:
        raise ValueError("correlation must lie in [-1, 1]")
    if price_volatility < 0.0 or generation_volatility < 0.0:
        raise ValueError("volatilities must be non-negative")
    base_price = np.broadcast_to(np.asarray(base_price, dtype=float), (n_periods,))
    base_generation = np.broadcast_to(np.asarray(base_generation, dtype=float), (n_periods,))
    if np.any(base_price <= 0.0) or np.any(base_generation < 0.0):
        raise ValueError("base price must be positive and generation non-negative")
    rng = np.random.default_rng(seed)
    z_price = rng.standard_normal((n_scenarios, n_periods))
    z_independent = rng.standard_normal((n_scenarios, n_periods))
    z_generation = correlation * z_price + math.sqrt(max(0.0, 1.0 - correlation**2)) * z_independent
    spot = base_price * np.exp(-0.5 * price_volatility**2 + price_volatility * z_price)
    generated = np.maximum(
        0.0,
        base_generation * (1.0 + generation_volatility * z_generation),
    )
    if np.std(spot) > 0.0 and np.std(generated) > 0.0:
        realized = float(np.corrcoef(spot.ravel(), generated.ravel())[0, 1])
    else:
        realized = 0.0
    return PriceGenerationScenarios(spot, generated, float(correlation), realized)


@dataclass(frozen=True)
class CashFlowRisk:
    expected_cash_flow: float
    lower_quantile: float
    tail_mean: float
    cash_flow_at_risk: float
    cash_flow_cvar: float


def cash_flow_risk(cash_flows, *, alpha: float = 0.95) -> CashFlowRisk:
    """Lower-tail cash-flow-at-risk and CVaR relative to expected cash flow."""

    values = np.asarray(cash_flows, dtype=float).ravel()
    if values.size < 2 or np.any(~np.isfinite(values)):
        raise ValueError("cash_flows must contain at least two finite scenarios")
    if not np.isfinite(alpha) or not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie in (0, 1)")
    expected = float(np.mean(values))
    quantile = float(np.quantile(values, 1.0 - alpha))
    tail = values[values <= quantile]
    tail_mean = float(np.mean(tail))
    return CashFlowRisk(
        expected_cash_flow=expected,
        lower_quantile=quantile,
        tail_mean=tail_mean,
        cash_flow_at_risk=float(expected - quantile),
        cash_flow_cvar=float(expected - tail_mean),
    )


@dataclass(frozen=True)
class PPAValuation:
    fair_value: float
    expected_merchant_revenue: float
    expected_hedged_cash_flow: float
    unhedged_std: float
    hedge_residual_std: float
    cash_flow_at_risk: float
    cash_flow_cvar: float
    price_generation_correlation: float
    volume_risk: float
    shape_risk: float
    profile_risk: float


def evaluate_ppa(
    kind: PPAKind,
    spot_prices,
    generation,
    *,
    fixed_price: float | None = None,
    contracted_volume=None,
    floor: float | None = None,
    cap: float | None = None,
    discount_factors=None,
    hedge_ratio: float = 1.0,
    alpha: float = 0.95,
) -> PPAValuation:
    """Fair value, cash-flow risk, and synthetic shape/volume/profile metrics."""

    spot, generated = _scenario_arrays(spot_prices, generation)
    if spot.ndim == 1:
        spot = spot[None, :]
        generated = generated[None, :]
    if spot.shape[0] < 2:
        raise ValueError("evaluate_ppa requires at least two scenarios")
    if not np.isfinite(hedge_ratio) or hedge_ratio < 0.0:
        raise ValueError("hedge_ratio must be finite and non-negative")
    periods = spot.shape[1]
    discount = (
        np.ones(periods) if discount_factors is None else np.asarray(discount_factors, dtype=float)
    )
    if discount.shape != (periods,) or np.any(~np.isfinite(discount)) or np.any(discount < 0.0):
        raise ValueError("discount_factors must be a non-negative vector over periods")
    settlement = ppa_settlement(
        kind,
        spot,
        generated,
        fixed_price=fixed_price,
        contracted_volume=contracted_volume,
        floor=floor,
        cap=cap,
    )
    merchant_pv = np.sum(discount * spot * generated, axis=1)
    settlement_pv = np.sum(discount * settlement, axis=1)
    hedged_pv = merchant_pv + hedge_ratio * settlement_pv
    risk = cash_flow_risk(hedged_pv, alpha=alpha)

    expected_spot = np.mean(spot, axis=0)
    expected_generation = np.mean(generated, axis=0)
    volume_component = np.sum(
        discount * expected_spot * (generated - expected_generation),
        axis=1,
    )
    scenario_average_price = np.mean(spot, axis=1, keepdims=True)
    shape_component = np.sum(
        discount * (spot - scenario_average_price) * expected_generation,
        axis=1,
    )
    profile_component = np.sum(
        discount * (spot - expected_spot) * (generated - expected_generation),
        axis=1,
    )
    if np.std(spot) > 0.0 and np.std(generated) > 0.0:
        correlation = float(np.corrcoef(spot.ravel(), generated.ravel())[0, 1])
    else:
        correlation = 0.0
    return PPAValuation(
        fair_value=float(np.mean(settlement_pv)),
        expected_merchant_revenue=float(np.mean(merchant_pv)),
        expected_hedged_cash_flow=float(np.mean(hedged_pv)),
        unhedged_std=float(np.std(merchant_pv, ddof=0)),
        hedge_residual_std=float(np.std(hedged_pv, ddof=0)),
        cash_flow_at_risk=risk.cash_flow_at_risk,
        cash_flow_cvar=risk.cash_flow_cvar,
        price_generation_correlation=correlation,
        volume_risk=float(np.std(volume_component, ddof=0)),
        shape_risk=float(np.std(shape_component, ddof=0)),
        profile_risk=float(np.std(profile_component, ddof=0)),
    )


def hedge_sensitivity(
    kind: PPAKind,
    spot_prices,
    generation,
    hedge_ratios,
    **contract_terms,
) -> dict[float, float]:
    """Map hedge ratio to residual cash-flow standard deviation."""

    ratios = np.asarray(hedge_ratios, dtype=float).ravel()
    if ratios.size == 0 or np.any(~np.isfinite(ratios)) or np.any(ratios < 0.0):
        raise ValueError("hedge_ratios must be non-empty, finite, and non-negative")
    return {
        float(ratio): evaluate_ppa(
            kind,
            spot_prices,
            generation,
            hedge_ratio=float(ratio),
            **contract_terms,
        ).hedge_residual_std
        for ratio in ratios
    }
