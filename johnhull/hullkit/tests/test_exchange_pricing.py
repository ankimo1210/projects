"""Library-level checks for the §26.14 exchange-option API (Hull 11e GE pp.627-628).

The frozen references in `test_exchange_reference.py` decide whether the prices
are right. These tests fix what the library itself must do: the American tree
must agree with the closed form when early exercise is worthless, the
decomposition helpers must be the identity Hull writes rather than a second
approximation, and the degenerate inputs must be handled rather than rounded.
Markets are synthetic; prices are in currency, maturities in years, yields and
volatilities annualised per year.
"""

import inspect
import json
import math
import sys
from itertools import pairwise
from pathlib import Path

import pytest
from hullkit import bsm, exotics

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import build_exchange_reference as exchange  # noqa: E402

PRICES = json.loads((ROOT / "docs/validation/section-26-14/prices.json").read_text())
RECORD = json.loads((ROOT / "docs/validation/section-26-14/numerical-check.json").read_text())
ROWS = PRICES["rows"]
IDS = lambda row: f"{row['market']}-{row['value_ratio']}"  # noqa: E731


def arguments(row):
    return dict(
        U0=row["spot_u"], V0=row["spot_v"], sigma_u=row["volatility_u"],
        sigma_v=row["volatility_v"], rho=row["correlation"], T=row["expiry"],
        q_u=row["yield_u"], q_v=row["yield_v"],
    )


def test_the_formula_takes_no_risk_free_rate():
    """The r-independence claim is structural here and measured in the record."""
    names = set(inspect.signature(exotics.exchange_option).parameters)
    assert "r" not in names and "rate" not in names
    assert RECORD["rate_independence"]["max_spread"] < 1e-11


@pytest.mark.parametrize("row", ROWS, ids=IDS)
def test_spread_volatility_is_the_ratio_volatility(row):
    spread = exotics.exchange_spread_volatility(
        row["volatility_u"], row["volatility_v"], row["correlation"])
    assert spread == pytest.approx(row["spread_volatility"], rel=1e-14)


@pytest.mark.parametrize("sigma_u, sigma_v", [(0.2, 0.2), (0.15, 0.45), (0.55, 0.7)])
def test_spread_volatility_at_the_correlation_extremes(sigma_u, sigma_v):
    assert exotics.exchange_spread_volatility(sigma_u, sigma_v, 1.0) == pytest.approx(
        abs(sigma_u - sigma_v))
    assert exotics.exchange_spread_volatility(sigma_u, sigma_v, -1.0) == pytest.approx(
        sigma_u + sigma_v)


@pytest.mark.parametrize("rho", [-1.5, 1.5, float("nan")])
def test_spread_volatility_rejects_impossible_correlations(rho):
    with pytest.raises(ValueError):
        exotics.exchange_spread_volatility(0.2, 0.3, rho)


def test_identical_assets_are_worth_the_discounted_forward_spread():
    """rho=1 with equal volatilities makes the ratio deterministic."""
    price = exotics.exchange_option(100.0, 125.0, 0.25, 0.25, 1.0, 2.0, q_u=0.01, q_v=0.04)
    expected = max(125.0 * math.exp(-0.04 * 2.0) - 100.0 * math.exp(-0.01 * 2.0), 0.0)
    assert price == pytest.approx(expected, rel=1e-14)
    assert exotics.exchange_option(125.0, 100.0, 0.25, 0.25, 1.0, 2.0) == 0.0
    with pytest.raises(ValueError, match="deterministic"):
        exotics.exchange_option_american(100.0, 125.0, 0.25, 0.25, 1.0, 2.0)


@pytest.mark.parametrize("row", ROWS, ids=IDS)
def test_better_and_worse_of_are_the_payoff_identity(row):
    """max(U,V) + min(U,V) = U + V, so the two helpers cannot both drift."""
    better = exotics.better_of_two_assets(**arguments(row))
    worse = exotics.worse_of_two_assets(**arguments(row))
    forward_u = row["spot_u"] * math.exp(-row["yield_u"] * row["expiry"])
    forward_v = row["spot_v"] * math.exp(-row["yield_v"] * row["expiry"])
    assert better + worse == pytest.approx(forward_u + forward_v, rel=1e-13)
    assert better >= max(forward_u, forward_v) - 1e-12
    assert worse <= min(forward_u, forward_v) + 1e-12


@pytest.mark.parametrize("item", RECORD["decomposition"]["rows"],
                         ids=lambda i: f"{i['market']}-{i['value_ratio']}")
def test_better_and_worse_of_match_the_directly_priced_references(item):
    row = next(r for r in ROWS if r["market"] == item["market"]
               and r["value_ratio"] == item["value_ratio"])
    assert exotics.better_of_two_assets(**arguments(row)) == pytest.approx(
        item["better_of"], abs=2e-9)
    assert exotics.worse_of_two_assets(**arguments(row)) == pytest.approx(
        item["worse_of"], abs=2e-9)


@pytest.mark.parametrize("row", ROWS, ids=IDS)
def test_the_american_tree_never_prices_below_the_european_formula(row):
    american = exotics.exchange_option_american(**arguments(row), steps=1024)
    european = exotics.exchange_option(**arguments(row))
    # A finite grid, so allow the measured O(1/steps) residual (0.0057 at 1024 steps).
    assert american >= european - 6e-3


@pytest.mark.parametrize("row", [r for r in ROWS if r["yield_v"] == 0.0], ids=IDS)
def test_without_a_yield_on_the_received_asset_the_tree_returns_the_european_price(row):
    """Rubinstein's equivalence: a call on a non-dividend asset is never exercised early."""
    american = exotics.exchange_option_american(**arguments(row), steps=1024)
    european = exotics.exchange_option(**arguments(row))
    assert american == pytest.approx(european, abs=6e-3, rel=1e-4)


@pytest.mark.parametrize("row", [r for r in ROWS if r["yield_v"] > 0.0 and r["value_ratio"] == 1.25],
                         ids=IDS)
def test_a_yield_on_the_received_asset_makes_early_exercise_worth_something(row):
    american = exotics.exchange_option_american(**arguments(row), steps=1024)
    european = exotics.exchange_option(**arguments(row))
    assert american > european + 1e-2
    recorded = next(item for item in RECORD["american"]["rows"]
                    if item["market"] == row["market"] and item["value_ratio"] == row["value_ratio"])
    assert american == pytest.approx(recorded["american_tree"], abs=5e-3, rel=2e-3)


def test_the_tree_converges_on_the_closed_form_where_they_must_agree():
    """With q_v = 0 the tree is pricing the European contract, so refine and watch."""
    row = next(r for r in ROWS if r["market"] == "asymmetric-vol" and r["value_ratio"] == 1.0)
    european = exotics.exchange_option(**arguments(row))
    errors = [
        abs(exotics.exchange_option_american(**arguments(row), steps=steps) - european)
        for steps in (128, 256, 512, 1024)
    ]
    # Plain CRR: the residual halves with each doubling, so the grid is the only error left.
    for coarse, fine in pairwise(errors):
        assert coarse / fine == pytest.approx(2.0, rel=0.05)
    assert errors[-1] < 6e-3


@pytest.mark.parametrize("row", ROWS[:8], ids=IDS)
def test_the_price_equals_calls_on_the_ratio_struck_at_one(row):
    """Hull p.628: U0 calls on V/U with risk-free rate q_u and dividend yield q_v."""
    spread = exotics.exchange_spread_volatility(
        row["volatility_u"], row["volatility_v"], row["correlation"])
    restated = row["spot_u"] * bsm.call_price(
        row["spot_v"] / row["spot_u"], 1.0, row["yield_u"], spread, row["expiry"], q=row["yield_v"])
    assert exotics.exchange_option(**arguments(row)) == pytest.approx(restated, rel=1e-12)


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(U0=0.0, V0=100.0, sigma_u=0.2, sigma_v=0.2, rho=0.0, T=1.0),
        dict(U0=100.0, V0=-1.0, sigma_u=0.2, sigma_v=0.2, rho=0.0, T=1.0),
        dict(U0=100.0, V0=100.0, sigma_u=0.2, sigma_v=0.2, rho=0.0, T=0.0),
        dict(U0=100.0, V0=100.0, sigma_u=-0.2, sigma_v=0.2, rho=0.0, T=1.0),
    ],
)
def test_invalid_inputs_are_rejected(kwargs):
    with pytest.raises(ValueError):
        exotics.exchange_option(**kwargs)
    with pytest.raises(ValueError):
        exotics.exchange_option_american(**kwargs)


def test_the_american_tree_rejects_a_grid_it_cannot_price():
    """A step so coarse that the ratio drift leaves the tree must fail, not silently price."""
    with pytest.raises(ValueError, match="steps"):
        exotics.exchange_option_american(100.0, 100.0, 0.2, 0.2, 0.0, 1.0, steps=0)
    with pytest.raises(ValueError, match="outside"):
        exotics.exchange_option_american(
            100.0, 100.0, 0.01, 0.01, 0.99, 5.0, q_u=0.5, q_v=0.0, steps=2)


def test_the_reference_engines_are_frozen_for_these_tests():
    """The saved spread volatilities come from the independent builder, not the library."""
    row = ROWS[0]
    assert exchange.spread_volatility(
        exchange.Market(row["market"], row["volatility_u"], row["volatility_v"],
                        row["correlation"], row["yield_u"], row["yield_v"], row["expiry"])
    ) == pytest.approx(row["spread_volatility"], rel=1e-15)
