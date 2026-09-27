"""Hull GE §27.5 tree with a representative arithmetic-average state."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class AveragePriceTree:
    """CRR stock nodes and representative running-average/value grids.

    Levels are indexed by time step, then number of up moves. Average grids
    include the initial spot observation and every subsequent stock node.
    """

    price: float
    stock_levels: tuple[tuple[float, ...], ...]
    average_grids: tuple[tuple[tuple[float, ...], ...], ...]
    value_grids: tuple[tuple[tuple[float, ...], ...], ...]
    up_probability: float
    discount_factor: float


def arithmetic_average_call_tree(
    spot: float,
    strike: float,
    rate: float,
    volatility: float,
    maturity: float,
    steps: int,
    average_points: int,
    *,
    dividend_yield: float = 0.0,
    american: bool = False,
) -> AveragePriceTree:
    """Price a discrete-average Asian call with Hull's nodewise state grid.

    At each surviving CRR stock node, the attainable minimum and maximum
    arithmetic averages are propagated forward. ``average_points`` equally
    spaced representative averages include both bounds; values at child
    averages between grid points use linear interpolation during rollback.
    The arithmetic average samples spot at inception and at each step. For
    ``american=True``, immediate exercise is compared with continuation at
    every node and every representative average. Rates and volatility are
    constant annual decimals; maturity is in years.
    """
    parameters = (spot, strike, rate, volatility, maturity, dividend_yield)
    if not all(math.isfinite(value) for value in parameters):
        raise ValueError("market and contract inputs must be finite")
    if (
        spot <= 0
        or strike < 0
        or volatility <= 0
        or maturity <= 0
        or not isinstance(steps, int)
        or steps < 1
        or not isinstance(average_points, int)
        or average_points < 2
    ):
        raise ValueError("invalid arithmetic-average tree inputs")
    dt = maturity / steps
    up_factor = math.exp(volatility * math.sqrt(dt))
    down_factor = 1 / up_factor
    probability = (math.exp((rate - dividend_yield) * dt) - down_factor) / (up_factor - down_factor)
    if not 0 <= probability <= 1:
        raise ValueError("negative branch probability: increase the number of steps")
    discount = math.exp(-rate * dt)
    stocks = [
        tuple(spot * up_factor**j * down_factor ** (t - j) for j in range(t + 1))
        for t in range(steps + 1)
    ]

    minima: list[list[float]] = [[spot]]
    maxima: list[list[float]] = [[spot]]
    for t in range(steps):
        child_min = [math.inf] * (t + 2)
        child_max = [-math.inf] * (t + 2)
        for j in range(t + 1):
            for next_j in (j, j + 1):
                next_stock = stocks[t + 1][next_j]
                low = ((t + 1) * minima[t][j] + next_stock) / (t + 2)
                high = ((t + 1) * maxima[t][j] + next_stock) / (t + 2)
                child_min[next_j] = min(child_min[next_j], low)
                child_max[next_j] = max(child_max[next_j], high)
        minima.append(child_min)
        maxima.append(child_max)

    grids = [
        [
            np.linspace(low, high, average_points) if high > low + 1e-12 else np.array([low])
            for low, high in zip(minima[t], maxima[t], strict=True)
        ]
        for t in range(steps + 1)
    ]
    values: list[list[np.ndarray]] = [[] for _ in range(steps + 1)]
    values[-1] = [np.maximum(grid - strike, 0.0) for grid in grids[-1]]
    for t in range(steps - 1, -1, -1):
        level = []
        for j, average in enumerate(grids[t]):
            up_average = ((t + 1) * average + stocks[t + 1][j + 1]) / (t + 2)
            down_average = ((t + 1) * average + stocks[t + 1][j]) / (t + 2)
            up_value = np.interp(up_average, grids[t + 1][j + 1], values[t + 1][j + 1])
            down_value = np.interp(down_average, grids[t + 1][j], values[t + 1][j])
            continuation = discount * (probability * up_value + (1 - probability) * down_value)
            level.append(np.maximum(continuation, average - strike) if american else continuation)
        values[t] = level
    return AveragePriceTree(
        price=float(values[0][0][0]),
        stock_levels=tuple(stocks),
        average_grids=tuple(
            tuple(tuple(float(x) for x in grid) for grid in level) for level in grids
        ),
        value_grids=tuple(
            tuple(tuple(float(x) for x in grid) for grid in level) for level in values
        ),
        up_probability=probability,
        discount_factor=discount,
    )
