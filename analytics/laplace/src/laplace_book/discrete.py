"""Discrete-time bridge: z-transform basics and the s-plane -> z-plane map.

Sampling a continuous signal every T seconds turns the Laplace world into the
z world via z = e^{sT}. That map sends the imaginary axis to the unit circle and
the left half-plane to the inside of the unit circle -- so continuous stability
(poles in the LHP) becomes discrete stability (poles inside |z| < 1). These
helpers keep chapter 11 (the discrete bridge) short and testable.
"""

from __future__ import annotations

import numpy as np
from scipy import signal


def geometric_sequence(a, n: int):
    """a^k for k = 0..n-1 -- the discrete analogue of the decaying exponential."""
    k = np.arange(n)
    return np.asarray(a, dtype=float) ** k


def numeric_ztransform(seq, z):
    """One-sided z-transform X(z) = sum_k seq[k] z^{-k} (scalar or array z)."""
    seq = np.asarray(seq, dtype=float)
    k = np.arange(seq.size, dtype=float)
    z = np.asarray(z, dtype=complex)
    scalar = z.ndim == 0
    out = np.array([np.sum(seq * zz ** (-k)) for zz in np.atleast_1d(z).ravel()])
    return complex(out[0]) if scalar else out.reshape(z.shape)


def s_to_z(s, dt: float):
    """Map s-plane point(s) to the z-plane: z = e^{s*dt}."""
    return np.exp(np.asarray(s, dtype=complex) * dt)


def discrete_tf(num, den, dt: float):
    """A discrete transfer function H(z) sampled with step dt."""
    return signal.TransferFunction(
        np.atleast_1d(num).astype(float), np.atleast_1d(den).astype(float), dt=dt
    )


def discrete_poles(sys) -> np.ndarray:
    """Poles of a discrete H(z) (denominator roots, in the z-plane)."""
    return np.asarray(sys.poles)


def is_stable_discrete(sys_or_poles, tol: float = 1e-9) -> bool:
    """Discrete stability: every pole strictly inside the unit circle |z| < 1."""
    poles = getattr(sys_or_poles, "poles", sys_or_poles)
    return bool(np.all(np.abs(np.asarray(poles)) < 1.0 - tol))


def discrete_step_response(sys, n: int = 30):
    """Unit-step response of a discrete system over n samples; returns (k, y)."""
    k, y = signal.dstep(sys, n=n)
    return np.asarray(k), np.squeeze(y[0])
