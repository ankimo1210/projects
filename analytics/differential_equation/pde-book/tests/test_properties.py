"""Property-based tests (hypothesis) for the PDE solvers.

Conservation laws and the harmonic property should hold for many inputs, not
just the hand-picked examples in test_solvers.py.
"""

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st
from pde_book import grids, solvers

SETTINGS = settings(max_examples=20, deadline=None)


@SETTINGS
@given(speed=st.floats(0.5, 2.0), left=st.booleans(), center=st.floats(0.25, 0.75))
def test_upwind_transport_conserves_mass(speed, left, center):
    """Periodic upwind advection conserves sum(u) for any speed/direction."""
    g = grids.Grid1D(0.0, 1.0, 201)
    x, dx = g.x, g.dx
    c = -speed if left else speed
    u0 = np.exp(-(((x - center) / 0.05) ** 2))
    U = solvers.solve_transport(u0, c, dx, 0.8 * dx / abs(c), 80, "upwind")
    assert abs(U[-1].sum() - U[0].sum()) / U[0].sum() < 1e-9


@SETTINGS
@given(a=st.floats(-3, 3), b=st.floats(-3, 3))
def test_laplace_reproduces_any_linear_field(a, b):
    """Linear u = a x + b y is harmonic, so Laplace must reproduce it exactly."""
    g = grids.Grid2D(0.0, 1.0, 0.0, 1.0, 17, 17)
    X, Y = g.meshgrid()
    target = a * X + b * Y
    u = solvers.solve_poisson_2d(np.zeros_like(X), g, boundary=target)
    np.testing.assert_allclose(u, target, atol=1e-9)


@SETTINGS
@given(amp=st.floats(0.5, 2.0), phase=st.floats(0, 2 * np.pi))
def test_burgers_conserves_momentum(amp, phase):
    """Conservative Burgers on a periodic domain conserves sum(u) to round-off."""
    g = grids.Grid1D(0.0, 1.0, 300)
    x, dx = g.x, g.dx
    nu = 1e-2
    u0 = amp * np.sin(2 * np.pi * x + phase)
    # Respect BOTH stability limits: advective CFL (dx/max|u|) and diffusive (dx^2/(2 nu)).
    dt = 0.4 * min(dx / max(amp, 0.1), dx**2 / (2 * nu))
    U = solvers.solve_burgers(u0, nu=nu, dx=dx, dt=dt, steps=150)
    assert np.all(np.isfinite(U[-1]))
    assert abs(U[-1].sum() - U[0].sum()) * dx < 1e-9


@SETTINGS
@given(mode=st.integers(1, 4), r=st.floats(0.6, 5.0))
def test_crank_nicolson_stays_bounded_for_any_r(mode, r):
    """Crank-Nicolson is unconditionally stable: a sine mode never grows for any r."""
    g = grids.Grid1D(0.0, 1.0, 81)
    x, dx = g.x, g.dx
    u0 = np.sin(mode * np.pi * x)
    U = solvers.solve_heat_crank_nicolson(u0, 1.0, dx, r * dx**2, 60)
    assert np.max(np.abs(U[-1])) <= np.max(np.abs(u0)) + 1e-9
