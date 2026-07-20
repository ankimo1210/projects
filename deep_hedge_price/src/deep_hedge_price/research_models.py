"""Opt-in local research adapters; never used by the core release path."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import torch
from torch import nn


class DirectInverseNetwork(nn.Module):
    """Ablation-only direct quote-to-parameter network."""

    research_only = True

    def __init__(self, n_quotes: int, n_parameters: int, hidden: int = 32):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(n_quotes, hidden),
            nn.SiLU(),
            nn.Linear(hidden, hidden),
            nn.SiLU(),
            nn.Linear(hidden, n_parameters),
        )

    def forward(self, quotes: torch.Tensor) -> torch.Tensor:
        """Map a quote vector directly to model parameters."""
        return self.network(quotes)


class LocalFoundationAdapter:
    """Wrap a caller-supplied local zero-shot model without download logic."""

    research_only = True

    def __init__(self, predict: Callable[[np.ndarray], np.ndarray] | None):
        if predict is None:
            raise RuntimeError("foundation model is disabled; provide an explicit local adapter")
        self._predict = predict

    def predict(self, context: np.ndarray) -> np.ndarray:
        """Run the wrapped local zero-shot model on a context array."""
        return np.asarray(self._predict(np.asarray(context, dtype=float)), dtype=float)


def conditional_diffusion_scenarios(
    condition: np.ndarray,
    *,
    horizon: int,
    n_scenarios: int,
    denoising_steps: int = 20,
    seed: int = 0,
) -> np.ndarray:
    """Small local Gaussian denoising baseline for scenario diagnostics."""
    history = np.asarray(condition, dtype=float)
    if history.ndim != 1 or len(history) < 3 or min(horizon, n_scenarios, denoising_steps) <= 0:
        raise ValueError("invalid diffusion scenario configuration")
    rng = np.random.default_rng(seed)
    level = float(history[-1])
    scale = float(np.std(np.diff(history))) or 1e-6
    scenarios = rng.normal(level, scale * np.sqrt(horizon), size=(n_scenarios, horizon))
    for step in range(denoising_steps, 0, -1):
        weight = 1 / (step + 1)
        scenarios[:, 0] = (1 - weight) * scenarios[:, 0] + weight * level
        scenarios[:, 1:] = (1 - weight) * scenarios[:, 1:] + weight * scenarios[:, :-1]
    return scenarios


def scenario_hard_check_rate(
    scenarios: np.ndarray,
    hard_check: Callable[[np.ndarray], bool],
) -> float:
    """Report scenario validity separately from point-forecast metrics."""
    values = np.asarray(scenarios, dtype=float)
    if values.ndim < 2:
        raise ValueError("scenarios must have a scenario axis")
    return float(np.mean([bool(hard_check(scenario)) for scenario in values]))
