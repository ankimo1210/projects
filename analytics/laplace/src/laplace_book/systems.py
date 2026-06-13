"""LTI systems and transfer functions -- the s-domain view of "input -> output".

A linear time-invariant system is summarised by its transfer function
H(s) = Y(s)/X(s). Everything the book needs about such systems -- building them,
reading off poles/zeros, judging stability, and computing step / impulse /
forced responses -- lives here so the notebooks stay short and the behaviour is
testable.

Thin wrappers over ``scipy.signal`` keep the numerics trustworthy; the helpers
add the *vocabulary* of the book (time constant, natural frequency, damping
ratio, stability class).
"""

from __future__ import annotations

import numpy as np
from scipy import signal

TransferFunction = signal.TransferFunction


# --------------------------------------------------------------------------- #
# Builders.
# --------------------------------------------------------------------------- #
def tf(num, den) -> TransferFunction:
    """A transfer function H(s) = num(s)/den(s) from coefficient lists."""
    return signal.TransferFunction(np.atleast_1d(num).astype(float), np.atleast_1d(den).astype(float))


def first_order(tau: float, gain: float = 1.0) -> TransferFunction:
    """H(s) = gain / (tau s + 1). One real pole at s = -1/tau (time constant tau)."""
    return tf([gain], [tau, 1.0])


def second_order(wn: float, zeta: float, gain: float = 1.0) -> TransferFunction:
    """H(s) = gain * wn^2 / (s^2 + 2 zeta wn s + wn^2).

    ``wn`` is the undamped natural frequency, ``zeta`` the damping ratio:
    zeta<1 underdamped (ringing), zeta=1 critical, zeta>1 overdamped.
    """
    return tf([gain * wn**2], [1.0, 2.0 * zeta * wn, wn**2])


# --------------------------------------------------------------------------- #
# Poles, zeros, and what they mean.
# --------------------------------------------------------------------------- #
def poles(sys) -> np.ndarray:
    """Poles of H(s): roots of the denominator (they set the response shape)."""
    return np.asarray(sys.poles)


def zeros(sys) -> np.ndarray:
    """Zeros of H(s): roots of the numerator."""
    return np.asarray(sys.zeros)


def evaluate(sys, s_value):
    """Evaluate H(s) at complex point(s) s (frequency response when s = i*omega)."""
    s_value = np.asarray(s_value, dtype=complex)
    return np.polyval(sys.num, s_value) / np.polyval(sys.den, s_value)


def dc_gain(sys) -> float:
    """Steady-state gain H(0) = lim_{s->0} H(s) (final value for a unit step)."""
    return float(np.polyval(sys.num, 0.0) / np.polyval(sys.den, 0.0))


def time_constant(sys) -> float:
    """Dominant time constant tau = -1/Re(slowest pole) (largest tau)."""
    p = poles(sys)
    re = p.real
    re = re[re < 0]
    if re.size == 0:
        raise ValueError("system has no left-half-plane pole; time constant undefined")
    return float(1.0 / np.min(np.abs(re)))


def second_order_params(sys):
    """Return (wn, zeta) for a system whose denominator is quadratic in s."""
    den = np.asarray(sys.den, dtype=float)
    if den.size != 3:
        raise ValueError("second_order_params expects a 2nd-order denominator")
    a2, a1, a0 = den / den[0]
    wn = float(np.sqrt(a0))
    zeta = float(a1 / (2.0 * wn)) if wn > 0 else float("inf")
    return wn, zeta


# --------------------------------------------------------------------------- #
# Stability -- decided by where the poles sit in the s-plane.
# --------------------------------------------------------------------------- #
def is_stable(sys, tol: float = 1e-9) -> bool:
    """True iff every pole is strictly in the left half-plane (Re < 0)."""
    return bool(np.all(poles(sys).real < -tol))


def classify_stability(sys, tol: float = 1e-9) -> str:
    """'stable' (all LHP), 'unstable' (any RHP), or 'marginal' (on i-axis)."""
    re = poles(sys).real
    if np.any(re > tol):
        return "unstable"
    if np.any(np.abs(re) <= tol):
        return "marginal"
    return "stable"


# --------------------------------------------------------------------------- #
# Time-domain responses (wrap scipy.signal so notebooks pass a t-grid).
# --------------------------------------------------------------------------- #
def step_response(sys, t):
    """Unit-step response y(t); returns y aligned with the given t-grid."""
    _, y = signal.step(sys, T=np.asarray(t, dtype=float))
    return y


def impulse_response(sys, t):
    """Impulse response h(t) -- the system's fingerprint."""
    _, y = signal.impulse(sys, T=np.asarray(t, dtype=float))
    return y


def forced_response(sys, u, t):
    """Output y(t) for an arbitrary input u(t) sampled on t (uses lsim)."""
    tout, y, _ = signal.lsim(sys, U=np.asarray(u, dtype=float), T=np.asarray(t, dtype=float))
    return y


def bode(sys, w=None):
    """Bode data (w, magnitude_dB, phase_deg) -- the frequency-response view."""
    return signal.bode(sys, w=w)


# --------------------------------------------------------------------------- #
# Combining systems.
# --------------------------------------------------------------------------- #
def series(g1, g2) -> TransferFunction:
    """Cascade: H = G1 * G2 (output of G1 feeds G2)."""
    num = np.polymul(np.atleast_1d(g1.num), np.atleast_1d(g2.num))
    den = np.polymul(np.atleast_1d(g1.den), np.atleast_1d(g2.den))
    return TransferFunction(num, den)


def feedback(g, k=None) -> TransferFunction:
    """Closed loop with negative feedback: H = G / (1 + G K).

    ``k`` is the feedback transfer function (default: unity feedback, K = 1).
    Computed as G/(1+GK) = Gnum Kden / (Gden Kden + Gnum Knum).
    """
    gnum, gden = np.atleast_1d(g.num), np.atleast_1d(g.den)
    if k is None:
        knum, kden = np.array([1.0]), np.array([1.0])
    else:
        knum, kden = np.atleast_1d(k.num), np.atleast_1d(k.den)
    num = np.polymul(gnum, kden)
    den = np.polyadd(np.polymul(gden, kden), np.polymul(gnum, knum))
    return TransferFunction(num, den)


# --------------------------------------------------------------------------- #
# Convolution -- the time-domain twin of multiplying transfers.
# --------------------------------------------------------------------------- #
def convolve(f, g, dt: float):
    """Causal convolution (f * g)(t) on a uniform grid of spacing dt.

    Returns an array the same length as ``f`` so it can be plotted against the
    same t-grid. This is the time-domain side of the convolution theorem
    L{f * g} = F(s) G(s).
    """
    f = np.asarray(f, dtype=float)
    g = np.asarray(g, dtype=float)
    full = np.convolve(f, g) * dt
    return full[: f.size]
