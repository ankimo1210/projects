"""Hull GE §27.6 knock-out barrier options on binomial and trinomial trees."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

_OPTIONS = ("call", "put")
_BARRIERS = ("up-and-out", "down-and-out")
_METHODS = ("simple", "inner", "on_barrier")


@dataclass(frozen=True)
class BarrierTree:
    """Price and geometry of a knock-out tree.

    ``barrier_level`` is the signed node level, in multiples of
    ``log_spacing`` from the spot, at and beyond which the option is dead.
    ``tree_barrier`` is the stock price of that level: the barrier the tree
    actually applies. Probabilities are ``(p_up, p_middle, p_down)``; a
    binomial tree has ``p_middle == 0``.
    """

    price: float
    method: str
    steps: int
    log_spacing: float
    probabilities: tuple[float, float, float]
    barrier_level: int
    tree_barrier: float


@dataclass(frozen=True)
class InterpolatedBarrier:
    """Hull's inner/outer interpolation: two tree prices and the weight on the outer one."""

    price: float
    inner: BarrierTree
    outer: BarrierTree
    weight: float


def standard_log_spacing(volatility: float, dt: float) -> float:
    """Hull §21.4 trinomial spacing ``ln u = sigma sqrt(3 dt)``."""
    return volatility * math.sqrt(3 * dt)


def barrier_log_spacing(spot: float, barrier: float, volatility: float, dt: float):
    """Hull §27.6 spacing that puts a node level exactly on the barrier.

    Returns ``(N, ln u)`` with ``N = int(|ln H - ln S0| / (sigma sqrt(3 dt)) + 0.5)``
    and ``ln u = |ln H - ln S0| / N``. ``N`` carries the sign of ``ln H - ln S0``
    (Hull's "positive or negative N"); the magnitude is rounded so a down
    barrier also gets the nearest level. ``N == 0`` means the barrier is within
    half a standard step of the spot and no such tree exists.
    """
    distance = math.log(barrier / spot)
    levels = int(abs(distance) / standard_log_spacing(volatility, dt) + 0.5)
    if levels == 0:
        raise ValueError(
            "barrier is within half a trinomial step of the spot: "
            "increase steps or use an adaptive mesh"
        )
    return int(math.copysign(levels, distance)), abs(distance) / levels


def trinomial_probabilities(
    log_spacing: float,
    rate: float,
    volatility: float,
    dt: float,
    *,
    dividend_yield: float = 0.0,
):
    """Hull §27.6 branch probabilities ``(p_up, p_middle, p_down)``.

    The one-step log return has mean ``mu dt`` exactly, with
    ``mu = r - q - sigma^2/2``, and second moment ``sigma^2 dt``. The true second
    moment is ``sigma^2 dt + (mu dt)^2``, so the second moment and the variance
    match only to first order in ``dt``. Values are returned even when a branch
    is negative; tree pricing rejects such spacings.
    """
    drift = (rate - dividend_yield - volatility**2 / 2) * dt
    spread = volatility**2 * dt / log_spacing**2
    return (
        drift / (2 * log_spacing) + spread / 2,
        1 - spread,
        -drift / (2 * log_spacing) + spread / 2,
    )


def _validate(spot, strike, barrier, rate, volatility, maturity, steps, option, barrier_type):
    values = (spot, strike, barrier, rate, volatility, maturity)
    if not all(isinstance(v, int | float) and math.isfinite(v) for v in values):
        raise ValueError("market and contract inputs must be finite numbers")
    if spot <= 0 or strike < 0 or barrier <= 0 or volatility <= 0 or maturity <= 0:
        raise ValueError("invalid barrier tree inputs")
    if isinstance(steps, bool) or not isinstance(steps, int) or steps < 1:
        raise ValueError("steps must be a positive integer")
    if option not in _OPTIONS:
        raise ValueError(f"option must be one of {_OPTIONS}, got {option!r}")
    if barrier_type not in _BARRIERS:
        raise ValueError(f"barrier_type must be one of {_BARRIERS}, got {barrier_type!r}")
    inside = barrier > spot if barrier_type == "up-and-out" else barrier < spot
    if not inside:
        raise ValueError("spot must be strictly inside the knock-out barrier")


def _outer_level(spot, barrier, log_spacing, up):
    """First node level at or beyond the barrier (the tree's implicit barrier)."""
    ratio = math.log(barrier / spot) / log_spacing
    nearest = round(ratio)
    if abs(ratio - nearest) <= 1e-9:
        return int(nearest)
    return math.ceil(ratio) if up else math.floor(ratio)


def _roll_back(spot, strike, rate, maturity, steps, log_spacing, probabilities, level, up, call):
    """Backward induction on levels -steps..steps with knock-out at ``level`` and beyond."""
    p_up, p_mid, p_down = probabilities
    discount = math.exp(-rate * maturity / steps)
    levels = np.arange(-steps, steps + 1)
    stock = spot * np.exp(levels * log_spacing)
    values = np.maximum(stock - strike, 0.0) if call else np.maximum(strike - stock, 0.0)
    values[levels >= level if up else levels <= level] = 0.0
    for step in range(steps - 1, -1, -1):
        values = discount * (p_up * values[2:] + p_mid * values[1:-1] + p_down * values[:-2])
        alive = np.arange(-step, step + 1)
        values[alive >= level if up else alive <= level] = 0.0
    return float(values[0])


def trinomial_barrier(
    spot: float,
    strike: float,
    barrier: float,
    rate: float,
    volatility: float,
    maturity: float,
    steps: int,
    *,
    option: str = "call",
    barrier_type: str = "up-and-out",
    method: str = "simple",
    dividend_yield: float = 0.0,
) -> BarrierTree:
    """Price a European knock-out option on a trinomial tree (Hull GE §27.6).

    ``method="simple"`` uses the §21.4 spacing and sets the value to zero at
    nodes at or beyond the barrier, so the tree's barrier is the outer level.
    ``"inner"`` knocks out one level earlier, at the inner barrier.
    ``"on_barrier"`` chooses ``ln u`` so that a level lies exactly on the
    barrier. The barrier is checked at every node. A lattice path moves one
    level per step, so it cannot jump over the tree's barrier level: this is
    continuous monitoring of that level, without the overshoot that the
    Broadie-Glasserman-Kou correction describes for discrete monitoring.
    A spacing with a negative branch probability, or a barrier within half a
    step of the spot, is rejected: Hull's remedy is an adaptive mesh.
    Rates, dividend yield and volatility are annual continuous decimals;
    maturity is in years.
    """
    _validate(spot, strike, barrier, rate, volatility, maturity, steps, option, barrier_type)
    if method not in _METHODS:
        raise ValueError(f"method must be one of {_METHODS}, got {method!r}")
    if not math.isfinite(dividend_yield):
        raise ValueError("dividend_yield must be finite")
    dt = maturity / steps
    up = barrier_type == "up-and-out"
    if method == "on_barrier":
        level, log_spacing = barrier_log_spacing(spot, barrier, volatility, dt)
    else:
        log_spacing = standard_log_spacing(volatility, dt)
        level = _outer_level(spot, barrier, log_spacing, up)
        if method == "inner":
            level += -1 if up else 1
    probabilities = trinomial_probabilities(
        log_spacing, rate, volatility, dt, dividend_yield=dividend_yield
    )
    if min(probabilities) < 0:
        raise ValueError(
            f"negative branch probability {min(probabilities):.4f}: "
            "increase steps or use an adaptive mesh"
        )
    price = _roll_back(
        spot, strike, rate, maturity, steps, log_spacing, probabilities, level, up, option == "call"
    )
    return BarrierTree(
        price=price,
        method=method,
        steps=steps,
        log_spacing=log_spacing,
        probabilities=probabilities,
        barrier_level=level,
        tree_barrier=spot * math.exp(level * log_spacing),
    )


def interpolated_barrier(
    spot: float,
    strike: float,
    barrier: float,
    rate: float,
    volatility: float,
    maturity: float,
    steps: int,
    *,
    option: str = "call",
    barrier_type: str = "up-and-out",
    dividend_yield: float = 0.0,
) -> InterpolatedBarrier:
    """Hull §27.6 approach: price at the inner and outer barriers, then interpolate.

    Hull does not fix the interpolation variable; this uses linear
    interpolation in the barrier price between the two tree barriers.
    """
    arguments = (spot, strike, barrier, rate, volatility, maturity, steps)
    options = dict(option=option, barrier_type=barrier_type, dividend_yield=dividend_yield)
    inner = trinomial_barrier(*arguments, method="inner", **options)
    outer = trinomial_barrier(*arguments, method="simple", **options)
    weight = (barrier - inner.tree_barrier) / (outer.tree_barrier - inner.tree_barrier)
    return InterpolatedBarrier(
        price=inner.price + weight * (outer.price - inner.price),
        inner=inner,
        outer=outer,
        weight=weight,
    )


def binomial_barrier(
    spot: float,
    strike: float,
    barrier: float,
    rate: float,
    volatility: float,
    maturity: float,
    steps: int,
    *,
    option: str = "call",
    barrier_type: str = "up-and-out",
    dividend_yield: float = 0.0,
) -> BarrierTree:
    """Hull §27.6 simple approach on a CRR binomial tree.

    Nodes at or beyond the barrier are worth zero, so the tree's barrier is
    the first CRR level ``S0 u^k`` at or beyond it.
    """
    _validate(spot, strike, barrier, rate, volatility, maturity, steps, option, barrier_type)
    if not math.isfinite(dividend_yield):
        raise ValueError("dividend_yield must be finite")
    dt = maturity / steps
    log_spacing = volatility * math.sqrt(dt)
    up_factor = math.exp(log_spacing)
    probability = (math.exp((rate - dividend_yield) * dt) - 1 / up_factor) / (
        up_factor - 1 / up_factor
    )
    if not 0 <= probability <= 1:
        raise ValueError("negative branch probability: increase the number of steps")
    up = barrier_type == "up-and-out"
    level = _outer_level(spot, barrier, log_spacing, up)
    discount = math.exp(-rate * dt)
    call = option == "call"
    net = np.arange(-steps, steps + 1, 2)
    stock = spot * np.exp(net * log_spacing)
    values = np.maximum(stock - strike, 0.0) if call else np.maximum(strike - stock, 0.0)
    values[net >= level if up else net <= level] = 0.0
    for step in range(steps - 1, -1, -1):
        values = discount * (probability * values[1:] + (1 - probability) * values[:-1])
        net = np.arange(-step, step + 1, 2)
        values[net >= level if up else net <= level] = 0.0
    return BarrierTree(
        price=float(values[0]),
        method="binomial",
        steps=steps,
        log_spacing=log_spacing,
        probabilities=(probability, 0.0, 1 - probability),
        barrier_level=level,
        tree_barrier=spot * math.exp(level * log_spacing),
    )
