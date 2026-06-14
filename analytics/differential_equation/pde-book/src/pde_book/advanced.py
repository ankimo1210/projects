"""Advanced PDE topics backing notebook 09.

Spectral (FFT) methods, the nonlinear dispersive KdV equation (solitons),
2-D reaction-diffusion (Turing/Gray-Scott patterns), and the 2-D wave equation.
Each has a test pinned to an analytic answer or a qualitative invariant.
"""

from __future__ import annotations

import numpy as np


# --------------------------------------------------------------------------- #
# Spectral method: heat equation on a periodic domain (exact in space).
# --------------------------------------------------------------------------- #
def solve_heat_spectral(u0, alpha, length, dt, steps):
    """Periodic heat equation via FFT. Each mode decays exactly as e^{-alpha k^2 dt}.

    ``u0`` is sampled on x = linspace(0, length, n, endpoint=False). Spectral
    differentiation is exact for band-limited data, so this is far more accurate
    per grid point than finite differences. Returns history (steps+1, n).
    """
    u = np.asarray(u0, dtype=float)
    n = u.size
    k = 2 * np.pi * np.fft.fftfreq(n, d=length / n)  # angular wavenumbers
    decay = np.exp(-alpha * k**2 * dt)
    uhat = np.fft.fft(u)
    U = np.empty((steps + 1, n))
    U[0] = u
    for s in range(steps):
        uhat = uhat * decay
        U[s + 1] = np.real(np.fft.ifft(uhat))
    return U


# --------------------------------------------------------------------------- #
# Nonlinear dispersive: KdV  u_t + u u_x + u_xxx = 0  (solitons).
# --------------------------------------------------------------------------- #
def kdv_soliton(x, t, amp, x0, length):
    """Exact single-soliton of u_t + u u_x + u_xxx = 0 on a periodic domain.

    u = 3 amp^2 sech^2( amp/2 (x - x0 - amp^2 t) ), travelling right at speed amp^2.
    Evaluated with periodic wrapping so it can be compared to the solver.
    """
    x = np.asarray(x, dtype=float)
    xi = (x - x0 - amp**2 * t + length / 2) % length - length / 2
    return 3 * amp**2 / np.cosh(amp / 2 * xi) ** 2


def solve_kdv(u0, dx, dt, steps):
    """KdV u_t + u u_x + u_xxx = 0 (periodic) via the integrating-factor RK4 scheme.

    The stiff linear term u_xxx is handled exactly in Fourier space (integrating
    factor), and the nonlinear term pseudo-spectrally with RK4 (Trefethen, p27).
    Conserves mass int u and momentum int u^2. Returns history (steps+1, n).
    """
    u = np.asarray(u0, dtype=float)
    n = u.size
    k = 2 * np.pi * np.fft.fftfreq(n, d=dx)
    ik3 = 1j * k**3
    g = -0.5j * dt * k
    E = np.exp(dt * ik3 / 2)
    E2 = E**2
    v = np.fft.fft(u)
    U = np.empty((steps + 1, n))
    U[0] = u
    for s in range(steps):
        a = g * np.fft.fft(np.real(np.fft.ifft(v)) ** 2)
        b = g * np.fft.fft(np.real(np.fft.ifft(E * (v + a / 2))) ** 2)
        c = g * np.fft.fft(np.real(np.fft.ifft(E * v + b / 2)) ** 2)
        d = g * np.fft.fft(np.real(np.fft.ifft(E2 * v + E * c)) ** 2)
        v = E2 * v + (E2 * a + 2 * E * (b + c) + d) / 6
        U[s + 1] = np.real(np.fft.ifft(v))
    return U


# --------------------------------------------------------------------------- #
# Reaction-diffusion: Gray-Scott (Turing patterns) on a periodic 2-D grid.
# --------------------------------------------------------------------------- #
def _laplacian2d(a, dx):
    return (
        np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1) - 4 * a
    ) / dx**2


def solve_gray_scott(u, v, Du, Dv, feed, kill, dx, dt, steps):
    """Gray-Scott reaction-diffusion (the classic Turing-pattern model).

    u_t = Du lap u - u v^2 + feed (1 - u);  v_t = Dv lap v + u v^2 - (feed+kill) v.
    Periodic boundaries, explicit Euler. Returns the final (u, v) fields. From a
    nearly-uniform state with a small seed, self-organized spots/stripes emerge.
    """
    u = np.asarray(u, dtype=float).copy()
    v = np.asarray(v, dtype=float).copy()
    for _ in range(steps):
        uvv = u * v * v
        u += dt * (Du * _laplacian2d(u, dx) - uvv + feed * (1 - u))
        v += dt * (Dv * _laplacian2d(v, dx) + uvv - (feed + kill) * v)
    return u, v


def gray_scott_seed(n=64, seed=0):
    """Standard Gray-Scott initial state: u=1, v=0, with a small noisy central seed."""
    rng = np.random.default_rng(seed)
    u = np.ones((n, n))
    v = np.zeros((n, n))
    c = slice(n // 2 - n // 16, n // 2 + n // 16)
    u[c, c] = 0.5
    v[c, c] = 0.25
    u += 0.02 * rng.standard_normal((n, n))
    v += 0.02 * rng.standard_normal((n, n))
    return np.clip(u, 0, 1), np.clip(v, 0, 1)


# --------------------------------------------------------------------------- #
# 2-D wave equation u_tt = c^2 (u_xx + u_yy), fixed edges.
# --------------------------------------------------------------------------- #
def solve_wave_2d(u0, v0, c, dx, dt, steps):
    """2-D wave equation on a square with fixed (Dirichlet) edges, leapfrog.

    Returns history of shape (steps+1, ny, nx). Stable for c dt / dx <= 1/sqrt(2).
    """
    u_prev = np.asarray(u0, dtype=float).copy()
    C2 = (c * dt / dx) ** 2
    ny, nx = u_prev.shape
    U = np.empty((steps + 1, ny, nx))
    U[0] = u_prev

    def lap(a):
        out = np.zeros_like(a)
        out[1:-1, 1:-1] = (
            a[2:, 1:-1] + a[:-2, 1:-1] + a[1:-1, 2:] + a[1:-1, :-2] - 4 * a[1:-1, 1:-1]
        )
        return out

    u_curr = u_prev + dt * np.asarray(v0, float) + 0.5 * C2 * lap(u_prev)
    u_curr[0, :] = u_curr[-1, :] = u_curr[:, 0] = u_curr[:, -1] = 0.0
    U[1] = u_curr
    for s in range(1, steps):
        u_next = 2 * u_curr - u_prev + C2 * lap(u_curr)
        u_next[0, :] = u_next[-1, :] = u_next[:, 0] = u_next[:, -1] = 0.0
        U[s + 1] = u_next
        u_prev, u_curr = u_curr, u_next
    return U


def wave_mode_2d(x, y, t, c, mode=(1, 1), length=1.0):
    """Exact 2-D standing wave sin(p pi x/L) sin(q pi y/L) cos(sqrt(p^2+q^2) pi c t / L)."""
    X, Y = np.meshgrid(x, y)
    p, q = mode
    omega = np.sqrt(p**2 + q**2) * np.pi * c / length
    return np.sin(p * np.pi * X / length) * np.sin(q * np.pi * Y / length) * np.cos(omega * t)
