"""Synthetic scenarios and sample data for the notebooks — no downloads.

Each scenario bundles parameters + initial condition(s) + a time grid so a
notebook can go from "here is a situation" to "here is its trajectory" in one
line. All randomness is seeded.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Scenario:
    """A ready-to-integrate situation: a time grid, initial state, and metadata."""

    t: np.ndarray
    y0: np.ndarray
    params: dict = field(default_factory=dict)
    name: str = ""


def time_grid(t0: float = 0.0, t1: float = 10.0, n: int = 400) -> np.ndarray:
    """Uniform time grid (the default integration window)."""
    return np.linspace(t0, t1, n)


def fan_initial_conditions(values, t0: float = 0.0, t1: float = 6.0, n: int = 300):
    """A spread of scalar initial conditions sharing one time grid.

    Useful for drawing a fan of solution curves over a direction field.
    """
    return time_grid(t0, t1, n), np.asarray(values, dtype=float)


def logistic_scenario() -> Scenario:
    """Logistic growth crossing, sitting at, and starting above carrying capacity."""
    return Scenario(
        t=time_grid(0, 12, 400),
        y0=np.array([0.1, 0.5, 1.0, 1.7]),  # several starting populations (units of K)
        params={"r": 0.9, "K": 1.0},
        name="logistic growth",
    )


def harmonic_scenarios() -> dict[str, Scenario]:
    """Under-, critically-, and over-damped oscillator settings (omega = 1)."""
    grid = time_grid(0, 14, 600)
    y0 = np.array([1.0, 0.0])
    return {
        "undamped": Scenario(grid, y0, {"omega": 1.0, "gamma": 0.0}, "undamped"),
        "underdamped": Scenario(grid, y0, {"omega": 1.0, "gamma": 0.15}, "underdamped"),
        "critical": Scenario(grid, y0, {"omega": 1.0, "gamma": 1.0}, "critical damping"),
        "overdamped": Scenario(grid, y0, {"omega": 1.0, "gamma": 2.0}, "overdamped"),
    }


def lotka_volterra_scenario() -> Scenario:
    """Classic predator-prey parameters with a coexistence equilibrium."""
    return Scenario(
        t=time_grid(0, 24, 1000),
        y0=np.array([2.0, 1.0]),  # prey, predator
        params={"alpha": 1.1, "beta": 0.4, "delta": 0.1, "gamma": 0.4},
        name="Lotka-Volterra",
    )


def sir_scenario() -> Scenario:
    """SIR outbreak with R0 = beta/gamma = 2.5 in a unit population."""
    return Scenario(
        t=time_grid(0, 60, 600),
        y0=np.array([0.99, 0.01, 0.0]),  # S, I, R
        params={"beta": 0.5, "gamma": 0.2, "N": 1.0},
        name="SIR outbreak",
    )


def make_noisy_decay(
    rate: float = 0.7,
    y0: float = 5.0,
    n: int = 40,
    noise: float = 0.15,
    t1: float = 6.0,
    seed: int = 0,
):
    """Noisy samples of exponential decay y0 e^{-rate t} (to fit an ODE to data)."""
    rng = np.random.default_rng(seed)
    t = np.linspace(0, t1, n)
    y = y0 * np.exp(-rate * t) + noise * rng.standard_normal(n)
    return t, y


def load_timeseries(path: str | None = None, seed: int = 0):
    """Bring-your-own-data hook. Returns (t, y).

    Default: a seeded synthetic logistic-with-noise series, so notebooks run
    offline. Pass ``path`` to a 2-column CSV (t, y) to use real data instead.
    """
    if path is not None:
        import pandas as pd

        df = pd.read_csv(path)
        return df.iloc[:, 0].to_numpy(float), df.iloc[:, 1].to_numpy(float)
    rng = np.random.default_rng(seed)
    t = np.linspace(0, 12, 80)
    y = 1.0 / (1.0 + np.exp(-0.9 * (t - 6))) + 0.03 * rng.standard_normal(t.size)
    return t, y
