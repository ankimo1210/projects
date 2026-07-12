"""Tests for Monte Carlo option prices and implied-volatility tables."""

import numpy as np
from rough_volatility.black_scholes import call_price
from rough_volatility.option_pricing import (
    mc_call_prices,
    smile_from_terminals,
    surface_from_terminals,
)


def _gbm_terminal(seed: int, n_paths: int, maturity: float, sigma: float) -> np.ndarray:
    rng = np.random.default_rng(seed)
    half = n_paths // 2
    z = rng.standard_normal(half)
    z = np.r_[z, -z]
    return 100.0 * np.exp(-0.5 * sigma**2 * maturity + sigma * np.sqrt(maturity) * z)


def test_gbm_monte_carlo_call_is_within_five_standard_errors() -> None:
    terminal = _gbm_terminal(60, 200_000, 0.75, 0.2)
    prices, standard_errors = mc_call_prices(terminal, 100.0, np.array([0.0]), maturity=0.75)
    reference = call_price(100.0, 100.0, 0.75, 0.2)
    assert abs(prices[0] - reference) < 5 * standard_errors[0]


def test_monte_carlo_put_call_parity_within_sampling_error() -> None:
    terminal = _gbm_terminal(61, 200_000, 1.0, 0.3)
    strike = 110.0
    call_payoff = np.maximum(terminal - strike, 0.0)
    put_payoff = np.maximum(strike - terminal, 0.0)
    difference = call_payoff - put_payoff
    error = difference.std(ddof=1) / np.sqrt(difference.size)
    assert abs((call_payoff.mean() - put_payoff.mean()) - (100.0 - strike)) < 5 * error


def test_smile_recovers_flat_gbm_volatility_and_uncertainty() -> None:
    terminal = _gbm_terminal(62, 300_000, 0.5, 0.25)
    smile = smile_from_terminals(
        terminal,
        100.0,
        np.linspace(-0.15, 0.15, 7),
        maturity=0.5,
    )
    assert list(smile.columns) == ["k", "price", "price_se", "iv", "iv_se", "ok"]
    assert smile["ok"].all()
    assert np.max(np.abs(smile["iv"] - 0.25)) < 0.006
    assert (smile["iv_se"] > 0).all()


def test_surface_combines_maturities() -> None:
    terminals = {
        0.25: _gbm_terminal(63, 50_000, 0.25, 0.2),
        1.00: _gbm_terminal(64, 50_000, 1.00, 0.2),
    }
    surface = surface_from_terminals(terminals, 100.0, [-0.1, 0.0, 0.1])
    assert set(surface["maturity"]) == {0.25, 1.0}
    assert len(surface) == 6


def test_degenerate_terminal_distribution_flags_failed_inversions() -> None:
    smile = smile_from_terminals(np.full(100, 100.0), 100.0, [-0.1, 0.0, 0.1], maturity=1.0)
    assert not smile["ok"].all()
    assert smile.loc[~smile["ok"], "iv"].isna().all()
