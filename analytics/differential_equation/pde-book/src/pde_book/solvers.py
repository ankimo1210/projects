"""Finite-difference solvers for the model PDEs of the book.

Each time-stepping solver returns the full history ``U`` of shape
``(steps + 1, nx)`` so notebooks can animate or draw space-time heatmaps. The
elliptic solver (Laplace/Poisson) returns the 2-D field directly.

Conventions:
- 1-D solvers take an initial array ``u0`` already sampled on the grid.
- Dirichlet boundaries are held at their initial values unless noted.
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


# --------------------------------------------------------------------------- #
# Parabolic: heat / diffusion equation u_t = alpha u_xx.
# --------------------------------------------------------------------------- #
def solve_heat_explicit(u0, alpha, dx, dt, steps):
    """Explicit FTCS for the 1-D heat equation with Dirichlet ends.

    Stable only when r = alpha dt / dx^2 <= 1/2 — used to *demonstrate* the
    stability limit, so it is intentionally not safeguarded.
    """
    u = np.asarray(u0, dtype=float).copy()
    r = alpha * dt / dx**2
    U = np.empty((steps + 1, u.size))
    U[0] = u
    for k in range(steps):
        lap = np.zeros_like(u)
        lap[1:-1] = u[2:] - 2 * u[1:-1] + u[:-2]
        u = u + r * lap
        u[0] = U[0, 0]
        u[-1] = U[0, -1]
        U[k + 1] = u
    return U


def solve_heat_implicit(u0, alpha, dx, dt, steps):
    """Backward-Euler (implicit) heat solver — unconditionally stable.

    Solves (I - r L) u^{n+1} = u^n on interior nodes each step, with the
    end values held fixed (homogeneous Dirichlet on the increment).
    """
    u = np.asarray(u0, dtype=float).copy()
    n = u.size
    r = alpha * dt / dx**2
    m = n - 2
    main = (1 + 2 * r) * np.ones(m)
    off = -r * np.ones(m - 1)
    A = sp.diags([off, main, off], offsets=[-1, 0, 1], format="csc")
    lu = spla.splu(A)
    U = np.empty((steps + 1, n))
    U[0] = u
    for k in range(steps):
        rhs = u[1:-1].copy()
        rhs[0] += r * u[0]
        rhs[-1] += r * u[-1]
        u[1:-1] = lu.solve(rhs)
        U[k + 1] = u
    return U


def heat_mode_solution(x, t, alpha, L, mode=1, amp=1.0):
    """Exact Dirichlet heat solution for a single sine mode initial condition.

    u(x,0) = amp sin(mode pi x / L)  =>  u(x,t) = amp e^{-alpha (mode pi/L)^2 t} sin(...).
    """
    x = np.asarray(x, dtype=float)
    k = mode * np.pi / L
    return amp * np.exp(-alpha * k**2 * t) * np.sin(k * x)


# --------------------------------------------------------------------------- #
# Hyperbolic: transport (advection) u_t + c u_x = 0.
# --------------------------------------------------------------------------- #
def solve_transport(u0, c, dx, dt, steps, scheme="upwind"):
    """1-D advection with periodic BCs.

    scheme="upwind" (stable for CFL<=1) or "ftcs" (unconditionally unstable —
    shown to illustrate how a "reasonable looking" scheme blows up).
    """
    u = np.asarray(u0, dtype=float).copy()
    C = c * dt / dx
    U = np.empty((steps + 1, u.size))
    U[0] = u
    for k in range(steps):
        if scheme == "upwind":
            if c >= 0:
                u = u - C * (u - np.roll(u, 1))
            else:
                u = u - C * (np.roll(u, -1) - u)
        elif scheme == "ftcs":
            u = u - 0.5 * C * (np.roll(u, -1) - np.roll(u, 1))
        else:  # pragma: no cover
            raise ValueError("scheme must be 'upwind' or 'ftcs'")
        U[k + 1] = u
    return U


# --------------------------------------------------------------------------- #
# Hyperbolic: wave equation u_tt = c^2 u_xx.
# --------------------------------------------------------------------------- #
def solve_wave(u0, v0, c, dx, dt, steps):
    """1-D wave equation, fixed (Dirichlet) ends, explicit leapfrog.

    u0, v0 are the initial displacement and velocity arrays. Stable for
    CFL number C = c dt / dx <= 1.
    """
    u_prev = np.asarray(u0, dtype=float).copy()
    C2 = (c * dt / dx) ** 2
    U = np.empty((steps + 1, u_prev.size))
    U[0] = u_prev
    # First step uses the initial velocity (Taylor start).
    lap = np.zeros_like(u_prev)
    lap[1:-1] = u_prev[2:] - 2 * u_prev[1:-1] + u_prev[:-2]
    u_curr = u_prev + dt * np.asarray(v0, float) + 0.5 * C2 * lap
    u_curr[0] = u_curr[-1] = 0.0
    U[1] = u_curr
    for k in range(1, steps):
        lap = np.zeros_like(u_curr)
        lap[1:-1] = u_curr[2:] - 2 * u_curr[1:-1] + u_curr[:-2]
        u_next = 2 * u_curr - u_prev + C2 * lap
        u_next[0] = u_next[-1] = 0.0
        U[k + 1] = u_next
        u_prev, u_curr = u_curr, u_next
    return U


def wave_mode_solution(x, t, c, L, mode=1, amp=1.0):
    """Exact standing-wave solution: u = amp sin(mode pi x/L) cos(mode pi c t/L)."""
    x = np.asarray(x, dtype=float)
    k = mode * np.pi / L
    return amp * np.sin(k * x) * np.cos(k * c * t)


# --------------------------------------------------------------------------- #
# Elliptic: Laplace / Poisson  laplacian(u) = f  with Dirichlet BCs.
# --------------------------------------------------------------------------- #
def solve_poisson_2d(rhs, grid, boundary):
    """Solve laplacian(u) = rhs on a 2-D grid with Dirichlet data ``boundary``.

    ``rhs`` and ``boundary`` are arrays of shape (ny, nx) (rhs used on interior,
    boundary used on the edges). Laplace's equation is the case rhs = 0.
    Returns u of shape (ny, nx). Uses a sparse 5-point stencil + direct solve.
    """
    nx, ny = grid.nx, grid.ny
    dx, dy = grid.dx, grid.dy
    rhs = np.asarray(rhs, dtype=float)
    boundary = np.asarray(boundary, dtype=float)

    u = boundary.copy()
    ix = np.arange(1, nx - 1)
    iy = np.arange(1, ny - 1)
    mx, my = ix.size, iy.size
    m = mx * my

    def idx(i, j):  # interior (i in x, j in y) -> flat index
        return j * mx + i

    A = sp.lil_matrix((m, m))
    b = np.zeros(m)
    cx = 1.0 / dx**2
    cy = 1.0 / dy**2
    for jj in range(my):
        for ii in range(mx):
            row = idx(ii, jj)
            i = ii + 1
            j = jj + 1
            A[row, row] = -2 * cx - 2 * cy
            b[row] = rhs[j, i]
            # x neighbours
            if ii > 0:
                A[row, idx(ii - 1, jj)] = cx
            else:
                b[row] -= cx * u[j, i - 1]
            if ii < mx - 1:
                A[row, idx(ii + 1, jj)] = cx
            else:
                b[row] -= cx * u[j, i + 1]
            # y neighbours
            if jj > 0:
                A[row, idx(ii, jj - 1)] = cy
            else:
                b[row] -= cy * u[j - 1, i]
            if jj < my - 1:
                A[row, idx(ii, jj + 1)] = cy
            else:
                b[row] -= cy * u[j + 1, i]
    sol = spla.spsolve(A.tocsr(), b)
    u[1:-1, 1:-1] = sol.reshape(my, mx)
    return u


# --------------------------------------------------------------------------- #
# Fourier: building blocks for ch. 03 / 04.
# --------------------------------------------------------------------------- #
def square_wave_partial_sum(x, n_terms, L=np.pi):
    """Partial sum of the Fourier sine series of a unit square wave on [0, L].

    Square wave (odd, period 2L): sum over odd k of (4/(pi k)) sin(k pi x / L).
    """
    x = np.asarray(x, dtype=float)
    s = np.zeros_like(x)
    for k in range(1, 2 * n_terms, 2):  # 1, 3, 5, ...
        s += (4.0 / (np.pi * k)) * np.sin(k * np.pi * x / L)
    return s
