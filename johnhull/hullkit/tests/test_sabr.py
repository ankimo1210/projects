"""Tests for hullkit.sabr (Hagan implied-vol expansion).

Pins the well-known limiting behaviour: beta=1 with no vol-of-vol is a flat smile
at alpha; the ATM branch is continuous with the general formula; a negative rho
tilts the smile downward in strike.
"""

import pytest
from hullkit import sabr


def test_flat_smile_when_volvol_zero_and_beta_one():
    for K in (80.0, 100.0, 120.0):
        iv = sabr.sabr_implied_vol(100.0, K, 1.0, 0.20, 1.0, 0.0, 1e-8)
        assert abs(iv - 0.20) < 1e-4, K


def test_atm_branch_is_continuous():
    args = (1.0, 0.20, 0.5, -0.3, 0.4)
    atm = sabr.sabr_implied_vol(100.0, 100.0, *args)
    near = sabr.sabr_implied_vol(100.0, 100.0 * (1 + 1e-6), *args)
    assert abs(atm - near) < 1e-4


def test_negative_rho_gives_downward_skew():
    lo = sabr.sabr_implied_vol(100.0, 90.0, 1.0, 0.20, 0.5, -0.5, 0.4)
    hi = sabr.sabr_implied_vol(100.0, 110.0, 1.0, 0.20, 0.5, -0.5, 0.4)
    assert lo > hi


def test_validates_inputs():
    with pytest.raises(ValueError):
        sabr.sabr_implied_vol(100.0, 100.0, 1.0, -0.1, 0.5, 0.0, 0.4)  # alpha <= 0
    with pytest.raises(ValueError):
        sabr.sabr_implied_vol(100.0, 100.0, 1.0, 0.2, 0.5, 1.5, 0.4)  # rho out of range
