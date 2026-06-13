"""Tests for pde_book.solvers — checked against analytic PDE solutions."""

import numpy as np
from pde_book import datasets, grids, solvers


# --------------------------------------------------------------------------- #
# Heat equation.
# --------------------------------------------------------------------------- #
def test_heat_explicit_matches_mode_decay_when_stable():
    g = grids.Grid1D(0.0, 1.0, 81)
    x, dx = g.x, g.dx
    alpha = 1.0
    dt = 0.4 * dx**2 / alpha  # r = 0.4 (stable)
    steps = 200
    u0 = solvers.heat_mode_solution(x, 0.0, alpha, L=1.0, mode=1)
    U = solvers.solve_heat_explicit(u0, alpha, dx, dt, steps)
    exact = solvers.heat_mode_solution(x, steps * dt, alpha, L=1.0, mode=1)
    np.testing.assert_allclose(U[-1], exact, atol=2e-3)


def test_heat_explicit_blows_up_when_unstable():
    g = grids.Grid1D(0.0, 1.0, 81)
    x, dx = g.x, g.dx
    dt = 0.7 * dx**2  # r = 0.7 > 1/2
    U = solvers.solve_heat_explicit(datasets.bump(x, 0.5, 0.15), 1.0, dx, dt, steps=300)
    assert np.max(np.abs(U[-1])) > 5.0  # high-frequency content explodes


def test_heat_implicit_is_stable_for_large_r():
    g = grids.Grid1D(0.0, 1.0, 81)
    x, dx = g.x, g.dx
    alpha = 1.0
    dt = 2.0 * dx**2 / alpha  # r = 2.0: explicit would explode
    steps = 100
    u0 = solvers.heat_mode_solution(x, 0.0, alpha, L=1.0, mode=1)
    U = solvers.solve_heat_implicit(u0, alpha, dx, dt, steps)
    assert np.max(np.abs(U[-1])) < np.max(np.abs(u0))  # decays, stays bounded
    exact = solvers.heat_mode_solution(x, steps * dt, alpha, L=1.0, mode=1)
    np.testing.assert_allclose(U[-1], exact, atol=5e-3)


# --------------------------------------------------------------------------- #
# Transport / advection.
# --------------------------------------------------------------------------- #
def test_transport_upwind_advects_to_the_right():
    g = grids.Grid1D(0.0, 1.0, 201)
    x, dx = g.x, g.dx
    c = 1.0
    dt = 0.8 * dx / c  # CFL = 0.8
    steps = 100
    u0 = datasets.gaussian(x, 0.3, 0.05)
    U = solvers.solve_transport(u0, c, dx, dt, steps, scheme="upwind")
    moved = x[np.argmax(U[-1])]
    assert abs(moved - (0.3 + c * steps * dt)) < 0.05  # peak near 0.7


def test_transport_ftcs_is_unstable():
    g = grids.Grid1D(0.0, 1.0, 201)
    x, dx = g.x, g.dx
    dt = 0.8 * dx
    U = solvers.solve_transport(datasets.gaussian(x, 0.3, 0.05), 1.0, dx, dt, 200, scheme="ftcs")
    assert np.max(np.abs(U[-1])) > 5.0


# --------------------------------------------------------------------------- #
# Wave equation.
# --------------------------------------------------------------------------- #
def test_wave_matches_standing_mode():
    g = grids.Grid1D(0.0, 1.0, 201)
    x, dx = g.x, g.dx
    c = 1.0
    dt = 0.8 * dx / c  # CFL = 0.8
    steps = 50
    u0 = solvers.wave_mode_solution(x, 0.0, c, L=1.0, mode=1)
    v0 = np.zeros_like(x)
    U = solvers.solve_wave(u0, v0, c, dx, dt, steps)
    exact = solvers.wave_mode_solution(x, steps * dt, c, L=1.0, mode=1)
    np.testing.assert_allclose(U[-1], exact, atol=5e-3)


# --------------------------------------------------------------------------- #
# Laplace / Poisson.
# --------------------------------------------------------------------------- #
def test_poisson_matches_sine_product_solution():
    g = grids.Grid2D(0.0, 1.0, 0.0, 1.0, 41, 41)
    X, Y = g.meshgrid()
    u_exact = np.sin(np.pi * X) * np.sin(np.pi * Y)
    rhs = -2 * np.pi**2 * u_exact  # laplacian(u) = -2 pi^2 u
    u = solvers.solve_poisson_2d(rhs, g, boundary=np.zeros_like(u_exact))
    np.testing.assert_allclose(u, u_exact, atol=1e-2)


def test_laplace_reproduces_linear_harmonic_function():
    g = grids.Grid2D(0.0, 1.0, 0.0, 1.0, 21, 21)
    X, _Y = g.meshgrid()
    boundary = X.copy()  # u = x on the boundary
    u = solvers.solve_poisson_2d(np.zeros_like(X), g, boundary=boundary)
    np.testing.assert_allclose(u, X, atol=1e-10)  # x is harmonic -> exact on the 5-pt stencil


# --------------------------------------------------------------------------- #
# Fourier.
# --------------------------------------------------------------------------- #
def test_square_wave_partial_sum_converges_away_from_jump():
    val = solvers.square_wave_partial_sum(np.pi / 2, 50, L=np.pi)  # midpoint of the +1 half
    assert abs(val - 1.0) < 0.05
    # more terms -> smaller error at this interior point
    e_few = abs(solvers.square_wave_partial_sum(np.pi / 2, 3, L=np.pi) - 1.0)
    e_many = abs(solvers.square_wave_partial_sum(np.pi / 2, 40, L=np.pi) - 1.0)
    assert e_many < e_few
