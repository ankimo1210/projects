"""§30.3 original quanto prices, raw currency density and independent PDE."""

import importlib
import math

import numpy as np
import pytest
from scipy.integrate import quad


def model():
    return importlib.import_module("hullkit._quanto")


def pde_call(S, K, r, q, sigma, T, M):
    smax = 4800.0
    dx = smax / M
    nt = math.ceil(T * (sigma * sigma * M * M + r) / 0.8)
    dt = T / nt
    i = np.arange(1, M)
    a = 0.5 * dt * (sigma * sigma * i * i - (r - q) * i)
    b = 1 - dt * (sigma * sigma * i * i + r)
    c = 0.5 * dt * (sigma * sigma * i * i + (r - q) * i)
    assert min(a.min(), b.min(), c.min()) >= 0
    grid = np.arange(M + 1) * dx
    payoff = np.maximum(grid - K, 0)
    v = payoff.copy()
    for _ in range(nt):
        v[1:-1] = np.maximum(a * v[:-2] + b * v[1:-1] + c * v[2:], payoff[1:-1])
        v[0] = 0
        v[-1] = smax - K
    return float(np.interp(S, grid, v))


def test_examples_30_3_and_30_4_printed_inputs_outputs():
    foreign = 15000 * math.exp((0.02 - 0.01) * 1)
    assert foreign == pytest.approx(15150.75, abs=0.005)
    assert model().quanto_forward(foreign, 0.2, 0.12, 0.3, 1) == pytest.approx(15260.23, abs=0.005)
    q = model().quanto_effective_yield(0.05, 0.03, 0.015, 0.25, 0.12, 0.2)
    assert q == pytest.approx(0.029, abs=1e-14)
    assert 0.05 - q - (0.03 - 0.015) == pytest.approx(0.006, abs=1e-14)
    american = model().quanto_option_price(
        1200, 1200, 0.05, 0.03, 0.015, 0.25, 0.12, 0.2, 2, american=True, steps=100
    )
    assert american == pytest.approx(179.83, abs=0.005)


def test_american_independent_monotone_pde_and_tree_converge():
    def price(n):
        return model().quanto_option_price(
            1200, 1200, 0.05, 0.03, 0.015, 0.25, 0.12, 0.2, 2, american=True, steps=n
        )

    q = 0.029
    coarse, fine = [pde_call(1200, 1200, 0.05, q, 0.25, 2, m) for m in [400, 800]]
    assert coarse == pytest.approx(180.20956, abs=0.00001)
    assert fine == pytest.approx(180.22000, abs=0.00001)
    assert abs(price(3200) - fine) < 0.015
    assert abs(price(1600) - fine) < 0.04
    euro100 = model().quanto_option_price(
        1200, 1200, 0.05, 0.03, 0.015, 0.25, 0.12, 0.2, 2, american=False, steps=100, method="tree"
    )
    continuous = model().quanto_option_price(1200, 1200, 0.05, 0.03, 0.015, 0.25, 0.12, 0.2, 2)
    assert price(100) >= euro100  # same grid lower bound
    assert price(100) < continuous  # coarse grid error, not an arbitrage claim
    assert fine > continuous


@pytest.mark.parametrize("rho", [-1.0, -0.5, 0.0, 0.3, 1.0])
def test_forward_and_european_payoff_match_raw_foreign_density_integral_and_mc(rho):
    S = 1200
    K = 1230
    T = 1.5
    rx = 0.05
    ry = 0.03
    qy = 0.015
    sigma = 0.25
    fx = 0.12
    fY = S * math.exp((ry - qy) * T)
    expected = model().quanto_forward(fY, sigma, fx, rho, T)
    w = sigma * math.sqrt(T)
    threshold = (math.log(K / fY) + w * w / 2) / w

    def density_cond(z):
        return math.exp(rho * fx * math.sqrt(T) * z - 0.5 * (rho * fx) ** 2 * T)

    def normal(z):
        return math.exp(-z * z / 2) / math.sqrt(2 * math.pi)

    integral = (
        math.exp(-rx * T)
        * quad(
            lambda z: density_cond(z) * max(fY * math.exp(-w * w / 2 + w * z) - K, 0) * normal(z),
            threshold,
            12,
            epsabs=1e-10,
        )[0]
    )
    price = model().quanto_option_price(S, K, rx, ry, qy, sigma, fx, rho, T)
    assert price == pytest.approx(integral, rel=1e-11, abs=1e-10)
    rng = np.random.default_rng(3032026)
    z = rng.standard_normal((2, 262144))
    stock = fY * np.exp(-0.5 * w * w + w * z[0])
    Wfx = math.sqrt(T) * (rho * z[0] + math.sqrt(1 - rho * rho) * z[1])
    density = model().quanto_measure_density(Wfx, fx, T)
    for samples, target in [
        (density, 1),
        (density * stock, expected),
        (math.exp(-rx * T) * density * np.maximum(stock - K, 0), price),
    ]:
        se = np.std(samples, ddof=1) / math.sqrt(samples.size)
        assert abs(samples.mean() - target) <= 5 * se + 1e-10


def test_siegel_inverse_fx_drift_ito_and_measure_change_are_distinct():
    row = model().inverse_fx_drifts(0.02, 0.05, 0.12)
    assert row["inverse_old_measure"] == pytest.approx(0.05 - 0.02 + 0.12**2, abs=1e-14)
    assert row["inverse_new_measure"] == pytest.approx(0.05 - 0.02, abs=1e-14)
    S0 = 100
    T = 1

    def price(z):
        return S0 * math.exp((0.02 - 0.05 - 0.5 * 0.12**2) * T + 0.12 * math.sqrt(T) * z)

    def mean(f):
        return quad(lambda z: f(z) * math.exp(-z * z / 2) / math.sqrt(2 * math.pi), -11, 11)[0]

    old = mean(lambda z: 1 / price(z))
    new = mean(lambda z: math.exp(0.12 * z - 0.5 * 0.12**2) / price(z))
    assert old == pytest.approx(math.exp(row["inverse_old_measure"] * T) / S0, rel=1e-12)
    assert new == pytest.approx(math.exp(row["inverse_new_measure"] * T) / S0, rel=1e-12)
    assert old != pytest.approx(1 / mean(price), rel=1e-3)
    assert new == pytest.approx(1 / mean(price), rel=1e-12)


def test_zero_time_zero_vol_and_invalid_domain():
    assert model().quanto_option_price(
        1200, 1000, 0.05, 0.03, 0.015, 0.25, 0.12, 0.2, 0
    ) == pytest.approx(200)
    assert (
        model().quanto_option_price(1200, 1000, 0.05, 0.03, 0.015, 0, 0.12, 0.2, 2, american=True)
        > 200
    )
    with pytest.raises(ValueError):
        model().quanto_forward(1200, 0.2, 0.12, 1.1, 1)
