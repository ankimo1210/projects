"""Defaultable binomial valuation of a convertible bond (Hull GE §27.4)."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ConvertibleTree:
    """Recombining surviving-stock nodes, indexed by number of up moves.

    ``bond_levels[t][j]`` is the value at time step ``t`` after ``j`` up
    moves. The absorbing default branch has stock zero and the fixed recovery
    value, and therefore is not repeated in these surviving levels.
    """

    price: float
    stock_levels: tuple[tuple[float, ...], ...]
    bond_levels: tuple[tuple[float, ...], ...]
    decisions: tuple[tuple[str, ...], ...]
    up_probability: float
    down_probability: float
    default_probability: float


def defaultable_branch_probabilities(
    rate: float,
    dividend_yield: float,
    volatility: float,
    hazard_rate: float,
    time_step: float,
) -> tuple[float, float, float]:
    """Return unconditional up, down and default probabilities from Hull §27.4.

    ``volatility`` is conditional on survival. The probabilities sum to one,
    and the stock's *unconditional* expected growth is ``exp((r-q) Δt)``.
    Reject a grid whose non-default branches are negative rather than using
    invalid risk-neutral weights.
    """
    values = (rate, dividend_yield, volatility, hazard_rate, time_step)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("rates, volatility, hazard and time step must be finite")
    if volatility <= 0 or hazard_rate < 0 or time_step <= 0:
        raise ValueError("need positive volatility and time step, nonnegative hazard")
    up_factor = math.exp(volatility * math.sqrt(time_step))
    down_factor = 1 / up_factor
    survival = math.exp(-hazard_rate * time_step)
    growth = math.exp((rate - dividend_yield) * time_step)
    up = (growth - down_factor * survival) / (up_factor - down_factor)
    down = (up_factor * survival - growth) / (up_factor - down_factor)
    if min(up, down) < -1e-12:
        raise ValueError("negative branch probability: increase the number of steps")
    return max(up, 0.0), max(down, 0.0), 1 - survival


def convertible_bond_tree(
    spot: float,
    face: float,
    conversion_ratio: float,
    call_price: float | None,
    rate: float,
    dividend_yield: float,
    volatility: float,
    hazard_rate: float,
    recovery_value: float,
    maturity: float,
    steps: int,
    coupon_amount: float = 0.0,
) -> ConvertibleTree:
    """Value a convertible with constant terms by backward induction.

    The holder may convert at every surviving node. The issuer may call at
    every node before maturity; after a call, the holder can still convert.
    ``coupon_amount`` is paid at each next step only if the bond survives to
    that step and was not converted earlier. Recovery is the absolute currency
    amount paid on default during a step. All rates are continuous annual
    decimals, and ``maturity`` is in years. This educational model assumes a
    stock-independent constant risk-neutral hazard and fixed recovery.
    """
    values = (
        spot,
        face,
        conversion_ratio,
        rate,
        dividend_yield,
        volatility,
        hazard_rate,
        recovery_value,
        maturity,
        coupon_amount,
    )
    if not all(math.isfinite(value) for value in values) or (
        call_price is not None and not math.isfinite(call_price)
    ):
        raise ValueError("contract and market parameters must be finite")
    if (
        spot <= 0
        or face <= 0
        or conversion_ratio < 0
        or recovery_value < 0
        or coupon_amount < 0
        or maturity <= 0
        or not isinstance(steps, int)
        or steps < 1
        or (call_price is not None and call_price < 0)
    ):
        raise ValueError("invalid convertible terms or time grid")
    dt = maturity / steps
    up, down, default = defaultable_branch_probabilities(
        rate, dividend_yield, volatility, hazard_rate, dt
    )
    up_factor = math.exp(volatility * math.sqrt(dt))
    down_factor = 1 / up_factor
    stock = tuple(
        tuple(spot * up_factor**j * down_factor ** (i - j) for j in range(i + 1))
        for i in range(steps + 1)
    )
    values_at_time: list[tuple[float, ...]] = [()] * (steps + 1)
    decisions: list[tuple[str, ...]] = [()] * (steps + 1)
    values_at_time[-1] = tuple(max(face, conversion_ratio * s) for s in stock[-1])
    decisions[-1] = tuple("convert" if conversion_ratio * s > face else "redeem" for s in stock[-1])
    discount = math.exp(-rate * dt)
    survival = up + down
    for i in range(steps - 1, -1, -1):
        next_values = values_at_time[i + 1]
        level: list[float] = []
        labels: list[str] = []
        for j, s in enumerate(stock[i]):
            continuation = discount * (
                up * next_values[j + 1]
                + down * next_values[j]
                + default * recovery_value
                + survival * coupon_amount
            )
            conversion = conversion_ratio * s
            holder_value = max(continuation, conversion)
            if call_price is not None and holder_value > max(call_price, conversion):
                level.append(max(call_price, conversion))
                labels.append("call-convert" if conversion > call_price else "call-redeem")
            else:
                level.append(holder_value)
                labels.append("convert" if conversion > continuation else "hold")
        values_at_time[i] = tuple(level)
        decisions[i] = tuple(labels)
    return ConvertibleTree(
        price=values_at_time[0][0],
        stock_levels=stock,
        bond_levels=tuple(values_at_time),
        decisions=tuple(decisions),
        up_probability=up,
        down_probability=down,
        default_probability=default,
    )
