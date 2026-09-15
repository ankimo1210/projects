"""Independent terminal-density checks for Hull 11e GE §26.10.

Markets are synthetic: spot/strike/payout are currency amounts, expiry is in
years, rate/dividend are continuously compounded per year, volatility is annual.
The oracle integrates discounted payoffs against a Gaussian log-return density;
it does not use hullkit prices, d1/d2, or a normal CDF. Only positive T/sigma and
European terminal settlement are covered; the expiry equality convention has
probability zero in this domain.
"""

import math
from typing import NamedTuple

import pytest
from hullkit import bsm, exotics
from scipy.integrate import quad


class Market(NamedTuple):
    spot: float
    strike: float
    rate: float
    volatility: float
    expiry: float
    dividend: float


MARKETS = [
    pytest.param(Market(100, 100, 0.05, 0.20, 1.0, 0.0), id="atm"),
    pytest.param(Market(100, 70, 0.02, 0.30, 0.5, 0.01), id="low-strike"),
    pytest.param(Market(100, 140, 0.04, 0.35, 2.0, 0.02), id="high-strike"),
    pytest.param(Market(100, 105, 0.01, 0.25, 1.5, 0.07), id="dividend-above-rate"),
    pytest.param(Market(100, 95, -0.025, 0.18, 0.75, 0.01), id="negative-rate"),
    pytest.param(Market(100, 100, 0.03, 0.22, 1.2, 0.03), id="zero-carry"),
    pytest.param(Market(100, 100, 0.03, 0.15, 1 / 365, 0.01), id="near-expiry"),
    pytest.param(Market(100, 130, 0.06, 0.70, 5.0, 0.025), id="long-high-vol"),
]
KINDS = ("call", "put")
PAYOUTS = (0.5, 1.0, 123.0)
ABS_TOL = 2e-9
REL_TOL = 2e-11


def _terminal_moment(market, kind, *, asset):
    """Integrate the terminal indicator or asset-weighted indicator."""
    spot, strike, rate, volatility, expiry, dividend = market
    drift = (rate - dividend - 0.5 * volatility**2) * expiry
    scale = volatility * math.sqrt(expiry)
    threshold = (math.log(strike / spot) - drift) / scale
    low, high = (threshold, math.inf) if kind == "call" else (-math.inf, threshold)

    def integrand(z):
        exponent = -0.5 * z * z - rate * expiry
        if asset:
            # Combine exponents to avoid overflow from exp(scale*z) in the tails.
            exponent += math.log(spot) + drift + scale * z
        return math.exp(exponent) / math.sqrt(2 * math.pi)

    value, estimated_error = quad(integrand, low, high, epsabs=1e-12, epsrel=1e-12)
    # Cash moments are later scaled by Q; asset moments are already in currency.
    scaled_error = estimated_error * (1.0 if asset else max(PAYOUTS))
    assert scaled_error < ABS_TOL / 10
    return value


@pytest.mark.parametrize("market", MARKETS)
@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("payout", PAYOUTS)
def test_cash_binary_against_terminal_density(market, kind, payout):
    expected = payout * _terminal_moment(market, kind, asset=False)
    actual = exotics.cash_or_nothing(*market, kind=kind, payout=payout)
    assert actual == pytest.approx(expected, abs=ABS_TOL, rel=REL_TOL)


@pytest.mark.parametrize("market", MARKETS)
@pytest.mark.parametrize("kind", KINDS)
def test_asset_binary_against_terminal_density(market, kind):
    expected = _terminal_moment(market, kind, asset=True)
    actual = exotics.asset_or_nothing(*market, kind=kind)
    assert actual == pytest.approx(expected, abs=ABS_TOL, rel=REL_TOL)


@pytest.mark.parametrize("market", MARKETS)
@pytest.mark.parametrize("kind", KINDS)
def test_binary_replication_matches_european_vanilla(market, kind):
    cash = exotics.cash_or_nothing(*market, kind=kind, payout=market.strike)
    asset = exotics.asset_or_nothing(*market, kind=kind)
    reconstructed = asset - cash if kind == "call" else cash - asset
    vanilla = (bsm.call_price if kind == "call" else bsm.put_price)(*market)
    assert reconstructed == pytest.approx(vanilla, abs=ABS_TOL, rel=REL_TOL)
