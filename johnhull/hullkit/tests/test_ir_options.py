"""Tests for hullkit.ir_options against Hull 11e Ch.29/30."""

import math

import pytest
from hullkit import ir_options


def test_caplet_floorlet_values_and_parity():
    p = math.exp(-0.065 * 1.25)
    caplet = ir_options.caplet_black(1e6, 0.25, 0.07, 0.08, 0.20, 1.0, p, kind="caplet")
    floorlet = ir_options.caplet_black(1e6, 0.25, 0.07, 0.08, 0.20, 1.0, p, kind="floorlet")
    assert caplet == pytest.approx(519.0046, abs=1e-3)
    assert floorlet == pytest.approx(2823.9125, abs=1e-3)
    # Black put-call parity: caplet - floorlet = L delta P (F - R_K)
    assert caplet - floorlet == pytest.approx(1e6 * 0.25 * p * (0.07 - 0.08), abs=1e-6)


def test_swaption_payer_receiver_parity_and_atm():
    L, A, s_F, sigma, T = 1e6, 3.5, 0.06, 0.20, 2.0
    payer = ir_options.swaption_black(L, A, s_F, 0.062, sigma, T, kind="payer")
    receiver = ir_options.swaption_black(L, A, s_F, 0.062, sigma, T, kind="receiver")
    assert payer - receiver == pytest.approx(L * A * (s_F - 0.062), abs=1e-6)
    # ATM: s_K = s_F -> payer == receiver
    pa = ir_options.swaption_black(L, A, s_F, s_F, sigma, T, kind="payer")
    ra = ir_options.swaption_black(L, A, s_F, s_F, sigma, T, kind="receiver")
    assert pa == pytest.approx(ra, abs=1e-9)


def test_cap_minus_floor_equals_swap():
    L = 1e6
    forwards = [0.05, 0.055, 0.06]
    accruals = [0.5, 0.5, 0.5]
    pay_disc = [math.exp(-0.05 * t) for t in (1.0, 1.5, 2.0)]
    fix_times = [0.5, 1.0, 1.5]
    R_K = 0.055
    cap = ir_options.cap_black(L, forwards, R_K, 0.2, accruals, pay_disc, fix_times, kind="cap")
    floor = ir_options.cap_black(L, forwards, R_K, 0.2, accruals, pay_disc, fix_times, kind="floor")
    swap = sum(L * d * p * (f - R_K) for f, d, p in zip(forwards, accruals, pay_disc, strict=True))
    assert cap - floor == pytest.approx(swap, abs=1e-6)


def test_bond_option_parity():
    p0t, f_b, k, sigma, T = 0.9, 102.0, 100.0, 0.08, 2.0
    c = ir_options.bond_option_black(p0t, f_b, k, sigma, T, kind="call")
    put = ir_options.bond_option_black(p0t, f_b, k, sigma, T, kind="put")
    assert c - put == pytest.approx(p0t * (f_b - k), abs=1e-9)


def test_convexity_adjustment_positive_and_scales():
    # G''/G' > 0 for a standard bond (price convex in yield) -> adjustment positive
    adj1 = ir_options.convexity_adjustment(0.05, 0.20, 1.0, 30.0)
    adj2 = ir_options.convexity_adjustment(0.05, 0.20, 2.0, 30.0)
    assert adj1 > 0.0
    assert adj2 == pytest.approx(2.0 * adj1, abs=1e-12)  # linear in T
    # expected yield = y_F + adjustment > y_F
    e_y = 0.05 + adj1
    assert e_y > 0.05


def test_validation_errors():
    with pytest.raises(ValueError):
        ir_options.caplet_black(1e6, 0.25, 0.07, 0.08, 0.2, 1.0, 0.9, kind="cap")
    with pytest.raises(ValueError):
        ir_options.swaption_black(1e6, 3.5, 0.06, 0.06, 0.2, 2.0, kind="straddle")


def test_cap_black_accepts_numpy_spot_vols():
    import numpy as np

    forwards = [0.05, 0.055, 0.06]
    accruals = [0.5, 0.5, 0.5]
    pay_disc = [math.exp(-0.05 * t) for t in (1.0, 1.5, 2.0)]
    fix_times = [0.5, 1.0, 1.5]
    spot = [0.18, 0.20, 0.19]
    cap_list = ir_options.cap_black(1e6, forwards, 0.055, spot, accruals, pay_disc, fix_times)
    cap_np = ir_options.cap_black(
        1e6, forwards, 0.055, np.array(spot), accruals, pay_disc, fix_times
    )
    assert cap_np == pytest.approx(cap_list, abs=1e-9)


def test_wrapper_reference_values():
    # magnitude pins so a sigma/T regression is caught (not just parity)
    assert ir_options.bond_option_black(0.9, 102.0, 100.0, 0.08, 2.0, kind="call") == pytest.approx(
        5.063184, abs=1e-5
    )
    assert ir_options.swaption_black(
        1e6, 3.5, 0.06, 0.062, 0.20, 2.0, kind="payer"
    ) == pytest.approx(20670.9113, abs=1e-2)
    fw = [0.05, 0.055, 0.06]
    ac = [0.5, 0.5, 0.5]
    pd = [math.exp(-0.05 * t) for t in (1.0, 1.5, 2.0)]
    ft = [0.5, 1.0, 1.5]
    assert ir_options.cap_black(1e6, fw, 0.055, 0.2, ac, pd, ft) == pytest.approx(
        6382.326, abs=1e-2
    )


def test_convexity_adjustment_coefficient_pin():
    # pin the 0.5 y^2 sigma^2 T coefficient (was only checked for sign + T-linearity)
    assert ir_options.convexity_adjustment(0.05, 0.20, 1.0, 30.0) == pytest.approx(0.0015, abs=1e-9)
