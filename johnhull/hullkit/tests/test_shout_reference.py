"""Independent shout-option checks for Hull 11e GE section 26.12, pp.625-626.

There is no hullkit shout pricer yet, so these tests fix the target a future one
has to hit: the analytic value at the moment of shouting, the reference table
built by two engines that share no pricing path, the domination bounds against
the European value (Ch.15) and the fixed-strike lookback (section 26.11), and the
payoff readings that a naive implementation gets wrong. Markets are synthetic;
prices and strikes are in currency, maturities in years, and rates, dividend
yields and volatilities are annualised. Continuous shouting is assumed: the
holder may shout once at any instant in [0, T], or never.
"""

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest
from hullkit import exotics
from scipy.integrate import quad
from scipy.stats import lognorm


def _reference_module():
    """Import the reference builder (it lives outside the installed packages)."""
    scripts = Path(__file__).resolve().parents[2] / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import build_shout_reference

    return build_shout_reference


shout = _reference_module()
VALIDATION = Path(__file__).resolve().parents[2] / "docs" / "validation" / "section-26-12"
PRICES = json.loads((VALIDATION / "prices.json").read_text(encoding="utf-8"))
RECORD = json.loads((VALIDATION / "numerical-check.json").read_text(encoding="utf-8"))
ROWS = PRICES["rows"]
# The two engines are numerical, so the saved agreement is the accuracy claim.
ENGINE_TOL = 1e-3
# Bounds and closed-form anchors are compared at the engines' resolution, not at
# machine precision; deep out-of-the-money rows only carry absolute accuracy.
ANCHOR_TOL = 1e-4


def _row(market, contract, ratio):
    for row in ROWS:
        if row["market"] == market and row["contract"] == contract and row["spot_ratio"] == ratio:
            return row
    raise KeyError((market, contract, ratio))


def _market_rows():
    for market in shout.MARKETS:
        for contract in shout.CONTRACTS:
            yield market, contract


# --- the value at the moment of shouting ---------------------------------


@pytest.mark.parametrize("contract", shout.CONTRACTS)
@pytest.mark.parametrize("spot", [60.0, 100.0, 140.0])
def test_shout_value_matches_the_payoff_expectation(spot, contract):
    """Hull p.625: after shouting the payoff is max(0, S_T - S_t) + (S_t - K)."""
    strike, rate, dividend, sigma, tau = 100.0, 0.06, 0.02, 0.30, 1.4
    scale = spot * math.exp((rate - dividend - 0.5 * sigma**2) * tau)
    law = lognorm(s=sigma * math.sqrt(tau), scale=scale)

    def integrand(terminal):
        if contract == "call":
            payoff = max(0.0, terminal - spot) + (spot - strike)
        else:
            payoff = max(0.0, spot - terminal) + (strike - spot)
        return payoff * law.pdf(terminal)

    # The payoff kinks at the shout level, so integrate each side separately.
    lower, lower_error = quad(integrand, 0.0, spot, limit=200, epsabs=1e-12, epsrel=1e-12)
    upper, upper_error = quad(integrand, spot, np.inf, limit=200, epsabs=1e-12, epsrel=1e-12)
    expectation = lower + upper
    assert lower_error + upper_error < 1e-9
    expected = math.exp(-rate * tau) * expectation
    assert shout.shout_now_value(spot, strike, rate, dividend, sigma, tau, contract) == pytest.approx(
        expected, abs=1e-9
    )


@pytest.mark.parametrize(("market", "contract"), list(_market_rows()))
def test_shouting_at_the_money_is_worth_the_european_option(market, contract):
    """At S=K the discounted intrinsic is zero, so the shout value is the ATM option."""
    value = shout.shout_now_value(100.0, 100.0, market.rate, market.dividend,
                                  market.volatility, market.expiry, contract)
    european = shout.black_scholes(100.0, 100.0, market.rate, market.dividend,
                                   market.volatility, market.expiry, contract)
    assert value == pytest.approx(european, rel=1e-13, abs=1e-13)


def test_hull_fifty_sixty_illustration():
    """Hull p.625: strike 50, shout at 60, payoff 10 below 60 and S_T - 50 above."""
    strike, shouted = 50.0, 60.0
    for terminal in (30.0, 45.0, 55.0, 59.99):
        assert max(terminal - strike, shouted - strike) == pytest.approx(10.0)
    for terminal in (60.01, 75.0, 120.0):
        assert max(terminal - strike, shouted - strike) == pytest.approx(terminal - strike)


@pytest.mark.parametrize("shouted", [60.0, 100.0, 140.0])
def test_the_two_payoff_readings_agree_wherever_shouting_can_help(shouted):
    """"Intrinsic value at the shout" and Hull's formula differ only below the strike.

    Above the strike the two readings coincide. Below it, the formula reading is
    weakly worse than never shouting, so neither reading changes the price of an
    optimally exercised contract.
    """
    strike = 100.0
    for terminal in np.linspace(1.0, 300.0, 61):
        formula = max(terminal - strike, shouted - strike)
        intrinsic = max(max(terminal - strike, 0.0), max(shouted - strike, 0.0))
        european = max(terminal - strike, 0.0)
        if shouted >= strike:
            assert formula == pytest.approx(intrinsic)
            assert formula >= european - 1e-12
        else:
            assert intrinsic == pytest.approx(european)
            assert formula <= european + 1e-12


# --- the reference table --------------------------------------------------


@pytest.mark.parametrize(("market", "contract"), list(_market_rows()))
def test_reference_table_is_reproduced(market, contract):
    """Rebuild each saved row with the convolution engine at the saved settings."""
    spots = [shout.STRIKE * ratio for ratio in shout.SPOT_RATIOS]
    values, _, _ = shout.convolution_reference(
        spots, shout.STRIKE, market.rate, market.dividend, market.volatility,
        market.expiry, contract, steps=PRICES["date_steps"],
    )
    for ratio, value in zip(shout.SPOT_RATIOS, values, strict=True):
        saved = _row(market.name, contract, ratio)["price"]
        assert value == pytest.approx(saved, rel=1e-7, abs=1e-9)


@pytest.mark.parametrize("market_name", ["hull-example-market", "long-high-vol"])
@pytest.mark.parametrize("contract", shout.CONTRACTS)
def test_integral_equation_reproduces_the_convolution_price(market_name, contract):
    """The free-boundary engine shares no pricing code with the grid engine."""
    market = next(item for item in shout.MARKETS if item.name == market_name)
    value, _, boundary = shout.integral_equation_reference(
        shout.STRIKE, shout.STRIKE, market.rate, market.dividend, market.volatility,
        market.expiry, contract, steps=100,
    )
    saved = _row(market_name, contract, 1.0)["price"]
    assert value == pytest.approx(saved, abs=ENGINE_TOL, rel=1e-4)
    assert np.all(np.isfinite(boundary))


def test_saved_record_reports_the_agreement_it_claims():
    """The stored comparisons must match the summary numbers in the same record."""
    comparisons = RECORD["agreement"]["comparisons"]
    assert len(comparisons) == len(shout.MARKETS) * len(shout.CONTRACTS)
    largest = max(abs(item["difference"]) for item in comparisons)
    assert largest == pytest.approx(RECORD["agreement"]["max_absolute"], rel=1e-12)
    assert largest < ENGINE_TOL


# --- bounds that any implementation has to respect ------------------------


@pytest.mark.parametrize("row", ROWS, ids=lambda row: f"{row['market']}-{row['contract']}-{row['spot_ratio']}")
def test_price_sits_between_the_european_option_and_the_lookback(row):
    """Never shouting is allowed, and one shout cannot beat the running extreme."""
    assert row["price"] >= row["european"] - ANCHOR_TOL
    assert row["price"] >= row["shout_immediately"] - ANCHOR_TOL
    if abs(row["rate"] - row["dividend"]) <= 1e-8:
        pytest.skip("the lookback closed form is not defined at r=q")
    if row["contract"] == "call":
        ceiling = exotics.lookback_fixed_call(row["spot"], row["strike"], row["spot"],
                                              row["rate"], row["volatility"], row["expiry"],
                                              q=row["dividend"])
    else:
        ceiling = exotics.lookback_fixed_put(row["spot"], row["strike"], row["spot"],
                                             row["rate"], row["volatility"], row["expiry"],
                                             q=row["dividend"])
    assert row["price"] <= ceiling + ANCHOR_TOL


def test_rows_inside_the_shout_region_match_the_closed_form():
    """Where shouting now is optimal the price is analytic, with no engine involved."""
    matched = 0
    for row in ROWS:
        if abs(row["price"] - row["shout_immediately"]) >= ANCHOR_TOL:
            continue
        matched += 1
        analytic = shout.shout_now_value(row["spot"], row["strike"], row["rate"],
                                         row["dividend"], row["volatility"], row["expiry"],
                                         row["contract"])
        assert row["price"] == pytest.approx(analytic, abs=ANCHOR_TOL)
    assert matched >= 8


def test_price_is_homogeneous_in_spot_and_strike():
    market = shout.MARKETS[1]
    base, _, _ = shout.convolution_reference([100.0], 100.0, market.rate, market.dividend,
                                             market.volatility, market.expiry, "call", steps=200)
    scaled, _, _ = shout.convolution_reference([250.0], 250.0, market.rate, market.dividend,
                                               market.volatility, market.expiry, "call", steps=200)
    assert 2.5 * base[0] == pytest.approx(scaled[0], rel=1e-9)


@pytest.mark.parametrize("contract", shout.CONTRACTS)
def test_price_grows_with_volatility_and_maturity(contract):
    market = shout.MARKETS[1]
    def price(volatility, expiry):
        values, _, _ = shout.convolution_reference([100.0], 100.0, market.rate, market.dividend,
                                                   volatility, expiry, contract, steps=200)
        return values[0]

    assert price(0.30, market.expiry) > price(0.20, market.expiry) + 1e-3
    assert price(0.20, 2.0) > price(0.20, 1.0) + 1e-3


@pytest.mark.parametrize("contract", shout.CONTRACTS)
def test_shout_boundary_starts_at_the_strike_and_moves_away(contract):
    """The boundary leaves the strike monotonically as maturity lengthens."""
    market = shout.MARKETS[1]
    _, taus, boundary = shout.integral_equation_price(100.0, 100.0, market.rate, market.dividend,
                                                      market.volatility, market.expiry, contract,
                                                      steps=100)
    assert boundary[0] == pytest.approx(100.0)
    distance = (boundary - 100.0) if contract == "call" else (100.0 - boundary)
    assert np.all(distance[1:] > 0.0)
    assert np.all(np.diff(distance) > -1e-9)
    assert taus[-1] == pytest.approx(market.expiry)


# --- shortcuts that look right and are not --------------------------------


def test_the_mirrored_european_symmetry_does_not_price_the_shout_put():
    """P(S,K,r,q) = C(K,S,q,r) holds for European options but not for shouts."""
    market = shout.MARKETS[1]
    spot, strike = 80.0, 100.0
    european_put = shout.black_scholes(spot, strike, market.rate, market.dividend,
                                       market.volatility, market.expiry, "put")
    mirrored_european = shout.black_scholes(strike, spot, market.dividend, market.rate,
                                            market.volatility, market.expiry, "call")
    assert european_put == pytest.approx(mirrored_european, rel=1e-12)

    put, _, _ = shout.convolution_reference([spot], strike, market.rate, market.dividend,
                                            market.volatility, market.expiry, "put", steps=200)
    mirrored, _, _ = shout.convolution_reference([strike], spot, market.dividend, market.rate,
                                                 market.volatility, market.expiry, "call", steps=200)
    assert abs(put[0] - mirrored[0]) > 1.0


@pytest.mark.parametrize("contract", shout.CONTRACTS)
def test_locking_the_original_strike_is_not_the_shout_value(contract):
    """After shouting the new option is struck at the shout level, not at K."""
    strike, rate, dividend, sigma, tau = 100.0, 0.05, 0.02, 0.2, 1.0
    for spot in (80.0, 120.0):
        correct = shout.shout_now_value(spot, strike, rate, dividend, sigma, tau, contract)
        wrong = math.exp(-rate * tau) * (spot - strike if contract == "call" else strike - spot)
        wrong += shout.black_scholes(spot, strike, rate, dividend, sigma, tau, contract)
        assert abs(correct - wrong) > 0.5


@pytest.mark.parametrize(("market", "contract"), list(_market_rows()))
def test_european_and_immediate_shout_are_both_rejected_as_prices(market, contract):
    """Two plausible wrong pricers: never shouting, and always shouting at once."""
    row = _row(market.name, contract, 1.0)
    never = row["european"]
    immediately = row["shout_immediately"]
    assert row["price"] > never + 1e-3
    assert row["price"] > immediately + 1e-3


def test_equal_rate_and_dividend_is_ordinary_here():
    """Unlike the section 26.11 lookback formulas, nothing divides by r-q."""
    market = next(item for item in shout.MARKETS if item.name == "zero-carry")
    assert market.rate == market.dividend
    row = _row("zero-carry", "call", 1.0)
    assert math.isfinite(row["price"]) and row["price"] > row["european"]
    with pytest.raises(ValueError):
        exotics.lookback_fixed_call(100.0, 100.0, 100.0, market.rate, market.volatility,
                                    market.expiry, q=market.dividend)
