"""Tests for pde_book.grids — spacing, stencils, stability numbers."""

import numpy as np
from pde_book import grids


def test_grid1d_spacing_and_endpoints():
    g = grids.Grid1D(0.0, 2.0, 5)
    assert g.x[0] == 0.0 and g.x[-1] == 2.0
    assert abs(g.dx - 0.5) < 1e-12
    assert g.x.size == 5


def test_grid2d_meshgrid_shapes():
    g = grids.Grid2D(0.0, 1.0, 0.0, 2.0, 4, 6)
    X, Y = g.meshgrid()
    assert X.shape == Y.shape == (g.ny, g.nx) == (6, 4)
    assert abs(g.dx - 1 / 3) < 1e-12
    assert abs(g.dy - 0.4) < 1e-12


def test_laplacian_1d_of_quadratic_is_two():
    x = np.linspace(-1, 1, 201)
    dx = x[1] - x[0]
    lap = grids.laplacian_1d(x**2, dx)  # (x^2)'' = 2 on the interior
    np.testing.assert_allclose(lap[1:-1], 2.0, atol=1e-9)


def test_laplacian_periodic_of_sine():
    x = np.linspace(0, 2 * np.pi, 400, endpoint=False)
    dx = x[1] - x[0]
    lap = grids.laplacian_1d(np.sin(x), dx, periodic=True)  # sin'' = -sin
    np.testing.assert_allclose(lap, -np.sin(x), atol=1e-3)


def test_second_difference_matrix_shape_and_action():
    n = 12
    dx = 0.1
    L = grids.second_difference_matrix(n, dx)
    assert L.shape == (n - 2, n - 2)
    x = np.linspace(0, (n - 1) * dx, n)
    u = x**2
    approx = L @ u[1:-1]
    # interior second difference of x^2 ~ 2 (endpoints of the interior excluded)
    np.testing.assert_allclose(approx[1:-1], 2.0, atol=1e-6)


def test_stability_numbers_and_thresholds():
    assert abs(grids.heat_number(1.0, 0.5, 1.0) - 0.5) < 1e-12
    assert abs(grids.courant_number(2.0, 0.5, 1.0) - 1.0) < 1e-12
    assert grids.heat_stable(1.0, 0.004, 0.1)  # r = 0.4 <= 0.5
    assert not grids.heat_stable(1.0, 0.006, 0.1)  # r = 0.6 > 0.5
    assert grids.cfl_ok(1.0, 0.1, 0.1)  # C = 1.0
    assert not grids.cfl_ok(1.0, 0.2, 0.1)  # C = 2.0
