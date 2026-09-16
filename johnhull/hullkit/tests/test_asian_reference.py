"""Independent Asian-option checks for Hull 11e GE section 26.13, pp.626-627.

hullkit prices the continuously averaged average-price call by matching the
first two moments of the average to a lognormal (Turnbull-Wakeman). That is an
approximation to a price that has no closed form, and nothing here measured its
error before. These tests fix three things: the moment match reproduces Hull's
printed Example 26.3 numbers, the simulated references agree with an exact
two-date price, and the approximation error of the moment match is a recorded,
bounded quantity rather than an assumption. Markets are synthetic; prices and
strikes are in currency, maturities in years, and rates, dividend yields and
volatilities are annualised. Observation dates are i*T/m for i=1..m.
"""

import json
import math
import sys
from pathlib import Path

import pytest
from hullkit import exotics


def _reference_module():
    """Import the reference builder (it lives outside the installed packages)."""
    scripts = Path(__file__).resolve().parents[2] / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import build_asian_reference

    return build_asian_reference


asian = _reference_module()
VALIDATION = Path(__file__).resolve().parents[2] / "docs" / "validation" / "section-26-13"
PRICES = json.loads((VALIDATION / "prices.json").read_text(encoding="utf-8"))
RECORD = json.loads((VALIDATION / "numerical-check.json").read_text(encoding="utf-8"))
ROWS = PRICES["rows"]
EXAMPLE = RECORD["hull_example_26_3"]
# Hull prints two decimals; the simulated references carry a standard error.
PRINT_TOL = 5e-3
SIGMA_TOL = 4.0


def _rows(**filters):
    return [row for row in ROWS
            if all(row[key] == value for key, value in filters.items())]


# --- Hull's printed numbers ----------------------------------------------


def test_example_26_3_continuous_moments_and_price():
    """Hull p.627: M1 = 52.59, M2 = 2,922.76, Black volatility 23.54%, price 5.62."""
    inputs = EXAMPLE["inputs"]
    price, first, second, vol = asian.turnbull_wakeman(
        inputs["spot"], inputs["strike"], inputs["rate"], inputs["dividend"],
        inputs["volatility"], inputs["expiry"], "call",
    )
    assert first == pytest.approx(52.59, abs=1e-2)
    assert second == pytest.approx(2922.76, abs=1e-2)
    assert vol == pytest.approx(0.2354, abs=5e-5)
    assert price == pytest.approx(5.62, abs=PRINT_TOL)


@pytest.mark.parametrize(("count", "printed"), [(12, 6.00), (52, 5.70), (250, 5.63)])
def test_example_26_3_discrete_observation_prices(count, printed):
    """Hull p.627: 12, 52 and 250 observations give 6.00, 5.70 and 5.63.

    Reproducing them fixes the observation convention: dates i*T/m with today
    excluded and maturity included, priced from the exact discrete moments.
    """
    inputs = EXAMPLE["inputs"]
    times = asian.observation_times(inputs["expiry"], count)
    price, *_ = asian.turnbull_wakeman(
        inputs["spot"], inputs["strike"], inputs["rate"], inputs["dividend"],
        inputs["volatility"], inputs["expiry"], "call", times,
    )
    assert price == pytest.approx(printed, abs=PRINT_TOL)


def test_hullkit_reproduces_the_independent_moment_match():
    """The shipped continuous call is a faithful Turnbull-Wakeman implementation."""
    for market in asian.MARKETS:
        if abs(market.rate - market.dividend) < 1e-12:
            continue  # the printed continuous moments divide by r-q
        mine, *_ = asian.turnbull_wakeman(asian.STRIKE, asian.STRIKE, market.rate,
                                          market.dividend, market.volatility,
                                          market.expiry, "call")
        theirs = exotics.asian_call_turnbull_wakeman(asian.STRIKE, asian.STRIKE, market.rate,
                                                     market.volatility, market.expiry,
                                                     q=market.dividend)
        assert theirs == pytest.approx(mine, rel=1e-8, abs=1e-8)


def test_equal_rate_and_dividend_needs_the_discrete_moments():
    """The printed continuous moments divide by r-q; the discrete ones never do."""
    market = next(item for item in asian.MARKETS if item.name == "zero-carry")
    with pytest.raises(ValueError):
        asian.continuous_moments(asian.STRIKE, market.rate, market.dividend,
                                 market.volatility, market.expiry)
    coarse, fine = (
        asian.turnbull_wakeman(asian.STRIKE, asian.STRIKE, market.rate, market.dividend,
                               market.volatility, market.expiry, "call",
                               asian.observation_times(market.expiry, count))[0]
        for count in (4000, 8000)
    )
    limit = 2.0 * fine - coarse
    shipped = exotics.asian_call_turnbull_wakeman(asian.STRIKE, asian.STRIKE, market.rate,
                                                  market.volatility, market.expiry,
                                                  q=market.dividend)
    assert shipped == pytest.approx(limit, abs=1e-6)


# --- exact anchors --------------------------------------------------------


@pytest.mark.parametrize("market", asian.MARKETS, ids=lambda market: market.name)
def test_two_date_price_satisfies_put_call_parity(market):
    """(A-K)+ minus (K-A)+ is A-K, so C - P is the discounted E[A] - K, exactly."""
    times = asian.observation_times(market.expiry, 2)
    call = asian.two_date_price(asian.STRIKE, asian.STRIKE, market.rate, market.dividend,
                                market.volatility, times, "call")
    put = asian.two_date_price(asian.STRIKE, asian.STRIKE, market.rate, market.dividend,
                               market.volatility, times, "put")
    first, _ = asian.discrete_moments(asian.STRIKE, market.rate, market.dividend,
                                      market.volatility, times)
    expected = math.exp(-market.rate * market.expiry) * (first - asian.STRIKE)
    assert call - put == pytest.approx(expected, abs=1e-10)


def test_simulated_reference_matches_the_exact_two_date_price():
    """Every two-observation row has an exact price; the gap must be sampling noise."""
    anchored = [row for row in ROWS if row["exact"] is not None and row["standard_error"] > 0.0]
    assert len(anchored) >= 30
    worst = max(abs(row["exact"] - row["reference"]) / row["standard_error"] for row in anchored)
    assert worst < SIGMA_TOL
    assert worst == pytest.approx(RECORD["anchor"]["max_standard_errors"], rel=1e-9)


def test_control_variate_run_is_reproducible():
    """Re-running one recorded schedule with the recorded seed returns the saved price."""
    market = next(item for item in asian.MARKETS if item.name == "positive-carry")
    times = asian.observation_times(market.expiry, 12)
    strikes = [asian.STRIKE / ratio for ratio in asian.SPOT_RATIOS]
    estimates = asian.control_variate_price(
        asian.STRIKE, strikes, market.rate, market.dividend, market.volatility,
        market.expiry, times, paths=PRICES["paths"],
    )
    for ratio, strike in zip(asian.SPOT_RATIOS, strikes, strict=True):
        for kind in asian.CONTRACTS:
            price, error = estimates[(strike, kind)]
            row = _rows(market=market.name, observations=12, contract=kind, spot_ratio=ratio)[0]
            assert ratio * price == pytest.approx(row["reference"], rel=1e-9, abs=1e-12)
            assert ratio * error == pytest.approx(row["standard_error"], rel=1e-9, abs=1e-12)


@pytest.mark.parametrize("row", [row for row in ROWS if row["reference"] > 0.5],
                         ids=lambda row: f"{row['market']}-{row['observations']}-{row['contract']}-{row['spot_ratio']}")
def test_geometric_average_brackets_the_arithmetic_price(row):
    """The arithmetic average dominates the geometric one path by path."""
    slack = SIGMA_TOL * row["standard_error"]
    if row["contract"] == "call":
        assert row["reference"] >= row["geometric"] - slack
    else:
        assert row["reference"] <= row["geometric"] + slack


# --- the measured approximation error ------------------------------------


def test_moment_match_overprices_hulls_own_example_by_about_one_percent():
    """Example 26.3 is inside the approximation's error, not on top of it."""
    for row in EXAMPLE["discrete"]:
        relative = row["approximation_error"] / row["reference"]
        assert row["approximation_error"] > 6.0 * row["standard_error"]
        assert 0.005 < relative < 0.015
    continuous = EXAMPLE["continuous"]
    assert continuous["approximation_error"] / continuous["extrapolated_reference"] > 0.005


def test_recorded_worst_case_error_matches_the_rows():
    """The headline error in the record is recomputed from the saved table."""
    worst = max(abs(row["turnbull_wakeman"] - row["reference"]) / row["reference"]
                for row in ROWS if row["reference"] > 0.5)
    assert worst == pytest.approx(RECORD["approximation_error"]["max_relative"], rel=1e-9)
    assert worst > 0.05


def test_error_has_both_signs_and_grows_with_the_volatility_time_scale():
    """Negligible at small sigma*sqrt(T), above 5% at large, and signed both ways.

    Matching two moments to a lognormal overprices near and above the average's
    own forward and underprices below it, so the error is not a one-sided
    premium. The ordering is not monotone market by market either: moneyness
    measured against that forward moves the error, so a market with a decaying
    forward can sit below a shorter, less volatile one.
    """
    scales = {}
    for market in asian.MARKETS:
        row = _rows(market=market.name, observations=52, contract="call", spot_ratio=1.0)[0]
        scales[market.volatility * math.sqrt(market.expiry)] = (
            (row["turnbull_wakeman"] - row["reference"]) / row["reference"]
        )
    ordered = [scales[key] for key in sorted(scales)]
    assert ordered[0] < 0.001
    assert ordered[-1] > 0.05

    resolved = [(row["turnbull_wakeman"] - row["reference"]) / row["reference"]
                for row in ROWS
                if row["reference"] > 0.5
                and abs(row["turnbull_wakeman"] - row["reference"]) > SIGMA_TOL * row["standard_error"]]
    assert max(resolved) > 0.05
    assert min(resolved) < -0.01
    recorded = RECORD["approximation_error"]
    assert max(resolved) == pytest.approx(recorded["largest_overprice"]["relative_error"], rel=1e-9)
    assert min(resolved) == pytest.approx(recorded["largest_underprice"]["relative_error"], rel=1e-9)


def test_parity_supplies_the_average_price_put_that_hullkit_lacks():
    """C - P = discount * (M1 - K) turns the shipped call into the missing put."""
    market = next(item for item in asian.MARKETS if item.name == "positive-carry")
    call = exotics.asian_call_turnbull_wakeman(asian.STRIKE, asian.STRIKE, market.rate,
                                               market.volatility, market.expiry,
                                               q=market.dividend)
    first, _ = asian.continuous_moments(asian.STRIKE, market.rate, market.dividend,
                                        market.volatility, market.expiry)
    implied = call - math.exp(-market.rate * market.expiry) * (first - asian.STRIKE)
    direct, *_ = asian.turnbull_wakeman(asian.STRIKE, asian.STRIKE, market.rate, market.dividend,
                                        market.volatility, market.expiry, "put")
    assert implied == pytest.approx(direct, abs=1e-8)
