"""Tests for hullkit.mc (GBM simulation, Hull Ch.14)."""

import numpy as np
import pytest
from hullkit import mc

PARAMS = dict(S0=100.0, mu=0.10, sigma=0.20, T=1.0)


def test_shape_and_initial_column():
    paths = mc.simulate_gbm_paths(**PARAMS, n_steps=50, n_paths=100)
    assert paths.shape == (100, 51)
    assert np.allclose(paths[:, 0], 100.0)
    assert np.all(paths > 0.0)


def test_seeded_reproducibility():
    a = mc.simulate_gbm_paths(**PARAMS, n_steps=10, n_paths=5, rng=np.random.default_rng(7))
    b = mc.simulate_gbm_paths(**PARAMS, n_steps=10, n_paths=5, rng=np.random.default_rng(7))
    assert np.array_equal(a, b)


def test_moments_match_theory():
    # E[S_T]=S0 e^{mu T}=110.517, Var per gbm_theory; SE(mean)~0.07 at 100k paths
    paths = mc.simulate_gbm_paths(**PARAMS, n_steps=50, n_paths=100_000)
    st = paths[:, -1]
    e_th, v_th = mc.gbm_theory(**PARAMS)
    assert e_th == pytest.approx(100.0 * np.exp(0.10), abs=1e-12)
    assert st.mean() == pytest.approx(e_th, abs=0.5)
    assert st.var() == pytest.approx(v_th, rel=0.03)


def test_lognormal_property():
    # ln S_T ~ N(ln S0 + (mu - sigma^2/2) T, sigma^2 T)  (Hull eq. 14.19)
    paths = mc.simulate_gbm_paths(**PARAMS, n_steps=50, n_paths=100_000)
    ln_st = np.log(paths[:, -1])
    assert ln_st.mean() == pytest.approx(np.log(100.0) + (0.10 - 0.02), abs=0.005)
    assert ln_st.var() == pytest.approx(0.04, rel=0.03)
