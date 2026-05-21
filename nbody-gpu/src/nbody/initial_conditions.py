"""Initial condition generators (host-side, then transferred to device)."""
from __future__ import annotations

import numpy as np


def plummer_sphere(
    n: int,
    total_mass: float = 1.0,
    scale_radius: float = 1.0,
    G: float = 1.0,
    seed: int | None = 0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate a Plummer sphere in virial equilibrium.

    Position sampling uses inverse-CDF on the enclosed-mass profile
    M(r)/M = r^3 / (r^2 + a^2)^{3/2}.
    Velocity sampling uses Aarseth-Henon-Wielen (1974) rejection on
    f(q) ∝ q^2 (1 - q^2)^{7/2}, q = v/v_escape(r).

    Returns
    -------
    pos : (N, 3) float32
    vel : (N, 3) float32
    mass: (N,)   float32  — equal mass m = total_mass / N
    """
    rng = np.random.default_rng(seed)
    M, a = float(total_mass), float(scale_radius)

    # --- positions: inverse-CDF on uniform X in (0, 1) ---
    X = rng.uniform(1e-12, 1.0 - 1e-12, size=n)
    r = a / np.sqrt(X ** (-2.0 / 3.0) - 1.0)
    # isotropic direction
    cos_t = rng.uniform(-1.0, 1.0, size=n)
    sin_t = np.sqrt(1.0 - cos_t * cos_t)
    phi = rng.uniform(0.0, 2.0 * np.pi, size=n)
    pos = np.empty((n, 3), dtype=np.float64)
    pos[:, 0] = r * sin_t * np.cos(phi)
    pos[:, 1] = r * sin_t * np.sin(phi)
    pos[:, 2] = r * cos_t

    # --- velocities: rejection sampling on f(q) ∝ q^2 (1-q^2)^{7/2} ---
    # max of f on [0,1] occurs at q^2 = 2/9 -> q = sqrt(2/9).
    # f_max value at that q ≈ 0.1
    q = np.empty(n)
    filled = 0
    while filled < n:
        m = n - filled
        q_try = rng.uniform(0.0, 1.0, size=m)
        u = rng.uniform(0.0, 0.1, size=m)
        f = q_try * q_try * (1.0 - q_try * q_try) ** 3.5
        accept = u < f
        k = int(accept.sum())
        q[filled:filled + k] = q_try[accept]
        filled += k

    v_escape = np.sqrt(2.0 * G * M) * (r * r + a * a) ** (-0.25)
    v = q * v_escape

    cos_tv = rng.uniform(-1.0, 1.0, size=n)
    sin_tv = np.sqrt(1.0 - cos_tv * cos_tv)
    phi_v = rng.uniform(0.0, 2.0 * np.pi, size=n)
    vel = np.empty((n, 3), dtype=np.float64)
    vel[:, 0] = v * sin_tv * np.cos(phi_v)
    vel[:, 1] = v * sin_tv * np.sin(phi_v)
    vel[:, 2] = v * cos_tv

    # Remove COM drift (numerical leftover).
    masses = np.full(n, M / n, dtype=np.float64)
    pos -= (masses[:, None] * pos).sum(0) / M
    vel -= (masses[:, None] * vel).sum(0) / M

    return pos.astype(np.float32), vel.astype(np.float32), masses.astype(np.float32)


def two_body_circular(
    m1: float = 1.0,
    m2: float = 1.0,
    separation: float = 1.0,
    G: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Two equal masses on a circular orbit about their COM.

    Useful as an analytic reference: period T = 2π sqrt(a^3 / (G (m1+m2)))
    where a is the separation.
    """
    M = m1 + m2
    # COM at origin
    r1 = m2 / M * separation
    r2 = m1 / M * separation
    # circular speed
    v_rel = np.sqrt(G * M / separation)
    v1 = m2 / M * v_rel
    v2 = m1 / M * v_rel
    pos = np.array([[-r1, 0, 0], [r2, 0, 0]], dtype=np.float32)
    vel = np.array([[0, -v1, 0], [0, v2, 0]], dtype=np.float32)
    mass = np.array([m1, m2], dtype=np.float32)
    return pos, vel, mass
