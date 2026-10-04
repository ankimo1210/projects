"""Hull §28.8 drift changes, raw Gaussian density and TN20 chain rule."""

import importlib
import math

import numpy as np
import pytest
from scipy.integrate import quad

CASES = [
    (np.eye(3), [0.2, -0.1, 0.15], [0.12, 0.08, -0.18], [-0.09, 0.17, 0.04]),
    (
        [[1, 0.45, -0.3], [0.45, 1, 0.2], [-0.3, 0.2, 1]],
        [0.2, -0.1, 0.15],
        [0.12, 0.08, -0.18],
        [-0.09, 0.17, 0.04],
    ),
    ([[1, -0.6], [-0.6, 1]], [0.3, 0.1], [-0.15, 0.12], [0.11, -0.09]),
    ([[1]], [0.3], [-0.15], [0.12]),
    ([[1, 1], [1, 1]], [0.2, -0.1], [0.08, 0.02], [0.12, -0.02]),
    ([[1, -1], [-1, 1]], [0.2, 0.05], [-0.1, 0.15], [0.15, -0.05]),
    ([[1, 1 - 1e-12], [1 - 1e-12, 1]], [0.2, -0.1], [0.08, 0.02], [0.12, -0.02]),
    (np.eye(2), [0.2, -0.1], [0, 0], [0, 0]),
    (np.eye(2), [0, 0], [0.08, 0.02], [0.12, -0.02]),
]


def model():
    return importlib.import_module("hullkit._numeraire_change")


def bilinear(x, C, y):
    return math.fsum(x[i] * C[i, j] * y[j] for i in range(len(x)) for j in range(len(y)))


@pytest.mark.parametrize("C,sv,sg,sh", CASES)
def test_original_2833_to_2835_covariance_and_inverse_direction(C, sv, sg, sh):
    C = np.asarray(C)
    sv, sg, sh = map(np.asarray, (sv, sg, sh))
    shift = bilinear(sv, C, sh - sg)
    actual = model().numeraire_drift_change(0.08, sv, sg, sh, C)
    assert actual == pytest.approx(0.08 + shift, abs=1e-12)
    assert model().numeraire_drift_change(actual, sv, sh, sg, C) == pytest.approx(0.08, abs=1e-12)


def test_nontraded_physical_to_q_drift_keeps_risk_adjustment_not_r():
    assert model().physical_to_q_drift(
        0.08, [0.2, -0.1, 0.15], [0.4, -0.25, 0.18]
    ) == pytest.approx(-0.052)
    C = np.ones((2, 2))
    assert model().physical_to_q_drift(0.08, [0.2, -0.1], [0.4, -0.2], C) == pytest.approx(
        model().physical_to_q_drift(0.08, [0.2, -0.1], [10.4, -10.2], C), abs=1e-12
    )


@pytest.mark.parametrize("state", [-20.0, 0.0, 50.0])
def test_absolute_drift_works_at_zero_and_negative_nontraded_state(state):
    C = np.array([[1, 0.45, -0.3], [0.45, 1, 0.2], [-0.3, 0.2, 1]])
    loading = np.array([3.0, -1.0, 2.0]) + state * np.array([0.005, 0.002, -0.001])
    old = 0.7 - 0.08 * state
    g = np.array([0.12, 0.08, -0.18])
    h = np.array([-0.09, 0.17, 0.04])
    expected = old + bilinear(loading, C, h - g)
    assert model().numeraire_drift_change(old, loading, g, h, C) == pytest.approx(
        expected, abs=1e-12
    )


@pytest.mark.parametrize("theta", [0.4, 1.7, 3.0])
def test_technical_note_20_nontraded_chain_rule(theta):
    s = np.array([0.22, -0.08])
    old = np.zeros(2)
    new = np.array([-0.35, 0.19])
    f = theta**2 + 2
    fx = 2 * theta
    theta_shift = model().numeraire_drift_change(0.0, theta * s, old, new)
    f_shift = model().numeraire_drift_change(0.0, fx * theta * s, old, new)
    assert f_shift == pytest.approx(fx * theta_shift, abs=1e-12)
    assert model().numeraire_drift_change(0.0, theta * fx / f * s, old, new) * f == pytest.approx(
        f_shift
    )


@pytest.mark.parametrize("case", CASES[:4])
def test_joint_gaussian_tilt_matches_quad_and_fixed_seed_raw_mc(case):
    C, sv, sg, sh = case
    C = np.asarray(C)
    sv, sg, sh = map(np.asarray, (sv, sg, sh))
    delta = sh - sg
    T = 1.7
    initial = 2.0
    mu = 0.08
    vv = bilinear(sv, C, sv)
    vw = bilinear(delta, C, delta)
    cov = bilinear(sv, C, delta)
    mu_new = model().numeraire_drift_change(mu, sv, sg, sh, C)
    expected = initial * math.exp(mu_new * T)
    sd = math.sqrt(vv * T)
    # Condition density on the variable shock; integrate the remaining Gaussian analytically.
    beta = cov * math.sqrt(T / vv)
    residue = vw * T - beta * beta
    oracle = quad(
        lambda z: (
            initial
            * math.exp((mu - 0.5 * vv) * T + sd * z)
            * math.exp(-0.5 * vw * T + beta * z + 0.5 * residue)
            * math.exp(-z * z / 2)
            / math.sqrt(2 * math.pi)
        ),
        -12,
        12,
        epsabs=1e-11,
        epsrel=1e-11,
    )[0]
    assert oracle == pytest.approx(expected, abs=1e-10)
    n = 262144
    vals, vecs = np.linalg.eigh(C)
    L = vecs * np.sqrt(np.maximum(vals, 0))[None, :]
    W = np.random.default_rng(7301).standard_normal((n, len(sv))) @ L.T * math.sqrt(T)
    density = model().numeraire_density(W, sg, sh, T, C)
    for sample, truth in [
        (density, 1.0),
        (density * initial * np.exp((mu - 0.5 * vv) * T + W @ sv), expected),
    ]:
        se = sample.std(ddof=1) / math.sqrt(n)
        assert abs(sample.mean() - truth) <= 5 * se
    changed = model().new_measure_brownian_increment(W, sg, sh, T, C)
    weighted = density[:, None] * changed
    se = weighted.std(axis=0, ddof=1) / math.sqrt(n)
    assert np.all(abs(weighted.mean(axis=0)) <= 5 * se)


def test_basis_rotation_and_local_state_loadings():
    angle = 0.713
    R = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
    b = np.array([3.0, -1.0])
    g = np.array([0.12, 0.08])
    h = np.array([-0.09, 0.17])
    assert model().numeraire_drift_change(0.7, b, g, h) == pytest.approx(
        model().numeraire_drift_change(0.7, b @ R, g @ R, h @ R), abs=1e-12
    )
    batch = model().numeraire_drift_change(
        np.array([0.7, -0.9]), np.array([[3.0, -1.0], [3.1, -0.96]]), g, h
    )
    assert batch.shape == (2,)


@pytest.mark.parametrize(
    "call",
    [
        lambda m: m.numeraire_drift_change(0.08, [0.2, 0.1], [0.1], [0.2, 0.3]),
        lambda m: m.numeraire_density([0.0, 0.0], [0.1, 0.2], [0.2, 0.3], -1),
        lambda m: m.numeraire_drift_change(
            0.08, [0.2, 0.1], [0.1, 0.2], [0.2, 0.3], [[1, 2], [2, 1]]
        ),
    ],
)
def test_undefined_factor_contract_rejected(call):
    with pytest.raises(ValueError):
        call(model())
