"""Printed-value pins for Hull 11e Global Edition Chapters 1, 24, 35 and 36.

Audit items (2026-09-14 section audit):

- CR-02: §24.7 Examples 24.5 / 24.6 (own-credit discounting, forward-contract CVA).
- CR-03: §24.8 Example 24.7 (Gaussian copula default-time thresholds + simulation).
- CR-04: §24.2 Table 24.1, §24.5 Tables 24.2-24.3, §24.6 Example 24.3 (Merton).
- CR-20: §35.4 Examples 35.1-35.2 and the seasonality interpolation, §35.7
  Example 35.4, §36.1 NPV, §36.2 Example 36.1, §36.3 Example 36.2, and the
  §1.7-1.9 hedging / speculation / arbitrage arithmetic.

Each test reproduces one printed example or table with the hullkit function that
implements the section, pins it at the print's rounding, and adds a tighter pin
on the computed value so a silent drift inside the rounding band is still
caught. Page numbers are PDF pages of the Global Edition PDF; they coincide with
the printed folios. Where no hullkit function offers a needed formula, the glue
is inline numpy/scipy and the docstring says so. No tolerance was loosened to
make a value pass; every printed value below reproduced within its rounding.
"""

import math

import numpy as np
import pytest
from hullkit import bsm, copula, credit, rates, xva
from scipy.stats import norm

# ---------------------------------------------------------------------------
# CR-04: historical default probabilities, hazard rates, Merton (GE §24.2-24.6)
# ---------------------------------------------------------------------------


def test_default_probabilities_hull_table_24_1():
    """Hull 11e GE §24.2 p.563, Table 24.1 (S&P cumulative default rates, %).

    BBB: 0.16% by year 1 and 0.45% by year 2, so the unconditional probability of
    a default during year 2 prints as 0.45 - 0.16 = 0.29%. CCC/C: 36.64% by
    year 2 and 41.41% by year 3, so the unconditional year-3 probability is
    41.41 - 36.64 = 4.77% and the probability conditional on surviving year 2 is
    0.0477 / 0.6336 = 7.53%. Pure table arithmetic (no hullkit function computes
    a conditional probability from a cumulative table); the tolerance is half a
    unit of the last printed decimal of a percentage (5e-5 on a decimal fraction).
    """
    q_bbb = {1: 0.0016, 2: 0.0045}
    q_ccc = {2: 0.3664, 3: 0.4141}

    bbb_year_2 = q_bbb[2] - q_bbb[1]
    assert bbb_year_2 == pytest.approx(0.0029, abs=5e-5)

    ccc_year_3 = q_ccc[3] - q_ccc[2]
    assert ccc_year_3 == pytest.approx(0.0477, abs=5e-5)

    ccc_year_3_conditional = ccc_year_3 / (1.0 - q_ccc[2])
    assert ccc_year_3_conditional == pytest.approx(0.0753, abs=5e-5)
    assert ccc_year_3_conditional == pytest.approx(0.075284, abs=1e-6)


def test_bbb_seven_year_average_hazard_hull_section_24_5():
    """Hull 11e GE §24.5 p.567 (Baa/BBB seven-year hazard from Table 24.1).

    Q(7) = 2.33% for BBB in Table 24.1; the text inverts eq. (24.1) (cited there
    as "equation (24.10)", a GE typo) to lambda(7) = -(1/7) ln[1 - Q(7)] and
    prints 0.0034, i.e. 0.34% or 34 basis points. hullkit exposes only the
    forward map `credit.default_prob(t, hazard)`, so the inversion is inline;
    the round trip through `default_prob` recovers 2.33% exactly (1e-12), and
    the hazard is pinned at the print rounding (5e-5) and at 3.368e-3 (1e-6).
    """
    q_7 = 0.0233
    hazard_7 = -math.log(1.0 - q_7) / 7.0
    assert hazard_7 == pytest.approx(0.0034, abs=5e-5)
    assert hazard_7 == pytest.approx(3.36796e-3, abs=1e-6)
    assert credit.default_prob(7.0, hazard_7) == pytest.approx(q_7, abs=1e-12)


def test_baa_hazard_and_excess_return_hull_tables_24_2_and_24_3():
    """Hull 11e GE §24.5 p.567-568, Tables 24.2 and 24.3 (R = 40%).

    p.568: "The spread of the Baa (or BBB) corporate bond yield over the risk-free
    rate was about 1.8% ... Equation (24.2) gives 0.018 / (1 - 0.4) = 0.03, or
    3%" -> `credit.hazard_from_spread`. Table 24.3 column 3 is the spread that
    compensates for the historical default rate, "0.47% x 0.6 = 0.28%, or 28
    basis points" for Baa; the whole column is the Table 24.2 historical hazard
    times (1 - R), rounded to the basis point, and column 4 is column 2 minus
    column 3. hullkit has no hazard -> spread helper, so the product is inline
    and `hazard_from_spread` is used for the round trip. Tolerance: 1e-12 on the
    exact 3%, 0.5 bp on a column printed in whole basis points.
    """
    assert credit.hazard_from_spread(0.018, 0.4) == pytest.approx(0.03, abs=1e-12)

    # Table 24.2 historical seven-year hazard rates (% p.a.) and Table 24.3 columns.
    historical_hazard_pct = np.array([0.04, 0.06, 0.13, 0.47, 2.40, 7.49, 16.90])
    bond_spread_bp = np.array([40, 47, 77, 143, 304, 542, 1278], dtype=float)
    printed_historical_spread_bp = np.array([2, 4, 8, 28, 144, 449, 1014], dtype=float)
    printed_excess_return_bp = np.array([38, 43, 69, 115, 160, 93, 264], dtype=float)

    historical_spread_bp = historical_hazard_pct * (1.0 - 0.4) * 100.0
    np.testing.assert_allclose(historical_spread_bp, printed_historical_spread_bp, atol=0.5)
    assert historical_spread_bp[3] == pytest.approx(28.2, abs=1e-9)  # Baa, unrounded
    np.testing.assert_allclose(
        bond_spread_bp - printed_historical_spread_bp, printed_excess_return_bp, atol=1e-9
    )

    # Round trip: the printed 28 bp implies a hazard of 0.47% back through eq. (24.2).
    assert credit.hazard_from_spread(0.0028, 0.4) == pytest.approx(0.0047, abs=5e-5)


def test_merton_debt_value_and_expected_loss_hull_example_24_3():
    """Hull 11e GE §24.6 p.571, Example 24.3 (Merton model).

    E0 = 3, sigma_E = 80%, D = 10, r = 5%, T = 1. `test_credit.py` already pins
    V0 = 12.40, sigma_V = 0.2123 and N(-d2) = 12.7%; this test pins the rest of
    the printed chain: d2 = 1.1408, the market value of the debt V0 - E0 = 9.40,
    the no-default value 10 e^{-0.05} = 9.51, and the expected loss
    (9.51 - 9.40) / 9.51 "about 1.2%". `credit.merton_default_prob` returns
    (V0, sigma_V, Q); d2 is recovered as -N^{-1}(Q). Tolerances: 5e-5 on d2 at
    four decimals, 5e-3 on the two-decimal money amounts, 5e-4 on a percentage
    printed to one decimal (the computed loss is 1.229%, inside that band).
    """
    E0, sigma_E, D, r, T = 3.0, 0.80, 10.0, 0.05, 1.0
    v0, sigma_v, q = credit.merton_default_prob(E0, sigma_E, D, r, T)

    d2 = -norm.ppf(q)
    assert d2 == pytest.approx(1.1408, abs=5e-5)
    d2_direct = (math.log(v0 / D) + (r - 0.5 * sigma_v**2) * T) / (sigma_v * math.sqrt(T))
    assert d2_direct == pytest.approx(d2, abs=1e-9)

    debt_value = v0 - E0
    assert debt_value == pytest.approx(9.40, abs=5e-3)
    assert debt_value == pytest.approx(9.39539, abs=1e-5)

    no_default_value = D * math.exp(-r * T)
    assert no_default_value == pytest.approx(9.51, abs=5e-3)

    expected_loss = (no_default_value - debt_value) / no_default_value
    assert expected_loss == pytest.approx(0.012, abs=5e-4)
    assert expected_loss == pytest.approx(0.012290, abs=1e-6)


# ---------------------------------------------------------------------------
# CR-02: credit risk in derivatives transactions (GE §24.7)
# ---------------------------------------------------------------------------


def test_option_value_with_counterparty_spread_hull_example_24_5():
    """Hull 11e GE §24.7 p.576, Example 24.5 (special case: single payoff at T).

    A 2-year uncollateralised option worth f_nd = 3 (BSM) sold by a company whose
    2-year zero-coupon yield is 1.5% above risk-free. The text values it with the
    closed form f = f_nd e^{-(y - y_nd) T} = 3 e^{-0.015 x 2} = 2.91. That form is
    inline (it needs no model). The same example run through eq. (24.5) with
    hullkit, `xva.default_probs_from_spreads` (eq. 24.2 hazard from the spread)
    feeding `xva.cva_single_payoff`, gives 3 - 0.0878 = 2.9122 for R = 40%: the
    hazard-rate route differs from the exact bond-ratio form at O((sT)^2 / (1-R))
    (here 9e-4 in value) and collapses onto it as R -> 0. Both round to the
    printed 2.91 (abs 5e-3); the closed form is also pinned at 2.91134 (1e-5).
    """
    f_nd, spread, T = 3.0, 0.015, 2.0

    f_closed_form = f_nd * math.exp(-spread * T)
    assert f_closed_form == pytest.approx(2.91, abs=5e-3)
    assert f_closed_form == pytest.approx(2.911337, abs=1e-5)

    default_probs = xva.default_probs_from_spreads([T], [spread], recovery=0.4)
    cva = xva.cva_single_payoff(f_nd, 0.4, default_probs)
    assert f_nd - cva == pytest.approx(2.91, abs=5e-3)
    assert f_nd - cva == pytest.approx(2.912213, abs=1e-5)
    assert abs((f_nd - cva) - f_closed_form) < 1e-3  # the eq. (24.2) approximation gap

    # With R = 0 the hazard route is exactly the bond-ratio closed form.
    q_zero_recovery = xva.default_probs_from_spreads([T], [spread], recovery=0.0)
    assert f_nd - xva.cva_single_payoff(f_nd, 0.0, q_zero_recovery) == pytest.approx(
        f_closed_form, abs=1e-12
    )


def test_forward_contract_cva_hull_example_24_6():
    """Hull 11e GE §24.7 p.576-577, Example 24.6 (special case: one forward).

    Long forward on 1M oz of gold, K = 1,500, F0 = 1,600, T = 2, sigma_F = 20%,
    r = 5%, R = 30%, two 1-year intervals with q1 = 2%, q2 = 3% and default at
    the midpoints t1 = 0.5, t2 = 1.5. Hull writes the expected exposure as
    w(t) = e^{-r(T-t)} [F0 N(d1(t)) - K N(d2(t))] (eq. 15A.1 on the forward) and
    v_i = w(t_i) e^{-r t_i} (1 - R) = e^{-rT} (1 - R) [F0 N(d1) - K N(d2)]. The
    bracket is Black's undiscounted call on the forward, i.e. `bsm.call_price`
    with S = F0 and r = 0 (so d1, d2 carry only sigma^2 t / 2); `xva.cva_single_payoff`
    only covers the eq. (24.5) single-payoff case and `xva.cva` assumes a constant
    hazard on a grid, so v_i and CVA = sum q_i v_i are assembled inline as Hull does.
    Printed: d1(t1) = 0.5271, d2(t1) = 0.3856, v1 = 92.67, v2 = 130.65, CVA = 5.77,
    f_nd = (F0 - K) e^{-rT} = 90.48, f = 84.71. The DVA-side exposure is the
    matching put; put-call parity at r = 0 gives call - put = F0 - K, which
    discounts to f_nd. Tolerances: 5e-5 on d's at four decimals, 5e-3 on the
    two-decimal dollar figures, plus 1e-4 pins on the computed values.
    """
    F0, K, sigma, r, R, T = 1600.0, 1500.0, 0.20, 0.05, 0.30, 2.0
    t_mid = np.array([0.5, 1.5])
    q = np.array([0.02, 0.03])

    d1_t1 = bsm.d1(F0, K, 0.0, sigma, t_mid[0])
    d2_t1 = bsm.d2(F0, K, 0.0, sigma, t_mid[0])
    assert d1_t1 == pytest.approx(0.5271, abs=5e-5)
    assert d2_t1 == pytest.approx(0.3856, abs=5e-5)

    undiscounted_call = bsm.call_price(F0, K, 0.0, sigma, t_mid)
    v = math.exp(-r * T) * (1.0 - R) * undiscounted_call
    np.testing.assert_allclose(v, [92.67, 130.65], atol=5e-3)
    np.testing.assert_allclose(v, [92.66547, 130.65167], atol=1e-4)

    cva = float(np.sum(q * v))
    assert cva == pytest.approx(5.77, abs=5e-3)
    assert cva == pytest.approx(5.77286, abs=1e-4)

    f_nd = (F0 - K) * math.exp(-r * T)
    assert f_nd == pytest.approx(90.48, abs=5e-3)
    assert f_nd - cva == pytest.approx(84.71, abs=5e-3)
    assert f_nd - cva == pytest.approx(84.71088, abs=1e-4)

    # Bank's exposure is the call on the forward, the counterparty's is the put;
    # their difference is the forward's value (put-call parity with r = 0).
    undiscounted_put = bsm.put_price(F0, K, 0.0, sigma, t_mid)
    np.testing.assert_allclose(undiscounted_call - undiscounted_put, F0 - K, atol=1e-9)
    assert math.exp(-r * T) * (undiscounted_call[0] - undiscounted_put[0]) == pytest.approx(
        f_nd, abs=1e-9
    )


# ---------------------------------------------------------------------------
# CR-03: Gaussian copula for time to default (GE §24.8)
# ---------------------------------------------------------------------------

EXAMPLE_24_7_CUMULATIVE_Q = np.array([0.01, 0.03, 0.06, 0.10, 0.15])
EXAMPLE_24_7_THRESHOLDS = np.array([-2.33, -1.88, -1.55, -1.28, -1.04])


def test_gaussian_copula_default_time_thresholds_hull_example_24_7():
    """Hull 11e GE §24.8 p.579, Example 24.7 (percentile-to-percentile map).

    Cumulative default probabilities 1%, 3%, 6%, 10%, 15% over years 1-5 map to
    the standard-normal thresholds N^{-1}(Q) printed as -2.33, -1.88, -1.55,
    -1.28, -1.04; a copula sample below the k-th threshold defaults by year k,
    above -1.04 survives the 5 years. The map is `scipy.stats.norm.ppf`, the same
    primitive `copula.portfolio_loss_samples` applies to its `pd`; hullkit exposes
    no standalone threshold helper, so the ppf is called directly. Tolerance 5e-3
    on thresholds printed to two decimals, 1e-5 on the computed values.
    """
    thresholds = norm.ppf(EXAMPLE_24_7_CUMULATIVE_Q)
    np.testing.assert_allclose(thresholds, EXAMPLE_24_7_THRESHOLDS, atol=5e-3)
    np.testing.assert_allclose(
        thresholds, [-2.326348, -1.880794, -1.554774, -1.281552, -1.036433], atol=1e-5
    )
    assert np.all(np.diff(thresholds) > 0.0)
    # p.579 also quotes the 5- and 10-percentile points -1.645 and -1.282.
    assert norm.ppf(0.05) == pytest.approx(-1.645, abs=5e-4)
    assert norm.ppf(0.10) == pytest.approx(-1.282, abs=5e-4)


def test_gaussian_copula_simulation_marginals_hull_example_24_7():
    """Hull 11e GE §24.8 p.579, Example 24.7 (simulated default times, rho = 0.2).

    Hull simulates 10 names with pairwise copula correlation 0.2 and buckets each
    x_i by the thresholds of the previous test. `copula.gaussian_copula_samples`
    draws a bivariate Gaussian copula, so the check is on one pair of names: with
    n = 400,000 seeded draws (rng seed 0), the frequency with which u < Q_k must
    equal the input cumulative probability Q_k for every horizon and both
    names. The marginal of each name is i.i.d. uniform, so the binomial standard
    error SE_k = sqrt(Q_k (1 - Q_k) / n) applies exactly: 1.57e-4 at 1% up to
    5.65e-4 at 15%; the test allows 3 SE (4.7e-4 ... 1.7e-3). With this seed the
    largest |z| across the 10 checks is 2.42. The copula correlation of the
    normal scores (0.1981) is pinned at the input 0.2 within 3 x (1 - rho^2)/sqrt(n)
    = 4.6e-3, and the copula is order-preserving: the year-k default sets nest.
    """
    n = 400_000
    rho = 0.2
    u, v = copula.gaussian_copula_samples(rho, n=n, rng=np.random.default_rng(0))
    assert u.shape == v.shape == (n,)

    standard_error = np.sqrt(EXAMPLE_24_7_CUMULATIVE_Q * (1.0 - EXAMPLE_24_7_CUMULATIVE_Q) / n)
    for name_uniforms in (u, v):
        # Bucketing on the uniform scale is identical to bucketing the normal
        # score against N^{-1}(Q_k), which is how Hull assigns default years.
        cumulative_frequency = np.array(
            [np.mean(name_uniforms < q_k) for q_k in EXAMPLE_24_7_CUMULATIVE_Q]
        )
        z = (cumulative_frequency - EXAMPLE_24_7_CUMULATIVE_Q) / standard_error
        assert np.all(np.abs(z) <= 3.0), z
        # Year-by-year default probabilities 1%, 2%, 3%, 4%, 5% (binomial SE per
        # bucket, at most 3.45e-4) and 85% survival (SE 5.65e-4), again at 3 SE.
        by_year = np.diff(np.concatenate([[0.0], cumulative_frequency]))
        by_year_expected = np.array([0.01, 0.02, 0.03, 0.04, 0.05])
        by_year_se = np.sqrt(by_year_expected * (1.0 - by_year_expected) / n)
        assert np.all(np.abs(by_year - by_year_expected) <= 3.0 * by_year_se)
        assert np.mean(name_uniforms >= 0.15) == pytest.approx(0.85, abs=3.0 * standard_error[-1])

    score_correlation = np.corrcoef(norm.ppf(u), norm.ppf(v))[0, 1]
    assert score_correlation == pytest.approx(rho, abs=3.0 * (1.0 - rho**2) / math.sqrt(n))
    assert score_correlation == pytest.approx(0.198055, abs=1e-5)


# ---------------------------------------------------------------------------
# CR-20: commodity price modelling and weather derivatives (GE §35.4, §35.7)
# ---------------------------------------------------------------------------


def test_live_cattle_risk_neutral_growth_hull_example_35_1():
    """Hull 11e GE §35.4 p.789-790, Example 35.1 (eq. 35.1, mu(t) from futures).

    October 2021 and December 2021 live-cattle futures of 60.60 and 62.70 cents
    per pound give an expected risk-neutral growth ln(62.70 / 60.60) = 0.034 per
    2 months, "20.4% per annum" when annualised as 6 x 0.034. Inline arithmetic
    (hullkit has no futures-curve drift helper); the computed 0.034067 and 0.2044
    are pinned at the print rounding (5e-4 on both) and at 1e-6 / 1e-5.
    """
    futures_october, futures_december = 60.60, 62.70
    growth_two_months = math.log(futures_december / futures_october)
    assert growth_two_months == pytest.approx(0.034, abs=5e-4)
    assert growth_two_months == pytest.approx(0.0340666, abs=1e-6)

    growth_annualised = growth_two_months * 6.0
    assert growth_annualised == pytest.approx(0.204, abs=5e-4)
    assert growth_annualised == pytest.approx(0.204399, abs=1e-5)


def test_cattle_breeding_investment_value_hull_example_35_2():
    """Hull 11e GE §35.4 p.790, Example 35.2 (real option valued off futures).

    Invest $100k now and $20k at 3, 6, 9 months; sell an expected 300,000 lb at
    the 1-year risk-neutral expected price 64.40 c/lb from the futures curve;
    r = 10% continuous. The value in $k prints as 17.729:
    -100 - 20e^{-0.025} - 20e^{-0.05} - 20e^{-0.075} + 300 x 0.644 e^{-0.1}.
    `rates.bond_price` is the discounted-cash-flow sum with a flat continuous
    rate (time 0 is a legitimate cash-flow date). Tolerance 5e-4 at three
    decimals; the computed value is 17.728933 (1e-5).
    """
    times = [0.0, 0.25, 0.5, 0.75, 1.0]
    cashflows = [-100.0, -20.0, -20.0, -20.0, 300.0 * 0.644]
    value = rates.bond_price(times, cashflows, 0.10)
    assert value == pytest.approx(17.729, abs=5e-4)
    assert value == pytest.approx(17.728933, abs=1e-5)


def test_seasonal_futures_interpolation_hull_section_35_4():
    """Hull 11e GE §35.4 p.793 ("Interpolation and Seasonality").

    September and December futures 40 and 44 with seasonal factors 0.95, 0.85,
    0.8, 1.1 for Sep-Dec. Deseasonalised: 40 / 0.95 = 42.1 and 44 / 1.1 = 40;
    linear interpolation gives 41.4 (Oct) and 40.7 (Nov); re-seasonalised
    41.4 x 0.85 = 35.2 and 40.7 x 0.8 = 32.6. `rates.zero_interp` is plain
    linear interpolation on a term structure, which is exactly the step Hull
    describes. Tolerance 5e-2 on figures printed to one decimal; the unrounded
    35.193 / 32.561 are also pinned (1e-3) so the rounded-intermediate route
    (35.19 / 32.56) and the exact route both sit inside the band.
    """
    months = [9.0, 12.0]
    factors = {9: 0.95, 10: 0.85, 11: 0.8, 12: 1.1}
    deseasonalised = [40.0 / factors[9], 44.0 / factors[12]]
    assert deseasonalised[0] == pytest.approx(42.1, abs=5e-2)
    assert deseasonalised[1] == pytest.approx(40.0, abs=1e-12)

    october = rates.zero_interp(10.0, months, deseasonalised)
    november = rates.zero_interp(11.0, months, deseasonalised)
    assert october == pytest.approx(41.4, abs=5e-2)
    assert november == pytest.approx(40.7, abs=5e-2)

    october_seasonal = october * factors[10]
    november_seasonal = november * factors[11]
    assert october_seasonal == pytest.approx(35.2, abs=5e-2)
    assert november_seasonal == pytest.approx(32.6, abs=5e-2)
    assert october_seasonal == pytest.approx(35.19298, abs=1e-3)
    assert november_seasonal == pytest.approx(32.56140, abs=1e-3)


def test_hdd_call_option_value_hull_example_35_4():
    """Hull 11e GE §35.7 p.797-798, Example 35.4 (February HDD call at O'Hare).

    Strike 700, $10,000 per degree day, HDD lognormal with mean 710 and
    sd(ln HDD) = 0.07. Hull applies eq. (15A.1): expected payoff
    10,000 [710 N(d1) - 700 N(d2)] with d1 = 0.2376, d2 = 0.1676, prints
    $250,900, and discounts one year at 3% to $243,400. The bracket is Black's
    undiscounted call with S = mean, r = 0 and sigma sqrt(T) = 0.07, i.e.
    `bsm.call_price(710, 700, 0, 0.07, 1)`. Computed: 250,863.6 and 243,449.5,
    both rounding to the printed values at the nearest $100 (abs 50). Note the
    printed 243,400 comes from discounting the unrounded payoff — 250,900 x
    e^{-0.03} = 243,485 would print 243,500 — so the tight pins are on the
    unrounded chain. The trend-adjusted rerun with mean 697 (footnote 8;
    697.5 would give 182,800) prints $180,400 and $175,100; computed 180,389.8
    and 175,058.5. d1 / d2 pinned at 5e-5 (four decimals).
    """
    strike, payment_rate, r, T, sigma = 700.0, 10_000.0, 0.03, 1.0, 0.07

    assert bsm.d1(710.0, strike, 0.0, sigma, T) == pytest.approx(0.2376, abs=5e-5)
    assert bsm.d2(710.0, strike, 0.0, sigma, T) == pytest.approx(0.1676, abs=5e-5)

    expected_payoff = payment_rate * bsm.call_price(710.0, strike, 0.0, sigma, T)
    assert expected_payoff == pytest.approx(250_900.0, abs=50.0)
    assert expected_payoff == pytest.approx(250_863.6, abs=0.1)

    option_value = expected_payoff * math.exp(-r * T)
    assert option_value == pytest.approx(243_400.0, abs=50.0)
    assert option_value == pytest.approx(243_449.5, abs=0.1)

    detrended_payoff = payment_rate * bsm.call_price(697.0, strike, 0.0, sigma, T)
    assert detrended_payoff == pytest.approx(180_400.0, abs=50.0)
    assert detrended_payoff == pytest.approx(180_389.8, abs=0.1)

    detrended_value = detrended_payoff * math.exp(-r * T)
    assert detrended_value == pytest.approx(175_100.0, abs=50.0)
    assert detrended_value == pytest.approx(175_058.5, abs=0.1)


# ---------------------------------------------------------------------------
# CR-20: real options (GE §36.1-36.3)
# ---------------------------------------------------------------------------


def test_npv_with_risk_adjusted_discount_rate_hull_section_36_1():
    """Hull 11e GE §36.1 p.802 (traditional NPV).

    A $100M investment returning an expected $25M per year for 5 years,
    discounted at a 12% continuously compounded risk-adjusted rate:
    -100 + 25 sum_{k=1..5} e^{-0.12 k} = -11.53 (millions). `rates.bond_price`
    discounts the inflows with a flat continuous rate. Tolerance 5e-3 at two
    decimals; computed -11.529509 (1e-6).
    """
    npv = -100.0 + rates.bond_price([1.0, 2.0, 3.0, 4.0, 5.0], [25.0] * 5, 0.12)
    assert npv == pytest.approx(-11.53, abs=5e-3)
    assert npv == pytest.approx(-11.529509, abs=1e-6)


def test_rental_option_real_option_hull_example_36_1():
    """Hull 11e GE §36.2 p.804-805, Example 36.1 (option to rent office space).

    Quoted rent V0 = $30/sq ft, real-world growth 12%, sigma 20%, market price
    of risk 0.3, r = 5%; option to rent 100,000 sq ft at $35 for 5 years starting
    in 2 years, rent annually in advance. Printed chain: annuity factor
    A = 1 + e^{-0.05} + ... + e^{-0.2} = 4.5355; risk-neutral growth
    0.12 - 0.3 x 0.2 = 6% so E^[V] = 30 e^{0.12} = 33.82; eq. (15A.1) with
    sigma sqrt(2) gives an expected payoff of $1.5015M; discounted two years,
    $1.3586M. `rates.bond_price` builds A (unit cash flows at 0..4) and
    `bsm.call_price(E^[V], 35, r=0, 0.2, 2)` is the undiscounted eq. (15A.1)
    bracket. The same number falls out of `bsm.call_price` on V0 with the
    dividend-yield slot q = r - (mu - lambda sigma) = -0.01 once the e^{-rT}
    inside it is undone, which is asserted as a consistency check. Tolerances:
    5e-5 on A at four decimals, 5e-3 on 33.82, $50 on amounts printed to
    $0.0001M, plus tight pins (1e-5 on A, $1 on the payoff and value).
    """
    V0, mu, sigma, market_price_of_risk, r = 30.0, 0.12, 0.20, 0.3, 0.05
    area, strike, T_option = 100_000.0, 35.0, 2.0

    annuity = rates.bond_price([0.0, 1.0, 2.0, 3.0, 4.0], [1.0] * 5, r)
    assert annuity == pytest.approx(4.5355, abs=5e-5)
    assert annuity == pytest.approx(4.535506, abs=1e-5)

    risk_neutral_growth = mu - market_price_of_risk * sigma
    assert risk_neutral_growth == pytest.approx(0.06, abs=1e-12)
    expected_v = V0 * math.exp(risk_neutral_growth * T_option)
    assert expected_v == pytest.approx(33.82, abs=5e-3)

    expected_payoff = area * annuity * bsm.call_price(expected_v, strike, 0.0, sigma, T_option)
    assert expected_payoff == pytest.approx(1_501_500.0, abs=50.0)
    assert expected_payoff == pytest.approx(1_501_507.5, abs=1.0)

    option_value = expected_payoff * math.exp(-r * T_option)
    assert option_value == pytest.approx(1_358_600.0, abs=50.0)
    assert option_value == pytest.approx(1_358_620.2, abs=1.0)
    assert option_value > 1_000_000.0  # "it is worth paying $1 million for the option"

    via_yield_slot = (
        area
        * annuity
        * bsm.call_price(V0, strike, r, sigma, T_option, q=r - risk_neutral_growth)
        * math.exp(r * T_option)
    )
    assert via_yield_slot == pytest.approx(expected_payoff, rel=1e-12)


def test_market_price_of_risk_from_capm_hull_example_36_2():
    """Hull 11e GE §36.3 p.805, Example 36.2 (eq. 36.2).

    Sales changes correlate 0.3 with the S&P 500, whose volatility is 20% and
    expected excess return 5%: lambda = (rho / sigma_m)(mu_m - r) =
    0.3 / 0.2 x 0.05 = 0.075. Pure arithmetic (hullkit has no CAPM helper);
    exact to 1e-12.
    """
    rho, sigma_market, market_excess_return = 0.3, 0.20, 0.05
    market_price_of_risk = rho / sigma_market * market_excess_return
    assert market_price_of_risk == pytest.approx(0.075, abs=1e-12)


# ---------------------------------------------------------------------------
# CR-20: Chapter 1 hedging / speculation / arbitrage arithmetic (GE §1.7-1.9)
# ---------------------------------------------------------------------------


def test_hedging_with_forwards_and_puts_hull_section_1_7():
    """Hull 11e GE §1.7 p.34-36 (ImportCo / ExportCo forwards, protective puts).

    Confirmed on the PDF: ImportCo buys GBP 10M three months forward at 1.2225,
    fixing $12,225,000; unhedged the bill would be $12,000,000 at 1.2000 or
    $13,000,000 at 1.3000. ExportCo sells GBP 30M forward at 1.2220, locking in
    $36,660,000. The option hedge (p.35-36): 1,000 shares at $28, ten July put
    contracts (100 shares each) struck at $27.50 quoted at $1 cost
    10 x 100 x $1 = $1,000, guarantee $27,500 for the holding, i.e. $26,500 net
    of the premium; Figure 1.4 plots the hedged value against the price. Dollar
    arithmetic is exact (abs 1e-6); the hedged-value floor is checked with the
    put payoff max(K - S, 0) across the Figure 1.4 price range.
    """
    assert 10e6 * 1.2225 == pytest.approx(12_225_000.0, abs=1e-6)
    assert 10e6 * 1.2000 == pytest.approx(12_000_000.0, abs=1e-6)
    assert 10e6 * 1.3000 == pytest.approx(13_000_000.0, abs=1e-6)
    assert 30e6 * 1.2220 == pytest.approx(36_660_000.0, abs=1e-6)

    shares, strike, premium, contracts, contract_size = 1_000, 27.50, 1.0, 10, 100
    hedge_cost = contracts * contract_size * premium
    assert hedge_cost == pytest.approx(1_000.0, abs=1e-6)
    assert shares * strike == pytest.approx(27_500.0, abs=1e-6)
    assert shares * strike - hedge_cost == pytest.approx(26_500.0, abs=1e-6)

    prices = np.linspace(20.0, 40.0, 81)
    hedged_value = shares * prices + shares * np.maximum(strike - prices, 0.0) - hedge_cost
    assert np.all(hedged_value >= 26_500.0 - 1e-9)
    assert hedged_value[prices <= strike].min() == pytest.approx(26_500.0, abs=1e-6)
    assert hedged_value[-1] == pytest.approx(shares * 40.0 - hedge_cost, abs=1e-6)


def test_speculation_with_futures_and_options_hull_tables_1_4_and_1_5():
    """Hull 11e GE §1.8 p.36-38, Tables 1.4 and 1.5.

    Table 1.4: spot 1.2220, July futures 1.2223, four contracts of GBP 62,500
    (GBP 250,000). Buying spot costs 250,000 x 1.2220 = $305,500; the futures
    need $20,000 margin. At 1.3000 the profits are $19,500 (spot) and
    (1.3000 - 1.2223) x 250,000 = $19,425 (futures); at 1.2000 the losses are
    $5,500 and $5,575. Table 1.5: $2,000 buys 100 shares at $20 or 2,000 calls
    struck at $22.50 at $1. At $27: shares +$700; calls pay 2,000 x $4.50 =
    $9,000, net +$7,000 ("10 times more profitable"). At $15: shares -$500,
    calls -$2,000. All confirmed on the PDF; exact dollar arithmetic (abs 1e-6).
    """
    spot, futures, notional, contracts, contract_size = 1.2220, 1.2223, 250_000.0, 4, 62_500.0
    assert contracts * contract_size == notional
    assert notional * spot == pytest.approx(305_500.0, abs=1e-6)
    assert (1.3000 - spot) * notional == pytest.approx(19_500.0, abs=1e-6)
    assert (1.3000 - futures) * notional == pytest.approx(19_425.0, abs=1e-6)
    assert (1.2000 - spot) * notional == pytest.approx(-5_500.0, abs=1e-6)
    assert (1.2000 - futures) * notional == pytest.approx(-5_575.0, abs=1e-6)

    budget, stock, call_strike, call_premium = 2_000.0, 20.0, 22.50, 1.0
    shares = budget / stock
    calls = budget / call_premium
    assert shares == 100 and calls == 2_000
    for terminal, shares_profit, calls_profit in ((27.0, 700.0, 7_000.0), (15.0, -500.0, -2_000.0)):
        assert shares * (terminal - stock) == pytest.approx(shares_profit, abs=1e-6)
        call_payoff = calls * max(terminal - call_strike, 0.0)
        assert call_payoff - budget == pytest.approx(calls_profit, abs=1e-6)
    assert 2_000 * 4.50 == pytest.approx(9_000.0, abs=1e-6)
    assert 7_000.0 / 700.0 == pytest.approx(10.0, abs=1e-12)


def test_cross_listing_arbitrage_hull_section_1_9():
    """Hull 11e GE §1.9 p.39 (NYSE / LSE arbitrage).

    A stock trades at $120 in New York and GBP 100 in London with the exchange
    rate at $1.2300 per pound: buying 100 shares in New York and selling them in
    London locks in 100 x ($1.23 x 100 - $120) = $300. Confirmed on the PDF;
    exact arithmetic (abs 1e-6).
    """
    profit = 100 * (1.23 * 100.0 - 120.0)
    assert profit == pytest.approx(300.0, abs=1e-6)
