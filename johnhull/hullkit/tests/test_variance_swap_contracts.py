"""§26.16 contract helpers and the library measured against the independent reference.

The reference JSON and generator (``scripts/build_variance_swap_reference.py``) are
test inputs only; ``hullkit.variance_swaps`` never imports them.
"""

import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest
from hullkit import variance_swaps as vs

PROJECT = Path(__file__).resolve().parents[2]
REFERENCE = json.loads(
    (PROJECT / "docs/validation/section-26-16/reference.json").read_text(encoding="utf-8")
)
sys.path.insert(0, str(PROJECT / "scripts"))


def test_realized_variance_matches_hull_formula_by_hand():
    """Hull p.629: sigma^2 = 252/(n-2) * sum ln(S_{i+1}/S_i)^2 with zero mean."""
    prices = [100.0, 101.0, 99.0, 100.5, 102.0]
    logs = [math.log(b / a) for a, b in itertools.pairwise(prices)]
    squares = math.fsum(x * x for x in logs)
    assert vs.realized_variance(prices) == pytest.approx(252.0 * squares / 3.0, rel=1e-15)
    assert vs.realized_variance(prices, denominator="n-1") == pytest.approx(
        252.0 * squares / 4.0, rel=1e-15
    )
    assert vs.realized_volatility(prices) == pytest.approx(
        math.sqrt(252.0 * squares / 3.0), rel=1e-15
    )
    assert vs.realized_variance(prices, periods_per_year=365) == pytest.approx(
        365.0 * squares / 3.0, rel=1e-15
    )


def test_realized_variance_expectation_matches_independent_reference():
    """Library estimator on simulated GBM paths vs the reference's exact expectation."""
    block = REFERENCE["realized_variance"]
    n, sigma, drift = block["observations"], block["sigma"], block["log_drift"]
    rng = np.random.default_rng(11)
    returns = rng.normal(drift / 252, sigma / math.sqrt(252), size=(40_000, n - 1))
    paths = 100.0 * np.exp(np.concatenate([np.zeros((40_000, 1)), np.cumsum(returns, 1)], 1))
    for row in block["rows"]:
        estimates = np.array(
            [vs.realized_variance(path, denominator=row["denominator"]) for path in paths]
        )
        se = estimates.std(ddof=1) / math.sqrt(len(estimates))
        assert abs(estimates.mean() - row["exact_expectation"]) < 4 * se


@pytest.mark.parametrize(
    "prices, kwargs, match",
    [
        ([100.0, 101.0], {}, "at least 3"),
        ([100.0], {"denominator": "n-1"}, "at least 2"),
        ([100.0, 0.0, 101.0], {}, "finite and > 0"),
        ([100.0, math.nan, 101.0], {}, "finite and > 0"),
        ([[100.0, 101.0, 102.0]], {}, "1-D"),
        ([100.0, 101.0, 102.0], {"denominator": "n"}, "denominator"),
        ([100.0, 101.0, 102.0], {"periods_per_year": 0.0}, "periods_per_year"),
    ],
)
def test_realized_variance_validation(prices, kwargs, match):
    with pytest.raises(ValueError, match=match):
        vs.realized_variance(prices, **kwargs)


def test_variance_notional_matches_first_order_volatility_exposure():
    """Hull p.629: L_var = L_vol / (2 sigma_K); both payoffs share slope L_vol at sigma_K."""
    notional = vs.variance_notional(100.0, 0.23)
    assert notional == pytest.approx(100.0 / 0.46, rel=1e-15)
    h = 1e-6
    slope = notional * (((0.23 + h) ** 2) - ((0.23 - h) ** 2)) / (2 * h)
    assert slope == pytest.approx(100.0, rel=1e-9)
    with pytest.raises(ValueError, match="volatility_strike"):
        vs.variance_notional(100.0, 0.0)
    with pytest.raises(ValueError, match="volatility_notional"):
        vs.variance_notional(math.inf, 0.2)


def test_example_26_4_library_equals_independent_reference():
    example = REFERENCE["example_26_4"]
    got = vs.fair_variance_from_implied_vols(
        1020.0,
        [row["strike"] for row in example["rows"]],
        [row["implied_volatility"] for row in example["rows"]],
        0.04,
        0.25,
        0.01,
    )
    assert got == pytest.approx(example["expected_variance"], abs=1e-14)
    value = vs.variance_swap_value(got, 0.045, 0.04, 0.25, notional=100.0)
    assert value == pytest.approx(example["swap_value"], abs=1e-12)
    cumulative = vs.vix_cumulative_variance(
        [row["strike"] for row in example["rows"]],
        [row["q"] for row in example["rows"]],
        example["forward"],
        0.04,
        0.25,
    )
    assert cumulative == pytest.approx(
        REFERENCE["vix"]["example_26_4"]["cumulative_variance_26_10"], abs=1e-15
    )


def test_library_strip_equals_independent_strip_on_heston_smile():
    """Library eq. 26.6/26.8 on the reference's Heston prices reproduces every saved strip."""
    import build_variance_swap_reference as ref

    block = REFERENCE["strip_convergence"]
    market = next(m for m in ref.HESTON_MARKETS if m["name"] == block["market"])
    pricer = ref.heston_pricer(
        ref.HESTON_SPOT,
        ref.HESTON_RATE,
        ref.HESTON_DIVIDEND,
        market["expiry"],
        **{key: market[key] for key in ("v0", "kappa", "theta", "xi", "rho")},
    )
    for family in block["families"]:
        for row in family["rows"][:2]:
            step = row["delta_k"]
            strikes = np.arange(family["strike_low"], family["strike_high"] + step / 2, step)
            # Lewis prices of far out-of-the-money calls carry ~1e-11 of cancellation
            # noise of either sign; the library rightly rejects negative quotes.
            prices = [tuple(max(v, 0.0) for v in pricer(float(k))) for k in strikes]
            s_star = vs.default_s_star(strikes, block["forward"])
            q = vs.otm_option_prices(
                strikes, [p[0] for p in prices], [p[1] for p in prices], s_star
            )
            got = vs.fair_variance(strikes, q, block["forward"], ref.HESTON_RATE, block["expiry"])
            assert got == pytest.approx(row["expected_variance"], abs=1e-13)
            assert s_star == row["s_star"]


def test_expected_volatility_equals_reference_approximation_and_misses_exact():
    for row in REFERENCE["volatility_convexity"]["rows"]:
        approx = vs.expected_volatility(row["expected_variance"], row["variance_of_variance"])
        assert approx == pytest.approx(row["approximation"], abs=1e-15)
        assert approx <= row["exact_expected_volatility"]
        assert approx < math.sqrt(row["expected_variance"])


def test_vix_index_interpolates_cumulative_variance():
    sigma = 0.2
    assert vs.vix_index(23 / 365, sigma**2 * 23 / 365, 37 / 365, sigma**2 * 37 / 365) == (
        pytest.approx(sigma, abs=1e-15)
    )
    block = REFERENCE["vix"]["interpolation"]
    import build_variance_swap_reference as ref

    market = next(m for m in ref.HESTON_MARKETS if m["name"] == block["market"])

    def cumulative(days):
        term = days / 365
        return (
            ref.heston_expected_variance(market["v0"], market["kappa"], market["theta"], term)
            * term
        )

    got = vs.vix_index(
        block["near_days"] / 365,
        cumulative(block["near_days"]),
        block["next_days"] / 365,
        cumulative(block["next_days"]),
    )
    assert got == pytest.approx(block["interpolated_volatility"], abs=1e-15)


@pytest.mark.parametrize(
    "args, match",
    [
        ((37 / 365, 0.004, 23 / 365, 0.003), "near_term < next_term"),
        ((31 / 365, 0.004, 37 / 365, 0.005), "bracket"),
        ((23 / 365, -0.001, 37 / 365, 0.005), "cumulative variances"),
        ((0.0, 0.0, 37 / 365, 0.005), "near_term"),
    ],
)
def test_vix_index_validation(args, match):
    with pytest.raises(ValueError, match=match):
        vs.vix_index(*args)
