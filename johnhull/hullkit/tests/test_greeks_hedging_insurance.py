"""Hull 19.13: put-delta insurance units and discrete replication gap risk."""

import math

import numpy as np
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


def test_example_19_9_initial_portfolio_sale_fraction_and_d1():
    result = greeks.portfolio_insurance_target(90e6, 87e6, 0.09, 0.03, 0.25, 0.5)
    assert result["d1"] == pytest.approx(0.4499, abs=0.00005)
    assert result["put_delta"] == pytest.approx(-0.3215, abs=0.00005)
    assert 100 * result["sell_fraction"] == pytest.approx(32.15, abs=0.005)
    assert result["target_risky_value"] + result["sale_value"] == pytest.approx(90e6, abs=1e-8)


def test_example_19_9_displayed_delta_changes_and_explicit_time_conventions():
    down_fixed = greeks.portfolio_insurance_target(88e6, 87e6, 0.09, 0.03, 0.25, 0.5)
    down_day = greeks.portfolio_insurance_target(88e6, 87e6, 0.09, 0.03, 0.25, 0.5 - 1 / 365)
    up_day = greeks.portfolio_insurance_target(92e6, 87e6, 0.09, 0.03, 0.25, 0.5 - 1 / 365)
    assert down_fixed["put_delta"] == pytest.approx(-0.3679, abs=0.00005)
    assert down_day["put_delta"] == pytest.approx(-0.36811261, abs=5e-9)
    assert up_day["put_delta"] == pytest.approx(-0.2787, abs=0.00005)
    up_fixed = greeks.portfolio_insurance_target(92e6, 87e6, 0.09, 0.03, 0.25, 0.5)
    base = greeks.portfolio_insurance_target(90e6, 87e6, 0.09, 0.03, 0.25, 0.5)
    assert up_fixed["put_delta"] == pytest.approx(-0.2787, abs=0.00005)
    # The printed differences use deltas rounded to four decimals.
    shown = [round(-row["put_delta"], 4) for row in (down_fixed, base, up_fixed)]
    assert 100 * (shown[0] - shown[1]) == pytest.approx(4.64, abs=1e-9)
    assert 100 * (shown[1] - shown[2]) == pytest.approx(4.28, abs=1e-9)
    assert down_fixed["put_delta"] < 0  # Minus sign is absent in source's 88m sentence.
    # Both printed deltas match the unchanged .5 years; after one day 88m
    # gives -0.3681 while 92m still rounds to -0.2787.


def test_example_19_10_index_futures_12296_rounded_to_123_short():
    result = greeks.insurance_futures_target(90e6, 87e6, 0.09, 0.03, 0.25, 0.5, 900, 250, 0.75)
    assert result["contracts_to_short"] == pytest.approx(122.96, abs=0.005)
    assert result["rounded_contracts_to_short"] == 123
    exact = result["sell_fraction"] * 90e6 / (900 * 250) * math.exp(-(0.09 - 0.03) * 0.75)
    assert result["contracts_to_short"] == pytest.approx(exact, abs=1e-12)


@pytest.mark.parametrize("value", [90e6, 88e6])
def test_insurance_put_delta_against_independent_payoff_density_spot_difference(value):
    ds = 1000
    reference = (
        density(value + ds, 87e6, 0.09, 0.25, 0.5, "put", 0.03)
        - density(value - ds, 87e6, 0.09, 0.25, 0.5, "put", 0.03)
    ) / (2 * ds)
    result = greeks.portfolio_insurance_target(value, 87e6, 0.09, 0.03, 0.25, 0.5)
    assert result["put_delta"] == pytest.approx(reference, abs=1e-9)


def test_insurance_sale_fraction_increases_when_original_portfolio_falls():
    targets = [
        greeks.portfolio_insurance_target(x, 87e6, 0.09, 0.03, 0.25, 0.5)["sell_fraction"]
        for x in [88e6, 90e6, 92e6]
    ]
    assert targets[0] > targets[1] > targets[2]


def test_gap_down_can_break_synthetic_insurance_floor_with_same_initial_premium():
    result = greeks.synthetic_put_replay([[90, 60]], [0, 0.5], 87, 0.09, 0.25)
    # Both comparisons start with capital S0 + fair put premium; synthetic
    # bank starts at premium - delta*S0, rather than free insurance proceeds.
    p = density(90, 87, 0.09, 0.25, 0.5, "put")
    ds = 0.001
    delta = (
        density(90 + ds, 87, 0.09, 0.25, 0.5, "put") - density(90 - ds, 87, 0.09, 0.25, 0.5, "put")
    ) / (2 * ds)
    independent = (1 + delta) * 60 + (p - delta * 90) * math.exp(0.09 * 0.5)
    assert result["insured_terminal"][0] == pytest.approx(independent, abs=1e-7)
    assert result["true_put_insured_terminal"][0] == pytest.approx(87, abs=1e-12)
    assert result["insured_terminal"][0] < 87 - 5


def test_synthetic_put_cash_recurrence_against_independent_discounted_gains():
    paths = np.array([[90, 82, 86, 79], [90, 95, 88, 94]], dtype=float)
    times = np.array([0, 0.1, 0.3, 0.5])
    result = greeks.synthetic_put_replay(paths, times, 87, 0.09, 0.25)
    holdings = greeks.delta_holdings(paths, times, 87, 0.09, 0.25, kind="put")
    initial = density(90, 87, 0.09, 0.25, 0.5, "put")
    reference = math.exp(0.09 * 0.5) * (
        initial + np.sum(holdings * np.diff(paths * np.exp(-0.09 * times), axis=1), axis=1)
    )
    assert result["synthetic_put_terminal"] == pytest.approx(reference, abs=1e-10)
    assert result["initial_put_value"] == pytest.approx([initial, initial], abs=1e-11)
