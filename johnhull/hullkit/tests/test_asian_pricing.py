"""Section 26.13 pricers against the independent references (Hull 11e GE pp.626-627).

The public functions added for §26.13 are checked three ways: against Hull's
printed Example 26.3 numbers, against the independent oracle in
``scripts/build_asian_reference.py``, and against the identities that hold
whatever the moment match does to the price - put-call parity and the seasoned
strike shift. The size of the approximation error itself is recorded in
``docs/validation/section-26-13/numerical-check.json`` and asserted here so it
cannot drift silently.
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
RECORD = json.loads((VALIDATION / "numerical-check.json").read_text(encoding="utf-8"))
EXAMPLE = RECORD["hull_example_26_3"]
STRIKE = asian.STRIKE
SIGMA_TOL = 4.0


@pytest.mark.parametrize("market", asian.MARKETS, ids=lambda market: market.name)
@pytest.mark.parametrize("count", [None, 12, 250])
def test_moments_match_the_independent_oracle(market, count):
    """Exact first two moments of the average, discrete and continuous."""
    times = None if count is None else asian.observation_times(market.expiry, count)
    if count is None and abs(market.rate - market.dividend) < 1e-12:
        pytest.skip("the printed continuous moments divide by r-q")
    first, second = exotics.asian_moments(STRIKE, market.rate, market.volatility,
                                          market.expiry, q=market.dividend, times=times)
    expected = (asian.continuous_moments(STRIKE, market.rate, market.dividend,
                                         market.volatility, market.expiry) if count is None
                else asian.discrete_moments(STRIKE, market.rate, market.dividend,
                                            market.volatility, times))
    assert first == pytest.approx(expected[0], rel=1e-10)
    assert second == pytest.approx(expected[1], rel=1e-10)


@pytest.mark.parametrize("market", asian.MARKETS, ids=lambda market: market.name)
@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize("count", [2, 52])
def test_average_price_matches_the_independent_moment_match(market, kind, count):
    times = asian.observation_times(market.expiry, count)
    price = exotics.asian_average_price(STRIKE, STRIKE, market.rate, market.volatility,
                                        market.expiry, q=market.dividend, kind=kind, times=times)
    expected, *_ = asian.turnbull_wakeman(STRIKE, STRIKE, market.rate, market.dividend,
                                          market.volatility, market.expiry, kind, times)
    assert price == pytest.approx(expected, rel=1e-10, abs=1e-12)


def test_hull_example_26_3_printed_prices():
    """Hull p.627: 5.62 continuously, 6.00 / 5.70 / 5.63 for 12 / 52 / 250 observations."""
    inputs = EXAMPLE["inputs"]
    continuous = exotics.asian_average_price(inputs["spot"], inputs["strike"], inputs["rate"],
                                             inputs["volatility"], inputs["expiry"],
                                             q=inputs["dividend"])
    assert continuous == pytest.approx(5.62, abs=5e-3)
    for count, printed in ((12, 6.00), (52, 5.70), (250, 5.63)):
        times = asian.observation_times(inputs["expiry"], count)
        price = exotics.asian_average_price(inputs["spot"], inputs["strike"], inputs["rate"],
                                            inputs["volatility"], inputs["expiry"],
                                            q=inputs["dividend"], times=times)
        assert price == pytest.approx(printed, abs=5e-3)


@pytest.mark.parametrize("market", asian.MARKETS, ids=lambda market: market.name)
@pytest.mark.parametrize("count", [None, 12])
def test_put_call_parity_is_exact(market, count):
    """C - P = exp(-r*T) * (M1 - K) holds however wrong the moment match is."""
    if count is None and abs(market.rate - market.dividend) < 1e-12:
        pytest.skip("the printed continuous moments divide by r-q")
    times = None if count is None else asian.observation_times(market.expiry, count)
    strike = STRIKE * 1.1
    call = exotics.asian_average_price(STRIKE, strike, market.rate, market.volatility,
                                       market.expiry, q=market.dividend, kind="call", times=times)
    put = exotics.asian_average_price(STRIKE, strike, market.rate, market.volatility,
                                      market.expiry, q=market.dividend, kind="put", times=times)
    first, _ = exotics.asian_moments(STRIKE, market.rate, market.volatility, market.expiry,
                                     q=market.dividend, times=times)
    expected = math.exp(-market.rate * market.expiry) * (first - strike)
    assert call - put == pytest.approx(expected, abs=1e-12)


def test_discrete_moments_need_no_carry_and_meet_the_continuous_limit():
    """The continuous moments divide by r-q; the discrete ones never do."""
    market = next(item for item in asian.MARKETS if item.name == "zero-carry")
    assert market.rate == market.dividend
    prices = [
        exotics.asian_average_price(STRIKE, STRIKE, market.rate, market.volatility,
                                    market.expiry, q=market.dividend,
                                    times=asian.observation_times(market.expiry, count))
        for count in (4000, 8000)
    ]
    limit = 2.0 * prices[1] - prices[0]
    continuous = exotics.asian_average_price(STRIKE, STRIKE, market.rate, market.volatility,
                                             market.expiry, q=market.dividend)
    assert continuous == pytest.approx(limit, abs=1e-6)


# --- seasoned contracts (Hull p.627) -------------------------------------


@pytest.mark.parametrize("observed", [70.0, 100.0, 140.0])
@pytest.mark.parametrize("future", [60.0, 100.0, 150.0])
def test_seasoned_strike_shift_is_a_payoff_identity(observed, future):
    """The K* payoff identity is algebra, not an approximation."""
    elapsed, remaining, strike = 0.4, 0.6, 100.0
    window = elapsed + remaining
    weight = remaining / window
    shifted = strike / weight - observed * elapsed / remaining
    blended = (elapsed * observed + remaining * future) / window
    assert max(blended - strike, 0.0) == pytest.approx(weight * max(future - shifted, 0.0))
    assert max(strike - blended, 0.0) == pytest.approx(weight * max(shifted - future, 0.0))


@pytest.mark.parametrize("kind", ["call", "put"])
def test_seasoned_price_is_the_scaled_shifted_option(kind):
    elapsed, remaining, strike, observed = 0.4, 0.6, 100.0, 96.0
    market = next(item for item in asian.MARKETS if item.name == "positive-carry")
    weight = remaining / (elapsed + remaining)
    shifted = strike / weight - observed * elapsed / remaining
    assert shifted > 0.0
    seasoned = exotics.asian_seasoned_average_price(
        STRIKE, strike, market.rate, market.volatility, elapsed, remaining, observed,
        q=market.dividend, kind=kind,
    )
    direct = weight * exotics.asian_average_price(STRIKE, shifted, market.rate,
                                                  market.volatility, remaining,
                                                  q=market.dividend, kind=kind)
    assert seasoned == pytest.approx(direct, rel=1e-12)


def test_seasoned_certain_exercise_is_a_forward():
    """A negative K* means the call is certain to pay, so it is worth the forward."""
    elapsed, remaining, strike, observed = 0.8, 0.2, 100.0, 180.0
    market = next(item for item in asian.MARKETS if item.name == "positive-carry")
    weight = remaining / (elapsed + remaining)
    shifted = strike / weight - observed * elapsed / remaining
    assert shifted < 0.0
    call = exotics.asian_seasoned_average_price(
        STRIKE, strike, market.rate, market.volatility, elapsed, remaining, observed,
        q=market.dividend, kind="call",
    )
    first, _ = asian.continuous_moments(STRIKE, market.rate, market.dividend,
                                        market.volatility, remaining)
    expected = weight * math.exp(-market.rate * remaining) * (first - shifted)
    assert call == pytest.approx(expected, rel=1e-12)
    put = exotics.asian_seasoned_average_price(
        STRIKE, strike, market.rate, market.volatility, elapsed, remaining, observed,
        q=market.dividend, kind="put",
    )
    assert put == 0.0


# --- average-strike options (Hull p.627) ---------------------------------


@pytest.mark.parametrize("row", RECORD["average_strike"]["rows"],
                         ids=lambda row: f"{row['market']}-{row['contract']}")
def test_average_strike_error_against_the_simulated_reference(row):
    """The exchange-option route is an approximation; its error is bounded and recorded."""
    times = asian.observation_times(row["expiry"], row["observations"])
    price = exotics.asian_average_strike(row["spot"], row["rate"], row["volatility"],
                                         row["expiry"], q=row["dividend"],
                                         kind=row["contract"], times=times)
    relative = (price - row["reference"]) / row["reference"]
    assert abs(relative) < 0.20
    resolved = abs(price - row["reference"]) > SIGMA_TOL * row["standard_error"]
    scale = row["volatility"] * math.sqrt(row["expiry"])
    if scale < 0.1:
        assert abs(relative) < 0.005
    else:
        assert resolved  # every other market's error is far larger than the sampling noise


def test_average_strike_is_worthless_with_a_single_observation_at_maturity():
    """One observation at T makes the average the terminal price, so nothing is exchanged."""
    market = next(item for item in asian.MARKETS if item.name == "positive-carry")
    for kind in ("call", "put"):
        price = exotics.asian_average_strike(STRIKE, market.rate, market.volatility,
                                             market.expiry, q=market.dividend, kind=kind,
                                             times=[market.expiry])
        assert price == pytest.approx(0.0, abs=1e-10)


def test_geometric_average_strike_control_is_exact_margrabe():
    """The recorded control is the exact jointly lognormal exchange price."""
    for row in RECORD["average_strike"]["rows"]:
        times = asian.observation_times(row["expiry"], row["observations"])
        exact = asian.geometric_average_strike_price(row["spot"], row["rate"], row["dividend"],
                                                     row["volatility"], row["expiry"], times,
                                                     row["contract"])
        assert exact == pytest.approx(row["geometric_exact"], rel=1e-12)


# --- input domain ---------------------------------------------------------


@pytest.mark.parametrize(("args", "kwargs"), [
    ((0.0, 100.0, 0.05, 0.2, 1.0), {}),
    ((100.0, 0.0, 0.05, 0.2, 1.0), {}),
    ((100.0, 100.0, 0.05, 0.0, 1.0), {}),
    ((100.0, 100.0, 0.05, 0.2, 0.0), {}),
    ((100.0, 100.0, 0.05, 0.2, 1.0), {"kind": "straddle"}),
    ((100.0, 100.0, 0.05, 0.2, 1.0), {"times": [1.5]}),
    ((100.0, 100.0, 0.05, 0.2, 1.0), {"times": []}),
])
def test_average_price_rejects_invalid_inputs(args, kwargs):
    with pytest.raises(ValueError):
        exotics.asian_average_price(*args, **kwargs)


def test_seasoned_rejects_invalid_windows():
    with pytest.raises(ValueError):
        exotics.asian_seasoned_average_price(100.0, 100.0, 0.05, 0.2, -0.1, 0.5, 100.0)
    with pytest.raises(ValueError):
        exotics.asian_seasoned_average_price(100.0, 100.0, 0.05, 0.2, 0.5, 0.0, 100.0)
