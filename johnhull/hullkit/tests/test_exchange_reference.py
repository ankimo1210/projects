"""Independent exchange-option checks for Hull 11e GE section 26.14, pp.627-628.

hullkit carries Margrabe's formula (eq. 26.5) and one printed-value test. The
section also claims the price does not depend on the risk-free rate, that it
equals U0 calls on V/U struck at 1 with rate qU and yield qV, that better-of
and worse-of options decompose into one asset plus or minus this option, and
that the American version is U0 American calls on the same ratio. These tests
check the formula against references that never use it, and turn each of those
claims into a measured quantity. Markets are synthetic; prices are in currency,
maturities in years, and yields and volatilities are annualised per year.
"""

import json
import math
import sys
from pathlib import Path

import pytest
from hullkit import bsm, exotics

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import build_exchange_reference as exchange  # noqa: E402

PRICES = json.loads((ROOT / "docs/validation/section-26-14/prices.json").read_text())
RECORD = json.loads((ROOT / "docs/validation/section-26-14/numerical-check.json").read_text())
ROWS = PRICES["rows"]


def market_of(row):
    return exchange.Market(
        row["market"], row["volatility_u"], row["volatility_v"], row["correlation"],
        row["yield_u"], row["yield_v"], row["expiry"],
    )


def library_price(row):
    return exotics.exchange_option(
        row["spot_u"], row["spot_v"], row["volatility_u"], row["volatility_v"],
        row["correlation"], row["expiry"], q_u=row["yield_u"], q_v=row["yield_v"],
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda row: f"{row['market']}-{row['value_ratio']}")
def test_formula_matches_the_conditioning_reference(row):
    """The library formula against a price built by conditioning on U_T."""
    tolerance = max(2e-9, 2e-11 * abs(row["conditional"]))
    assert library_price(row) == pytest.approx(row["conditional"], abs=tolerance)


@pytest.mark.parametrize("row", ROWS, ids=lambda row: f"{row['market']}-{row['value_ratio']}")
def test_the_two_quadrature_routes_agree(row):
    """Conditioning in the original measure and integrating the ratio under U."""
    assert row["ratio"] == pytest.approx(row["conditional"], abs=2e-9, rel=1e-10)


@pytest.mark.parametrize("row", ROWS, ids=lambda row: f"{row['market']}-{row['value_ratio']}")
def test_simulation_agrees_within_four_standard_errors(row):
    if row["standard_error"] == 0.0:
        pytest.skip("a degenerate row carries no sampling noise")
    assert abs(row["simulated"] - row["conditional"]) <= 4.0 * row["standard_error"]


def test_engine_agreement_is_recorded_at_machine_precision():
    engines = RECORD["engines"]
    assert engines["rows"] == len(ROWS) == 24
    assert engines["max_absolute_gap"] < 1e-11
    assert engines["max_relative_gap"] < 1e-11
    assert engines["max_simulated_standard_errors"] < 4.0


@pytest.mark.parametrize("probe", RECORD["rate_independence"]["probes"],
                         ids=lambda p: f"{p['market']}-{p['value_ratio']}")
def test_the_price_does_not_move_with_the_risk_free_rate(probe):
    """Hull p.628: the growth rate and the discount rate cancel."""
    assert probe["rates"] == [0.0, 0.08, -0.02]
    assert probe["spread"] < 1e-11
    assert probe["prices"][0] == pytest.approx(probe["prices"][1], abs=1e-11)
    assert probe["prices"][0] == pytest.approx(probe["prices"][2], abs=1e-11)


@pytest.mark.parametrize("row", ROWS, ids=lambda row: f"{row['market']}-{row['value_ratio']}")
def test_the_numeraire_reinterpretation_prices_the_same_contract(row):
    """Hull p.628: U0 calls on V/U struck at 1.0, rate qU, dividend yield qV."""
    spread = exchange.spread_volatility(market_of(row))
    restated = row["spot_u"] * bsm.call_price(
        row["spot_v"] / row["spot_u"], 1.0, row["yield_u"], spread, row["expiry"],
        q=row["yield_v"],
    )
    assert restated == pytest.approx(row["conditional"], abs=2e-9, rel=1e-10)


@pytest.mark.parametrize("item", RECORD["decomposition"]["rows"],
                         ids=lambda i: f"{i['market']}-{i['value_ratio']}")
def test_better_of_and_worse_of_decompose_into_the_exchange_option(item):
    """Hull p.628, with both sides priced directly rather than assumed."""
    assert abs(item["better_residual"]) < 1e-9
    assert abs(item["worse_residual"]) < 1e-9
    assert abs(item["sum_residual"]) < 1e-9
    assert item["better_of"] >= item["worse_of"]
    assert item["exchange"] >= 0.0


def test_the_decomposition_is_not_a_tautology_of_the_recorded_numbers():
    """A wrong spread volatility must break the decomposition residuals."""
    # A market with zero correlation would hide the mistake, so pick a correlated one.
    item = next(i for i in RECORD["decomposition"]["rows"]
                if next(r for r in ROWS if r["market"] == i["market"]
                        and r["value_ratio"] == i["value_ratio"])["correlation"] != 0.0)
    row = next(r for r in ROWS if r["market"] == item["market"]
               and r["value_ratio"] == item["value_ratio"])
    market = market_of(row)
    forward_u = row["spot_u"] * math.exp(-market.yield_u * market.expiry)
    wrong = math.sqrt(market.volatility_u**2 + market.volatility_v**2)  # cross term dropped
    scale = wrong * math.sqrt(market.expiry)
    ratio_forward = (row["spot_v"] / row["spot_u"]) * math.exp(
        (market.yield_u - market.yield_v) * market.expiry)
    d1 = (math.log(ratio_forward) + 0.5 * scale**2) / scale
    mispriced = forward_u * (ratio_forward * _cdf(d1) - _cdf(d1 - scale))
    assert abs(item["better_of"] - (forward_u + mispriced)) > 1e-3


def _cdf(x):
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


@pytest.mark.parametrize("row", RECORD["correlation_limits"]["rows"],
                         ids=lambda r: f"rho{r['correlation']}-{r['value_ratio']}")
def test_the_option_collapses_onto_the_forward_spread(row):
    """As the ratio volatility vanishes only the discounted spread is left."""
    assert row["price"] >= row["discounted_forward_spread"] - 1e-12
    assert row["excess_over_forward"] >= 0.0
    if row["spread_volatility"] < 0.03:
        assert row["excess_over_forward"] < 1e-12


def test_the_collapse_is_monotone_in_the_correlation():
    rows = [r for r in RECORD["correlation_limits"]["rows"] if r["value_ratio"] == 1.25]
    excess = [r["excess_over_forward"] for r in rows]
    assert rows[0]["correlation"] < rows[-1]["correlation"]
    assert excess[0] > excess[-1]


@pytest.mark.parametrize("row", RECORD["american"]["rows"],
                         ids=lambda r: f"{r['market']}-{r['value_ratio']}")
def test_the_american_tree_reproduces_the_european_price(row):
    """Rubinstein's route priced on a CRR tree on V/U; residual is a grid effect."""
    assert abs(row["tree_residual"]) < 0.01
    assert row["american_tree"] >= row["european_tree"] - 1e-12


def test_early_exercise_is_worthless_without_a_yield_on_the_asset_received():
    american = RECORD["american"]
    assert american["max_premium_without_yield"] < 1e-9
    assert american["max_premium_with_yield"] > 1.0
    for row in american["rows"]:
        if row["yield_v"] == 0.0:
            assert row["early_exercise_premium"] < 1e-9
        elif row["value_ratio"] == 1.25:
            assert row["early_exercise_premium"] > 0.0


def test_the_library_reproduces_the_printed_free_example_both_ways():
    """Section 26.14 prints no worked example, so the pinned case is our own."""
    assert RECORD["limitations"][3].startswith("Section 26.14 prints no worked example")
    market = exchange.Market("pinned", 0.2, 0.2, 0.5, 0.0, 0.0, 1.0)
    reference = exchange.conditional_price(100.0, 100.0, market)
    assert reference == pytest.approx(7.965567, abs=1e-6)
    assert exotics.exchange_option(100.0, 100.0, 0.2, 0.2, 0.5, 1.0) == pytest.approx(
        reference, abs=1e-12
    )


def test_dropping_the_cross_term_is_detected_by_every_row():
    """The common mistake in sigma-hat must fail the reference comparison."""
    failures = 0
    for row in ROWS:
        if row["correlation"] == 0.0:
            continue  # the cross term is zero here, so the error is invisible by construction
        market = market_of(row)
        wrong = math.sqrt(market.volatility_u**2 + market.volatility_v**2)
        scale = wrong * math.sqrt(market.expiry)
        ratio_forward = (row["spot_v"] / row["spot_u"]) * math.exp(
            (market.yield_u - market.yield_v) * market.expiry)
        d1 = (math.log(ratio_forward) + 0.5 * scale**2) / scale
        mispriced = row["spot_u"] * math.exp(-market.yield_u * market.expiry) * (
            ratio_forward * _cdf(d1) - _cdf(d1 - scale))
        if abs(mispriced - row["conditional"]) > max(2e-9, 2e-11 * abs(row["conditional"])):
            failures += 1
    assert failures == len([row for row in ROWS if row["correlation"] != 0.0])
