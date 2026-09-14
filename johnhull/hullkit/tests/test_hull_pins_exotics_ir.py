"""Printed-value pins for Hull 11e Global Edition Chapters 26, 29, 30 and 32.

Audit item EX-01 (2026-09-14 section audit). Each test reproduces one printed
example or table value with the hullkit function that implements the section
and pins it at the print's rounding, plus a tighter pin on the computed value
so a silent drift inside the rounding band is still caught. Page numbers are
PDF pages of the Global Edition PDF; they coincide with the printed folios.
"""

import math

import pytest
from hullkit import exotics, ir_options, rates, swaps, trees
from hullkit import hull_white as hw


def test_up_and_out_call_hull_table_26_1():
    """Hull 11e GE §26.17 p.633-634, Table 26.1 (static options replication).

    A 9-month up-and-out call on a non-dividend-paying stock: S0 = 50, K = 50,
    barrier H = 60, r = 10%, sigma = 30%. The replicating portfolio of Table 26.1
    is worth 0.73; the text compares it with "0.31 given by the analytic formula
    for the up-and-out option" (p.634). The audit probe gave 0.3136; the analytic
    value is 0.313571, which rounds to the printed 0.31 (abs 5e-3). The 0.73
    replicating-portfolio value needs the time-stepped option ladder of Table
    26.1, which hullkit does not implement, so it is not pinned here.
    """
    value = exotics.barrier_call(50.0, 50.0, 60.0, 0.10, 0.30, 0.75, barrier="up-and-out")
    assert value == pytest.approx(0.31, abs=5e-3)
    assert value == pytest.approx(0.313571, abs=1e-5)


def test_floating_lookback_call_hull_example_26_2():
    """Hull 11e GE §26.11 p.624, Example 26.2.

    Newly issued floating lookback on a non-dividend-paying stock: S0 = Smin = 50,
    sigma = 40%, r = 10%, q = 0, T = 0.25. The text prints the floating lookback
    put as 7.79 and the newly issued floating lookback call as 8.04. The computed
    call 8.0371 rounds to the printed 8.04 (abs 5e-3); the put (7.79) is pinned
    in ``test_exotics_puts.py``.
    """
    value = exotics.lookback_floating_call(50.0, 50.0, 0.10, 0.40, 0.25)
    assert value == pytest.approx(8.04, abs=5e-3)
    assert value == pytest.approx(8.03712, abs=1e-5)


def test_asian_average_price_call_hull_example_26_3():
    """Hull 11e GE §26.13 p.627, Example 26.3 (continuous arithmetic average).

    S0 = 50, K = 50, r = 10%, q = 0, sigma = 40%, T = 1. The text prints the
    first two moments of the average, M1 = 52.59 and M2 = 2,922.76 (eqs. 26.3 and
    26.4), F0 = 52.59, the Black volatility 23.54%, and the option value 5.62.
    `asian_call_turnbull_wakeman` does the moment match internally; the
    computed 5.6168 rounds to the printed 5.62 (abs 5e-3). M1, M2 and the
    implied Black volatility are recomputed inline from eqs. (26.3)-(26.4)
    because no hullkit function returns them; the tolerances are the print
    rounding (1e-2 on M1/M2 at two decimals, 5e-5 on a percentage at two
    decimals). The 12/52/250-observation values (6.00, 5.70, 5.63) are for a
    discrete average, which hullkit does not implement.
    """
    S0, K, r, q, sigma, T = 50.0, 50.0, 0.10, 0.0, 0.40, 1.0
    value = exotics.asian_call_turnbull_wakeman(S0, K, r, sigma, T, q=q)
    assert value == pytest.approx(5.62, abs=5e-3)
    assert value == pytest.approx(5.61679, abs=1e-5)

    b = r - q
    m1 = (math.exp(b * T) - 1.0) * S0 / (b * T)
    m2 = 2.0 * math.exp((2.0 * b + sigma**2) * T) * S0**2 / (
        (b + sigma**2) * (2.0 * b + sigma**2) * T**2
    ) + 2.0 * S0**2 / (b * T**2) * (1.0 / (2.0 * b + sigma**2) - math.exp(b * T) / (b + sigma**2))
    black_vol = math.sqrt(math.log(m2 / m1**2) / T)
    assert m1 == pytest.approx(52.59, abs=1e-2)
    assert m2 == pytest.approx(2922.76, abs=1e-2)
    assert black_vol == pytest.approx(0.2354, abs=5e-5)


def test_bond_option_black_hull_example_29_1():
    """Hull 11e GE §29.1 p.690, Example 29.1 (European call on a coupon bond).

    10-month call on a 9.75-year 10% semiannual bond, face 1,000, cash price 960,
    coupons of 50 in 3 and 9 months, 3-/9-/10-month zero rates 9.0% / 9.5% / 10%
    (continuous), forward-price volatility 9%. The text prints the coupon PV
    I = 95.45, the forward bond price F_B = 939.68 (eq. 29.3), P(0, T) = 0.9200,
    and then (a) 9.49 for a cash strike of 1,000 and (b) 7.97 for a quoted strike
    of 1,000, i.e. cash strike 1,000 + 100 x 0.08333 = 1,008.33 (one month of
    accrued interest). I comes from `rates.bond_price`; F_B and P(0, T) are the
    one-line eq. (29.3) glue. Computed with unrounded inputs: 9.4873 and 7.9686,
    both within the two-decimal print (abs 5e-3).
    """
    T = 10.0 / 12.0
    coupon_pv = rates.bond_price([0.25, 0.75], [50.0, 50.0], [0.09, 0.095])
    forward_bond = (960.0 - coupon_pv) * math.exp(0.10 * T)
    p0t = math.exp(-0.10 * T)
    assert coupon_pv == pytest.approx(95.45, abs=5e-3)
    assert forward_bond == pytest.approx(939.68, abs=5e-3)
    assert p0t == pytest.approx(0.9200, abs=5e-5)

    call_cash_strike = ir_options.bond_option_black(p0t, forward_bond, 1000.0, 0.09, T, kind="call")
    assert call_cash_strike == pytest.approx(9.49, abs=5e-3)
    assert call_cash_strike == pytest.approx(9.48726, abs=1e-5)

    quoted_strike_cash = 1000.0 + 100.0 / 12.0
    assert quoted_strike_cash == pytest.approx(1008.33, abs=5e-3)
    call_quoted_strike = ir_options.bond_option_black(
        p0t, forward_bond, quoted_strike_cash, 0.09, T, kind="call"
    )
    assert call_quoted_strike == pytest.approx(7.97, abs=5e-3)
    assert call_quoted_strike == pytest.approx(7.96860, abs=1e-5)


def test_payer_swaption_black_hull_example_29_4():
    """Hull 11e GE §29.3 p.701, Example 29.4 (European payer swaption).

    Zero curve flat at 6% (continuous); right to pay 6.2% in a 3-year semiannual
    swap starting in 5 years, principal 100 million, forward swap rate 6.1%
    continuous = 6.194% semiannual, volatility 20%. The text prints the annuity
    A = 2.0035 (six discount factors at 5.5 ... 8 years times 1/2), s_F = 0.06194,
    and the value 2.19 (in $ millions). A is built from `swaps.discount` on the
    flat curve, s_F from `rates.from_continuous`; the computed A = 2.003558 sits
    inside 1e-4 of the printed 2.0035 (Hull truncates rather than rounds here),
    and the computed value 2.1908 rounds to the printed 2.19 (abs 5e-3).
    """
    flat_curve = ([1.0, 10.0], [0.06, 0.06])
    pay_times = [5.5, 6.0, 6.5, 7.0, 7.5, 8.0]
    annuity = 0.5 * sum(swaps.discount(t, flat_curve) for t in pay_times)
    forward_swap_rate = rates.from_continuous(0.061, 2)
    assert annuity == pytest.approx(2.0035, abs=1e-4)
    assert forward_swap_rate == pytest.approx(0.06194, abs=5e-6)

    value_millions = ir_options.swaption_black(
        100.0, annuity, forward_swap_rate, 0.062, 0.20, 5.0, kind="payer"
    )
    assert value_millions == pytest.approx(2.19, abs=5e-3)
    assert value_millions == pytest.approx(2.19082, abs=1e-5)


def test_quanto_american_call_crr_hull_example_30_4():
    """Hull 11e GE §30.3 p.713-714, Example 30.4 (quanto American call, CRR tree).

    2-year American option paying S - K in sterling, S the S&P 500: S0 = K = 1,200,
    r_GBP = 5%, r_USD = 3%, dividend yield 1.5%, sigma_S = 25%, sigma_FX = 12%,
    correlation 0.2. Eq. (30.7) raises the S&P growth rate by
    0.2 x 0.25 x 0.12 = 0.006 under the sterling numeraire, so the index behaves
    like an asset with yield q = 0.05 - (0.03 - 0.015 + 0.006) = 0.029. The text
    then values it with S = 1,200, K = 1,200, r = 0.05, q = 0.029, sigma = 0.25,
    T = 2 and 100 time steps (DerivaGem) as 179.83. `trees.crr_price` with N = 100
    gives 179.826 (audit probe agrees), inside the two-decimal print (abs 5e-3).
    The pin is specific to N = 100: N = 500 gives 180.14, so this is a check of
    the DerivaGem tree, not of the converged price.
    """
    quanto_drift = 0.2 * 0.25 * 0.12
    assert quanto_drift == pytest.approx(0.006, abs=1e-12)
    effective_yield = 0.05 - (0.03 - 0.015 + quanto_drift)
    assert effective_yield == pytest.approx(0.029, abs=1e-12)

    value = trees.crr_price(
        1200.0, 1200.0, 0.05, 0.25, 2.0, 100, q=effective_yield, kind="call", american=True
    )
    assert value == pytest.approx(179.83, abs=5e-3)
    assert value == pytest.approx(179.826, abs=1e-3)


def test_hull_white_zcb_put_analytic_hull_table_32_3():
    """Hull 11e GE §32.5 p.748-749, Example 32.1 with Tables 32.2 and 32.3.

    3-year (3 x 365 days) European put on a zero-coupon bond paying 100 in 9 years
    (9 x 365 days), strike 63, Hull-White a = 0.1, sigma = 0.01, zero curve of
    Table 32.2 (continuous, actual/365, linear interpolation between pillars).
    Table 32.3 prints the analytic value 1.8093 in every row; only that column
    is pinned. The tree column (1.8468 ... 1.8091) depends on the tree
    conventions and is not required. `hw_zcb_option` prices a unit-face bond,
    so strike 0.63 is scaled by 100; `rates.discount_factor` interpolates zero
    rates linearly, matching the stated convention. Computed 1.809294, within
    the four-decimal print (abs 5e-5).
    """
    days = [3, 31, 62, 94, 185, 367, 731, 1096, 1461, 1826, 2194, 2558, 2922, 3287, 3653]
    rate_pct = [
        5.01772, 4.98284, 4.97234, 4.96157, 4.99058, 5.09389, 5.79733, 6.30595,
        6.73464, 6.94816, 7.08807, 7.27527, 7.30852, 7.39790, 7.49015,
    ]  # fmt: skip
    curve = ([d / 365.0 for d in days], [p / 100.0 for p in rate_pct])
    params = hw.HullWhiteParams(mean_reversion=0.1, volatility=0.01)
    expiry = 3.0 * 365.0 / 365.0
    bond_maturity = 9.0 * 365.0 / 365.0

    put = 100.0 * hw.hw_zcb_option(expiry, bond_maturity, 0.63, curve, params, option_type="put")
    assert put == pytest.approx(1.8093, abs=5e-5)
    assert put == pytest.approx(1.809294, abs=1e-6)
