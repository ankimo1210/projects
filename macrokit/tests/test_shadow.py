import numpy as np
import pytest

from macrokit.termstructure import acm, shadow

THETA = shadow.pack(
    rho_q=(0.997, 0.95, 0.8),
    delta0=1.0,
    sigma=np.array([[0.15, 0.0, 0.0], [0.05, 0.2, 0.0], [0.0, -0.05, 0.25]]),
    mu=np.zeros(3),
    rho=np.diag([0.99, 0.94, 0.8]),
    omega=0.05,
)


def test_pack_and_unpack_round_trip():
    p = shadow.unpack(THETA)
    np.testing.assert_allclose(p.rho_q[0], [0.997, 0.95, 0.8])
    np.testing.assert_allclose(p.sigma[0, 1, 0], 0.05)
    np.testing.assert_allclose(p.omega, [0.05])
    np.testing.assert_allclose(
        shadow.pack(p.rho_q[0], p.delta0[0], p.sigma[0], p.mu[0], p.rho[0], p.omega[0]), THETA
    )


def test_far_from_the_bound_forwards_are_the_gaussian_affine_forwards():
    p = shadow.unpack(THETA)
    x = np.array([[0.4, -0.3, 0.2]])
    months = np.array([3, 24, 120])
    approx = shadow.shadow_forwards(THETA, x, -100.0, months)[0]
    # Independent check: price the shadow bond with the ACM recursion in decimal per month.
    a, b = acm.pricing_recursion(
        np.zeros(3),
        np.diag(p.rho_q[0]),
        (p.sigma[0] @ p.sigma[0].T) / 1200**2,
        0.0,
        p.delta0[0] / 1200,
        np.ones(3),
        121,
    )
    xd = x[0] / 1200
    exact = [1200 * (a[n] - a[n + 1] + (b[n] - b[n + 1]) @ xd) for n in months]
    np.testing.assert_allclose(approx, exact, atol=1e-8)


def test_expected_short_average_matches_simulation():
    rng = np.random.default_rng(31)
    p = shadow.unpack(THETA)
    x0 = np.array([-0.8, 0.1, 0.0])
    horizon, paths = 24, 100_000
    x = np.broadcast_to(x0, (paths, 3)).copy()
    total = np.zeros(paths)
    for _ in range(horizon):
        total += np.maximum(0.0, p.delta0[0] + x.sum(axis=1))
        x = p.mu[0] + x @ p.rho[0].T + rng.standard_normal((paths, 3)) @ p.sigma[0].T
    simulated = (total / horizon).mean()
    closed = shadow.expected_short_average(THETA, x0[None], 0.0, horizon)[0]
    assert closed == pytest.approx(simulated, abs=5e-3)  # ~4 Monte Carlo standard errors


def test_very_low_bound_reduces_to_the_gaussian_expectation():
    states = np.array([[0.4, -0.3, 0.2], [-1.0, 0.5, 0.0]])
    low = shadow.expected_short_average(THETA, states, -10.0, 120)
    np.testing.assert_allclose(low, shadow.expected_gaussian_average(THETA, states, 120), atol=1e-4)
    near = shadow.expected_short_average(THETA, states, 0.0, 120)
    assert np.abs(near - shadow.expected_gaussian_average(THETA, states, 120)).max() > 0.01


def _simulated_forwards(n, rng):
    p = shadow.unpack(THETA)
    x = np.zeros(3)
    states = np.empty((n, 3))
    for t in range(n):
        x = p.mu[0] + p.rho[0] @ x + p.sigma[0] @ rng.standard_normal(3)
        states[t] = x
    clean = shadow.shadow_forwards(THETA, states, 0.0, shadow.FORWARD_MONTHS)
    return clean + 0.05 * rng.standard_normal(clean.shape), states


def test_loglik_prefers_the_true_parameters():
    forwards, _ = _simulated_forwards(600, np.random.default_rng(32))
    bumped = THETA + 0.05
    values = shadow.loglik(np.vstack([THETA, bumped]), forwards, 0.0)
    assert values[0] > values[1]


def test_filtered_states_track_the_true_states():
    forwards, states = _simulated_forwards(600, np.random.default_rng(33))
    filtered = shadow.filtered_states(THETA, forwards, 0.0)
    true_rate = shadow.shadow_rate(THETA, states)
    assert np.corrcoef(shadow.shadow_rate(THETA, filtered), true_rate)[0, 1] > 0.95


def test_loglik_penalises_non_stationary_dynamics():
    p = shadow.unpack(THETA)
    explosive = shadow.pack(p.rho_q[0], p.delta0[0], p.sigma[0], p.mu[0], 1.01 * np.eye(3), 0.05)
    forwards, _ = _simulated_forwards(50, np.random.default_rng(34))
    values = shadow.loglik(np.vstack([THETA, explosive]), forwards, 0.0)
    assert values[1] == -shadow.PENALTY
    assert np.isfinite(values[0]) and values[0] > -shadow.PENALTY


def test_one_degenerate_member_does_not_penalise_the_batch():
    forwards, _ = _simulated_forwards(50, np.random.default_rng(35))
    degenerate = THETA.copy()
    degenerate[22] = -40.0  # omega ~ 4e-18: the innovation matrix is numerically singular
    alone = shadow.loglik(THETA, forwards, 0.0)
    values = shadow.loglik(np.vstack([THETA, degenerate]), forwards, 0.0)
    np.testing.assert_allclose(values[0], alone[0], rtol=1e-12)
    assert values[1] == -shadow.PENALTY
