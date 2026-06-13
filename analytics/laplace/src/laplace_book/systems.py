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
    """A transfer function H(s) = num(s)/den(s) from coefficient lists.

    Note: scipy normalizes the stored num/den so the denominator is monic; the
    ratio H(s) and its poles/zeros are unchanged (so reading raw ``sys.den`` back
    may not show the coefficients you passed in).
    """
    return signal.TransferFunction(
        np.atleast_1d(num).astype(float), np.atleast_1d(den).astype(float)
    )


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
    _, a1, a0 = den / den[0]
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


def routh_hurwitz(den, tol: float = 1e-12):
    """Routh-Hurwitz stability test from denominator coefficients (highest power first).

    Returns ``(stable, n_rhp, table)``: ``stable`` is True iff the first column has
    no sign change; ``n_rhp`` is the number of right-half-plane roots (= number of
    first-column sign changes). A zero pivot is replaced by a small epsilon (the
    standard trick); a full zero row (imaginary-axis roots) is a known edge case
    this simple version does not special-case.
    """
    a = np.trim_zeros(np.atleast_1d(np.asarray(den, dtype=float)), "f")
    n = a.size
    if n == 0:
        raise ValueError("empty denominator")
    ncols = (n + 1) // 2
    table = np.zeros((n, ncols))
    table[0, : a[0::2].size] = a[0::2]
    if n > 1:
        table[1, : a[1::2].size] = a[1::2]
    for i in range(2, n):
        if abs(table[i - 1, 0]) < tol:
            table[i - 1, 0] = tol  # epsilon trick for a zero pivot
        for j in range(ncols - 1):
            piv = table[i - 1, 0]
            table[i, j] = (piv * table[i - 2, j + 1] - table[i - 2, 0] * table[i - 1, j + 1]) / piv
    first = table[:, 0].copy()
    first[np.abs(first) < tol] = tol
    signs = np.sign(first)
    n_rhp = int(np.sum(signs[1:] != signs[:-1]))
    return (n_rhp == 0), n_rhp, table


def partial_fraction_numeric(num, den):
    """Numeric partial-fraction expansion via ``scipy.signal.residue``.

    Returns ``(residues, poles, direct)`` with
    num/den = sum_i residues[i]/(s - poles[i]) + direct(s). Complements the
    symbolic ``transforms.partial_fractions`` and handles repeated poles.
    """
    r, p, k = signal.residue(np.atleast_1d(num).astype(float), np.atleast_1d(den).astype(float))
    return r, p, k


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
    _, y, _ = signal.lsim(sys, U=np.asarray(u, dtype=float), T=np.asarray(t, dtype=float))
    return y


def bode(sys, w=None):
    """Bode data (w, magnitude_dB, phase_deg) -- the frequency-response view."""
    return signal.bode(sys, w=w)


def gain_phase_margin(sys, w=None):
    """Gain and phase margins of open-loop ``sys`` under negative unity feedback.

    Returns ``dict(gain_margin, phase_margin_deg, wgc, wpc)``. ``gain_margin`` is a
    linear factor (inf if the phase never reaches -180 deg); ``phase_margin_deg`` is
    in degrees (inf if the gain never reaches 1). The first crossing of each kind
    is linearly interpolated on the frequency grid.
    """
    if w is None:
        w = np.logspace(-2, 3, 4000)
    w = np.asarray(w, dtype=float)
    H = evaluate(sys, 1j * w)
    mag = np.abs(H)
    phase = np.unwrap(np.angle(H)) * 180.0 / np.pi

    pm, wgc = float("inf"), float("nan")
    gc = np.where(np.diff(np.sign(mag - 1.0)))[0]
    if gc.size:
        i = gc[0]
        m1, m2 = mag[i] - 1.0, mag[i + 1] - 1.0
        wgc = float(w[i] + (w[i + 1] - w[i]) * (-m1) / (m2 - m1))
        pm = float(180.0 + np.interp(wgc, w, phase))

    gm, wpc = float("inf"), float("nan")
    pc = np.where(np.diff(np.sign(phase + 180.0)))[0]
    if pc.size:
        i = pc[0]
        p1, p2 = phase[i] + 180.0, phase[i + 1] + 180.0
        wpc = float(w[i] + (w[i + 1] - w[i]) * (-p1) / (p2 - p1))
        m = float(np.interp(wpc, w, mag))
        gm = 1.0 / m if m > 0 else float("inf")

    return {"gain_margin": gm, "phase_margin_deg": pm, "wgc": wgc, "wpc": wpc}


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


def pid(kp: float = 0.0, ki: float = 0.0, kd: float = 0.0) -> TransferFunction:
    """PID controller K(s) = kp + ki/s + kd s.

    Written as (kd s^2 + kp s + ki)/s when an integral term is present, and as
    kd s + kp otherwise -- so pure P / PD have a proper, pole-free form (no
    spurious s/s that would make K(0) a 0/0). An ideal derivative (kd > 0) is
    improper, so scipy will warn; a realizable controller filters it as
    kd s / (tau s + 1).
    """
    if ki != 0.0:
        num, den = [kd, kp, ki], [1.0, 0.0]
    else:
        num, den = [kd, kp], [1.0]
    while len(num) > 1 and num[0] == 0:  # drop leading zeros (e.g. pure P -> just kp)
        num = num[1:]
    return tf(num, den)


def root_locus(g, k_values):
    """Closed-loop pole locations as the loop gain k sweeps over ``k_values``.

    For unity feedback around k*G, the closed-loop poles are the roots of the
    characteristic polynomial den_G(s) + k * num_G(s). At k=0 they start at the
    open-loop poles; as k grows they migrate toward the open-loop zeros (and to
    infinity). Returns (k_values, locus) where locus[i] is the pole array for
    k_values[i].
    """
    num = np.atleast_1d(g.num).astype(float)
    den = np.atleast_1d(g.den).astype(float)
    k_values = np.asarray(k_values, dtype=float)
    locus = [np.roots(np.polyadd(den, k * num)) for k in k_values]
    return k_values, locus


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
