"""Hull §29.1 printed examples, independent lognormal integration and OU variance."""

import importlib
import math

import numpy as np
import pytest
from scipy.integrate import quad


def model():
    return importlib.import_module("hullkit._bond_market")


def payoff_integral(p, F, K, sigma, T, kind):
    w = sigma * math.sqrt(T)
    if w == 0:
        return p * max(F - K if kind == "call" else K - F, 0)
    boundary = (math.log(K / F) + w * w / 2) / w
    sign = 1 if kind == "call" else -1
    lo, hi = (max(boundary, -12), 12) if sign == 1 else (-12, min(boundary, 12))
    return (
        p
        * quad(
            lambda z: (
                max(sign * (F * math.exp(-w * w / 2 + w * z) - K), 0)
                * math.exp(-z * z / 2)
                / math.sqrt(2 * math.pi)
            ),
            lo,
            hi,
            epsabs=1e-11,
        )[0]
    )


def test_example_291_printed_cash_and_quoted_strikes_and_independent_price():
    m = model()
    T = 10 / 12
    p = math.exp(-0.1 * T)
    coupons = [50 * math.exp(-0.09 * 0.25), 50 * math.exp(-0.095 * 0.75)]
    F = m.cash_bond_forward(960, coupons, p)
    assert sum(coupons) == pytest.approx(95.45, abs=0.005)
    assert F == pytest.approx(939.68, abs=0.005)
    assert p == pytest.approx(0.9200, abs=0.00005)
    assert m.bond_clean_price(960, 25) == pytest.approx(935.0)
    strike = m.cash_bond_strike(1000, 100 / 12)
    assert strike == pytest.approx(1008.33, abs=0.005)
    for K, printed in [(1000, 9.49), (strike, 7.97)]:
        value = m.cash_bond_option(p, F, K, 0.09, T, "call")
        assert value == pytest.approx(printed, abs=0.005)
        assert value == pytest.approx(payoff_integral(p, F, K, 0.09, T, "call"), abs=1e-10)


def test_example_292_half_year_yield_and_modified_duration_reproduce_both_prices():
    m = model()
    expiry = 2.25
    times = np.arange(0.5, 10.001, 0.5)
    cash = np.full(len(times), 4.0)
    cash[-1] += 100
    spot = float(np.sum(cash * np.exp(-0.05 * times)))
    before = times < expiry
    p = math.exp(-0.05 * expiry)
    forward = m.cash_bond_forward(spot, cash[before] * np.exp(-0.05 * times[before]), p)
    t = times[~before] - expiry
    remaining = cash[~before]
    row = m.forward_yield_duration(forward, t, remaining, 2)
    exact_y = 2 * math.expm1(0.05 / 2)
    assert row["forward_yield"] == pytest.approx(exact_y, abs=1e-13)
    h = 1e-5

    def pv(y):
        return np.sum(remaining * (1 + y / 2) ** (-2 * t))

    modified = -(pv(exact_y + h) - pv(exact_y - h)) / (2 * h * forward)
    assert row["modified_duration"] == pytest.approx(modified, rel=1e-8)
    assert spot == pytest.approx(122.82, abs=0.005)
    assert forward == pytest.approx(120.6226, abs=0.00005)
    sigma = m.bond_price_volatility(row["modified_duration"], row["forward_yield"], 0.2)
    assert sigma == pytest.approx(0.05920, abs=0.000005)
    for K, printed in [(m.cash_bond_strike(115, 2), 2.36), (115, 1.74)]:
        value = m.cash_bond_option(p, forward, K, sigma, expiry, "put")
        assert value == pytest.approx(printed, abs=0.005)
        assert value == pytest.approx(
            payoff_integral(p, forward, K, sigma, expiry, "put"), abs=1e-10
        )
    assert m.bond_price_volatility(5, 0.08, 0.2) == pytest.approx(0.08)


@pytest.mark.parametrize("a", [0.0, 0.15])
def test_schematic_291_292_gaussian_model_variance_and_fixed_seed_ou(a):
    m = model()
    T = np.linspace(0, 10, 21)
    row = m.gaussian_bond_volatility(T, 10, a, 0.02)
    assert row["log_price_sd"][0] == 0 and row["log_price_sd"][-1] == 0
    assert np.max(row["log_price_sd"]) > 0
    assert np.all(np.diff(row["forward_price_volatility"]) <= 1e-12)
    t = 3.0
    B = (10 - t) if a == 0 else -math.expm1(-a * (10 - t)) / a
    var_x = 0.02**2 * t if a == 0 else 0.02**2 * (-math.expm1(-2 * a * t)) / (2 * a)
    z = np.random.default_rng(2912026).standard_normal(262144)
    logprice = -B * math.sqrt(var_x) * z
    expected = m.gaussian_bond_volatility(t, 10, a, 0.02)["log_price_sd"] ** 2
    squares = logprice**2
    se = squares.std(ddof=1) / math.sqrt(len(z))
    assert abs(squares.mean() - expected) <= 5 * se


@pytest.mark.parametrize(
    "call",
    [
        lambda m: m.cash_bond_forward(100, [110], 0.95),
        lambda m: m.forward_yield_duration(100, [0], [100], 2),
        lambda m: m.cash_bond_option(0.95, 100, 100, 0.2, -1),
        lambda m: m.gaussian_bond_volatility(11, 10, 0.15, 0.02),
    ],
)
def test_undefined_bond_inputs_rejected(call):
    with pytest.raises(ValueError):
        call(model())
