"""Hull §35.8 regression equations and independent covariance/holdout cash."""

import numpy as np
import pytest
from hullkit import _commodity_foundations as c


def test_independent_normal_equations_and_contract_cash_units():
    price = np.array([1, 2, 3, 4, 5, 6.0])
    temp = np.array([4, 1, 3, 6, 2, 5.0])
    profit = 100 + 2 * price - 3 * temp
    model = c.joint_energy_weather_hedge(profit, price, temp, ticks=[25, 10])
    cov = np.cov(np.vstack([profit, price, temp]), ddof=1)
    reference = np.linalg.solve(cov[1:, 1:], cov[1:, 0])
    assert model["coefficients"] == pytest.approx(reference, abs=1e-12)
    assert model["intercept"] == pytest.approx(100)
    assert model["positions"] == pytest.approx([-2 / 25, 3 / 10])
    actual = c.energy_weather_hedge_cash(
        model, profit, price, temp, energy_entry=3, weather_entry=4
    )
    assert actual == pytest.approx(np.full(6, 100 + 2 * 3 - 3 * 4))
    with pytest.raises(ValueError, match="rank"):
        c.joint_energy_weather_hedge(profit, price, 2 * price)


def test_independent_frozen_hedge_on_new_correlated_factor_sample():
    rng = np.random.default_rng(3538)

    def sample(n):
        P = rng.normal(size=n)
        T = 0.4 * P + np.sqrt(1 - 0.4**2) * rng.normal(size=n)
        Y = 10 + 2 * P - 3 * T + 0.1 * rng.normal(size=n)
        return P, T, Y

    price, temp, profit = sample(1200)
    model = c.joint_energy_weather_hedge(profit, price, temp, ticks=[25, 10])
    assert model["coefficients"] == pytest.approx([2, -3], abs=0.02)
    newP, newT, newY = sample(10000)
    hedged = c.energy_weather_hedge_cash(model, newY, newP, newT, energy_entry=0, weather_entry=0)
    independent = newY - model["coefficients"][0] * newP - model["coefficients"][1] * newT
    assert hedged == pytest.approx(independent, abs=1e-13)
    price_coefficient = np.cov(profit, price, ddof=1)[0, 1] / np.var(price, ddof=1)
    weather_coefficient = np.cov(profit, temp, ddof=1)[0, 1] / np.var(temp, ddof=1)
    assert np.var(hedged) < 0.01 * np.var(newY)
    assert np.var(hedged) < np.var(newY - price_coefficient * newP)
    assert np.var(hedged) < np.var(newY - weather_coefficient * newT)
