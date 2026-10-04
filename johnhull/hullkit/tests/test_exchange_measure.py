"""Hull §28.7 ratio pricing, income, independent quadrature and raw Q MC."""

import importlib
import math

import numpy as np
import pytest
from scipy.integrate import quad

CASES = [
    (0.2, 0.2, 0.5, 0.0, 0.0, 1.0),
    (0.2, 0.2, 0.0, 0.0, 0.0, 1.0),
    (0.25, 0.25, 0.5, 0.06, 0.0, 1.5),
    (0.25, 0.25, 0.5, 0.0, 0.06, 1.5),
    (0.15, 0.45, 0.3, 0.02, 0.0, 2.0),
    (0.2, 0.2, 1.0, 0.0, 0.0, 1.0),
    (0.2, 0.2, -1.0, 0.0, 0.0, 1.0),
    (0.15, 0.45, 1.0, 0.0, 0.02, 2.0),
    (0.0, 0.25, 0.3, 0.01, 0.03, 1.0),
    (0.25, 0.0, 0.3, 0.01, 0.03, 1.0),
    (0.0, 0.0, 0.3, 0.01, 0.03, 1.0),
]


def model():
    return importlib.import_module("hullkit._exchange_measure")


def ratio_integral(U, V, su, sv, rho, qu, qv, t):
    variance = (su * su + sv * sv - 2 * rho * su * sv) * t
    m = math.log(V / U) + (qu - qv) * t - variance / 2
    scale = math.sqrt(max(variance, 0))
    if scale == 0:
        return U * math.exp(-qu * t) * max(math.exp(m) - 1, 0)
    boundary = -m / scale
    return (
        U
        * math.exp(-qu * t)
        * quad(
            lambda z: (
                max(math.exp(m + scale * z) - 1, 0) * math.exp(-z * z / 2) / math.sqrt(2 * math.pi)
            ),
            max(boundary, -12),
            12,
            epsabs=1e-10,
            epsrel=1e-11,
        )[0]
    )


@pytest.mark.parametrize("ratio", [0.8, 1.0, 1.25])
@pytest.mark.parametrize("su,sv,rho,qu,qv,t", CASES)
def test_original_equations_2830_to_2832_against_independent_ratio_integral(
    ratio, su, sv, rho, qu, qv, t
):
    U, V = 100.0, 100 * ratio
    actual = model().exchange_measure_price(U, V, su, sv, rho, t, qu, qv)
    expected = ratio_integral(U, V, su, sv, rho, qu, qv, t)
    assert actual == pytest.approx(expected, abs=1e-9, rel=1e-10)
    from hullkit.exotics import exchange_option

    assert actual == pytest.approx(exchange_option(U, V, su, sv, rho, t, qu, qv), abs=1e-9)


def test_existing_section_2614_reference_and_zero_ratio_variance():
    assert model().exchange_measure_price(100, 100, 0.2, 0.2, 0.5, 1) == pytest.approx(
        7.965567455405804, abs=1e-10
    )
    assert model().exchange_measure_price(100, 125, 0.2, 0.2, 1.0, 1) == pytest.approx(25.0)
    assert model().exchange_measure_price(100, 125, 0.2, 0.2, 1.0, 0) == pytest.approx(25.0)


@pytest.mark.parametrize("r,eta", [(0.0, 0.0), (0.08, 0.0), (-0.02, 0.0), (0.04, 0.03)])
def test_same_payoff_price_under_q_stochastic_discount_and_given_asset_measure(r, eta):
    U, V, su, sv, rho, qu, qv, t = 100.0, 110.0, 0.25, 0.3, 0.4, 0.06, 0.02, 1.5
    n = 262144
    z = np.random.default_rng(287320).standard_normal((n, 4))
    wu = math.sqrt(t) * z[:, 0]
    wv = math.sqrt(t) * (rho * z[:, 0] + math.sqrt(1 - rho * rho) * z[:, 1])
    wr = math.sqrt(t) * (0.25 * z[:, 0] - 0.3 * z[:, 1] + math.sqrt(1 - 0.25**2 - 0.3**2) * z[:, 2])
    J = r * t + eta * (t / 2 * wr + math.sqrt(t**3 / 12) * z[:, 3])
    u = U * np.exp(J - qu * t - 0.5 * su * su * t + su * wu)
    v = V * np.exp(J - qv * t - 0.5 * sv * sv * t + sv * wv)
    values = np.exp(-J) * np.maximum(v - u, 0)
    exact = ratio_integral(U, V, su, sv, rho, qu, qv, t)
    se = values.std(ddof=1) / math.sqrt(n)
    assert abs(values.mean() - exact) <= 5 * se
    density = model().exchange_numeraire_density(u, U, J, t, qu)
    se_density = density.std(ddof=1) / math.sqrt(n)
    assert abs(density.mean() - 1) <= 5 * se_density
    means = model().exchange_ratio_statistics(V / U, su, sv, rho, t, qu, qv)
    assert means["mean_given"] == pytest.approx(V / U * math.exp((qu - qv) * t))
    assert abs(np.mean(density * v / u) - means["mean_given"]) <= 5 * np.std(
        density * v / u, ddof=1
    ) / math.sqrt(n)


def test_conditional_means_keep_q_drift_and_given_measure_distinct():
    row = model().exchange_ratio_statistics(1.1, 0.2, 0.3, 0.4, 1.5, 0.06, 0.02)
    assert row["relative_drift_given"] == pytest.approx(0.04)
    assert row["relative_drift_Q"] == pytest.approx(0.056)
    assert row["spread_variance"] == pytest.approx(0.082)
    assert row["mean_Q"] == pytest.approx(1.1 * math.exp(0.056 * 1.5))


@pytest.mark.parametrize(
    "args",
    [
        (0, 100, 0.2, 0.2, 0.5, 1),
        (100, 100, -0.2, 0.2, 0.5, 1),
        (100, 100, 0.2, 0.2, 1.1, 1),
        (100, 100, 0.2, 0.2, 0.5, -1),
    ],
)
def test_undefined_exchange_inputs_rejected(args):
    with pytest.raises(ValueError):
        model().exchange_measure_price(*args)
