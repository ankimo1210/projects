"""Printed-value pins for Hull 11e Global Edition, Chapters 12, 13, 15, 17 and 18.

Audit ids covered (johnhull/docs/SECTION_AUDIT_2026-09-14.md):

- OP-03: GE §13.10-13.11 and §17.6 -- the DerivaGem tree values 7.671 / 7.47 /
  6.76 and Examples 13.1-13.3.
- OP-11: GE §12.1, Business Snapshot 12.1, §15.1-15.3, §15.7, §15.11 --
  Example 12.1 and its variants, the American-style box spread, Examples
  15.1-15.3, Business Snapshot 15.1, Example 15.7, the implied-volatility
  walk-through (1.875 -> 23.5%).
- OP-13: GE §17.1-17.5 -- Tables 17.1 / 17.2 (K = 960), the zero-cost range
  forward, Business Snapshot 17.1, Examples 17.1-17.2, eq. (17.10) and the
  implied dividend yield.
- OP-14: GE §18.4-18.11 -- Example 18.5, the bounds and eq. (18.2), Examples
  18.6-18.7, the one-step futures tree (1.592), American futures vs spot
  option ordering, futures-style options and the ``c e^{rT}`` identity.

Every number is read from the Global Edition PDF; its printed page numbers
coincide with the PDF page numbers, so ``p.NNN`` below is both. Tolerances
follow the print rounding (abs=5e-3 for two printed decimals, 5e-4 for three,
0.5 for "about $NNN"). Where Hull adds rounded intermediates, the test
reproduces the printed figure with the same rounding and also pins the
unrounded value so that the discrepancy is visible rather than hidden.
"""

import math

import numpy as np
import pytest
from hullkit import bsm, payoffs, trees, volatility
from scipy.stats import norm

# --------------------------------------------------------------------------
# OP-03: GE §13.10-13.11, §17.6
# --------------------------------------------------------------------------


def test_derivagem_american_put_section_13_10():
    """Hull 11e GE §13.10 p.303-304: S=50, K=52, r=5%, sigma=30%, T=2, American put.

    DerivaGem prints 7.428 with 2 steps, 7.671 with 5 steps, 7.47 with 500
    steps, and 6.76 for the 500-step European put (also the BSM value). The
    5-step parameters print as u=1.2089, d=0.8272, a=1.0202, p=0.5056 (p.303).
    Tolerances: 5e-4 for three printed decimals, 5e-3 for two, 5e-5 for four.
    """
    S, K, r, sigma, T = 50.0, 52.0, 0.05, 0.30, 2.0
    u, d = trees.crr_params(sigma, T / 5)
    assert u == pytest.approx(1.2089, abs=5e-5)
    assert d == pytest.approx(0.8272, abs=5e-5)
    assert math.exp(r * T / 5) == pytest.approx(1.0202, abs=5e-5)
    assert trees.risk_neutral_p(u, d, r, T / 5) == pytest.approx(0.5056, abs=5e-5)

    assert trees.crr_price(S, K, r, sigma, T, 2, kind="put", american=True) == pytest.approx(
        7.428, abs=5e-4
    )
    assert trees.crr_price(S, K, r, sigma, T, 5, kind="put", american=True) == pytest.approx(
        7.671, abs=5e-4
    )
    assert trees.crr_price(S, K, r, sigma, T, 500, kind="put", american=True) == pytest.approx(
        7.47, abs=5e-3
    )
    assert trees.crr_price(S, K, r, sigma, T, 500, kind="put", american=False) == pytest.approx(
        6.76, abs=5e-3
    )
    assert bsm.put_price(S, K, r, sigma, T) == pytest.approx(6.76, abs=5e-3)


def test_example_13_1_index_call_two_step_tree():
    """Hull 11e GE §13.11 p.305, Example 13.1 / Figure 13.11 (also §17.6 eq. 17.15).

    Index 810, K=800, r=5%, q=2%, sigma=20%, 6-month European call, two steps:
    u=1.1052, d=0.9048, a=1.0075, p=0.5126 and the option is worth 53.39. The
    figure's node values (index / option) are pinned too. abs=5e-5 for four
    printed decimals, 5e-3 for the two-decimal node values.
    """
    S, K, r, q, sigma, T, N = 810.0, 800.0, 0.05, 0.02, 0.20, 0.5, 2
    dt = T / N
    u, d = trees.crr_params(sigma, dt)
    assert u == pytest.approx(1.1052, abs=5e-5)
    assert d == pytest.approx(0.9048, abs=5e-5)
    assert math.exp((r - q) * dt) == pytest.approx(1.0075, abs=5e-5)
    assert trees.risk_neutral_p(u, d, r, dt, q=q) == pytest.approx(0.5126, abs=5e-5)

    stock, option = trees.binomial_tree(S, K, r, T, N, u, d, q=q, kind="call")
    assert option[0][0] == pytest.approx(53.39, abs=5e-3)
    assert trees.crr_price(S, K, r, sigma, T, N, q=q, kind="call") == pytest.approx(53.39, abs=5e-3)
    np.testing.assert_allclose(stock[1], [895.19, 732.92], atol=5e-3)
    np.testing.assert_allclose(option[1], [100.66, 5.06], atol=5e-3)
    np.testing.assert_allclose(stock[2], [989.34, 810.00, 663.17], atol=5e-3)
    np.testing.assert_allclose(option[2], [189.34, 10.00, 0.00], atol=5e-3)


def test_example_13_2_currency_american_call_three_step_tree():
    """Hull 11e GE §13.11 p.306, Example 13.2 / Figure 13.12 (also §17.6 eq. 17.16).

    Spot 0.6100 USD, K=0.6000, r=5%, r_f=7%, sigma=12%, 3-month American call,
    three steps: u=1.0352, d=0.9660, a=0.9983, p=0.4673, value 0.019. The
    figure prints every node to three decimals, so abs=5e-4 throughout; the
    unrounded root is 0.01888.
    """
    S, K, r, rf, sigma, T, N = 0.61, 0.60, 0.05, 0.07, 0.12, 0.25, 3
    dt = T / N
    u, d = trees.crr_params(sigma, dt)
    assert u == pytest.approx(1.0352, abs=5e-5)
    assert d == pytest.approx(0.9660, abs=5e-5)
    assert math.exp((r - rf) * dt) == pytest.approx(0.9983, abs=5e-5)
    assert trees.risk_neutral_p(u, d, r, dt, q=rf) == pytest.approx(0.4673, abs=5e-5)

    stock, option = trees.binomial_tree(S, K, r, T, N, u, d, q=rf, kind="call", american=True)
    assert option[0][0] == pytest.approx(0.019, abs=5e-4)
    assert option[0][0] == pytest.approx(0.01888, abs=5e-6)
    np.testing.assert_allclose(stock[1], [0.632, 0.589], atol=5e-4)
    np.testing.assert_allclose(option[1], [0.033, 0.007], atol=5e-4)
    np.testing.assert_allclose(stock[2], [0.654, 0.610, 0.569], atol=5e-4)
    np.testing.assert_allclose(option[2], [0.054, 0.015, 0.000], atol=5e-4)
    np.testing.assert_allclose(stock[3], [0.677, 0.632, 0.589, 0.550], atol=5e-4)
    np.testing.assert_allclose(option[3], [0.077, 0.032, 0.000, 0.000], atol=5e-4)


def test_example_13_3_futures_american_put_three_step_tree():
    """Hull 11e GE §13.11 p.307, Example 13.3 / Figure 13.13.

    Futures 31, K=30, r=5%, sigma=30%, 9-month American put, three steps with
    a=1 (obtained here as q=r): u=1.1618, d=0.8607, p=0.4626 and the option is
    worth 2.84 (unrounded 2.8356). Node values are two-decimal, abs=5e-3.
    """
    F, K, r, sigma, T, N = 31.0, 30.0, 0.05, 0.30, 0.75, 3
    dt = T / N
    u, d = trees.crr_params(sigma, dt)
    assert u == pytest.approx(1.1618, abs=5e-5)
    assert d == pytest.approx(0.8607, abs=5e-5)
    assert math.exp((r - r) * dt) == pytest.approx(1.000, abs=1e-12)
    assert trees.risk_neutral_p(u, d, r, dt, q=r) == pytest.approx(0.4626, abs=5e-5)

    stock, option = trees.binomial_tree(F, K, r, T, N, u, d, q=r, kind="put", american=True)
    assert option[0][0] == pytest.approx(2.84, abs=5e-3)
    assert trees.crr_price(F, K, r, sigma, T, N, q=r, kind="put", american=True) == pytest.approx(
        2.84, abs=5e-3
    )
    np.testing.assert_allclose(stock[1], [36.02, 26.68], atol=5e-3)
    np.testing.assert_allclose(option[1], [0.93, 4.54], atol=5e-3)
    np.testing.assert_allclose(stock[2], [41.85, 31.00, 22.97], atol=5e-3)
    np.testing.assert_allclose(option[2], [0.00, 1.76, 7.03], atol=5e-3)
    np.testing.assert_allclose(stock[3], [48.62, 36.02, 26.68, 19.77], atol=5e-3)
    np.testing.assert_allclose(option[3], [0.00, 0.00, 3.32, 10.23], atol=5e-3)


# --------------------------------------------------------------------------
# OP-11: GE §12.1, Business Snapshot 12.1, §15.1-15.3, §15.7, §15.11
# --------------------------------------------------------------------------


def test_example_12_1_principal_protected_note():
    """Hull 11e GE §12.1 p.269-270, Example 12.1 and its variants.

    3-year rate 6%: the zero costs 1,000e^{-0.18} = 835.27, leaving 164.73 for
    a 3-year ATM call on a 1,000 portfolio with q=1.5%. Hull says the call is
    cheaper than 164.73 "if the volatility ... is less than about 15%" -- the
    break-even volatility is 14.94%, and at exactly 15% the call costs 165.07.
    With sigma=25% the call is "about $221" (221.15). With r=3% the funds are
    86.07 and the ATM call costs about $119 (T=3), $217 (T=10, funds 259.18)
    and $281 (T=20, funds 451.19). "About" figures are integer dollars, so
    abs=0.5; the exact ones use abs=5e-3.
    """
    S = K = 1000.0
    q = 0.015
    assert S * math.exp(-0.06 * 3) == pytest.approx(835.27, abs=5e-3)
    assert S - S * math.exp(-0.06 * 3) == pytest.approx(164.73, abs=5e-3)

    call_15 = bsm.call_price(S, K, 0.06, 0.15, 3.0, q=q)
    assert call_15 == pytest.approx(165.07, abs=5e-3)
    breakeven_vol = volatility.implied_vol(S - S * math.exp(-0.06 * 3), S, K, 0.06, 3.0, q=q)
    assert breakeven_vol == pytest.approx(0.1494, abs=5e-5)
    assert 0.14 < breakeven_vol < 0.15  # "less than about 15%"
    assert bsm.call_price(S, K, 0.06, 0.25, 3.0, q=q) == pytest.approx(221.0, abs=0.5)

    assert S - S * math.exp(-0.03 * 3) == pytest.approx(86.07, abs=5e-3)
    assert bsm.call_price(S, K, 0.03, 0.15, 3.0, q=q) == pytest.approx(119.0, abs=0.5)
    assert bsm.call_price(S, K, 0.03, 0.15, 10.0, q=q) == pytest.approx(217.0, abs=0.5)
    assert S - S * math.exp(-0.03 * 10) == pytest.approx(259.18, abs=5e-3)
    assert bsm.call_price(S, K, 0.03, 0.15, 20.0, q=q) == pytest.approx(281.0, abs=0.5)
    assert S - S * math.exp(-0.03 * 20) == pytest.approx(451.19, abs=5e-3)


def test_business_snapshot_12_1_american_box_spread():
    """Hull 11e GE §12.3 p.277, Business Snapshot 12.1 (S=50, sigma=30%, r=8%, T=2/12).

    DerivaGem table: calls 0.26 (K=60) and 0.96 (K=55) for both styles; puts
    9.46 / 5.23 European and 10.00 / 5.44 American. Bull call spread 0.70,
    bear put spread 4.23 (European) or 4.56 (American); box 4.93 European
    (= 5e^{-0.08 x 2/12}) and 5.26 American. American puts come from a 500-step
    CRR tree (no hullkit closed form); the 60-strike put is at its intrinsic
    value 10.00 exactly. Hull's 5.26 is the sum of the two-decimal spreads
    0.70 + 4.56; the unrounded American box is 5.2665, which would print as
    5.27, so the test pins both rather than widening the tolerance.
    """
    S, r, sigma, T = 50.0, 0.08, 0.30, 2.0 / 12.0
    K1, K2 = 55.0, 60.0
    c60, c55 = bsm.call_price(S, K2, r, sigma, T), bsm.call_price(S, K1, r, sigma, T)
    p60, p55 = bsm.put_price(S, K2, r, sigma, T), bsm.put_price(S, K1, r, sigma, T)
    assert c60 == pytest.approx(0.26, abs=5e-3)
    assert c55 == pytest.approx(0.96, abs=5e-3)
    assert p60 == pytest.approx(9.46, abs=5e-3)
    assert p55 == pytest.approx(5.23, abs=5e-3)

    N = 500
    C60 = trees.crr_price(S, K2, r, sigma, T, N, kind="call", american=True)
    C55 = trees.crr_price(S, K1, r, sigma, T, N, kind="call", american=True)
    P60 = trees.crr_price(S, K2, r, sigma, T, N, kind="put", american=True)
    P55 = trees.crr_price(S, K1, r, sigma, T, N, kind="put", american=True)
    assert C60 == pytest.approx(c60, abs=1e-3)  # no dividends: American call = European
    assert C55 == pytest.approx(c55, abs=1e-3)
    assert P60 == pytest.approx(10.00, abs=5e-3)
    assert P60 == K2 - S  # exercised immediately: intrinsic value
    assert P55 == pytest.approx(5.44, abs=5e-3)

    bull_call = c55 - c60
    bear_put_eu, bear_put_am = p60 - p55, P60 - P55
    assert bull_call == pytest.approx(0.70, abs=5e-3)
    assert bear_put_eu == pytest.approx(4.23, abs=5e-3)
    assert bear_put_am == pytest.approx(4.56, abs=5e-3)

    box_eu = bull_call + bear_put_eu
    assert box_eu == pytest.approx(4.93, abs=5e-3)
    assert box_eu == pytest.approx(payoffs.box_spread_value(K1, K2, r, T), abs=1e-10)
    box_am_rounded = round(bull_call, 2) + round(bear_put_am, 2)
    assert box_am_rounded == pytest.approx(5.26, abs=1e-12)
    assert bull_call + bear_put_am == pytest.approx(5.2665, abs=5e-4)
    assert bull_call + bear_put_am > 5.10  # selling the American box at 5.10 loses money


def test_example_15_1_lognormal_price_interval():
    """Hull 11e GE §15.1 p.339, Example 15.1: S0=40, mu=16%, sigma=20%, T=0.5.

    ln S_T ~ phi(3.759, 0.02), standard deviation 0.141, and the 95% interval
    prints as 32.55 < S_T < 56.56. Those bounds are exp(3.759 -/+ 1.96 x 0.141)
    with the rounded mean and standard deviation; the unrounded interval is
    32.51 to 56.60. Both are pinned. Pure numpy glue (no hullkit distribution
    helper exists for eq. 15.3).
    """
    S0, mu, sigma, T = 40.0, 0.16, 0.20, 0.5
    mean = math.log(S0) + (mu - sigma**2 / 2) * T
    var = sigma**2 * T
    assert mean == pytest.approx(3.759, abs=5e-4)
    assert var == pytest.approx(0.02, abs=1e-12)
    assert math.sqrt(var) == pytest.approx(0.141, abs=5e-4)

    lo_rounded, hi_rounded = math.exp(3.759 - 1.96 * 0.141), math.exp(3.759 + 1.96 * 0.141)
    assert lo_rounded == pytest.approx(32.55, abs=5e-3)
    assert hi_rounded == pytest.approx(56.56, abs=5e-3)
    lo, hi = math.exp(mean - 1.96 * math.sqrt(var)), math.exp(mean + 1.96 * math.sqrt(var))
    assert lo == pytest.approx(32.51, abs=5e-3)
    assert hi == pytest.approx(56.60, abs=5e-3)


def test_example_15_2_lognormal_mean_and_variance():
    """Hull 11e GE §15.1 p.340, Example 15.2: S0=20, mu=20%, sigma=40%, T=1.

    E(S_T) = 20e^{0.2} = 24.43, var(S_T) = 400e^{0.4}(e^{0.16} - 1) = 103.54,
    standard deviation 10.18 (eqs. 15.4-15.5). abs=5e-3.
    """
    S0, mu, sigma, T = 20.0, 0.20, 0.40, 1.0
    mean = S0 * math.exp(mu * T)
    var = S0**2 * math.exp(2 * mu * T) * (math.exp(sigma**2 * T) - 1.0)
    assert mean == pytest.approx(24.43, abs=5e-3)
    assert var == pytest.approx(103.54, abs=5e-3)
    assert math.sqrt(var) == pytest.approx(10.18, abs=5e-3)


def test_example_15_3_average_return_distribution():
    """Hull 11e GE §15.2 p.341, Example 15.3: mu=17%, sigma=20%, T=3.

    The average continuously compounded return is normal with mean
    0.17 - 0.2^2/2 = 0.15 and standard deviation sqrt(0.2^2/3) = 0.1155, so
    the 95% range is -7.6% to +37.6% per annum (eq. 15.7). abs=5e-5 on the
    four-decimal 0.1155 and 5e-4 (= 0.05%) on the percentage bounds.
    """
    mu, sigma, T = 0.17, 0.20, 3.0
    mean = mu - sigma**2 / 2
    sd = math.sqrt(sigma**2 / T)
    assert mean == pytest.approx(0.15, abs=1e-12)
    assert sd == pytest.approx(0.1155, abs=5e-5)
    assert mean - 1.96 * sd == pytest.approx(-0.076, abs=5e-4)
    assert mean + 1.96 * sd == pytest.approx(0.376, abs=5e-4)


def test_business_snapshot_15_1_mutual_fund_returns():
    """Hull 11e GE §15.3 p.343, Business Snapshot 15.1.

    Annual returns 15%, 20%, 30%, -20%, 25%: arithmetic mean 14%, $100 grows
    to 179.40 while 14% compounded would give 192.54, and the realized
    (geometric) return is 12.4% (multipliers: arithmetic mean 1.140, geometric
    mean 1.124). abs=5e-3 on dollars, 5e-4 on the returns.
    """
    returns = np.array([0.15, 0.20, 0.30, -0.20, 0.25])
    multipliers = 1.0 + returns
    assert returns.mean() == pytest.approx(0.14, abs=1e-12)
    assert 100.0 * multipliers.prod() == pytest.approx(179.40, abs=5e-3)
    assert 100.0 * 1.14**5 == pytest.approx(192.54, abs=5e-3)
    geometric = multipliers.prod() ** (1.0 / 5.0)
    assert geometric - 1.0 == pytest.approx(0.124, abs=5e-4)
    assert 100.0 * geometric**5 == pytest.approx(179.40, abs=5e-3)
    assert multipliers.mean() == pytest.approx(1.140, abs=5e-4)
    assert geometric == pytest.approx(1.124, abs=5e-4)


def test_example_15_7_warrant_cost():
    """Hull 11e GE §15.10 p.358, Example 15.7.

    1,000,000 shares at $40, 200,000 warrants with K=60 and T=5, r=3%,
    sigma=30%, no dividends: the 5-year call is worth 7.04, each warrant
    N/(N+M) x 7.04 = 5.87, the issue costs $1.17 million and the stock is
    expected to fall by 1.17 to 38.83. abs=5e-3.
    """
    n_shares, n_warrants = 1_000_000, 200_000
    call = bsm.call_price(40.0, 60.0, 0.03, 0.30, 5.0)
    assert call == pytest.approx(7.04, abs=5e-3)
    warrant = n_shares / (n_shares + n_warrants) * call
    assert warrant == pytest.approx(5.87, abs=5e-3)
    total_cost_millions = n_warrants * warrant / 1e6
    assert total_cost_millions == pytest.approx(1.17, abs=5e-3)
    assert 40.0 - total_cost_millions == pytest.approx(38.83, abs=5e-3)


def test_implied_volatility_section_15_11():
    """Hull 11e GE §15.11 p.358: c=1.875, S0=21, K=20, r=10%, T=0.25.

    The bisection narrative prints c=1.76 at sigma=0.20 (too low), 2.10 at
    0.30 (too high), 0.25 also too high, and the implied volatility as 0.235
    (23.5%). Brent's method gives 0.2345, inside the abs=5e-4 window for three
    printed decimals; the bracketing values use abs=5e-3.
    """
    price, S, K, r, T = 1.875, 21.0, 20.0, 0.10, 0.25
    assert bsm.call_price(S, K, r, 0.20, T) == pytest.approx(1.76, abs=5e-3)
    assert bsm.call_price(S, K, r, 0.20, T) < price
    assert bsm.call_price(S, K, r, 0.30, T) == pytest.approx(2.10, abs=5e-3)
    assert bsm.call_price(S, K, r, 0.30, T) > price
    assert bsm.call_price(S, K, r, 0.25, T) > price
    iv = volatility.implied_vol(price, S, K, r, T)
    assert iv == pytest.approx(0.235, abs=5e-4)
    assert iv == pytest.approx(0.2345, abs=5e-5)
    assert bsm.call_price(S, K, r, iv, T) == pytest.approx(price, abs=1e-10)


# --------------------------------------------------------------------------
# OP-13: GE §17.1-17.5
# --------------------------------------------------------------------------


def test_tables_17_1_and_17_2_portfolio_insurance_strike():
    """Hull 11e GE §17.1 p.385-386, Tables 17.1 and 17.2 (beta = 2.0).

    $500,000 portfolio, index 1,000, r=12%, q=4% on both, three months. CAPM
    gives the Table 17.1 chain for an index of 1,040 (index return 4%, plus 1%
    dividends, minus 3% risk-free, x2 = 4% excess, 7% expected, 6% capital
    gain, $530,000) and the Table 17.2 column 570,000 ... 370,000 for indices
    1,080 ... 880. The strike protecting $450,000 is 960 (footnote: 955 for
    $445,000), and 10 contracts pay (960 - 880) x 10 x 100 = $80,000 when the
    index is 880; the beta=1 case (p.385) needs 5 contracts at K=900 paying
    $10,000. The CAPM chain is arithmetic glue; the payoffs use
    ``payoffs.leg_payoff``. Exact to rounding (abs=1e-6).
    """
    value, beta, index0, r, q = 500_000.0, 2.0, 1_000.0, 0.12, 0.04
    quarter = 0.25
    rf_q, div_q = r * quarter, q * quarter
    assert rf_q == pytest.approx(0.03, abs=1e-12)
    assert div_q == pytest.approx(0.01, abs=1e-12)

    index_return = (1_040.0 - index0) / index0
    total_index = index_return + div_q
    excess_index = total_index - rf_q
    expected_portfolio = rf_q + beta * excess_index
    capital_gain = expected_portfolio - div_q
    assert index_return == pytest.approx(0.04, abs=1e-12)
    assert total_index == pytest.approx(0.05, abs=1e-12)
    assert excess_index == pytest.approx(0.02, abs=1e-12)
    assert beta * excess_index == pytest.approx(0.04, abs=1e-12)
    assert expected_portfolio == pytest.approx(0.07, abs=1e-12)
    assert capital_gain == pytest.approx(0.06, abs=1e-12)
    assert value * (1.0 + capital_gain) == pytest.approx(530_000.0, abs=1e-6)

    index_levels = np.array([1_080.0, 1_040.0, 1_000.0, 960.0, 920.0, 880.0])
    excess = (index_levels - index0) / index0 + div_q - rf_q
    portfolio_values = value * (1.0 + rf_q + beta * excess - div_q)
    np.testing.assert_allclose(
        portfolio_values, [570_000, 530_000, 490_000, 450_000, 410_000, 370_000], atol=1e-6
    )
    strike = np.interp(450_000.0, portfolio_values[::-1], index_levels[::-1])
    assert strike == pytest.approx(960.0, abs=1e-9)
    assert np.interp(445_000.0, portfolio_values[::-1], index_levels[::-1]) == pytest.approx(
        955.0, abs=1e-9
    )

    n_contracts = beta * value / (index0 * 100.0)
    assert n_contracts == pytest.approx(10.0, abs=1e-12)
    assert payoffs.leg_payoff(880.0, n_contracts * 100.0, "put", strike) == pytest.approx(
        80_000.0, abs=1e-6
    )
    assert payoffs.leg_payoff(880.0, 5 * 100.0, "put", 900.0) == pytest.approx(10_000.0, abs=1e-6)


def test_range_forward_zero_cost_strikes_section_17_2():
    """Hull 11e GE §17.2 p.388: spot = forward = 1.3200, r = r_f = 2%, sigma=14%, T=0.25.

    A European put with K1=1.3000 and a European call with K2=1.3414 "are both
    worth 0.0273", so the range forward costs nothing. Priced with
    ``bsm.put_price``/``call_price`` and q = r_f (eqs. 17.11-17.12). abs=5e-5
    for four printed decimals; the two premiums differ by 1.2e-5 because K2 is
    quoted to four decimals.
    """
    S, r, rf, sigma, T = 1.32, 0.02, 0.02, 0.14, 0.25
    K1, K2 = 1.3000, 1.3414
    assert S * math.exp((r - rf) * T) == pytest.approx(1.32, abs=1e-12)  # forward = spot
    put = bsm.put_price(S, K1, r, sigma, T, q=rf)
    call = bsm.call_price(S, K2, r, sigma, T, q=rf)
    assert put == pytest.approx(0.0273, abs=5e-5)
    assert call == pytest.approx(0.0273, abs=5e-5)
    assert put == pytest.approx(call, abs=2e-5)
    assert K1 < S < K2


def test_business_snapshot_17_1_stocks_vs_bonds_guarantee():
    """Hull 11e GE §17.4 p.393, Business Snapshot 17.1.

    Index 1,000, q=1%, sigma=15%, r=5%, T=10: to beat bonds the index must
    reach 1,000e^{0.04 x 10} = 1,492 and the guarantee is a European put with
    K=1,492 worth 169.7, "about 17% of the fund". abs=0.5 on the integer strike,
    5e-2 on the one-decimal put (with the unrounded strike 1,491.82 the put is
    169.64).
    """
    S, q, sigma, r, T = 1_000.0, 0.01, 0.15, 0.05, 10.0
    strike = S * math.exp((r - q) * T)
    assert strike == pytest.approx(1_492.0, abs=0.5)
    put = bsm.put_price(S, 1_492.0, r, sigma, T, q=q)
    assert put == pytest.approx(169.7, abs=5e-2)
    assert bsm.put_price(S, strike, r, sigma, T, q=q) == pytest.approx(169.64, abs=5e-3)
    assert put / S == pytest.approx(0.17, abs=5e-3)


def test_example_17_1_index_call():
    """Hull 11e GE §17.4 p.391-392, Example 17.1 (moved here from the vol 02 notebook).

    S0=930, K=900, r=8%, sigma=20%, T=2/12, q=3% (0.2% + 0.3% over two months):
    d1=0.5444, d2=0.4628, N(d1)=0.7069, N(d2)=0.6782, c=51.83 by eq. (17.4), so
    one contract on 100 x the index costs $5,183. Two printed intermediates do
    not round-trip: d1 is truncated (0.54448 rounds to 0.5445, pinned with
    abs=1e-4) and N(d2)=0.6782 is N(0.4628) evaluated at the printed d2 (the
    unrounded N(d2)=0.67826 would print 0.6783). The test pins the printed
    values from the printed arguments and the unrounded values at abs=5e-6;
    the price uses 5e-3 and the integer contract cost 0.5.
    """
    S, K, r, sigma, T, q = 930.0, 900.0, 0.08, 0.20, 2.0 / 12.0, 0.03
    d_1, d_2 = bsm.d1(S, K, r, sigma, T, q=q), bsm.d2(S, K, r, sigma, T, q=q)
    assert d_1 == pytest.approx(0.5444, abs=1e-4)
    assert d_1 == pytest.approx(0.54448, abs=5e-6)
    assert d_2 == pytest.approx(0.4628, abs=5e-5)
    assert norm.cdf(0.5444) == pytest.approx(0.7069, abs=5e-5)
    assert norm.cdf(0.4628) == pytest.approx(0.6782, abs=5e-5)
    assert norm.cdf(d_1) == pytest.approx(0.70694, abs=5e-6)
    assert norm.cdf(d_2) == pytest.approx(0.67826, abs=5e-6)
    call = bsm.call_price(S, K, r, sigma, T, q=q)
    assert call == pytest.approx(51.83, abs=5e-3)
    assert 100.0 * call == pytest.approx(5_183.0, abs=0.5)


def test_example_17_2_currency_implied_volatility():
    """Hull 11e GE §17.5 p.394-395, Example 17.2.

    4-month GBP call, S0=K=1.6000, r=8%, r_f=11%, price 4.3 cents: sigma=20%
    gives 0.0639, sigma=10% gives 0.0285, and the implied volatility is 14.1%.
    ``volatility.implied_vol`` with q = r_f returns 0.1411 whether T is 4/12 or
    Hull's rounded 0.3333. abs=5e-5 for the four-decimal prices, 5e-4 for the
    one-decimal percentage.
    """
    S, K, r, rf, T, price = 1.6, 1.6, 0.08, 0.11, 4.0 / 12.0, 0.043
    assert bsm.call_price(S, K, r, 0.20, T, q=rf) == pytest.approx(0.0639, abs=5e-5)
    assert bsm.call_price(S, K, r, 0.10, T, q=rf) == pytest.approx(0.0285, abs=5e-5)
    iv = volatility.implied_vol(price, S, K, r, T, q=rf)
    assert iv == pytest.approx(0.141, abs=5e-4)
    assert volatility.implied_vol(price, S, K, r, 0.3333, q=rf) == pytest.approx(0.141, abs=5e-4)
    assert bsm.call_price(S, K, r, iv, T, q=rf) == pytest.approx(price, abs=1e-10)


def test_equation_17_10_forward_price_and_implied_dividend_yield():
    """Hull 11e GE §17.4 p.392-394, eqs. (17.8)-(17.10) and the implied yield.

    On the Example 17.1 inputs the put-call parity rearrangement
    F0 = K + (c - p)e^{rT} recovers S0e^{(r-q)T} = 937.78, both estimators
    q = r - ln(F0/S0)/T and q = -ln((c - p + Ke^{-rT})/S0)/T return the 3%
    yield, and Black's formula on F0 (eq. 17.8, ``call_price`` with q=r)
    reproduces the 51.83 of eq. (17.4). Identities, so abs=1e-9; the forward is
    printed here to two decimals (abs=5e-3).
    """
    S, K, r, sigma, T, q = 930.0, 900.0, 0.08, 0.20, 2.0 / 12.0, 0.03
    call = bsm.call_price(S, K, r, sigma, T, q=q)
    put = bsm.put_price(S, K, r, sigma, T, q=q)
    forward = K + (call - put) * math.exp(r * T)
    assert forward == pytest.approx(S * math.exp((r - q) * T), abs=1e-9)
    assert forward == pytest.approx(937.78, abs=5e-3)
    assert r - math.log(forward / S) / T == pytest.approx(q, abs=1e-9)
    assert -math.log((call - put + K * math.exp(-r * T)) / S) / T == pytest.approx(q, abs=1e-9)
    assert bsm.call_price(forward, K, r, sigma, T, q=r) == pytest.approx(call, abs=1e-9)
    assert bsm.call_price(forward, K, r, sigma, T, q=r) == pytest.approx(51.83, abs=5e-3)


# --------------------------------------------------------------------------
# OP-14: GE §18.4-18.11
# --------------------------------------------------------------------------


def test_example_18_5_put_call_parity_on_futures():
    """Hull 11e GE §18.4 p.406, Example 18.5.

    Six-month call on a commodity worth 0.56 with K=8.50, futures 8.00, r=10%:
    eq. (18.1) rearranged gives the put as 0.56 + 8.50e^{-0.05} - 8.00e^{-0.05}
    = 1.04 (unrounded 1.0356). abs=5e-3.
    """
    call, K, F, r, T = 0.56, 8.50, 8.00, 0.10, 0.5
    put = call + K * math.exp(-r * T) - F * math.exp(-r * T)
    assert put == pytest.approx(1.04, abs=5e-3)
    assert call + K * math.exp(-r * T) == pytest.approx(put + F * math.exp(-r * T), abs=1e-12)


def test_futures_option_bounds_and_equation_18_2():
    """Hull 11e GE §18.4-18.5 p.406, eqs. (18.1)-(18.4) and the American bounds.

    Checked on the Example 13.3 futures (F0=31, K=30, r=5%, sigma=30%, T=0.75):
    Black prices (``call_price``/``put_price`` with q=r) satisfy eq. (18.1),
    c >= (F0 - K)e^{-rT} (18.3) and p >= max((K - F0)e^{-rT}, 0) (18.4); the
    three-step American tree prices satisfy C >= F0 - K, P >= K - F0, exceed
    their European counterparts, and obey eq. (18.2):
    F0e^{-rT} - K < C - P < F0 - Ke^{-rT}.
    """
    F, K, r, sigma, T = 31.0, 30.0, 0.05, 0.30, 0.75
    disc = math.exp(-r * T)
    c = bsm.call_price(F, K, r, sigma, T, q=r)
    p = bsm.put_price(F, K, r, sigma, T, q=r)
    assert c + K * disc == pytest.approx(p + F * disc, abs=1e-12)
    assert c >= max((F - K) * disc, 0.0)
    assert p >= max((K - F) * disc, 0.0)

    C = trees.crr_price(F, K, r, sigma, T, 3, q=r, kind="call", american=True)
    P = trees.crr_price(F, K, r, sigma, T, 3, q=r, kind="put", american=True)
    assert C >= max(F - K, 0.0)
    assert P >= max(K - F, 0.0)
    assert C > c and P > p  # positive r: early exercise carries value
    assert F * disc - K < C - P < F - K * disc
    assert P == pytest.approx(2.84, abs=5e-3)  # Example 13.3 again


def test_example_18_6_black_put_on_futures():
    """Hull 11e GE §18.7 p.408-409, Example 18.6 (pinned in pytest for the first time).

    Four-month put on a futures price of 20 with K=20, r=9%, sigma=25%:
    d1 = sigma sqrt(T)/2 = 0.07216, d2 = -0.07216, N(-d1)=0.4712,
    N(-d2)=0.5288 and p = e^{-0.03}(20 x 0.5288 - 20 x 0.4712) = 1.12
    (unrounded 1.1166). Hull's 0.07216 is truncated -- the value 0.0721688
    rounds to 0.07217 -- so that pin uses abs=1e-5; the rest 5e-5 / 5e-3.
    """
    F, K, r, sigma, T = 20.0, 20.0, 0.09, 0.25, 4.0 / 12.0
    d_1, d_2 = bsm.d1(F, K, r, sigma, T, q=r), bsm.d2(F, K, r, sigma, T, q=r)
    assert d_1 == pytest.approx(sigma * math.sqrt(T) / 2, abs=1e-12)
    assert d_1 == pytest.approx(0.07216, abs=1e-5)
    assert d_2 == pytest.approx(-d_1, abs=1e-12)
    assert norm.cdf(-d_1) == pytest.approx(0.4712, abs=5e-5)
    assert norm.cdf(-d_2) == pytest.approx(0.5288, abs=5e-5)
    put = bsm.put_price(F, K, r, sigma, T, q=r)
    assert put == pytest.approx(1.12, abs=5e-3)
    assert put == pytest.approx(1.1166, abs=5e-5)


def test_example_18_7_black_call_on_spot_gold():
    """Hull 11e GE §18.8 p.409, Example 18.7.

    Six-month call on spot gold, K=1,200, six-month futures 1,240, r=5%,
    sigma=20%: d1=0.3026, d2=0.1611 and eq. (18.7) gives $88.37
    (``call_price`` on F0 with q=r). abs=5e-5 / 5e-3.
    """
    F, K, r, sigma, T = 1_240.0, 1_200.0, 0.05, 0.20, 0.5
    assert bsm.d1(F, K, r, sigma, T, q=r) == pytest.approx(0.3026, abs=5e-5)
    assert bsm.d2(F, K, r, sigma, T, q=r) == pytest.approx(0.1611, abs=5e-5)
    assert bsm.call_price(F, K, r, sigma, T, q=r) == pytest.approx(88.37, abs=5e-3)


def test_one_step_futures_tree_section_18_9():
    """Hull 11e GE §18.9 p.410-412, Figure 18.1 and eqs. (18.9)-(18.10).

    Futures 30 moving to 33 or 28 in one month, call K=29, r=6%: the riskless
    hedge needs Delta=0.8, its value today is -1.6e^{-0.06/12} = -1.592, so the
    option is worth 1.592; equivalently p = (1 - d)/(u - d) = 0.4 with u=1.1,
    d=28/30 (Hull rounds to 0.9333). ``binomial_tree`` with q=r gives a=1.
    abs=5e-4 for three printed decimals.
    """
    F, K, r, T = 30.0, 29.0, 0.06, 1.0 / 12.0
    u, d = 33.0 / 30.0, 28.0 / 30.0
    assert d == pytest.approx(0.9333, abs=5e-5)
    p = trees.risk_neutral_p(u, d, r, T, q=r)
    assert p == pytest.approx(0.4, abs=1e-12)
    stock, option = trees.binomial_tree(F, K, r, T, 1, u, d, q=r, kind="call")
    assert trees.tree_delta(stock, option) == pytest.approx(0.8, abs=1e-12)
    assert option[0][0] == pytest.approx(1.592, abs=5e-4)
    assert -1.6 * math.exp(-r * T) == pytest.approx(-1.592, abs=5e-4)
    assert option[0][0] == pytest.approx(math.exp(-r * T) * (p * 4.0 + (1 - p) * 0.0), abs=1e-12)


def test_american_futures_vs_spot_option_ordering_section_18_10():
    """Hull 11e GE §18.3 and §18.10 p.405, 412.

    European futures and spot options coincide when the futures contract
    matures with the option (§18.3): Black on F0 = S0e^{(r-q)T} equals BSM on
    S0. For American options (400-step CRR trees, futures tree via q=r) a
    normal market (F0 > S0, here q=0 < r) makes the futures call worth more and
    the futures put worth less than the spot option; an inverted market
    (q=12% > r=6%) reverses both inequalities. Ordering only, no printed value.
    """
    S, K, r, sigma, T, N = 100.0, 100.0, 0.06, 0.25, 1.0, 400
    for q, normal_market in ((0.0, True), (0.12, False)):
        F = S * math.exp((r - q) * T)
        assert (F > S) is normal_market
        eu_spot = bsm.call_price(S, K, r, sigma, T, q=q)
        eu_fut = bsm.call_price(F, K, r, sigma, T, q=r)
        assert eu_fut == pytest.approx(eu_spot, abs=1e-9)

        C_spot = trees.crr_price(S, K, r, sigma, T, N, q=q, kind="call", american=True)
        C_fut = trees.crr_price(F, K, r, sigma, T, N, q=r, kind="call", american=True)
        P_spot = trees.crr_price(S, K, r, sigma, T, N, q=q, kind="put", american=True)
        P_fut = trees.crr_price(F, K, r, sigma, T, N, q=r, kind="put", american=True)
        if normal_market:
            assert C_fut > C_spot and P_fut < P_spot
        else:
            assert C_fut < C_spot and P_fut > P_spot


def test_futures_style_option_section_18_11():
    """Hull 11e GE §18.11 p.413: futures-style options.

    The futures price of a futures-style call is F0N(d1) - KN(d2) and of a put
    KN(-d2) - F0N(-d1), i.e. the Black price compounded forward, c e^{rT}
    (checked on the Example 18.6 inputs: 1.1506 = 1.1166e^{0.03}); it does not
    depend on r; put-call parity is p + F0 = c + K; and the futures price
    always exceeds the intrinsic value, so early exercise is never optimal.
    No hullkit function prices futures-style options, so the formulas are
    built inline from ``bsm.d1``/``bsm.d2``. Identities, abs=1e-9.
    """
    F, K, r, sigma, T = 20.0, 20.0, 0.09, 0.25, 4.0 / 12.0

    def futures_style(F0, rate):
        d_1, d_2 = bsm.d1(F0, K, rate, sigma, T, q=rate), bsm.d2(F0, K, rate, sigma, T, q=rate)
        call = F0 * norm.cdf(d_1) - K * norm.cdf(d_2)
        put = K * norm.cdf(-d_2) - F0 * norm.cdf(-d_1)
        return call, put

    fs_call, fs_put = futures_style(F, r)
    assert fs_call == pytest.approx(
        bsm.call_price(F, K, r, sigma, T, q=r) * math.exp(r * T), abs=1e-9
    )
    assert fs_put == pytest.approx(
        bsm.put_price(F, K, r, sigma, T, q=r) * math.exp(r * T), abs=1e-9
    )
    assert fs_put == pytest.approx(1.1506, abs=5e-5)
    assert fs_put + F == pytest.approx(fs_call + K, abs=1e-9)
    for other_rate in (0.0, 0.05, 0.20):
        assert futures_style(F, other_rate)[0] == pytest.approx(fs_call, abs=1e-9)

    grid = np.linspace(10.0, 40.0, 31)
    calls, puts = futures_style(grid, r)
    assert np.all(calls >= np.maximum(grid - K, 0.0) - 1e-9)
    assert np.all(puts >= np.maximum(K - grid, 0.0) - 1e-9)
