"""Hull §29.3 printed swaption and independent annuity/coupon-bond validation."""

import importlib
import math
from datetime import date

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.optimize import brentq


def model():
    return importlib.import_module("hullkit._swaption_market")


def test_example_294_printed_values_and_independent_payoff_integral():
    from hullkit._cap_floor_market import actual_year_fraction, black_rate_d

    m = model()
    times = np.arange(5.5, 8.001, 0.5)
    discounts = np.exp(-0.06 * times)
    A = m.swap_annuity(np.full(6, 0.5), discounts)
    F = 2 * math.expm1(0.061 / 2)
    assert A == pytest.approx(2.0035, abs=0.0001)  # book truncates this intermediate value
    assert F == pytest.approx(0.06194, abs=0.000005)
    d1, d2 = black_rate_d(F, 0.062, 0.2, 5)
    assert d1 == pytest.approx(0.2214, abs=0.00005)
    assert d2 == pytest.approx(-0.2258, abs=0.00005)
    payer = m.swaption_market_price(1e8, A, F, 0.062, 0.2, 5)
    receiver = m.swaption_market_price(1e8, A, F, 0.062, 0.2, 5, "receiver")
    assert payer / 1e6 == pytest.approx(2.19, abs=0.005)
    w = 0.2 * math.sqrt(5)
    boundary = (math.log(0.062 / F) + w * w / 2) / w
    oracle = (
        1e8
        * A
        * quad(
            lambda z: (
                max(F * math.exp(-w * w / 2 + w * z) - 0.062, 0)
                * math.exp(-z * z / 2)
                / math.sqrt(2 * math.pi)
            ),
            boundary,
            12,
            epsabs=1e-13,
        )[0]
    )
    assert payer == pytest.approx(oracle, abs=1e-7, rel=1e-11)
    assert payer - receiver == pytest.approx(1e8 * A * (F - 0.062), abs=1e-7)
    assert actual_year_fraction(date(2026, 3, 1), date(2026, 9, 1), 365) == pytest.approx(
        0.5041, abs=0.00005
    )


@pytest.mark.parametrize("family", ["black", "normal", "shifted"])
@pytest.mark.parametrize("kind", ["payer", "receiver"])
def test_negative_rate_models_and_independent_terminal_distribution(family, kind):
    m = model()
    F = 0.03 if family == "black" else -0.005
    K = 0.025 if family == "black" else -0.002
    shift = 0.03 if family == "shifted" else 0.0
    sig = 0.008 if family == "normal" else 0.25
    T = 1.5
    w = sig * math.sqrt(T)
    sign = 1 if kind == "payer" else -1
    if family == "normal":
        root = (K - F) / w

        def value(z):
            return F + w * z
    else:
        root = (math.log((K + shift) / (F + shift)) + w * w / 2) / w

        def value(z):
            return (F + shift) * math.exp(-w * w / 2 + w * z) - shift

    lo, hi = (root, 12) if kind == "payer" else (-12, root)
    expected = (
        1e6
        * 2.3
        * quad(
            lambda z: max(sign * (value(z) - K), 0) * math.exp(-z * z / 2) / math.sqrt(2 * math.pi),
            lo,
            hi,
            epsabs=1e-13,
        )[0]
    )
    actual = m.swaption_market_price(1e6, 2.3, F, K, sig, T, kind, model=family, shift=shift)
    assert actual == pytest.approx(expected, abs=1e-7, rel=1e-10)


def test_annuity_forward_mean_and_coupon_bond_identity_under_exact_q_discount_mc():
    m = model()
    r0 = 0.04
    eta = 0.012
    T = 1.0
    times = np.array([1.5, 2.0, 2.5, 3.0])
    a = np.full(4, 0.5)
    K = 0.045
    N = 1e6
    P0 = np.exp(-r0 * times + eta * eta * times**3 / 6)
    A0 = float(a @ P0)
    F = (math.exp(-r0 * T + eta * eta * T**3 / 6) - P0[-1]) / A0
    n = 262144
    rng = np.random.default_rng(2026100432)
    z = rng.standard_normal((n, 2))
    rate = r0 + eta * math.sqrt(T) * z[:, 0]
    J = r0 * T + eta * (T**1.5 * z[:, 0] / 2 + math.sqrt(T**3 / 12) * z[:, 1])
    dt = times - T
    B = np.exp(-rate[:, None] * dt + eta * eta * dt**3 / 6)
    AT = m.swap_annuity(a, B)
    S = (1 - B[:, -1]) / AT
    D = np.exp(-J)
    density = m.annuity_numeraire_density(D, AT, A0)
    for x, truth in [(density, 1.0), (density * S, F)]:
        assert abs(x.mean() - truth) <= 5 * x.std(ddof=1) / math.sqrt(n)
    value = m.swaption_coupon_bond_payoff(N, B, a, K)
    assert np.allclose(value, N * AT * np.maximum(S - K, 0), atol=1e-8, rtol=1e-12)

    def payoff(zz):
        r = r0 + eta * math.sqrt(T) * zz
        bonds = np.exp(-r * dt + eta * eta * dt**3 / 6)
        return max(1 - bonds[-1] - K * float(a @ bonds), 0)

    root = brentq(
        lambda zz: float(
            1
            - np.exp(-(r0 + eta * math.sqrt(T) * zz) * dt[-1] + eta * eta * dt[-1] ** 3 / 6)
            - K * np.sum(a * np.exp(-(r0 + eta * math.sqrt(T) * zz) * dt + eta * eta * dt**3 / 6))
        ),
        -12,
        12,
    )
    oracle = (
        N
        * quad(
            lambda zz: (
                math.exp(-r0 * T - 0.5 * T * (eta * math.sqrt(T) * zz) + eta * eta * T**3 / 24)
                * payoff(zz)
                * math.exp(-zz * zz / 2)
                / math.sqrt(2 * math.pi)
            ),
            root,
            12,
            epsabs=1e-12,
        )[0]
    )
    sample = D * value
    assert abs(sample.mean() - oracle) <= 5 * sample.std(ddof=1) / math.sqrt(n)


@pytest.mark.parametrize(
    "call",
    [
        lambda m: m.swap_annuity([0.5], [0]),
        lambda m: m.swaption_market_price(1e6, 2.3, 0.03, 0.04, 0.2, -1),
        lambda m: m.annuity_numeraire_density(0.95, 2.3, 0),
    ],
)
def test_undefined_swaption_inputs_rejected(call):
    with pytest.raises(ValueError):
        call(model())
