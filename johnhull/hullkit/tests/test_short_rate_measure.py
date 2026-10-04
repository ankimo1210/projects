"""§31.3 Hull P/Q sign convention, Gaussian tilt and bond return PDE."""

import importlib
import math

import numpy as np
import pytest
from hullkit._short_rate_models import cir_bond, mean_reversion_loading, vasicek_bond
from scipy.integrate import quad


def model():
    return importlib.import_module("hullkit._short_rate_measure")


@pytest.mark.parametrize(
    "which,a,b,s,risk",
    [
        ("vasicek", 0.15, 0.025, 0.012, -0.2),
        ("cir", 0.1, 0.03, 0.07, -1.0),
        ("cir", 0.1, 0, 0.07, 0.5),
        ("vasicek", 0, 0.03, 0.01, -0.2),
    ],
)
def test_affine_drift_roundtrip_and_coefficient_identity(which, a, b, s, risk):
    changed = model().short_rate_measure_change(which, a, a * b, s, risk, "q_to_p")
    back = model().short_rate_measure_change(
        which, changed["a"], changed["constant_drift"], s, risk, "p_to_q"
    )
    assert back["a"] == pytest.approx(a, abs=1e-14)
    assert back["constant_drift"] == pytest.approx(a * b, abs=1e-14)
    rates = np.array([0, 0.01, 0.04, 0.2])
    old = a * b - a * rates
    new = changed["constant_drift"] - changed["a"] * rates
    expected = risk * s * (rates if which == "cir" else np.ones(4))
    assert new - old == pytest.approx(expected, abs=1e-14)
    if changed["a"] == 0:
        assert changed["b"] is None  # no division by zero


@pytest.mark.parametrize("a", [0, 0.15])
def test_vasicek_physical_expectation_matches_independent_gaussian_tilt_and_raw_mc(a):
    m = model()
    r0 = 0.04
    bq = 0.025
    s = 0.012
    lam = -0.2
    T = 3
    changed = m.short_rate_measure_change("vasicek", a, a * bq, s, lam)
    B = mean_reversion_loading(a, T)
    B2 = mean_reversion_loading(2 * a, T)
    qmean = bq + (r0 - bq) * math.exp(-a * T)
    pmean = qmean + lam * s * B
    cov = s * B
    variance = s * s * B2

    def conditional_r(z):
        return qmean + cov / math.sqrt(T) * z

    integral = quad(
        lambda z: (
            math.exp(lam * math.sqrt(T) * z - 0.5 * lam * lam * T)
            * conditional_r(z)
            * math.exp(-z * z / 2)
            / math.sqrt(2 * math.pi)
        ),
        -11,
        11,
        epsabs=1e-13,
    )[0]
    expected = r0 if a == 0 else r0 * math.exp(-a * T)
    expected += changed["constant_drift"] * B
    assert expected == pytest.approx(pmean, abs=1e-14)
    assert expected == pytest.approx(integral, abs=1e-13)
    rng = np.random.default_rng(3132026)
    z = rng.standard_normal((2, 131072))
    W = math.sqrt(T) * z[0]
    rT = qmean + cov / T * W + math.sqrt(max(variance - cov * cov / T, 0)) * z[1]
    density = np.exp(lam * W - 0.5 * lam * lam * T)
    for samples, target in [(density, 1), (density * rT, pmean)]:
        se = samples.std(ddof=1) / math.sqrt(samples.size)
        assert abs(samples.mean() - target) <= 5 * se


@pytest.mark.parametrize("which", ["vasicek", "cir"])
def test_physical_bond_excess_return_matches_independent_generator_derivatives(which):
    rate = 0.04
    a = 0.1
    b = 0.03
    s = 0.01 if which == "vasicek" else 0.07
    risk = -0.6
    T = 5
    h = 1e-4
    f = vasicek_bond if which == "vasicek" else cir_bond
    row = f(rate, a, b, s, T)
    p = row["price"]
    vt = -(f(rate, a, b, s, T + h)["price"] - f(rate, a, b, s, T - h)["price"]) / (2 * h)
    vr = (f(rate + h, a, b, s, T)["price"] - f(rate - h, a, b, s, T)["price"]) / (2 * h)
    vrr = (f(rate + h, a, b, s, T)["price"] - 2 * p + f(rate - h, a, b, s, T)["price"]) / h**2
    changed = model().short_rate_measure_change(which, a, a * b, s, risk)
    drift = changed["constant_drift"] - changed["a"] * rate
    diffusion = s if which == "vasicek" else s * math.sqrt(rate)
    p_return = (vt + drift * vr + 0.5 * diffusion**2 * vrr) / p
    assert model().physical_bond_return(which, rate, s, row["B"], risk) == pytest.approx(
        p_return, abs=1e-9
    )
    assert p_return > rate


def test_cir_local_state_dependent_risk_price_matches_independent_gaussian_one_step_tilt():
    r = 0.04
    a = 0.1
    b = 0.03
    s = 0.07
    k = -1
    dt = 0.01
    changed = model().short_rate_measure_change("cir", a, a * b, s, k)
    mean = r + (changed["constant_drift"] - changed["a"] * r) * dt
    lam = k * math.sqrt(r)
    qmean = r + a * (b - r) * dt
    sd = s * math.sqrt(r * dt)
    integral = quad(
        lambda z: (
            math.exp(lam * math.sqrt(dt) * z - 0.5 * lam * lam * dt)
            * (qmean + sd * z)
            * math.exp(-z * z / 2)
            / math.sqrt(2 * math.pi)
        ),
        -11,
        11,
        epsabs=1e-13,
    )[0]
    assert mean == pytest.approx(integral, abs=1e-13)
    # This verifies local drift, not a full continuous-path CIR density claim.


def test_invalid_model_and_direction_rejected():
    with pytest.raises(ValueError):
        model().short_rate_measure_change("vasicek", 0.1, 0.003, 0.01, -0.2, "wrong")
    with pytest.raises(ValueError):
        model().short_rate_measure_change("wrong", 0.1, 0.003, 0.01, -0.2)
