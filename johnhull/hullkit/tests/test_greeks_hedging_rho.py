"""Hull 19.9: rho with spot and dividend/foreign rate held fixed."""

import math

import pytest
from hullkit import _greeks_hedging as greeks
from scipy.integrate import quad
from scipy.stats import norm


def density(spot, strike, rate, sigma, time, kind, yield_rate=0):
    width = sigma * math.sqrt(time)
    mean = math.log(spot) + (rate - yield_rate - sigma * sigma / 2) * time
    cutoff = (math.log(strike) - mean) / width
    sign = 1 if kind == "call" else -1
    low, high = (cutoff, 12) if kind == "call" else (-12, cutoff)
    return (
        math.exp(-rate * time)
        * quad(
            lambda z: max(sign * (math.exp(mean + width * z) - strike), 0) * norm.pdf(z),
            low,
            high,
            epsabs=1e-11,
        )[0]
    )


def test_example_19_7_rho_units_rate_point_and_basis_point():
    result = greeks.rho_units(49, 50, 0.05, 0.2, 0.3846)
    assert result["per_unit_rate"] == pytest.approx(8.91, abs=0.005)
    assert result["per_rate_point"] == pytest.approx(0.0891, abs=0.00005)
    assert result["per_basis_point"] * 10000 == pytest.approx(result["per_unit_rate"], abs=1e-12)


@pytest.mark.parametrize(
    "kind,yield_rate", [("call", 0), ("put", 0), ("call", 0.03), ("put", 0.03)]
)
def test_rho_against_independent_density_rate_difference_fixed_spot_and_yield(kind, yield_rate):
    step = 1e-5
    reference = (
        density(49, 50, 0.05 + step, 0.2, 0.3846, kind, yield_rate)
        - density(49, 50, 0.05 - step, 0.2, 0.3846, kind, yield_rate)
    ) / (2 * step)
    rho = greeks.rho_units(49, 50, 0.05, 0.2, 0.3846, kind=kind, yield_rate=yield_rate)[
        "per_unit_rate"
    ]
    assert rho == pytest.approx(reference, abs=2e-8)
    assert rho > 0 if kind == "call" else rho < 0


def test_rho_call_put_difference_from_discounted_strike():
    call = greeks.rho_units(49, 50, 0.05, 0.2, 0.3846)["per_unit_rate"]
    put = greeks.rho_units(49, 50, 0.05, 0.2, 0.3846, kind="put")["per_unit_rate"]
    assert call - put == pytest.approx(0.3846 * 50 * math.exp(-0.05 * 0.3846), abs=1e-12)


def test_rate_repricing_first_order_error_shrinks_quadratically():
    rho = greeks.rho_units(49, 50, 0.05, 0.2, 0.3846)["per_unit_rate"]
    errors = []
    for shock in [0.01, 0.005, 0.0025]:
        exact = density(49, 50, 0.05 + shock, 0.2, 0.3846, "call") - density(
            49, 50, 0.05, 0.2, 0.3846, "call"
        )
        errors.append(abs(exact - rho * shock))
    assert errors[0] / errors[1] > 3.5
    assert errors[1] / errors[2] > 3.5


def test_rho_requires_defined_diffusive_formula():
    with pytest.raises(ValueError):
        greeks.rho_units(49, 50, 0.05, 0.2, -1)
