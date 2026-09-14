"""Printed-value pins for Hull 11e *Global Edition*, Chapters 20-23.

Audit items covered: VN-01 (GE Ch.20: smiles, surfaces, Appendix 20A, §20.8),
VN-03 (GE §21.1-21.2: trees, tree Greeks, control variate), VN-07 (GE
§22.2-22.4: historical simulation, model building, linear model) and VN-12
(GE §23.6-23.7: GARCH term structure, EWMA correlation, consistency).

Every number below was read from the GE PDF (`options, futures and other
derivatives 11th.pdf`); in that file the PDF page index coincides with the
printed page number (verified by form-feed counting: Example 20.1 sits on PDF
page 452, whose footer reads 452), so "p.NNN" cites both at once. Section,
example and table numbers are GE numbers and differ from the US edition.

Only public hullkit functions plus numpy/scipy glue are used. Where a printed
number needs a formula hullkit does not expose (bilinear surface interpolation,
the Breeden-Litzenberger butterfly density, tree gamma/theta, BRW weights,
the eq. (23.14) integral), the docstring says so and the arithmetic is inline.
Tolerances are matched to the print rounding (half a unit in the last printed
digit) unless the docstring justifies something wider; values that do not
reproduce are pinned at the computed value with both numbers documented.
"""

import math

import numpy as np
import pytest
from hullkit import bsm, risk, trees, volatility
from scipy.integrate import quad
from scipy.stats import norm

# ---------------------------------------------------------------------------
# VN-01  GE Chapter 20
# ---------------------------------------------------------------------------


def test_example_20_1_put_call_parity_implied_vol_hull_ge():
    """Hull 11e GE §20.1 p.452, Example 20.1: FX call/put share one implied vol.

    S0 = 0.60, r = 5%, r_f = 10%, K = 0.59, T = 1, market call 0.0236. Print:
    call implied vol 14.5%; the parity put p = 0.0236 + 0.59e^{-0.05} -
    0.60e^{-0.10} = 0.0419; put implied vol also 14.5%. Vols are printed to
    0.1% (abs 5e-4 on a decimal scale), the put price to 4 dp (abs 5e-5). The
    call/put vols must agree to solver precision, not just to print rounding,
    because both prices satisfy eq. (20.1) exactly.
    """
    S, K, r, q, T = 0.60, 0.59, 0.05, 0.10, 1.0
    c_mkt = 0.0236
    iv_call = volatility.implied_vol(c_mkt, S, K, r, T, q=q, kind="call")
    assert iv_call == pytest.approx(0.145, abs=5e-4)

    p_parity = c_mkt + K * math.exp(-r * T) - S * math.exp(-q * T)
    assert p_parity == pytest.approx(0.0419, abs=5e-5)

    iv_put = volatility.implied_vol(p_parity, S, K, r, T, q=q, kind="put")
    assert iv_put == pytest.approx(0.145, abs=5e-4)
    assert iv_put == pytest.approx(iv_call, abs=1e-8)


def test_table_20_2_volatility_surface_interpolation_hull_ge():
    """Hull 11e GE §20.5 p.459, Table 20.2 and the two worked look-ups.

    A 9-month option with K/S0 = 1.05 interpolates between the 6-month (13.4)
    and 1-year (14.0) entries to 13.7%; a 1.5-year option with K/S0 = 0.925
    uses bilinear interpolation between the 1-year (14.7, 14.0) and 2-year
    (15.0, 14.4) rows to 14.525%. hullkit has no surface interpolator, so
    ``np.interp`` is applied along maturity then strike; the results are exact
    linear arithmetic, so the tolerance is 1e-9.
    """
    k_over_s = np.array([0.90, 0.95, 1.00, 1.05, 1.10])
    maturities = np.array([1 / 12, 0.25, 0.5, 1.0, 2.0, 5.0])
    surface = np.array(
        [
            [14.2, 13.0, 12.0, 13.1, 14.5],
            [14.0, 13.0, 12.0, 13.1, 14.2],
            [14.1, 13.3, 12.5, 13.4, 14.3],
            [14.7, 14.0, 13.5, 14.0, 14.8],
            [15.0, 14.4, 14.0, 14.5, 15.1],
            [14.8, 14.6, 14.4, 14.7, 15.0],
        ]
    )
    nine_month = np.interp(0.75, maturities, surface[:, 3])
    assert nine_month == pytest.approx(13.7, abs=1e-9)

    along_strike = np.array([np.interp(0.925, k_over_s, row) for row in surface])
    eighteen_month = np.interp(1.5, maturities, along_strike)
    assert eighteen_month == pytest.approx(14.525, abs=1e-9)


def test_example_20a_1_breeden_litzenberger_density_hull_ge():
    """Hull 11e GE Appendix 20A pp.468-469, Example 20A.1 and eq. (20A.2).

    S0 = 10, r = 3%, T = 0.25; implied vols at K = 6..14 are 30%..22% in 1%
    steps. The butterfly density g(K) = e^{rT}(c1 + c3 - 2c2)/delta^2 with
    delta = 0.5 and vols interpolated linearly to the half-strikes gives the
    printed g1..g8 = 0.0057, 0.0444, 0.1545, 0.2781, 0.2813, 0.1659, 0.0573,
    0.0113 (abs 5e-5) from DerivaGem prices 4.045, 3.549, 3.055 (abs 5e-4).
    The area under the histogram prints as 0.9985 (computed 0.99847, abs 5e-5)
    and the flat-26%-lognormal comparison probabilities as 0.0031 and 0.0167
    (abs 5e-5). Eq. (20A.2) is applied inline to ``bsm.call_price`` here
    (``volatility.breeden_litzenberger_density`` is pinned in ``test_volatility.py``); the lognormal bin probabilities use scipy.
    """
    S0, r, T = 10.0, 0.03, 0.25
    strikes = np.arange(6.0, 14.01, 1.0)
    vols = np.arange(0.30, 0.219, -0.01)
    delta = 0.5

    mids = np.arange(6.5, 13.51, 1.0)
    density = []
    for k in mids:
        legs = np.array([k - delta, k, k + delta])
        leg_vols = np.interp(legs, strikes, vols)
        c1, c2, c3 = bsm.call_price(S0, legs, r, leg_vols, T)
        if k == 6.5:
            assert (c1, c2, c3) == pytest.approx((4.045, 3.549, 3.055), abs=5e-4)
        density.append(math.exp(r * T) * (c1 + c3 - 2.0 * c2) / delta**2)
    density = np.array(density)

    printed = [0.0057, 0.0444, 0.1545, 0.2781, 0.2813, 0.1659, 0.0573, 0.0113]
    assert density == pytest.approx(printed, abs=5e-5)
    assert density.sum() == pytest.approx(0.9985, abs=5e-5)

    sigma = 0.26

    def lognormal_cdf(x):
        z = (math.log(x / S0) - (r - 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        return norm.cdf(z)

    assert lognormal_cdf(7.0) - lognormal_cdf(6.0) == pytest.approx(0.0031, abs=5e-5)
    assert lognormal_cdf(14.0) - lognormal_cdf(13.0) == pytest.approx(0.0167, abs=5e-5)


def test_table_20_3_single_jump_frown_hull_ge():
    """Hull 11e GE §20.8 pp.461-462, Table 20.3: the two-point jump "frown".

    S0 = 50 moves to 58 or 42 in one month, r = 12%: u = 1.16, d = 0.84,
    a = 1.0101, p = 0.5314 (abs 5e-5). A one-step ``binomial_tree`` with those
    u, d reproduces the printed call and put prices at K = 42..58 (abs 5e-3).
    The printed implied vols are backed out of the *rounded* printed prices:
    doing the same with ``implied_vol`` reproduces 58.8, 66.6, 69.5, 69.2, 66.1,
    60.0 (abs 0.06 pp: print is to 0.1 pp and the K = 44 value lands on 58.85,
    so a strict 0.05 half-unit would be a coin flip). Using the unrounded tree
    prices instead moves the vols by up to 0.09 pp (K = 46: 66.69), which is
    why the rounded prices are the right input. Call and put vols from the
    unrounded prices agree to 1e-6, the §20.1 result.

    Two entries are not solved for: at K = 42 the call equals its lower bound
    S0 - Ke^{-rT} and at K = 58 the put equals Ke^{-rT} - S0, so the implied
    vol is 0 by definition and the root is ill-conditioned (the put price is
    flat in sigma to 1e-9 up to ~10% vol); the bound equality is asserted.

    K = 56 does NOT reproduce: the printed 1.05 call implies 49.9% (49.89 from
    the rounded price, 49.93 from the unrounded 1.0522), the print shows 49.0,
    and no nearby price gives 49.0 (a 0.95 call still implies 47.7). Suspected
    GE typo; the computed 49.9 is pinned (abs 0.05).
    """
    S0, u, d, r, T = 50.0, 1.16, 0.84, 0.12, 1.0 / 12.0
    assert math.exp(r * T) == pytest.approx(1.0101, abs=5e-5)
    assert trees.risk_neutral_p(u, d, r, T) == pytest.approx(0.5314, abs=5e-5)

    printed = {
        42: (8.42, 0.00, 0.0),
        44: (7.37, 0.93, 58.8),
        46: (6.31, 1.86, 66.6),
        48: (5.26, 2.78, 69.5),
        50: (4.21, 3.71, 69.2),
        52: (3.16, 4.64, 66.1),
        54: (2.10, 5.57, 60.0),
        56: (1.05, 6.50, 49.0),  # implied-vol entry suspected typo, see docstring
        58: (0.00, 7.42, 0.0),
    }
    for K, (call_print, put_print, iv_print) in printed.items():
        _, call_tree = trees.binomial_tree(S0, K, r, T, 1, u, d, kind="call")
        _, put_tree = trees.binomial_tree(S0, K, r, T, 1, u, d, kind="put")
        call, put = float(call_tree[0][0]), float(put_tree[0][0])
        assert call == pytest.approx(call_print, abs=5e-3)
        assert put == pytest.approx(put_print, abs=5e-3)

        if K == 42:
            assert call == pytest.approx(S0 - K * math.exp(-r * T), abs=1e-9)
            continue
        if K == 58:
            assert put == pytest.approx(K * math.exp(-r * T) - S0, abs=1e-9)
            continue

        iv_call = volatility.implied_vol(call, S0, K, r, T, kind="call")
        iv_put = volatility.implied_vol(put, S0, K, r, T, kind="put")
        assert iv_call == pytest.approx(iv_put, abs=1e-6)

        iv_from_print = 100.0 * volatility.implied_vol(call_print, S0, K, r, T, kind="call")
        if K == 56:
            assert iv_from_print == pytest.approx(49.9, abs=0.05)
            assert 100.0 * iv_call == pytest.approx(49.9, abs=0.05)
        else:
            assert iv_from_print == pytest.approx(iv_print, abs=0.06)


# ---------------------------------------------------------------------------
# VN-03  GE §21.1-21.2
# ---------------------------------------------------------------------------

_EX21_1 = dict(S0=50.0, K=50.0, r=0.10, sigma=0.40, T=5.0 / 12.0)


def test_example_21_1_american_put_tree_convergence_hull_ge():
    """Hull 11e GE §21.1 pp.473-475, Example 21.1 and Figure 21.3.

    5-month American put, S0 = K = 50, r = 10%, sigma = 40%, five monthly
    steps: u = 1.1224, d = 0.8909, a = 1.0084, p = 0.5073 (abs 5e-5). The
    5-step root value prints as 4.49 (abs 5e-3) and DerivaGem with 30, 50, 100,
    500 steps gives 4.263, 4.272, 4.278, 4.283 (abs 5e-4). T is 5/12 exactly:
    the printed 0.4167 taken literally moves the 30-step value to 4.2636, which
    rounds the other way. Figure 21.3 node checks (Hull's node A = second-lowest
    node at step 4, stock 39.69, exercised at 10.31; node B = lowest node at
    step 2, also stock 39.69, held at 10.36 because its successors are the
    step-3 values 6.38 and 14.64; node E = middle node at step 4, 2.66; hullkit
    indexes j = 0 as the highest node), all abs 5e-3.
    """
    S0, K, r, sigma, T = (_EX21_1[k] for k in ("S0", "K", "r", "sigma", "T"))
    dt = T / 5
    u, d = trees.crr_params(sigma, dt)
    assert u == pytest.approx(1.1224, abs=5e-5)
    assert d == pytest.approx(0.8909, abs=5e-5)
    assert math.exp(r * dt) == pytest.approx(1.0084, abs=5e-5)
    assert trees.risk_neutral_p(u, d, r, dt) == pytest.approx(0.5073, abs=5e-5)

    price_5 = trees.crr_price(S0, K, r, sigma, T, 5, kind="put", american=True)
    assert price_5 == pytest.approx(4.49, abs=5e-3)
    for n_steps, printed in ((30, 4.263), (50, 4.272), (100, 4.278), (500, 4.283)):
        price = trees.crr_price(S0, K, r, sigma, T, n_steps, kind="put", american=True)
        assert price == pytest.approx(printed, abs=5e-4), n_steps

    stock, option = trees.binomial_tree(S0, K, r, T, 5, u, d, kind="put", american=True)
    assert stock[4][3] == pytest.approx(39.69, abs=5e-3)  # node A
    assert option[4][3] == pytest.approx(10.31, abs=5e-3)  # node A, exercised
    assert stock[2][2] == pytest.approx(39.69, abs=5e-3)  # node B
    assert option[2][2] == pytest.approx(10.36, abs=5e-3)  # node B, held
    assert option[3][2] == pytest.approx(6.38, abs=5e-3)  # B's up-successor
    assert option[3][3] == pytest.approx(14.64, abs=5e-3)  # B's down-successor
    assert option[4][2] == pytest.approx(2.66, abs=5e-3)  # node E


def _tree_gamma_theta(stock, option, dt):
    """Eq. (21.9)/(21.10) from the step-2 nodes; hullkit exposes only tree_delta.

    gamma = [(f22 - f21)/(S22 - S21) - (f21 - f20)/(S21 - S20)] / h with
    h = 0.5 (S22 - S20); theta = (f21 - f00) / (2 dt) per year.
    """
    s2, f2 = stock[2], option[2]
    h = 0.5 * (s2[0] - s2[2])
    gamma = ((f2[0] - f2[1]) / (s2[0] - s2[1]) - (f2[1] - f2[2]) / (s2[1] - s2[2])) / h
    theta = (f2[1] - option[0][0]) / (2.0 * dt)
    return float(gamma), float(theta)


def test_example_21_2_tree_greeks_hull_ge():
    """Hull 11e GE §21.1 p.477, Example 21.2: delta, gamma, theta from Figure 21.3.

    Five-step tree of Example 21.1: delta = (2.16 - 6.96)/(56.12 - 44.55) =
    -0.41 (abs 5e-3, via ``tree_delta``); gamma from nodes B, C, F with
    h = 11.65 prints as 0.03 (computed 0.0341, abs 5e-3 on the 2-dp print);
    theta = (3.77 - 4.49)/0.1667 = -4.3 per year (abs 0.05) or -0.012 per
    calendar day (abs 5e-4). With 50 steps DerivaGem gives -0.415, 0.034 and
    -0.0117 per day (abs 5e-4, 5e-4, 5e-5). ``trees.py`` exposes only
    ``tree_delta``, so gamma and theta are computed inline from the
    ``binomial_tree`` node values (helper ``_tree_gamma_theta``).
    """
    S0, K, r, sigma, T = (_EX21_1[k] for k in ("S0", "K", "r", "sigma", "T"))

    dt = T / 5
    u, d = trees.crr_params(sigma, dt)
    stock, option = trees.binomial_tree(S0, K, r, T, 5, u, d, kind="put", american=True)
    assert 0.5 * (stock[2][0] - stock[2][2]) == pytest.approx(11.65, abs=5e-3)
    assert trees.tree_delta(stock, option) == pytest.approx(-0.41, abs=5e-3)
    gamma, theta = _tree_gamma_theta(stock, option, dt)
    assert gamma == pytest.approx(0.03, abs=5e-3)
    assert theta == pytest.approx(-4.3, abs=0.05)
    assert theta / 365.0 == pytest.approx(-0.012, abs=5e-4)

    dt50 = T / 50
    u, d = trees.crr_params(sigma, dt50)
    stock, option = trees.binomial_tree(S0, K, r, T, 50, u, d, kind="put", american=True)
    assert trees.tree_delta(stock, option) == pytest.approx(-0.415, abs=5e-4)
    gamma, theta = _tree_gamma_theta(stock, option, dt50)
    assert gamma == pytest.approx(0.034, abs=5e-4)
    assert theta / 365.0 == pytest.approx(-0.0117, abs=5e-5)


def test_control_variate_american_put_hull_ge():
    """Hull 11e GE §21.3 pp.483-485, control variate technique (Figure 21.10).

    Same 5-step tree priced European gives f_E = 4.32 (abs 5e-3); the BSM put
    is f_BSM = 4.08 (abs 5e-3); the American tree value f_A = 4.49. The
    control-variate estimate f_A + (f_BSM - f_E) prints as 4.25: Hull adds the
    rounded numbers (4.49 + 4.08 - 4.32 = 4.25 exactly), the unrounded sum is
    4.2454 (abs 5e-3 covers both). The 100-step American benchmark is 4.278
    (abs 5e-4).
    """
    S0, K, r, sigma, T = (_EX21_1[k] for k in ("S0", "K", "r", "sigma", "T"))
    f_e = trees.crr_price(S0, K, r, sigma, T, 5, kind="put", american=False)
    f_a = trees.crr_price(S0, K, r, sigma, T, 5, kind="put", american=True)
    f_bsm = float(bsm.put_price(S0, K, r, sigma, T))
    assert f_e == pytest.approx(4.32, abs=5e-3)
    assert f_bsm == pytest.approx(4.08, abs=5e-3)
    assert f_a == pytest.approx(4.49, abs=5e-3)

    assert f_a + (f_bsm - f_e) == pytest.approx(4.25, abs=5e-3)
    assert round(f_a, 2) + (round(f_bsm, 2) - round(f_e, 2)) == pytest.approx(4.25, abs=1e-9)

    f_a_100 = trees.crr_price(S0, K, r, sigma, T, 100, kind="put", american=True)
    assert f_a_100 == pytest.approx(4.278, abs=5e-4)


def test_example_21_3_american_call_on_index_futures_hull_ge():
    """Hull 11e GE §21.2 pp.478-479, Example 21.3 and Figure 21.5.

    4-month American call on index futures, F0 = K = 300, r = 8%, sigma = 30%,
    four monthly steps with q = r so a = 1: u = 1.0905, d = 0.9170, p = 0.4784
    (abs 5e-5). The 4-step value prints as 19.16 and DerivaGem gives 20.18 and
    20.22 with 50 and 100 steps (abs 5e-3). T = 1/3 exactly (printed 0.3333).
    This is a lattice, not Monte Carlo, so no seed is involved.
    """
    F0, K, r, sigma, T = 300.0, 300.0, 0.08, 0.30, 1.0 / 3.0
    dt = T / 4
    u, d = trees.crr_params(sigma, dt)
    assert u == pytest.approx(1.0905, abs=5e-5)
    assert d == pytest.approx(0.9170, abs=5e-5)
    assert math.exp((r - r) * dt) == pytest.approx(1.0, abs=1e-12)
    assert trees.risk_neutral_p(u, d, r, dt, q=r) == pytest.approx(0.4784, abs=5e-5)

    for n_steps, printed in ((4, 19.16), (50, 20.18), (100, 20.22)):
        price = trees.crr_price(F0, K, r, sigma, T, n_steps, q=r, kind="call", american=True)
        assert price == pytest.approx(printed, abs=5e-3), n_steps


def test_example_21_4_american_put_on_currency_hull_ge():
    """Hull 11e GE §21.2 pp.479-480, Example 21.4 and Figure 21.6.

    1-year American put on a currency, S0 = 1.61, K = 1.60, r = 8%, r_f = 9%,
    sigma = 12%, four quarterly steps: a = e^{(0.08-0.09)0.25} = 0.9975,
    u = 1.0618, d = 0.9418, p = 0.4642 (abs 5e-5). The 4-step value prints as
    0.0710 and DerivaGem gives 0.0738 with both 50 and 100 steps (abs 5e-5).
    Lattice pricing, no Monte Carlo seed involved.
    """
    S0, K, r, q, sigma, T = 1.61, 1.60, 0.08, 0.09, 0.12, 1.0
    dt = T / 4
    u, d = trees.crr_params(sigma, dt)
    assert math.exp((r - q) * dt) == pytest.approx(0.9975, abs=5e-5)
    assert u == pytest.approx(1.0618, abs=5e-5)
    assert d == pytest.approx(0.9418, abs=5e-5)
    assert trees.risk_neutral_p(u, d, r, dt, q=q) == pytest.approx(0.4642, abs=5e-5)

    for n_steps, printed in ((4, 0.0710), (50, 0.0738), (100, 0.0738)):
        price = trees.crr_price(S0, K, r, sigma, T, n_steps, q=q, kind="put", american=True)
        assert price == pytest.approx(printed, abs=5e-5), n_steps


# ---------------------------------------------------------------------------
# VN-07  GE §22.2-22.4
# ---------------------------------------------------------------------------

# Table 22.4 (p.520): the 15 largest of the 500 scenario losses, $000s, ranked.
_TABLE_22_4_LOSSES = np.array(
    [
        922.484,
        858.423,
        653.541,
        490.215,
        422.291,
        362.733,
        360.532,
        353.788,
        323.505,
        305.216,
        245.151,
        241.561,
        231.269,
        230.626,
        229.683,
    ]
)
_TABLE_22_4_SCENARIOS = [427, 429, 424, 415, 482]


def test_table_22_4_historical_simulation_var_es_hull_ge():
    """Hull 11e GE §22.2 pp.519-520, Table 22.4 and the ES paragraph.

    Four-index portfolio, 500 scenarios: the one-day 99% VaR is the fifth
    worst loss, $422,291, the ten-day VaR sqrt(10) x that = $1,335,401, and the
    ES is the mean of the five worst, $669,391 (abs 5e-4 in $000s, abs 1 in $).
    Hull's 501-day data set is not in the repo, so the P&L array fed to
    ``historical_var_es`` is the 15 printed losses padded with 485 zero-loss
    scenarios: with alpha = 0.99 and n = 500 the function uses k = 5, so VaR
    and ES depend only on the five largest losses and the padding is inert.
    """
    pnl = -np.concatenate([_TABLE_22_4_LOSSES, np.zeros(500 - _TABLE_22_4_LOSSES.size)])
    var_1d, es_1d = risk.historical_var_es(pnl, alpha=0.99)
    assert var_1d == pytest.approx(422.291, abs=5e-4)
    assert es_1d == pytest.approx(669.391, abs=5e-4)
    assert math.sqrt(10.0) * var_1d * 1000.0 == pytest.approx(1_335_401, abs=1.0)


def test_brw_weighted_historical_simulation_hull_ge():
    """Hull 11e GE §22.2 p.521, "Weighting Observations" (Boudoukh-Richardson-
    Whitelaw weights) applied to Table 22.4.

    Weight of scenario i is lambda^{n-i}(1-lambda)/(1-lambda^n) with
    lambda = 0.995, n = 500. Scenarios 427, 429, 424, 415 print as 0.003776,
    0.003814, 0.003719, 0.003555 (abs 5e-7) and the cumulative weights as
    0.004833, 0.007590, 0.011309, 0.014864. The first cumulative value is a
    misprint of 0.003776: it must equal the first weight, and the printed
    second cumulative 0.007590 = 0.003776 + 0.003814 confirms it. The VaR is
    the third-ranked loss, $653,541 (first scenario whose cumulative weight
    exceeds 0.01), and the ES uses weights 0.003776, 0.003814 and
    0.01 - 0.003776 - 0.003814 on the top three losses: "about $833,200"
    (computed 833.23 in $000s, abs 0.1). hullkit has no weighted historical
    simulation, so the weights and the tail average are computed inline.
    """
    lam, n = 0.995, 500

    def weight(i):
        return lam ** (n - i) * (1.0 - lam) / (1.0 - lam**n)

    assert sum(weight(i) for i in range(1, n + 1)) == pytest.approx(1.0, abs=1e-12)

    weights = np.array([weight(i) for i in _TABLE_22_4_SCENARIOS[:4]])
    assert weights == pytest.approx([0.003776, 0.003814, 0.003719, 0.003555], abs=5e-7)
    cumulative = np.cumsum(weights)
    assert cumulative == pytest.approx([0.003776, 0.007590, 0.011309, 0.014864], abs=5e-7)
    assert cumulative[0] != pytest.approx(0.004833, abs=5e-7)  # printed value is a misprint

    first_over = int(np.argmax(cumulative > 0.01))
    assert first_over == 2
    assert _TABLE_22_4_LOSSES[first_over] == pytest.approx(653.541)

    tail_weights = np.array([weights[0], weights[1], 0.01 - weights[0] - weights[1]])
    es_weighted = float(tail_weights @ _TABLE_22_4_LOSSES[:3] / 0.01)
    assert es_weighted == pytest.approx(833.2, abs=0.1)


def test_section_22_3_model_building_microsoft_att_hull_ge():
    """Hull 11e GE §22.3 pp.522-524: Microsoft / AT&T model-building example.

    $10M Microsoft at 2% daily vol (sigma_X = 200,000) and $5M AT&T at 1%
    (sigma_Y = 50,000), correlation 0.3. Print (all to the nearest $100, so
    abs 50): portfolio sigma 220,200; one-day 99% VaR 465,300 / 116,300 /
    512,300; ten-day VaR 1,471,300 / 367,800 / 1,620,100; diversification
    benefit 219,000; ten-day ES (eq. 22.1) 421,400 for AT&T and 1,856,100
    combined. Hull's Y is N^{-1}(0.99) = 2.3263 unrounded; the VaR prints only
    match with the unrounded value (2.326 x 220,200 = 512,185, not 512,300).

    The Microsoft ten-day ES does NOT reproduce: ``normal_es`` gives 1,685,629
    but the print says 1,687,000. Plugging the rounded Y = 2.326 into
    e^{-Y^2/2}/(sqrt(2 pi) 0.01) gives 2.6674 instead of 2.6652 and hence
    1,686,994, which is the printed figure - while the AT&T and combined ES
    values only match with the unrounded Y. The print is therefore internally
    inconsistent for that one entry; the computed 1,685,629 is pinned (abs 1).
    """
    z = norm.ppf(0.99)
    assert z == pytest.approx(2.3263, abs=5e-5)

    sigma_x, sigma_y = 200_000.0, 50_000.0
    sigma_p = risk.portfolio_sigma([10e6, 5e6], [0.02, 0.01], [[1.0, 0.3], [0.3, 1.0]])
    assert sigma_p == pytest.approx(220_200, abs=50)
    assert sigma_p == pytest.approx(
        math.hypot(sigma_x, sigma_y, math.sqrt(2 * 0.3 * sigma_x * sigma_y))
    )

    assert risk.normal_var(sigma_x) == pytest.approx(465_300, abs=50)
    assert risk.normal_var(sigma_y) == pytest.approx(116_300, abs=50)
    assert risk.normal_var(sigma_p) == pytest.approx(512_300, abs=50)

    var10_x = risk.normal_var(sigma_x, horizon=10)
    var10_y = risk.normal_var(sigma_y, horizon=10)
    var10_p = risk.normal_var(sigma_p, horizon=10)
    assert var10_x == pytest.approx(1_471_300, abs=50)
    assert var10_y == pytest.approx(367_800, abs=50)
    assert var10_p == pytest.approx(1_620_100, abs=50)
    assert var10_x + var10_y - var10_p == pytest.approx(219_000, abs=50)

    assert risk.normal_es(sigma_y, horizon=10) == pytest.approx(421_400, abs=50)
    assert risk.normal_es(sigma_p, horizon=10) == pytest.approx(1_856_100, abs=50)

    es10_x = risk.normal_es(sigma_x, horizon=10)
    assert es10_x == pytest.approx(1_685_629, abs=1.0)
    rounded_y_multiplier = math.exp(-0.5 * 2.326**2) / (math.sqrt(2.0 * math.pi) * 0.01)
    assert sigma_x * math.sqrt(10.0) * rounded_y_multiplier == pytest.approx(1_687_000, abs=50)


def test_table_22_8_linear_model_four_index_var_es_hull_ge():
    """Hull 11e GE §22.4 p.527, Tables 22.7-22.8 and the four-index linear model.

    Amounts ($000s) 4,000 / 3,000 / 1,000 / 2,000 in S&P 500, FTSE 100, CAC 40,
    Nikkei 225 with the printed covariance matrix: variance 14,406.193, sigma
    120.03, one-day 99% VaR 2.326 x 120.03 = 279.222, ES (eq. 22.1) 319.894.
    The covariance matrix is printed to 6 dp, and a'Ca from those rounded
    entries is 14,404.0, i.e. 0.015% below the value Hull obtained from the
    unrounded spreadsheet, so a relative tolerance of 2e-4 is used for all
    four numbers (the underlying 501-day data set is not in the repo).
    ``portfolio_sigma`` takes vols and correlations, so both are rebuilt from
    the covariance matrix (exactly, since C = diag(s) R diag(s)); the
    correlations so obtained agree with the printed Table 22.7 to within
    0.003, which is what 6-dp rounding of the covariances allows.
    """
    cov = np.array(
        [
            [0.000275, 0.000094, 0.000177, 0.000080],
            [0.000094, 0.000187, 0.000138, 0.000102],
            [0.000177, 0.000138, 0.000237, 0.000097],
            [0.000080, 0.000102, 0.000097, 0.000173],
        ]
    )
    corr_printed = np.array(
        [
            [1.0, 0.415, 0.694, 0.368],
            [0.415, 1.0, 0.656, 0.566],
            [0.694, 0.656, 1.0, 0.482],
            [0.368, 0.566, 0.482, 1.0],
        ]
    )
    amounts = np.array([4000.0, 3000.0, 1000.0, 2000.0])

    vols = np.sqrt(np.diag(cov))
    corr = cov / np.outer(vols, vols)
    assert np.abs(corr - corr_printed).max() <= 0.003

    sigma = risk.portfolio_sigma(amounts, vols, corr)
    assert sigma**2 == pytest.approx(float(amounts @ cov @ amounts), rel=1e-12)
    assert sigma**2 == pytest.approx(14_406.193, rel=2e-4)
    assert sigma == pytest.approx(120.03, rel=2e-4)
    assert risk.normal_var(sigma) == pytest.approx(279.222, rel=2e-4)
    assert risk.normal_es(sigma) == pytest.approx(319.894, rel=2e-4)


def test_example_22_1_delta_linear_model_hull_ge():
    """Hull 11e GE §22.4 pp.529-530, Example 22.1.

    Options with delta 1,000 on Microsoft ($120) and 20,000 on AT&T ($30) are
    equivalent to $120,000 and $600,000 positions; with daily vols 2% and 1%
    and correlation 0.3 the standard deviation of dP in $000s is
    sqrt((120 x 0.02)^2 + (600 x 0.01)^2 + 2 x 120 x 0.02 x 600 x 0.01 x 0.3)
    = 7.099 (abs 5e-4).
    """
    amounts = [120.0 * 1_000, 30.0 * 20_000]
    assert amounts == [120_000.0, 600_000.0]
    sigma_thousands = risk.portfolio_sigma([120.0, 600.0], [0.02, 0.01], [[1.0, 0.3], [0.3, 1.0]])
    assert sigma_thousands == pytest.approx(7.099, abs=5e-4)


# ---------------------------------------------------------------------------
# VN-12  GE §23.6-23.7 (plus the §23.2/23.3 examples they build on)
# ---------------------------------------------------------------------------

# Table 23.1 (p.550): GARCH(1,1) MLE on S&P 500, July 2015 - July 2020.
_SPX_GARCH = dict(omega=0.0000039818, alpha=0.223793, beta=0.747577)


def test_example_23_1_ewma_update_hull_ge():
    """Hull 11e GE §23.2 p.545, Example 23.1: EWMA with lambda = 0.9.

    sigma_{n-1} = 1%/day, u_{n-1} = 2%: sigma_n^2 = 0.9 x 0.0001 + 0.1 x 0.0004
    = 0.00013 (abs 1e-9), i.e. 1.14% per day (abs 5e-5 on the decimal scale).
    ``ewma_variance`` returns var[1] for a two-element return series seeded
    with ``init``.
    """
    var = volatility.ewma_variance([0.02, 0.0], lam=0.90, init=0.0001)
    assert var[1] == pytest.approx(0.00013, abs=1e-9)
    assert math.sqrt(var[1]) == pytest.approx(0.0114, abs=5e-5)


def test_example_23_2_garch_long_run_variance_hull_ge():
    """Hull 11e GE §23.3 p.546, Example 23.2.

    sigma_n^2 = 0.000002 + 0.13 u^2 + 0.86 sigma^2: gamma = 0.01 and
    V_L = omega/gamma = 0.0002 (abs 1e-9), a daily volatility of 0.014 = 1.4%
    (printed to 3 dp, abs 5e-4).
    """
    v_l = volatility.garch11_long_run(0.000002, 0.13, 0.86)
    assert 1.0 - 0.13 - 0.86 == pytest.approx(0.01, abs=1e-12)
    assert v_l == pytest.approx(0.0002, abs=1e-9)
    assert math.sqrt(v_l) == pytest.approx(0.014, abs=5e-4)


def _garch_term_vol(t_days, v0, omega, alpha, beta):
    """Eq. (23.14): annualised vol for a T-day option, T in days, 252 days/year."""
    v_l = volatility.garch11_long_run(omega, alpha, beta)
    a = math.log(1.0 / (alpha + beta))
    avg_var = v_l + (1.0 - math.exp(-a * t_days)) / (a * t_days) * (v0 - v_l)
    return math.sqrt(252.0 * avg_var)


def test_table_23_3_garch_volatility_term_structure_hull_ge():
    """Hull 11e GE §23.6 pp.554-555, eq. (23.14) and Table 23.3.

    S&P 500 GARCH(1,1) from Table 23.1: omega = 0.0000039818, alpha =
    0.223793, beta = 0.747577, so V_L = 0.0001391 (abs 5e-8) and
    a = ln(1/0.97137) = 0.02905 (abs 5e-6). With V(0) = 0.0003 the option
    volatilities for 10, 30, 50, 100, 500 days print as 26.5, 24.9, 23.8, 22.0,
    19.5 % (abs 0.05 pp; computed 26.50, 24.92, 23.76, 21.96, 19.45). The
    eq. (23.14) closed form is not in hullkit, so it is inline in
    ``_garch_term_vol``; it is cross-checked against the numerical average of
    ``garch11_forecast`` over [0, T] (eq. 23.13 with (alpha+beta)^t = e^{-at}),
    which must agree to 1e-8 relative.
    """
    omega, alpha, beta = (_SPX_GARCH[k] for k in ("omega", "alpha", "beta"))
    assert alpha + beta == pytest.approx(0.97137, abs=5e-6)
    assert volatility.garch11_long_run(omega, alpha, beta) == pytest.approx(0.0001391, abs=5e-8)
    assert math.log(1.0 / (alpha + beta)) == pytest.approx(0.02905, abs=5e-6)

    v0 = 0.0003
    days = [10, 30, 50, 100, 500]
    printed = [26.5, 24.9, 23.8, 22.0, 19.5]
    term_vols = [100.0 * _garch_term_vol(t, v0, omega, alpha, beta) for t in days]
    assert term_vols == pytest.approx(printed, abs=0.05)

    for t, closed_form in zip(days, term_vols, strict=True):
        avg_var = (
            quad(lambda s: volatility.garch11_forecast(v0, s, omega, alpha, beta), 0, t)[0] / t
        )
        assert 100.0 * math.sqrt(252.0 * avg_var) == pytest.approx(closed_form, rel=1e-8)


def test_table_23_4_volatility_change_impact_hull_ge():
    """Hull 11e GE §23.6 pp.555-556, eq. (23.15) and Table 23.4.

    With V(0) = 0.0003, sigma(0) = sqrt(252 x 0.0003) = 27.50% (abs 5e-3 pp).
    A 1% rise in the instantaneous volatility moves the T-day option
    volatility by (1 - e^{-aT})/(aT) x sigma(0)/sigma(T) x 1%, printed for
    10, 30, 50, 100, 500 days as 0.90, 0.74, 0.61, 0.41, 0.10 % (abs 5e-3 pp;
    computed 0.900, 0.736, 0.610, 0.407, 0.097). Eq. (23.15) is inline.
    """
    omega, alpha, beta = (_SPX_GARCH[k] for k in ("omega", "alpha", "beta"))
    a = math.log(1.0 / (alpha + beta))
    v0 = 0.0003
    sigma0 = math.sqrt(252.0 * v0)
    assert 100.0 * sigma0 == pytest.approx(27.50, abs=5e-3)

    days = [10, 30, 50, 100, 500]
    printed = [0.90, 0.74, 0.61, 0.41, 0.10]
    impacts = [
        100.0
        * (1.0 - math.exp(-a * t))
        / (a * t)
        * sigma0
        / _garch_term_vol(t, v0, omega, alpha, beta)
        * 0.01
        for t in days
    ]
    assert impacts == pytest.approx(printed, abs=5e-3)


def test_example_23_3_ewma_correlation_update_hull_ge():
    """Hull 11e GE §23.7 p.557, Example 23.3: EWMA covariance with lambda = 0.95.

    Day n-1: rho = 0.6, sigma_X = 1%, sigma_Y = 2%, so cov = 0.00012; moves
    x = 0.5%, y = 2.5%. Updates: sigma_X^2 = 0.00009625, sigma_Y^2 =
    0.00041125, cov = 0.00012025 (abs 1e-12, exact arithmetic); vols 0.981%
    and 2.028% (abs 5e-6); correlation 0.6044 (abs 5e-5; computed 0.60441 from
    unrounded vols, 0.60443 from Hull's rounded 0.00981 x 0.02028).
    """
    x = [0.005, 0.0]
    y = [0.025, 0.0]
    var_x = volatility.ewma_variance(x, lam=0.95, init=0.01**2)[1]
    var_y = volatility.ewma_variance(y, lam=0.95, init=0.02**2)[1]
    cov = volatility.ewma_covariance(x, y, lam=0.95, init=0.6 * 0.01 * 0.02)[1]
    assert var_x == pytest.approx(0.00009625, abs=1e-12)
    assert var_y == pytest.approx(0.00041125, abs=1e-12)
    assert cov == pytest.approx(0.00012025, abs=1e-12)
    assert math.sqrt(var_x) == pytest.approx(0.00981, abs=5e-6)
    assert math.sqrt(var_y) == pytest.approx(0.02028, abs=5e-6)
    assert cov / math.sqrt(var_x * var_y) == pytest.approx(0.6044, abs=5e-5)


def test_garch_covariance_update_reduces_to_ewma_hull_ge():
    """Hull 11e GE §23.7 p.557: cov_n = omega + alpha x y + beta cov_{n-1} and the
    long-term covariance omega/(1 - alpha - beta).

    The GE text prints the formulas but no numeric example, so there is no
    printed value to pin; this test pins the two structural claims made on the
    page instead. (i) With omega = 0, alpha = 1 - lambda, beta = lambda the
    GARCH update is the EWMA update of ``ewma_covariance`` (Example 23.3
    inputs, abs 1e-15). (ii) The long-term covariance is the same formula as
    ``garch11_long_run``. The Example 23.2 parameters applied to the Example
    23.3 inputs give cov_n = 0.00012145, which is a derived number, not a
    printed one.
    """
    x_prev, y_prev, cov_prev = 0.005, 0.025, 0.00012

    def garch_cov_update(omega, alpha, beta):
        return omega + alpha * x_prev * y_prev + beta * cov_prev

    lam = 0.95
    ewma = volatility.ewma_covariance([x_prev, 0.0], [y_prev, 0.0], lam=lam, init=cov_prev)[1]
    assert garch_cov_update(0.0, 1.0 - lam, lam) == pytest.approx(ewma, abs=1e-15)

    omega, alpha, beta = 0.000002, 0.13, 0.86
    assert garch_cov_update(omega, alpha, beta) == pytest.approx(0.00012145, abs=1e-12)
    assert omega / (1.0 - alpha - beta) == pytest.approx(
        volatility.garch11_long_run(omega, alpha, beta), rel=1e-12
    )


def test_eq_23_17_inconsistent_covariance_matrix_hull_ge():
    """Hull 11e GE §23.7 p.558, eq. (23.17) consistency condition.

    Omega = [[1, 0, 0.9], [0, 1, 0.9], [0.9, 0.9, 1]] is symmetric with unit
    variances but not positive-semidefinite: with w = (1, 1, -1), w'Omega w =
    3 - 2(0.9 + 0.9) = -0.6 < 0 (the print states only that (23.17) fails; the
    -0.6 is the arithmetic on the page, abs 1e-12). The smallest eigenvalue
    (-0.273) confirms it. Computed with numpy; hullkit has no PSD helper.
    """
    omega = np.array([[1.0, 0.0, 0.9], [0.0, 1.0, 0.9], [0.9, 0.9, 1.0]])
    w = np.array([1.0, 1.0, -1.0])
    assert float(w @ omega @ w) == pytest.approx(-0.6, abs=1e-12)
    assert np.linalg.eigvalsh(omega).min() < 0.0
    assert np.allclose(omega, omega.T)
