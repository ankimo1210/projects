"""Tests for hullkit.mc_advanced (variance reduction + quasi-MC).

Every estimator must be unbiased (price -> BSM); control variates and importance
sampling must shrink the standard error; Sobol QMC must beat plain MC accuracy.
"""

import numpy as np
from hullkit import bsm
from hullkit import mc_advanced as mca


def test_all_estimators_are_unbiased():
    S0, K, r, sigma, T = 100.0, 100.0, 0.05, 0.20, 1.0
    true = bsm.call_price(S0, K, r, sigma, T)
    n = 2**14
    p, p_se = mca.plain_price(S0, K, r, sigma, T, n, np.random.default_rng(0))
    c, _ = mca.control_variate_price(S0, K, r, sigma, T, n, np.random.default_rng(0))
    q = mca.qmc_price(S0, K, r, sigma, T, 14, seed=0)
    assert abs(p - true) < 4 * p_se
    assert abs(c - true) < 0.05
    assert abs(q - true) < 0.02


def test_control_variate_reduces_standard_error():
    S0, K, r, sigma, T = 100.0, 100.0, 0.05, 0.20, 1.0
    n = 2**14
    _, p_se = mca.plain_price(S0, K, r, sigma, T, n, np.random.default_rng(0))
    _, c_se = mca.control_variate_price(S0, K, r, sigma, T, n, np.random.default_rng(0))
    assert c_se < 0.6 * p_se


def test_importance_sampling_helps_deep_otm():
    S0, K, r, sigma, T = 100.0, 150.0, 0.05, 0.20, 1.0
    true = bsm.call_price(S0, K, r, sigma, T)
    n = 2**14
    _, p_se = mca.plain_price(S0, K, r, sigma, T, n, np.random.default_rng(1))
    i, i_se = mca.importance_sampling_price(S0, K, r, sigma, T, n, np.random.default_rng(1))
    assert abs(i - true) < 4 * i_se
    assert i_se < 0.5 * p_se


def test_qmc_converges_faster_than_plain():
    out = mca.error_vs_n(100.0, 100.0, 0.05, 0.20, 1.0, ms=range(8, 15), seed=0)
    assert len(out["N"]) == len(out["qmc"]) == 7
    # at the largest sample size Sobol QMC is more accurate than plain MC
    assert out["qmc"][-1] < out["plain"][-1]
