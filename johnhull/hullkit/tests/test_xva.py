"""Tests for hullkit.xva (exposure profiles + CVA/DVA/FVA).

The exposure of an at-the-money forward starts at zero and grows; PFE dominates
EE; and CVA matches a hand-computed constant-exposure case exactly.
"""

import numpy as np
from hullkit import xva


def test_exposure_profile_shape():
    S0, r, sigma, T = 100.0, 0.05, 0.20, 1.0
    k = S0 * np.exp(r * T)  # at-the-money forward
    _, mtm = xva.forward_exposure(
        S0, r, sigma, k, T, n_steps=50, n_paths=40_000, rng=np.random.default_rng(0)
    )
    ee = xva.expected_exposure(mtm)
    pf = xva.pfe(mtm, 0.975)
    assert ee[0] < 1e-9  # MtM is exactly 0 at inception
    assert ee[-1] > ee[1]  # exposure grows with diffusion
    assert np.all(pf >= ee - 1e-9)  # PFE quantile dominates the mean


def test_cva_matches_hand_computation():
    # constant EE = 5, r = 0  =>  CVA = (1-R) * EE * (1 - e^{-lambda T})
    t = np.linspace(0.0, 1.0, 51)
    ee = np.full(51, 5.0)
    expected = (1 - 0.4) * 5.0 * (1 - np.exp(-0.02 * 1.0))
    assert abs(xva.cva(t, ee, hazard=0.02, recovery=0.4, r=0.0) - expected) < 1e-12


def test_cva_dva_fva_are_positive():
    S0, r, sigma, T = 100.0, 0.05, 0.20, 1.0
    k = S0 * np.exp(r * T)
    t, mtm = xva.forward_exposure(
        S0, r, sigma, k, T, n_steps=50, n_paths=40_000, rng=np.random.default_rng(1)
    )
    ee = xva.expected_exposure(mtm)
    ene = xva.expected_negative_exposure(mtm)
    assert xva.cva(t, ee, 0.02, 0.4, r) > 0
    assert xva.dva(t, ene, 0.015, 0.4, r) > 0
    assert xva.fva(t, ee, 0.01, r) > 0
