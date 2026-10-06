"""Hull 19.12: dividend/currency Greeks and fixed-futures rho."""

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


def test_example_19_8_currency_futures_contract_units_and_source_rounding():
    result = greeks.futures_hedge_units(-458000, 0.04, 0.07, 0.75, contract_size=62500)
    assert result["futures_units"] == pytest.approx(-468421.81, abs=0.01)
    assert result["contracts"] == pytest.approx(-7.494749, abs=1e-6)
    assert result["rounded_contracts"] == -7
    # Printed 468442 follows a four-decimal rounded exponential factor,
    # rather than the full-precision exponential above.
    assert -458000 * round(math.exp(-(0.04 - 0.07) * 0.75), 4) == pytest.approx(-468442, abs=0.5)


@pytest.mark.parametrize(
    "kind,yield_rate",
    [("call", 0), ("put", 0), ("call", 0.02), ("put", 0.02), ("call", 0.07), ("put", 0.07)],
)
def test_table_19_6_all_greeks_against_independent_terminal_density_changes(kind, yield_rate):
    s, k, r, sig, t = 49, 50, 0.05, 0.2, 0.3846
    result = greeks.option_greek_details(s, k, r, sig, t, kind=kind, yield_rate=yield_rate)

    def value(spot=s, rate=r, vol=sig, time=t, q=yield_rate):
        return density(spot, k, rate, vol, time, kind, q)

    ds, dv, dt, dr, dq = 0.01, 1e-5, 1e-5, 1e-5, 1e-5
    v = value()
    reference = {
        "value": v,
        "delta": (value(spot=s + ds) - value(spot=s - ds)) / (2 * ds),
        "gamma": (value(spot=s + ds) - 2 * v + value(spot=s - ds)) / ds**2,
        "theta": -(value(time=t + dt) - value(time=t - dt)) / (2 * dt),
        "vega": (value(vol=sig + dv) - value(vol=sig - dv)) / (2 * dv),
        "rho_domestic": (value(rate=r + dr) - value(rate=r - dr)) / (2 * dr),
        "rho_yield": (value(q=yield_rate + dq) - value(q=yield_rate - dq)) / (2 * dq),
    }
    for key, expected in reference.items():
        assert result[key] == pytest.approx(expected, abs=2e-7)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_fixed_futures_rho_is_discount_only_not_fixed_q_domestic_rho(kind):
    f, k, r, sig, t = 105, 100, 0.05, 0.2, 0.75
    result = greeks.futures_option_greeks(f, k, r, sig, t, kind=kind)
    dr = 1e-5
    # r and q move together so F and the terminal distribution stay fixed.
    reference = (
        density(f, k, r + dr, sig, t, kind, r + dr) - density(f, k, r - dr, sig, t, kind, r - dr)
    ) / (2 * dr)
    assert result["rho_domestic"] == pytest.approx(reference, abs=1e-8)
    assert result["rho_domestic"] == pytest.approx(-t * result["value"], abs=1e-12)
    assert result["rho_domestic"] < 0
    fixed_q = greeks.option_greek_details(f, k, r, sig, t, kind=kind, yield_rate=r)
    assert abs(result["rho_domestic"] - fixed_q["rho_domestic"]) > 1


@pytest.mark.parametrize("yield_rate", [0, 0.03, 0.07])
def test_forward_pv_and_immediate_futures_price_deltas_are_distinct(yield_rate):
    spot, strike, rate, time = 50, 55, 0.04, 0.75
    result = greeks.futures_hedge_units(1200, rate, yield_rate, time)
    ds = 0.01

    def forward_value(s):
        return s * math.exp(-yield_rate * time) - strike * math.exp(-rate * time)

    def future_quote(s):
        return s * math.exp((rate - yield_rate) * time)

    assert result["forward_delta"] == pytest.approx(
        (forward_value(spot + ds) - forward_value(spot - ds)) / (2 * ds), abs=1e-11
    )
    assert result["futures_delta"] == pytest.approx(
        (future_quote(spot + ds) - future_quote(spot - ds)) / (2 * ds), abs=1e-11
    )
    assert result["futures_units"] * result["futures_delta"] == pytest.approx(1200, abs=1e-10)
    assert result["futures_delta"] / result["forward_delta"] == pytest.approx(
        math.exp(rate * time), abs=1e-12
    )


def test_contract_size_and_greek_maturity_must_be_mathematically_valid():
    with pytest.raises(ValueError):
        greeks.futures_hedge_units(1200, 0.04, 0, 0.75, contract_size=0)
    with pytest.raises(ValueError):
        greeks.option_greek_details(49, 50, 0.05, 0.2, 0)
