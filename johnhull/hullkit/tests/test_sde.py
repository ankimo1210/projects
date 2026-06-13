"""Tests for hullkit.sde (A1 stochastic-calculus primitives).

The Itô/Stratonovich pins are *exact* algebraic identities (telescoping sums),
not Monte-Carlo approximations, so they hold for any seed. The GBM/Girsanov pins
tie the simulation back to the closed-form values the Hull volumes rely on.
"""

import numpy as np
from hullkit import bsm, mc, sde


def test_brownian_paths_shape_and_variance():
    W = sde.brownian_paths(2.0, 1000, 5000, rng=np.random.default_rng(0))
    assert W.shape == (5000, 1001)
    assert np.allclose(W[:, 0], 0.0)
    # Var[W_T] = T = 2.0
    assert abs(W[:, -1].var() - 2.0) < 0.15


def test_quadratic_variation_converges_to_time():
    W = sde.brownian_paths(1.0, 2000, 4000, rng=np.random.default_rng(1))
    qv = sde.quadratic_variation(W)
    assert abs(qv.mean() - 1.0) < 0.02
    # refining the mesh shrinks the spread of the realized QV around T
    coarse = sde.quadratic_variation(
        sde.brownian_paths(1.0, 50, 4000, rng=np.random.default_rng(1))
    )
    assert qv.std() < coarse.std()


def test_ito_and_stratonovich_are_exact_identities():
    W = sde.brownian_paths(1.0, 500, 3000, rng=np.random.default_rng(2))
    w_t = W[:, -1]
    qv = sde.quadratic_variation(W)
    left = sde.ito_riemann_sum(W, alpha=0.0)  # Itô
    mid = sde.ito_riemann_sum(W, alpha=0.5)  # Stratonovich
    # telescoping identities — exact to floating point, independent of the seed
    assert np.allclose(left, 0.5 * (w_t**2 - qv))
    assert np.allclose(mid, 0.5 * w_t**2)
    # the gap is exactly ½[W]_T -> ½T: the Itô correction
    assert abs(np.mean(mid - left) - 0.5) < 0.02


def test_euler_maruyama_matches_gbm_mean():
    S0, mu, sigma, T = 100.0, 0.10, 0.20, 1.0
    paths = sde.euler_maruyama(
        lambda x, t: mu * x,
        lambda x, t: sigma * x,
        S0,
        T,
        300,
        100_000,
        rng=np.random.default_rng(3),
    )
    e_st, _ = mc.gbm_theory(S0, mu, sigma, T)
    # weak order 1: terminal mean within a fraction of a percent
    assert abs(paths[:, -1].mean() - e_st) / e_st < 0.01


def test_girsanov_reweights_real_world_to_risk_neutral_price():
    S0, K, r, sigma, T, mu = 100.0, 100.0, 0.05, 0.20, 1.0, 0.12
    rng = np.random.default_rng(4)
    # simulate under the REAL-WORLD drift mu (one exact log-Euler step)
    s_t = mc.simulate_gbm_paths(S0, mu, sigma, T, 1, 500_000, rng=rng)[:, -1]
    w = sde.girsanov_weights(s_t, S0, sigma, T, mu_from=mu, mu_to=r)
    assert abs(w.mean() - 1.0) < 0.02  # E^P[dQ/dP] = 1
    price = float(np.mean(w * np.exp(-r * T) * np.maximum(s_t - K, 0.0)))
    assert abs(price - bsm.call_price(S0, K, r, sigma, T)) < 0.10
