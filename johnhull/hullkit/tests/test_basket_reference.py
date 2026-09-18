"""Independent numerical reference tests for positive European baskets."""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))


def test_one_asset_exact_moments():
    from build_basket_reference import moments_direct

    m1, m2 = moments_direct([100.0], [1.0], .05, [.02], [.2], [[1.0]], 1.0)
    want = 100.0 * math.exp(.03)
    assert m1 == pytest.approx(want)
    assert m2 == pytest.approx(want * want * math.exp(.04))


@pytest.mark.parametrize("kind, expected", [("call", 4.77934047324348), ("put", 4.77934047324348)])
def test_conditional_integral_against_one_random_asset(kind, expected):
    # Cash 40 plus an ATM lognormal of forward 60: 60*(2*Phi(.1)-1).
    from build_basket_reference import conditional_two_asset
    value, error = conditional_two_asset(
        [100., 100.], [.4, .6], 100., 0., [0., 0.], [0., .2],
        [[1., .4], [.4, 1.]], 1., kind)
    assert value == pytest.approx(expected, abs=1e-10)
    assert error < 1e-8


def test_conditional_integral_refuses_singular_correlation():
    from build_basket_reference import conditional_two_asset
    with pytest.raises(ValueError, match="nondegenerate"):
        conditional_two_asset([100., 100.], [.5, .5], 100., .05, [0., 0.],
                              [.2, .2], [[1., 1.], [1., 1.]], 1.)


@pytest.mark.parametrize("rho, vols, rate, expiry", [
    (.35, [.2, .3], .03, 1.), (-.65, [.65, .4], -.01, 2.)
])
def test_mc_matches_conditional_integral_and_pathwise_parity(rho, vols, rate, expiry):
    from build_basket_reference import conditional_two_asset, simulate

    corr = [[1., rho], [rho, 1.]]
    args = ([100., 80.], [.6, .5], rate, [.01, .025], vols, corr, expiry)
    result = simulate(*args, strikes=[80., 100., 120.], paths=120_000, seed=1926)
    first = .6*100*math.exp((rate-.01)*expiry) + .5*80*math.exp((rate-.025)*expiry)
    for strike in [80., 100., 120.]:
        for kind in ["call", "put"]:
            expected, _ = conditional_two_asset(args[0], args[1], strike, *args[2:], kind)
            row = result[(strike, kind)]
            assert abs(row["price"] - expected) < 4 * row["standard_error"]
            assert row["standard_error"] > 0
            if kind == "call":
                assert row["standard_error"] < row["raw_standard_error"]
        assert result[(strike, "call")]["price"] - result[(strike, "put")]["price"] == pytest.approx(
            math.exp(-rate*expiry)*(first-strike), abs=1e-12)
        assert result[(strike, "call")]["standard_error"] == result[(strike, "put")]["standard_error"]


def test_mc_singular_psd_and_reproducibility():
    from build_basket_reference import simulate

    args = ([100., 80.], [.6, .5], .03, [.01, .01], [.2, .2], [[1., 1.], [1., 1.]], 1.)
    first = simulate(*args, strikes=[100.], paths=5000, seed=912)
    assert first == simulate(*args, strikes=[100.], paths=5000, seed=912)
    assert first[(100., "call")]["standard_error"] > 0


def test_mc_cash_basket_is_exact():
    from build_basket_reference import simulate

    row = simulate([100.], [1.], 0., [0.], [0.], [[1.]], 1.,
                   strikes=[95.], paths=1000, seed=2)[(95., "call")]
    assert row["price"] == 5.
    assert row["standard_error"] == 0.


def test_moment_match_is_exact_for_single_and_proportional_assets():
    from build_basket_reference import moment_match_price

    # Zero-rate ATM 100 with sigma .2: 100*(2 Phi(.1)-1).
    for spots, weights, vol, corr in [
        ([100.], [1.], [.2], [[1.]]),
        ([100., 100.], [.4, .6], [.2, .2], [[1., 1.], [1., 1.]]),
    ]:
        assert moment_match_price(spots, weights, 100., 0., [0.]*len(spots),
                                  vol, corr, 1., "call") == pytest.approx(7.96556745540580, abs=1e-12)


def test_generator_content_is_reproducible_and_market_grid_complete():
    from build_basket_reference import build_artifacts

    prices, record = build_artifacts(paths=1000, pilot_paths=1000)
    assert (prices, record) == build_artifacts(paths=1000, pilot_paths=1000)
    ordinary = [row for row in prices["rows"] if row["anchor"] is None]
    assert len(ordinary) == 48
    assert len({row["market"] for row in ordinary if len(row["spots"]) == 2}) == 6
    assert len({row["market"] for row in ordinary if len(row["spots"]) == 3}) == 2
    assert all(row["conditional_tail_bound"] < 1e-20 for row in ordinary
               if row["conditional"] is not None)


def test_saved_reference_uncertainty_and_summary_are_recomputed():
    import json

    root = Path(__file__).resolve().parents[2] / "docs" / "validation" / "section-26-15"
    prices = json.loads((root / "prices.json").read_text())
    record = json.loads((root / "numerical-check.json").read_text())
    rows = prices["rows"]
    anchored = [row for row in rows if row["reference_method"] != "mc"
                and row["standard_error"] > 1e-14]
    worst = max(abs(row["mc"]-row["reference"])/row["standard_error"] for row in anchored)
    assert worst < 4.
    assert record["mc_validation"]["max_standard_errors"] == pytest.approx(worst)
    eligible = [row for row in rows if row["reference"] >= record["price_floor"]]
    assert record["approximation_error"]["max_absolute"] == pytest.approx(
        max(abs(row["approximation"]-row["reference"]) for row in rows))
    assert record["approximation_error"]["max_relative"] == pytest.approx(
        max(abs(row["approximation"]-row["reference"])/row["reference"] for row in eligible))
    for row in rows:
        assert row["error_sign_established"] == (
            abs(row["approximation"]-row["reference"]) > row["reference_uncertainty"])
