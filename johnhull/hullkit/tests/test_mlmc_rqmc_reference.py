"""Independent GBM references for the RB-F08 synthetic research."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest
from hullkit.bsm import call_price
from scipy.integrate import quad
from scipy.special import ndtri


def reference():
    path = Path(__file__).resolve().parents[2] / "research/RB-F08/reference_methods.py"
    spec = importlib.util.spec_from_file_location("rbf08_reference", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def parameters():
    return dict(spot=100.0, strike=100.0, rate=0.03, sigma=0.2, maturity=1.0, yield_rate=0.02)


@pytest.mark.parametrize("strike", [80.0, 100.0, 120.0])
@pytest.mark.parametrize("q", [0.0, 0.02])
@pytest.mark.parametrize("sigma", [0.0, 0.2, 0.7])
def test_black_own_erf_reference_matches_existing_formula(parameters, strike, q, sigma):
    p = dict(parameters, strike=strike, yield_rate=q, sigma=sigma)
    expected = call_price(p["spot"], strike, p["rate"], sigma, p["maturity"], q=q)
    assert reference().black_call(p) == pytest.approx(expected, rel=1e-12, abs=1e-11)


@pytest.mark.parametrize("sigma", [0.0, 0.2, 0.7])
def test_one_step_euler_closed_form_matches_normal_integral(parameters, sigma):
    p = dict(parameters, sigma=sigma)
    a = p["spot"] * (1 + (p["rate"] - p["yield_rate"]) * p["maturity"]) - p["strike"]
    b = p["spot"] * sigma * np.sqrt(p["maturity"])
    if b:

        def integrand(z):
            return max(a + b * z, 0) * np.exp(-z * z / 2) / np.sqrt(2 * np.pi)

        value, error = quad(integrand, -a / b, np.inf, epsabs=1e-11, epsrel=1e-12)
        assert error < 1e-8
    else:
        value = max(a, 0)
    expected = np.exp(-p["rate"] * p["maturity"]) * value
    assert reference().one_step_euler_call(p) == pytest.approx(expected, rel=1e-11, abs=1e-10)


@pytest.mark.parametrize("strike", [80.0, 100.0, 120.0])
@pytest.mark.parametrize("clip", [(1e-3, 1 - 1e-3), (0.1, 0.9)])
def test_clipped_lognormal_partial_integral_matches_u_quadrature(parameters, strike, clip):
    p = dict(parameters, strike=strike)
    lower, upper = clip
    a = p["spot"] * np.exp((p["rate"] - p["yield_rate"] - 0.5 * p["sigma"] ** 2) * p["maturity"])
    b = p["sigma"] * np.sqrt(p["maturity"])
    discount = np.exp(-p["rate"] * p["maturity"])

    def payoff(u):
        return discount * max(a * np.exp(b * ndtri(u)) - strike, 0)

    kink = 0.5 * (1 + __import__("math").erf(np.log(strike / a) / b / np.sqrt(2)))
    interior, _ = quad(
        payoff,
        lower,
        upper,
        points=[kink] if lower < kink < upper else None,
        epsabs=2e-10,
        epsrel=1e-11,
    )
    expected = lower * payoff(lower) + (1 - upper) * payoff(upper) + interior
    assert reference().clipped_black_call(p, clip) == pytest.approx(expected, abs=1e-9, rel=1e-11)


def test_scalar_euler_replay_keeps_negative_path_and_dividend_drift(parameters):
    p = dict(parameters, sigma=1.0)
    normals = np.array([[-4.0, 0.0], [0.0, 0.0], [0.2, -0.1]])
    fine = 100 * np.prod(1 + (0.03 - 0.02) / 2 + np.sqrt(0.5) * normals, axis=1)
    expected = np.exp(-0.03) * np.maximum(fine - 100, 0)
    np.testing.assert_allclose(
        reference().scalar_euler_payoffs(p, normals), expected, rtol=0, atol=1e-12
    )
    assert len(expected) == 3


def test_nextafter_clip_and_zero_volatility_are_explicit(parameters):
    r = reference()
    clip = (np.nextafter(0.0, 1.0), np.nextafter(1.0, 0.0))
    assert r.clipped_black_call(parameters, clip) == pytest.approx(
        r.black_call(parameters), abs=1e-10
    )
    p = dict(parameters, sigma=0.0)
    assert r.clipped_black_call(p, (0.1, 0.9)) == pytest.approx(r.black_call(p), abs=1e-12)


@pytest.mark.parametrize(
    "change",
    [dict(spot=0), dict(strike=-1), dict(sigma=-0.2), dict(maturity=0), dict(rate=float("nan"))],
)
def test_references_reject_undefined_contracts(parameters, change):
    with pytest.raises(ValueError):
        reference().black_call(dict(parameters, **change))


def test_clip_and_nonfinite_shock_rejected(parameters):
    r = reference()
    with pytest.raises(ValueError):
        r.clipped_black_call(parameters, (0, 1))
    with pytest.raises(ValueError):
        r.scalar_euler_payoffs(parameters, np.array([[0.0, np.nan]]))
