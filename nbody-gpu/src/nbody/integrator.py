"""Symplectic leapfrog (kick-drift-kick) integrator."""
from __future__ import annotations

import cupy as cp

from .forces import compute_acceleration


def leapfrog_step(
    pos: cp.ndarray,
    vel: cp.ndarray,
    mass: cp.ndarray,
    acc: cp.ndarray,
    dt: float,
    eps: float = 1e-2,
    G: float = 1.0,
) -> None:
    """Advance (pos, vel) by one timestep dt in place.

    Uses kick-drift-kick form which is symplectic to 2nd order:
        v_{n+1/2} = v_n + (dt/2) a_n
        x_{n+1}   = x_n + dt v_{n+1/2}
        a_{n+1}   = a(x_{n+1})
        v_{n+1}   = v_{n+1/2} + (dt/2) a_{n+1}

    `acc` is read on entry (a_n) and overwritten with a_{n+1} on exit, so
    callers can chain steps without recomputing acceleration.
    """
    half_dt = cp.float32(0.5 * dt)
    vel += half_dt * acc
    pos += cp.float32(dt) * vel
    compute_acceleration(pos, mass, eps=eps, G=G, out=acc)
    vel += half_dt * acc
