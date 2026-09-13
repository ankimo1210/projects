"""Tests for hullkit.cds: Hull Tables 25.1–25.5, Example 25.1, CDS forwards/options."""

import pytest
from hullkit import cds
from hullkit.credit_curve import HazardCurve

HULL = dict(curve=0.02, recovery=0.4, r=0.05, maturity=5.0, freq=1)


def test_tables_25_2_to_25_4_legs_and_par_spread():
    legs = cds.cds_legs(**HULL)
    assert legs.annuity == pytest.approx(4.0728, abs=5e-5)
    assert legs.accrual == pytest.approx(0.0422, abs=5e-5)
    assert legs.protection == pytest.approx(0.0506, abs=5e-5)
    assert legs.risky_duration == pytest.approx(4.1150, abs=5e-5)
    assert cds.cds_par_spread(**HULL) * 1e4 == pytest.approx(123.0, abs=0.5)


def test_hazard_curve_and_float_inputs_agree():
    curve = HazardCurve.from_constant(0.02)
    assert cds.cds_par_spread(curve, 0.4, 0.05, 5.0) == pytest.approx(
        cds.cds_par_spread(0.02, 0.4, 0.05, 5.0), abs=1e-15
    )


def test_mark_to_market_at_150bp():
    assert cds.cds_mtm(0.0150, **HULL) == pytest.approx(0.0111, abs=5e-5)
    assert cds.cds_mtm(0.0150, side="buyer", **HULL) == pytest.approx(-0.0111, abs=5e-5)
    with pytest.raises(ValueError):
        cds.cds_mtm(0.0150, side="dealer", **HULL)


def test_implied_hazard_for_100bp_and_round_trip():
    lam = cds.implied_hazard(0.0100, 0.4, 0.05, 5.0)
    assert lam == pytest.approx(0.0163, abs=5e-5)
    assert cds.cds_par_spread(lam, 0.4, 0.05, 5.0) == pytest.approx(0.0100, abs=1e-12)


def test_binary_cds_table_25_5():
    legs = cds.cds_legs(0.02, 0.4, 0.05, 5.0, binary=True)
    assert legs.protection == pytest.approx(0.0844, abs=5e-5)
    assert cds.binary_cds_spread(0.02, 0.05, 5.0) * 1e4 == pytest.approx(205.0, abs=0.5)


def test_example_25_1_fixed_coupon_price():
    spread = cds.actual360_to_actual_actual(0.0034)
    coupon = cds.actual360_to_actual_actual(0.0040)
    assert spread == pytest.approx(0.00345, abs=5e-6)
    assert coupon == pytest.approx(0.00406, abs=5e-6)
    lam = cds.implied_hazard(spread, 0.4, 0.04, 5.0, freq=4)
    assert lam == pytest.approx(0.005717, abs=5e-6)
    duration = cds.cds_risky_duration(lam, 0.4, 0.04, 5.0, freq=4)
    assert duration == pytest.approx(4.447, abs=5e-4)
    assert cds.fixed_coupon_price(spread, coupon, duration) == pytest.approx(100.27, abs=5e-3)
    # seller pays 0.27% of notional up front (Hull: 1,000,000 * 125 * 0.0027 for the index)
    assert cds.upfront_payment(spread, coupon, duration, notional=1.0) == pytest.approx(
        -0.0027, abs=5e-5
    )


def test_bootstrap_from_cds_round_trip():
    tenors, quotes = [1.0, 3.0, 5.0], [0.0060, 0.0100, 0.0140]
    curve = cds.bootstrap_from_cds(tenors, quotes, recovery=0.4, r=0.05, freq=4)
    for T, q in zip(tenors, quotes, strict=True):
        assert cds.cds_par_spread(curve, 0.4, 0.05, T, freq=4) == pytest.approx(q, abs=1e-10)
    assert curve.hazards[0] < curve.hazards[1] < curve.hazards[2]  # upward-sloping quotes


def test_forward_spread_is_between_spot_spreads_for_upward_curve():
    curve = HazardCurve((1.0, 5.0), (0.01, 0.03))
    spot_1y = cds.cds_par_spread(curve, 0.4, 0.05, 1.0, freq=4)
    spot_5y = cds.cds_par_spread(curve, 0.4, 0.05, 5.0, freq=4)
    fwd = cds.cds_forward_spread(curve, 0.4, 0.05, start=1.0, maturity=5.0, freq=4)
    assert spot_1y < spot_5y < fwd  # forward exceeds both because the 1–5y hazard is 3%


def test_cds_option_parity_and_zero_vol_limit():
    F, K, A = 0.0280, 0.0250, 4.0
    payer = cds.cds_option(F, K, 0.5, 1.0, A, kind="payer")
    receiver = cds.cds_option(F, K, 0.5, 1.0, A, kind="receiver")
    assert payer - receiver == pytest.approx(A * (F - K), abs=1e-12)
    assert cds.cds_option(F, K, 1e-9, 1.0, A, kind="payer") == pytest.approx(
        A * max(F - K, 0.0), abs=1e-9
    )
    assert cds.cds_option(F, K, 1e-9, 1.0, A, kind="receiver") == pytest.approx(0.0, abs=1e-9)
    with pytest.raises(ValueError):
        cds.cds_option(F, K, 0.5, 1.0, A, kind="straddle")


def test_validation_errors():
    with pytest.raises(ValueError):
        cds.cds_legs(0.02, 1.0, 0.05, 5.0)
    with pytest.raises(ValueError):
        cds.cds_legs(0.02, 0.4, 0.05, 0.3, freq=1)
    with pytest.raises(ValueError):
        cds.cds_forward_spread(0.02, 0.4, 0.05, start=5.0, maturity=5.0)
