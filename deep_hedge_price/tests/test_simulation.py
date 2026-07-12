from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from deep_hedge_price.config import MarketConfig
from deep_hedge_price.simulation import simulate_gbm


def test_shapes_positivity_and_reproducibility():
    config = MarketConfig(n_steps=7)
    first = simulate_gbm(config, 10, seed=123)
    second = simulate_gbm(config, 10, seed=123)
    assert first.shape == (10, 8)
    assert np.all(first.numpy() > 0)
    assert np.array_equal(first.numpy(), second.numpy())
    assert np.all(first[:, 0].numpy() == config.s0)


def test_terminal_mean_matches_exact_gbm_moment():
    config = MarketConfig(antithetic_sampling=True)
    terminal = simulate_gbm(config, 40_000, seed=7)[:, -1].double().numpy()
    expected = config.s0 * math.exp(config.mu * config.maturity_years)
    assert abs(terminal.mean() - expected) < 0.12


def test_antithetic_pairs_cancel_shocks():
    config = replace(MarketConfig(), n_steps=3, antithetic_sampling=True)
    paths = simulate_gbm(config, 8, seed=99).double()
    increments = np.diff(np.log(paths.numpy()), axis=1)
    drift = (config.mu - 0.5 * config.volatility**2) * config.dt
    assert np.allclose(increments[:4] + increments[4:], 2 * drift, atol=2e-7)
