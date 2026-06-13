"""Property-based tests (hypothesis): invariants that must hold for many inputs.

These complement the example-based tests by letting hypothesis search the
parameter space for counterexamples to conservation / classification / accuracy.
"""

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st
from ode_book import solvers, systems

# Solvers loop in Python, so disable the per-example deadline and keep counts modest.
SETTINGS = settings(max_examples=25, deadline=None)


@SETTINGS
@given(rate=st.floats(0.2, 3.0), y0=st.floats(-3.0, 3.0))
def test_rk4_matches_exponential_decay(rate, y0):
    """RK4 reproduces the closed-form solution of dy/dt = -rate*y for any (rate, y0)."""
    t = np.linspace(0, 3, 400)
    Y = solvers.rk4(systems.exponential(-rate), [y0], t)[:, 0]
    np.testing.assert_allclose(Y, y0 * np.exp(-rate * t), atol=1e-4, rtol=1e-4)


@SETTINGS
@given(a=st.floats(-3, 3), b=st.floats(-3, 3), c=st.floats(-3, 3), d=st.floats(-3, 3))
def test_symmetric_negative_definite_is_stable_node(a, b, c, d):
    """A = -(M Mᵀ) - I is symmetric negative-definite, so it must be a stable node."""
    M = np.array([[a, b], [c, d]])
    A = -(M @ M.T) - np.eye(2)  # real, symmetric, all eigenvalues < 0
    assert systems.classify_fixed_point(A) == "stable node"


@SETTINGS
@given(
    S=st.floats(0, 1),
    inf=st.floats(0, 1),
    R=st.floats(0, 1),
    beta=st.floats(0.1, 1.0),
    gamma=st.floats(0.1, 1.0),
)
def test_sir_derivatives_sum_to_zero(S, inf, R, beta, gamma):
    """S' + I' + R' = 0 for every state and parameter (population is conserved)."""
    deriv = systems.sir(beta, gamma, N=1.0)(0.0, np.array([S, inf, R]))
    assert abs(float(np.sum(deriv))) < 1e-12


@SETTINGS
@given(omega=st.floats(0.3, 3.0), gamma=st.floats(0.05, 0.9))
def test_underdamped_oscillator_is_stable_spiral(omega, gamma):
    """0 < gamma < omega gives complex eigenvalues with negative real part."""
    if gamma >= omega:  # only test the under-damped regime
        return
    J = np.array([[0.0, 1.0], [-(omega**2), -2 * gamma]])
    assert systems.classify_fixed_point(J) == "stable spiral"
