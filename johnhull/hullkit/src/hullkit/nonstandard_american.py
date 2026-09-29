"""CRR valuation of Hull GE §26.3 options with scheduled exercise terms.

The caller supplies exercise strikes by *integer tree step*. No calendar date
is silently rounded onto the CRR grid. Step ``N`` must be present: its strike
defines the final payoff. Omit earlier steps for a lockout or Bermudan option.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from numbers import Integral, Real

import numpy as np


@dataclass(frozen=True)
class ScheduledOption:
    """Root price and trees, with exercise flags at each node (high stock first)."""

    price: float
    stock: tuple[tuple[float, ...], ...]
    values: tuple[tuple[float, ...], ...]
    exercise: tuple[tuple[bool, ...], ...]
    schedule: tuple[tuple[int, float], ...]


def _finite(name: str, value: Real, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    result = float(value)
    if positive and result <= 0.0:
        raise ValueError(f"{name} must be positive")
    return result


def _schedule(exercise_strikes: Mapping[int, float], steps: int) -> tuple[tuple[int, float], ...]:
    if not isinstance(exercise_strikes, Mapping) or not exercise_strikes:
        raise ValueError("exercise_strikes must map grid steps to positive strikes")
    result = []
    for step, strike in exercise_strikes.items():
        if isinstance(step, bool) or not isinstance(step, Integral) or not 0 <= step <= steps:
            raise ValueError("exercise_strikes keys must be integer grid steps in 0..N")
        try:
            strike = _finite("exercise_strikes strike", strike, positive=True)
        except ValueError as exc:
            raise ValueError(f"exercise_strikes: {exc}") from exc
        result.append((int(step), strike))
    if steps not in exercise_strikes:
        raise ValueError("exercise_strikes must include maturity step N")
    return tuple(sorted(result))


def scheduled_option(
    kind: str,
    spot: float,
    r: float,
    sigma: float,
    maturity: float,
    steps: int,
    exercise_strikes: Mapping[int, float],
    q: float = 0.0,
) -> ScheduledOption:
    """Price a call/put with discrete exercise dates and possibly changing strike.

    Rates and dividend yield are annual continuously compounded. Time step
    ``i`` occurs at ``i * maturity / steps``. The CRR probability must lie
    strictly inside (0, 1). The last schedule entry is the terminal strike.
    """
    if kind not in ("call", "put"):
        raise ValueError("kind must be 'call' or 'put'")
    spot = _finite("spot", spot, positive=True)
    r = _finite("r", r)
    q = _finite("q", q)
    sigma = _finite("sigma", sigma, positive=True)
    maturity = _finite("maturity", maturity, positive=True)
    if isinstance(steps, bool) or not isinstance(steps, Integral) or steps < 1:
        raise ValueError("steps must be a positive integer")
    steps = int(steps)
    schedule = _schedule(exercise_strikes, steps)
    strikes = dict(schedule)

    dt = maturity / steps
    if dt <= 0.0:
        raise ValueError("maturity/steps is below floating-point resolution")
    try:
        log_u = sigma * math.sqrt(dt)
        u = math.exp(log_u)
        d = 1.0 / u
        growth = math.exp((r - q) * dt)
        discount = math.exp(-r * dt)
        p = (growth - d) / (u - d)
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("CRR parameters exceed floating-point range") from exc
    if not (math.isfinite(p) and 0.0 < p < 1.0 and math.isfinite(discount)):
        raise ValueError("CRR probability must be strictly between zero and one")

    stock = []
    for i in range(steps + 1):
        try:
            row = np.array([spot * math.exp((i - 2 * j) * log_u) for j in range(i + 1)])
        except OverflowError as exc:
            raise ValueError("stock tree exceeds floating-point range") from exc
        if not np.isfinite(row).all():
            raise ValueError("stock tree exceeds floating-point range")
        stock.append(row)

    values = [None] * (steps + 1)
    exercise = [None] * (steps + 1)

    def payoff(row: np.ndarray, strike: float) -> np.ndarray:
        return np.maximum(row - strike, 0.0) if kind == "call" else np.maximum(strike - row, 0.0)

    values[steps] = payoff(stock[steps], strikes[steps])
    exercise[steps] = values[steps] > 0.0
    for i in range(steps - 1, -1, -1):
        continuation = discount * (p * values[i + 1][:-1] + (1.0 - p) * values[i + 1][1:])
        if i in strikes:
            intrinsic = payoff(stock[i], strikes[i])
            exercise[i] = (intrinsic > continuation) & (intrinsic > 0.0)
            values[i] = np.where(exercise[i], intrinsic, continuation)
        else:
            exercise[i] = np.zeros(i + 1, dtype=bool)
            values[i] = continuation

    return ScheduledOption(
        price=float(values[0][0]),
        stock=tuple(tuple(float(x) for x in row) for row in stock),
        values=tuple(tuple(float(x) for x in row) for row in values),
        exercise=tuple(tuple(bool(x) for x in row) for row in exercise),
        schedule=schedule,
    )
