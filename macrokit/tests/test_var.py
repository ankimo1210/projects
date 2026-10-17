import numpy as np
import pytest

from macrokit.termstructure import var


def _ar_path(rng, n=4000):
    mu = np.array([0.1, -0.2])
    phi = np.array([[0.9, 0.05], [0.0, 0.7]])
    x = np.zeros((n, 2))
    for t in range(1, n):
        x[t] = mu + phi @ x[t - 1] + rng.normal(scale=0.1, size=2)
    return mu, phi, x


def test_fit_var1_recovers_a_long_path():
    _mu, phi, x = _ar_path(np.random.default_rng(1))
    fit = var.fit_var1(x)
    np.testing.assert_allclose(fit.phi, phi, atol=0.03)
    np.testing.assert_allclose(fit.sigma, 0.01 * np.eye(2), atol=0.002)


def test_batch_fit_matches_one_at_a_time():
    rng = np.random.default_rng(2)
    paths = np.stack([_ar_path(rng, 300)[2] for _ in range(3)])
    mus, phis = var.fit_var1_batch(paths)
    for b in range(3):
        single = var.fit_var1(paths[b])
        np.testing.assert_allclose(mus[b], single.mu, atol=1e-10)
        np.testing.assert_allclose(phis[b], single.phi, atol=1e-10)


def test_simulation_starts_at_x0_and_is_reproducible():
    _mu, _phi, x = _ar_path(np.random.default_rng(3), 200)
    fit = var.fit_var1(x)
    a = var.simulate_var1_batch(fit.mu, fit.phi, fit.resid, x[0], 4, np.random.default_rng(9))
    b = var.simulate_var1_batch(fit.mu, fit.phi, fit.resid, x[0], 4, np.random.default_rng(9))
    assert a.shape == (4, 200, 2)
    np.testing.assert_array_equal(a, b)
    np.testing.assert_array_equal(a[:, 0], np.broadcast_to(x[0], (4, 2)))


def test_simulation_follows_the_var_recursion():
    mu = np.array([0.3, -0.4])
    phi = np.array([[0.9, 0.2], [-0.1, 0.7]])
    x0 = np.array([1.5, -2.0])
    sim = var.simulate_var1_batch(mu, phi, np.zeros((20, 2)), x0, 3, np.random.default_rng(5))
    assert sim.shape == (3, 21, 2)
    for path in sim:
        s = x0.copy()
        rows = [s]
        for _ in range(20):
            s = mu + phi @ s
            rows.append(s)
        np.testing.assert_allclose(path, np.array(rows), rtol=1e-12, atol=1e-12)


def test_simulation_adds_the_residual_drawn_for_each_step():
    mu = np.array([0.3, -0.4])
    phi = np.array([[0.9, 0.2], [-0.1, 0.7]])
    x0 = np.array([1.5, -2.0])
    resid = np.random.default_rng(6).normal(size=(20, 2))
    sim = var.simulate_var1_batch(mu, phi, resid, x0, 3, np.random.default_rng(7))
    draws = resid[np.random.default_rng(7).integers(0, 20, size=(3, 20))]
    for b, path in enumerate(sim):
        s = x0.copy()
        for t in range(1, 21):
            s = mu + phi @ s + draws[b, t - 1]
            np.testing.assert_allclose(path[t], s, rtol=1e-12, atol=1e-12)


def test_expected_average_matches_matrix_powers():
    mu = np.array([0.01, 0.02])
    phi = np.array([[0.95, 0.1], [0.0, 0.8]])
    d0, d1 = 0.5, np.array([1.0, 2.0])
    x = np.array([[0.3, -0.1], [0.0, 0.2]])
    horizon = 7
    expected = np.zeros(2)
    for t in range(2):
        state = x[t].copy()
        for _ in range(horizon):
            expected[t] += d0 + d1 @ state
            state = mu + phi @ state
    np.testing.assert_allclose(
        var.expected_average(mu, phi, d0, d1, x, horizon), expected / horizon
    )
    batch = var.expected_average(np.stack([mu, mu]), np.stack([phi, phi]), d0, d1, x, horizon)
    assert batch.shape == (2, 2)
    np.testing.assert_allclose(batch[1], expected / horizon)


def test_max_abs_eig():
    assert var.max_abs_eig(np.diag([0.5, -0.99])) == pytest.approx(0.99)
