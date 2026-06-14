"""Tests for hullkit.fd_advanced (explicit scheme + stability).

The explicit scheme is accurate when stable (small von-Neumann factor) and
blows up when the time grid is too coarse — the reason CN/implicit are preferred.
"""

from hullkit import bsm
from hullkit import fd_advanced as fda


def test_explicit_matches_bsm_when_stable():
    price = fda.fd_explicit(100.0, 100.0, 0.05, 0.20, 1.0, n_s=100, n_t=4000)
    assert fda.stability_factor(0.20, 100, 4000) < 0.5
    assert abs(price - bsm.call_price(100.0, 100.0, 0.05, 0.20, 1.0)) < 0.05


def test_explicit_blows_up_when_unstable():
    assert fda.stability_factor(0.20, 200, 100) > 1.0
    price = fda.fd_explicit(100.0, 100.0, 0.05, 0.20, 1.0, n_s=200, n_t=100)
    assert abs(price) > 1e6  # unstable: oscillations amplify without bound


def test_stability_factor_scales_with_steps():
    # finer time grid (larger n_t) lowers the factor; finer space grid raises it
    assert fda.stability_factor(0.20, 100, 8000) < fda.stability_factor(0.20, 100, 1000)
    assert fda.stability_factor(0.20, 400, 1000) > fda.stability_factor(0.20, 100, 1000)
