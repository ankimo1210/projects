"""Hull GE §27.7 options on two correlated assets on three-dimensional trees."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

_METHODS = ("transform", "rubinstein", "adjusted")
_EXERCISES = ("european", "american")
_MOVES = ((1, 1), (1, -1), (-1, 1), (-1, -1))


@dataclass(frozen=True)
class TwoAssetLattice:
    """One step of a recombining three-dimensional tree for two log prices.

    A node ``(n, j, k)``, with ``j`` and ``k`` in ``-n, -n + 2, ..., n``, has
    ``ln S_i = ln S_i(0) + n drift_i + j j_move_i + k k_move_i``. Each step moves
    ``(j, k)`` by ``(+1, +1), (+1, -1), (-1, +1), (-1, -1)`` with ``probabilities``
    in that order. Log moves are per step; ``dt`` is the step in years.
    """

    method: str
    dt: float
    drift: tuple[float, float]
    j_move: tuple[float, float]
    k_move: tuple[float, float]
    probabilities: tuple[float, float, float, float]

    def branches(self):
        """The four ``((d ln S1, d ln S2), probability)`` branches of one step."""
        return [
            (
                tuple(
                    d + j * a + k * b
                    for d, a, b in zip(self.drift, self.j_move, self.k_move, strict=True)
                ),
                probability,
            )
            for (j, k), probability in zip(_MOVES, self.probabilities, strict=True)
        ]

    def log_moments(self):
        """Mean vector and covariance matrix of the one-step log returns."""
        moves = np.array([move for move, _ in self.branches()])
        weights = np.array(self.probabilities)
        mean = weights @ moves
        centred = moves - mean
        return mean, (weights[:, None] * centred).T @ centred


@dataclass(frozen=True)
class TwoAssetTree:
    """Price from a two-asset tree and the one-step lattice it used."""

    price: float
    method: str
    exercise: str
    steps: int
    lattice: TwoAssetLattice


def _finite(*values):
    return all(
        isinstance(v, int | float) and not isinstance(v, bool) and math.isfinite(v) for v in values
    )


def _pair(values, name):
    if not isinstance(values, tuple | list) or len(values) != 2:
        raise ValueError(f"{name} must hold two values")
    if not _finite(*values):
        raise ValueError(f"{name} must be finite numbers")
    return float(values[0]), float(values[1])


def _binomial(mean, variance):
    """Binomial step ``+-h`` with probability ``p`` matching the mean and variance exactly."""
    size = math.sqrt(variance + mean**2)
    if size == 0.0:
        return 0.0, 0.5
    return size, min(max(0.5 + mean / (2 * size), 0.0), 1.0)


def two_asset_lattice(
    rate: float,
    volatilities: tuple[float, float],
    correlation: float,
    dt: float,
    *,
    method: str = "adjusted",
    dividend_yields: tuple[float, float] = (0.0, 0.0),
) -> TwoAssetLattice:
    """One step of Hull §27.7's three-dimensional trees.

    ``"transform"`` models ``x1 = sigma2 ln S1 + sigma1 ln S2`` and
    ``x2 = sigma2 ln S1 - sigma1 ln S2``, which are uncorrelated, on two binomial
    trees. Hull asks each tree to match the first two moments; for a step
    ``+-h_i`` with probability ``p_i`` that fixes ``h_i = sqrt(v_i + m_i^2)`` and
    ``p_i = 1/2 + m_i / (2 h_i)`` for the one-step mean ``m_i`` and variance
    ``v_i`` (the common shortcut ``h_i = sd_i sqrt(dt)`` matches the variance
    only to first order). ``"rubinstein"`` is the nonrectangular tree with four
    branches of probability 0.25 and the factors ``u1, d1, A, B, C, D``.
    ``"adjusted"`` combines the §21.4 alternative binomial trees (probabilities
    0.5) and sets the joint probabilities to ``0.25(1 +- rho)`` (Table 27.3).
    All three match the one-step mean and covariance of the log returns
    exactly. Rates, yields and volatilities are annual continuous decimals.
    """
    if method not in _METHODS:
        raise ValueError(f"method must be one of {_METHODS}, got {method!r}")
    sigma1, sigma2 = _pair(volatilities, "volatilities")
    q1, q2 = _pair(dividend_yields, "dividend_yields")
    if not _finite(rate, correlation, dt):
        raise ValueError("rate, correlation and dt must be finite numbers")
    if sigma1 <= 0 or sigma2 <= 0:
        raise ValueError("volatilities must be positive")
    if not -1.0 <= correlation <= 1.0:
        raise ValueError("correlation must lie in [-1, 1]")
    if dt <= 0:
        raise ValueError("dt must be positive")
    m1 = (rate - q1 - sigma1**2 / 2) * dt
    m2 = (rate - q2 - sigma2**2 / 2) * dt
    shock1, shock2 = sigma1 * math.sqrt(dt), sigma2 * math.sqrt(dt)
    if method == "transform":
        scale = (sigma1 * sigma2) ** 2 * dt
        h1, p1 = _binomial(sigma2 * m1 + sigma1 * m2, 2 * (1 + correlation) * scale)
        h2, p2 = _binomial(sigma2 * m1 - sigma1 * m2, 2 * (1 - correlation) * scale)
        return TwoAssetLattice(
            method=method,
            dt=dt,
            drift=(0.0, 0.0),
            j_move=(h1 / (2 * sigma2), h1 / (2 * sigma1)),
            k_move=(h2 / (2 * sigma2), -h2 / (2 * sigma1)),
            probabilities=(p1 * p2, p1 * (1 - p2), (1 - p1) * p2, (1 - p1) * (1 - p2)),
        )
    if method == "rubinstein":
        return TwoAssetLattice(
            method=method,
            dt=dt,
            drift=(m1, m2),
            j_move=(shock1, correlation * shock2),
            k_move=(0.0, math.sqrt(1 - correlation**2) * shock2),
            probabilities=(0.25, 0.25, 0.25, 0.25),
        )
    same, opposite = 0.25 * (1 + correlation), 0.25 * (1 - correlation)
    return TwoAssetLattice(
        method=method,
        dt=dt,
        drift=(m1, m2),
        j_move=(shock1, 0.0),
        k_move=(0.0, shock2),
        probabilities=(same, opposite, opposite, same),
    )


def two_asset_tree(
    spots: tuple[float, float],
    payoff: Callable[[np.ndarray, np.ndarray], np.ndarray],
    rate: float,
    volatilities: tuple[float, float],
    correlation: float,
    maturity: float,
    steps: int,
    *,
    method: str = "adjusted",
    exercise: str = "european",
    dividend_yields: tuple[float, float] = (0.0, 0.0),
) -> TwoAssetTree:
    """Price an option on two correlated assets on a three-dimensional tree (Hull §27.7).

    ``payoff(s1, s2)`` receives two equal-shape arrays of node prices and returns
    the exercise value at each node. It is applied at maturity and, for
    ``exercise="american"``, at every earlier node. The lattice is
    :func:`two_asset_lattice` with ``dt = maturity / steps``; the tree at step
    ``n`` has ``(n + 1)^2`` nodes, so the cost grows with ``steps^3``.
    """
    s1, s2 = _pair(spots, "spots")
    if s1 <= 0 or s2 <= 0:
        raise ValueError("spots must be positive")
    if not callable(payoff):
        raise ValueError("payoff must be callable as payoff(s1, s2)")
    if exercise not in _EXERCISES:
        raise ValueError(f"exercise must be one of {_EXERCISES}, got {exercise!r}")
    if not _finite(maturity) or maturity <= 0:
        raise ValueError("maturity must be a positive finite number")
    if isinstance(steps, bool) or not isinstance(steps, int) or steps < 1:
        raise ValueError("steps must be a positive integer")
    if not _finite(rate):
        raise ValueError("rate must be finite")
    lattice = two_asset_lattice(
        rate,
        volatilities,
        correlation,
        maturity / steps,
        method=method,
        dividend_yields=dividend_yields,
    )
    base = (math.log(s1), math.log(s2))

    def exercise_value(step):
        levels = np.arange(-step, step + 1, 2)
        j, k = np.meshgrid(levels, levels, indexing="ij")
        prices = [
            np.exp(start + step * drift + j * a + k * b)
            for start, drift, a, b in zip(
                base, lattice.drift, lattice.j_move, lattice.k_move, strict=True
            )
        ]
        value = np.asarray(payoff(*prices), dtype=float)
        if value.shape != j.shape:
            raise ValueError(f"payoff must return an array of shape {j.shape}, got {value.shape}")
        if not np.all(np.isfinite(value)):
            raise ValueError("payoff must return finite values")
        return value

    p_uu, p_ud, p_du, p_dd = lattice.probabilities
    discount = math.exp(-rate * lattice.dt)
    values = exercise_value(steps)
    for step in range(steps - 1, -1, -1):
        values = discount * (
            p_uu * values[1:, 1:]
            + p_ud * values[1:, :-1]
            + p_du * values[:-1, 1:]
            + p_dd * values[:-1, :-1]
        )
        if exercise == "american":
            values = np.maximum(values, exercise_value(step))
    return TwoAssetTree(
        price=float(values[0, 0]),
        method=method,
        exercise=exercise,
        steps=steps,
        lattice=lattice,
    )
