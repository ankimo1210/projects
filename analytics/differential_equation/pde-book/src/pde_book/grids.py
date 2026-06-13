"""Grids, finite-difference stencils, and stability (CFL) numbers.

A PDE solver is "a rule on a grid". This module holds the grids and the
dimensionless numbers that decide whether an explicit scheme stays stable, kept
separate from the time-stepping in ``solvers`` so the tests can pin them down.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp


@dataclass
class Grid1D:
    """Uniform 1-D grid on [x0, x1] with n points."""

    x0: float
    x1: float
    n: int

    @property
    def x(self) -> np.ndarray:
        return np.linspace(self.x0, self.x1, self.n)

    @property
    def dx(self) -> float:
        return (self.x1 - self.x0) / (self.n - 1)


@dataclass
class Grid2D:
    """Uniform 2-D grid on [x0,x1] x [y0,y1] with (nx, ny) points."""

    x0: float
    x1: float
    y0: float
    y1: float
    nx: int
    ny: int

    @property
    def x(self) -> np.ndarray:
        return np.linspace(self.x0, self.x1, self.nx)

    @property
    def y(self) -> np.ndarray:
        return np.linspace(self.y0, self.y1, self.ny)

    @property
    def dx(self) -> float:
        return (self.x1 - self.x0) / (self.nx - 1)

    @property
    def dy(self) -> float:
        return (self.y1 - self.y0) / (self.ny - 1)

    def meshgrid(self):
        """Return (X, Y) with shape (ny, nx) — row index = y, col index = x."""
        return np.meshgrid(self.x, self.y)


# --------------------------------------------------------------------------- #
# Spatial stencils.
# --------------------------------------------------------------------------- #
def laplacian_1d(u: np.ndarray, dx: float, periodic: bool = False) -> np.ndarray:
    """Second difference (discrete 1-D Laplacian) of an array.

    Interior points use the 3-point central stencil. If ``periodic`` the array
    wraps; otherwise the two end values are returned unchanged (caller sets BCs).
    """
    u = np.asarray(u, dtype=float)
    if periodic:
        return (np.roll(u, -1) - 2.0 * u + np.roll(u, 1)) / dx**2
    out = np.zeros_like(u)
    out[1:-1] = (u[2:] - 2.0 * u[1:-1] + u[:-2]) / dx**2
    return out


def second_difference_matrix(n: int, dx: float) -> sp.csr_matrix:
    """Sparse (n-2)x(n-2) second-difference operator for interior Dirichlet nodes."""
    m = n - 2
    main = -2.0 * np.ones(m)
    off = np.ones(m - 1)
    L = sp.diags([off, main, off], offsets=[-1, 0, 1], format="csr") / dx**2
    return L


# --------------------------------------------------------------------------- #
# Dimensionless stability numbers (the heart of "do not break the grid").
# --------------------------------------------------------------------------- #
def heat_number(alpha: float, dt: float, dx: float) -> float:
    """Diffusion number r = alpha dt / dx^2. Explicit FTCS is stable iff r <= 1/2."""
    return alpha * dt / dx**2


def courant_number(c: float, dt: float, dx: float) -> float:
    """CFL number C = |c| dt / dx. Explicit advection/wave needs C <= 1."""
    return abs(c) * dt / dx


def heat_stable(alpha: float, dt: float, dx: float) -> bool:
    return heat_number(alpha, dt, dx) <= 0.5 + 1e-12


def cfl_ok(c: float, dt: float, dx: float) -> bool:
    return courant_number(c, dt, dx) <= 1.0 + 1e-12
