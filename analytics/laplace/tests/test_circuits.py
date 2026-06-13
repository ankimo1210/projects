"""Tests for laplace_book.circuits (RC / RLC transfer functions)."""

import numpy as np
from laplace_book import circuits as C
from laplace_book import systems as S


def test_rc_lowpass_gain_and_timeconstant():
    R, Cap = 1000.0, 1e-6  # tau = RC = 1 ms
    sys = C.rc_lowpass(R, Cap)
    assert abs(S.dc_gain(sys) - 1.0) < 1e-12
    assert abs(S.time_constant(sys) - R * Cap) < 1e-15
    np.testing.assert_allclose(S.poles(sys), [-1.0 / (R * Cap)], rtol=1e-9)


def test_rc_highpass_blocks_dc():
    sys = C.rc_highpass(1000.0, 1e-6)
    assert abs(S.dc_gain(sys)) < 1e-12  # no DC through a high-pass


def test_rlc_params_regimes():
    # Underdamped: small R.
    p = C.rlc_params(R=10.0, L=1e-3, C=1e-6)
    assert p["regime"] == "underdamped" and p["zeta"] < 1
    assert abs(p["wn"] - 1.0 / np.sqrt(1e-3 * 1e-6)) < 1e-3
    # Overdamped: large R.
    p2 = C.rlc_params(R=5000.0, L=1e-3, C=1e-6)
    assert p2["regime"] == "overdamped" and p2["zeta"] > 1


def test_rlc_vc_matches_second_order():
    R, L, Cap = 10.0, 1e-3, 1e-6
    sys = C.rlc_series_vc(R, L, Cap)
    wn, zeta = S.second_order_params(sys)
    p = C.rlc_params(R, L, Cap)
    assert abs(wn - p["wn"]) < 1e-3
    assert abs(zeta - p["zeta"]) < 1e-9
    assert abs(S.dc_gain(sys) - 1.0) < 1e-12  # capacitor passes DC fully
