"""Hull 20.4: strike, spot/forward moneyness and unadjusted spot-delta axes."""

import math

import numpy as np
import pytest
from hullkit import _smile_surface as smile
from scipy.integrate import quad
from scipy.stats import lognorm


def price(spot, strike, sigma, kind):
    r, q, t = 0.04, 0.07, 0.75
    terminal = lognorm(
        s=sigma * math.sqrt(t), scale=spot * math.exp((r - q - sigma * sigma / 2) * t)
    )
    low, high = (strike, math.inf) if kind == "call" else (0, strike)
    sign = 1 if kind == "call" else -1
    return (
        math.exp(-r * t)
        * quad(lambda x: sign * (x - strike) * terminal.pdf(x), low, high, epsabs=1e-11)[0]
    )


def test_source_50_delta_definitions_differ_from_atm_spot_and_forward():
    spot, r, q, sigma, time = 100, 0.04, 0, 0.2, 0.75
    atm = smile.atm_definitions(spot, r, q, sigma, time)
    assert atm["spot_strike"] == pytest.approx(100, abs=1e-12)
    assert atm["forward_strike"] == pytest.approx(100 * math.exp(r * time), abs=1e-12)
    assert atm["call_50_delta_strike"] == pytest.approx(atm["put_50_delta_strike"], abs=1e-12)
    assert atm["call_50_delta_strike"] == pytest.approx(
        atm["forward_strike"] * math.exp(sigma * sigma * time / 2), abs=1e-12
    )
    assert atm["call_50_delta_strike"] > atm["forward_strike"] > atm["spot_strike"]


@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize("axis", ["strike", "spot_moneyness", "forward_moneyness", "spot_delta"])
def test_smile_axis_round_trip_and_delta_against_independent_payoff_price_changes(axis, kind):
    strikes = np.array([90, 100, 110.0])
    vols = np.array([0.16, 0.14, 0.18])
    result = smile.smile_coordinates(strikes, 100, 0.04, 0.07, vols, 0.75, kind=kind)
    recovered = smile.strike_from_smile_axis(
        axis, result[axis], 100, 0.04, 0.07, vols, 0.75, kind=kind
    )
    assert recovered == pytest.approx(strikes, abs=1e-10)
    independent = np.array(
        [
            (price(100 + 0.001, k, v, kind) - price(100 - 0.001, k, v, kind)) / 0.002
            for k, v in zip(strikes, vols, strict=True)
        ]
    )
    assert result["spot_delta"] == pytest.approx(independent, abs=3e-9)
    assert result["delta_convention"] == "spot, not premium-adjusted"


def test_currency_unit_rescaling_preserves_moneyness_and_delta_coordinates():
    a = smile.smile_coordinates([0.9, 1, 1.1], 1, 0.04, 0.07, 0.2, 0.75)
    b = smile.smile_coordinates([90, 100, 110], 100, 0.04, 0.07, 0.2, 0.75)
    for key in ["spot_moneyness", "forward_moneyness", "spot_delta"]:
        assert a[key] == pytest.approx(b[key], abs=1e-12)


@pytest.mark.parametrize("kind,delta", [("call", 0.5), ("put", -0.5)])
def test_50_delta_can_be_outside_discounted_spot_delta_range(kind, delta):
    with pytest.raises(ValueError):
        smile.strike_from_smile_axis("spot_delta", delta, 100, 0.04, 0.9, 0.2, 2, kind=kind)


def test_unknown_smile_axis_is_rejected():
    with pytest.raises(ValueError):
        smile.strike_from_smile_axis("premium_adjusted_delta", 0.5, 100, 0.04, 0, 0.2, 0.75)
