"""Known cash dividends in hullkit.bsm (audit item OP-04).

Hull 11e *Global Edition* §11.7 pp.262-263 (eqs. 11.8-11.11) and §15.12
pp.360-363 (Example 15.9, eqs. 15.23-15.25, Black's approximation). In the GE
PDF the printed page number equals the PDF page index, so ``p.NNN`` is both.

GE §15.12 describes Black's approximation (p.363) but prints no numerical
example for it, and the end-of-chapter Problems 15.13 / 15.19 print no answers.
The approximation is therefore pinned by its defining identity and its ordering
against the European value (it is not a bound on an escrowed-dividend tree: its
two legs apply sigma to different risky components, e.g. S=40, K=35, r=5%,
sigma=20%, T=0.5, dividends 0.5 at 0.2 and 3.0 at 0.45 give Black 5.642 against
a 1,000-step escrowed CRR American value of 5.577), and the
Problem inputs are used only for the early-exercise conditions, whose
thresholds are plain arithmetic.
"""

import math

import numpy as np
import pytest
from hullkit import bsm
from scipy.stats import norm

# Hull 11e GE Example 15.9 p.360-361.
EX159 = dict(S=40.0, K=40.0, r=0.09, sigma=0.30, T=0.5)
EX159_TIMES = [2.0 / 12.0, 5.0 / 12.0]
EX159_AMOUNTS = [0.5, 0.5]


def test_example_15_9_pv_of_dividends_hull_ge():
    """Hull 11e GE §15.12 p.360, Example 15.9: 0.5e^{-0.09x2/12} + 0.5e^{-0.09x5/12} = 0.9742."""
    pv = bsm.pv_dividends(EX159_TIMES, EX159_AMOUNTS, EX159["r"], EX159["T"])
    assert pv == pytest.approx(0.9742, abs=5e-5)
    assert pv == pytest.approx(0.5 * math.exp(-0.015) + 0.5 * math.exp(-0.0375), abs=1e-15)


def test_example_15_9_d1_d2_and_call_price_hull_ge():
    """Hull 11e GE §15.12 p.361, Example 15.9: S0 - D = 39.0258, d1 = 0.2020, d2 = -0.0102.

    Print: N(d1) = 0.5800, N(d2) = 0.4959, c = 3.67 (computed 3.6712).
    Tolerances are half a unit in the last printed digit.
    """
    pv = bsm.pv_dividends(EX159_TIMES, EX159_AMOUNTS, EX159["r"], EX159["T"])
    s_adj = EX159["S"] - pv
    assert s_adj == pytest.approx(39.0258, abs=5e-5)

    args = dict(K=EX159["K"], r=EX159["r"], sigma=EX159["sigma"], T=EX159["T"])
    d_1 = bsm.d1(s_adj, **args)
    d_2 = bsm.d2(s_adj, **args)
    assert d_1 == pytest.approx(0.2020, abs=5e-5)
    assert d_2 == pytest.approx(-0.0102, abs=5e-5)
    assert norm.cdf(d_1) == pytest.approx(0.5800, abs=5e-5)
    assert norm.cdf(d_2) == pytest.approx(0.4959, abs=5e-5)

    call = bsm.call_price_cash_dividends(
        **EX159, dividend_times=EX159_TIMES, dividend_amounts=EX159_AMOUNTS
    )
    assert call == pytest.approx(3.67, abs=5e-3)
    assert call == pytest.approx(bsm.call_price(s_adj, **args), abs=1e-14)


def test_dividends_after_maturity_are_ignored_hull_ge():
    """Hull 11e GE §15.12 p.360: only ex-dividend dates during the option's life count."""
    with_later = bsm.call_price_cash_dividends(
        **EX159, dividend_times=[*EX159_TIMES, 0.75], dividend_amounts=[*EX159_AMOUNTS, 5.0]
    )
    base = bsm.call_price_cash_dividends(
        **EX159, dividend_times=EX159_TIMES, dividend_amounts=EX159_AMOUNTS
    )
    assert with_later == base
    assert bsm.pv_dividends([0.75], [5.0], 0.09, T=0.5) == 0.0
    assert bsm.pv_dividends([0.75], [5.0], 0.09) == pytest.approx(5.0 * math.exp(-0.0675))


@pytest.mark.parametrize(("times", "amounts"), [([], []), ([0.1, 0.3], [0.0, 0.0]), ([0.9], [1.0])])
def test_no_dividend_in_life_reduces_exactly_to_bsm(times, amounts):
    """D = 0 must return exactly `bsm.call_price` / `bsm.put_price` (no float drift)."""
    S, K, r, sigma, T = 42.0, 40.0, 0.10, 0.20, 0.5
    assert bsm.call_price_cash_dividends(S, K, r, sigma, T, times, amounts) == bsm.call_price(
        S, K, r, sigma, T
    )
    assert bsm.put_price_cash_dividends(S, K, r, sigma, T, times, amounts) == bsm.put_price(
        S, K, r, sigma, T
    )
    assert bsm.black_american_call_approx(S, K, r, sigma, T, times, amounts) == bsm.call_price(
        S, K, r, sigma, T
    )


def test_vector_strikes_match_scalar_loop():
    strikes = np.array([35.0, 40.0, 45.0])
    vector = bsm.put_price_cash_dividends(40.0, strikes, 0.09, 0.3, 0.5, EX159_TIMES, EX159_AMOUNTS)
    scalar = [
        bsm.put_price_cash_dividends(40.0, k, 0.09, 0.3, 0.5, EX159_TIMES, EX159_AMOUNTS)
        for k in strikes
    ]
    np.testing.assert_allclose(vector, scalar, rtol=0, atol=1e-13)


def test_put_call_parity_and_bounds_with_dividends_hull_ge():
    """Hull 11e GE §11.7 p.263, eqs. (11.8)-(11.11) on the Example 15.9 prices."""
    S, K, r, sigma, T = 40.0, 40.0, 0.09, 0.30, 0.5
    D = bsm.pv_dividends(EX159_TIMES, EX159_AMOUNTS, r, T)
    for k in (30.0, 40.0, 50.0):
        c = bsm.call_price_cash_dividends(S, k, r, sigma, T, EX159_TIMES, EX159_AMOUNTS)
        p = bsm.put_price_cash_dividends(S, k, r, sigma, T, EX159_TIMES, EX159_AMOUNTS)
        assert bsm.put_call_parity_residual(c, p, S, k, r, T, D) == pytest.approx(0.0, abs=1e-12)
        assert c >= bsm.european_call_lower_bound(S, k, r, T, D)
        assert p >= bsm.european_put_lower_bound(S, k, r, T, D)
        lower, upper = bsm.american_call_put_bounds(S, k, r, T, D)
        # European c - p = S0 - D - K e^{-rT} lies inside the American bounds (11.11).
        assert lower <= c - p <= upper

    # The bounds themselves (exact arithmetic).
    assert bsm.european_call_lower_bound(S, 30.0, r, T, D) == pytest.approx(
        S - D - 30.0 * math.exp(-r * T), abs=1e-14
    )
    assert bsm.european_put_lower_bound(S, 50.0, r, T, D) == pytest.approx(
        D + 50.0 * math.exp(-r * T) - S, abs=1e-14
    )
    assert bsm.european_call_lower_bound(S, 50.0, r, T, D) == 0.0
    assert bsm.american_call_put_bounds(S, K, r, T, D) == pytest.approx(
        (S - D - K, S - K * math.exp(-r * T)), abs=1e-14
    )
    # D = 0 recovers eqs. (11.4) and (11.5).
    assert bsm.european_call_lower_bound(S, 30.0, r, T) == pytest.approx(
        S - 30.0 * math.exp(-r * T), abs=1e-14
    )


@pytest.mark.parametrize(
    ("S", "K", "r", "sigma", "T", "times", "amounts", "thresholds"),
    [
        # Problem 15.13 p.366: S=70, K=65, r=10%, T=8m, sigma=32%, $1 at 3m and 6m.
        (70.0, 65.0, 0.10, 0.32, 8 / 12, [3 / 12, 6 / 12], [1.0, 1.0], (1.6049, 1.0744)),
        # Problem 15.19 p.367: S=50, K=55, r=8%, T=15m, sigma=25%, $1.50 at 4m and 10m.
        (50.0, 55.0, 0.08, 0.25, 15 / 12, [4 / 12, 10 / 12], [1.5, 1.5], (2.1566, 1.8031)),
    ],
)
def test_problems_15_13_and_15_19_never_optimal_to_exercise_early_hull_ge(
    S, K, r, sigma, T, times, amounts, thresholds
):
    """Hull 11e GE §15.12 p.362, eqs. (15.23) and (15.25) on Problems 15.13 / 15.19.

    The Problems ask to show early exercise is never optimal on either
    dividend date; the thresholds K(1 - e^{-r(t_{i+1}-t_i)}) are computed
    here (no printed answer). With every condition False, Black's
    approximation must collapse to the European call.
    """
    got = bsm.call_early_exercise_thresholds(K, r, T, times)
    np.testing.assert_allclose(got, thresholds, rtol=0, atol=5e-5)
    flags = bsm.call_early_exercise_can_be_optimal(K, r, T, times, amounts)
    assert flags.tolist() == [False, False]
    european = bsm.call_price_cash_dividends(S, K, r, sigma, T, times, amounts)
    assert bsm.black_american_call_approx(S, K, r, sigma, T, times, amounts) == european


def test_early_exercise_condition_flags_large_dividend_near_maturity():
    """Eq. (15.24) p.362 holds for a large final dividend close to T."""
    flags = bsm.call_early_exercise_can_be_optimal(40.0, 0.05, 0.5, [0.25, 0.45], [0.1, 2.0])
    assert flags.tolist() == [False, True]
    # A dividend exactly at maturity has threshold 0.
    assert bsm.call_early_exercise_thresholds(40.0, 0.05, 0.5, [0.5]).tolist() == [0.0]
    # Dates after T are dropped, so the output aligns with the in-life dates.
    assert bsm.call_early_exercise_thresholds(40.0, 0.05, 0.5, [0.25, 0.75]).shape == (1,)


def test_black_approximation_takes_the_larger_european_leg_hull_ge():
    """Hull 11e GE §15.12 p.363: max(European to T, European to just before t_n).

    A large dividend just before maturity makes the t_n leg dominate, so the
    approximation is strictly above the European call. The t_n leg removes only
    the dividends paid before t_n (exercise just before t_n keeps D_n).
    """
    S, K, r, sigma, T = 40.0, 35.0, 0.05, 0.20, 0.5
    times, amounts = [0.2, 0.45], [0.5, 3.0]
    european = bsm.call_price_cash_dividends(S, K, r, sigma, T, times, amounts)
    black = bsm.black_american_call_approx(S, K, r, sigma, T, times, amounts)

    t_n_leg = bsm.call_price(S - 0.5 * math.exp(-r * 0.2), K, r, sigma, 0.45)
    assert black == pytest.approx(max(european, t_n_leg), abs=1e-14)
    assert black == t_n_leg
    assert black > european + 0.5


def test_black_approximation_never_below_european_on_a_grid():
    rng = np.random.default_rng(1509)
    for _ in range(50):
        S = rng.uniform(20.0, 60.0)
        K = rng.uniform(20.0, 60.0)
        T = rng.uniform(0.1, 2.0)
        times = np.sort(rng.uniform(0.0, 1.2 * T, size=3))
        amounts = rng.uniform(0.0, 2.0, size=3)
        r, sigma = rng.uniform(0.0, 0.1), rng.uniform(0.05, 0.6)
        european = bsm.call_price_cash_dividends(S, K, r, sigma, T, times, amounts)
        black = bsm.black_american_call_approx(S, K, r, sigma, T, times, amounts)
        assert black >= european


@pytest.mark.parametrize(
    ("times", "amounts", "match"),
    [
        ([0.1, 0.2], [0.5], "equal length"),
        ([0.3, 0.2], [0.5, 0.5], "strictly increasing"),
        ([0.2, 0.2], [0.5, 0.5], "strictly increasing"),
        ([-0.1], [0.5], "dividend_times must contain only finite values >= 0"),
        ([np.nan], [0.5], "dividend_times must contain only finite values >= 0"),
        ([0.1], [-0.5], "dividend_amounts must contain only finite values >= 0"),
        (0.1, 0.5, "1-D sequences"),
    ],
)
def test_dividend_schedule_validation(times, amounts, match):
    with pytest.raises(ValueError, match=match):
        bsm.call_price_cash_dividends(40.0, 40.0, 0.09, 0.3, 0.5, times, amounts)
    with pytest.raises(ValueError, match=match):
        bsm.black_american_call_approx(40.0, 40.0, 0.09, 0.3, 0.5, times, amounts)


def test_price_and_scalar_validation():
    with pytest.raises(ValueError, match=r"S - PV\(dividends\) must be > 0"):
        bsm.call_price_cash_dividends(1.0, 1.0, 0.0, 0.3, 0.5, [0.1], [1.0])
    with pytest.raises(ValueError, match=r"S - PV\(dividends\) must be > 0"):
        bsm.black_american_call_approx(1.0, 1.0, 0.0, 0.3, 0.5, [0.1, 0.2], [0.9, 0.5])
    with pytest.raises(ValueError, match="S must contain only finite values > 0"):
        bsm.put_price_cash_dividends(-1.0, 40.0, 0.09, 0.3, 0.5, [0.1], [0.5])
    with pytest.raises(ValueError, match="T must be a finite scalar"):
        bsm.call_price_cash_dividends(40.0, 40.0, 0.09, 0.3, np.array([0.5, 1.0]), [0.1], [0.5])
    with pytest.raises(ValueError, match="r must be a finite scalar"):
        bsm.pv_dividends([0.1], [0.5], np.nan)
    with pytest.raises(ValueError, match="K must be > 0"):
        bsm.call_early_exercise_thresholds(0.0, 0.05, 0.5, [0.1])
    with pytest.raises(
        ValueError, match=r"D \(present value of dividends\) must be finite and >= 0"
    ):
        bsm.european_call_lower_bound(40.0, 40.0, 0.05, 0.5, D=-1.0)
    with pytest.raises(ValueError, match="T must be finite and >= 0"):
        bsm.american_call_put_bounds(40.0, 40.0, 0.05, -0.5)
