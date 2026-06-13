"""Circuit models as transfer functions H(s) = V_out(s) / V_in(s).

Writing a circuit's impedances in the s-domain (R, sL, 1/(sC)) turns the
voltage-divider rule into algebra: the transfer function drops out directly.
These are the canonical first- and second-order examples used in the control /
circuits chapter; each returns a ``scipy.signal`` transfer function built by
``systems.tf`` so the same response/stability helpers apply.
"""

from __future__ import annotations

import numpy as np

from .systems import TransferFunction, tf


# --------------------------------------------------------------------------- #
# First-order RC.
# --------------------------------------------------------------------------- #
def rc_lowpass(R: float, C: float) -> TransferFunction:
    """RC low-pass, output across C: H(s) = 1 / (RC s + 1). Time constant tau = RC."""
    return tf([1.0], [R * C, 1.0])


def rc_highpass(R: float, C: float) -> TransferFunction:
    """RC high-pass, output across R: H(s) = RC s / (RC s + 1)."""
    return tf([R * C, 0.0], [R * C, 1.0])


# --------------------------------------------------------------------------- #
# Second-order series RLC.
# --------------------------------------------------------------------------- #
def rlc_series_vc(R: float, L: float, C: float) -> TransferFunction:
    """Series RLC, output across C (low-pass): H(s) = 1 / (LC s^2 + RC s + 1)."""
    return tf([1.0], [L * C, R * C, 1.0])


def rlc_series_vr(R: float, L: float, C: float) -> TransferFunction:
    """Series RLC, output across R (band-pass): H(s) = RC s / (LC s^2 + RC s + 1)."""
    return tf([R * C, 0.0], [L * C, R * C, 1.0])


def rlc_params(R: float, L: float, C: float) -> dict:
    """Natural frequency, damping ratio and regime of a series RLC circuit.

    wn = 1/sqrt(LC),  zeta = (R/2) sqrt(C/L). The regime follows from zeta:
    underdamped (<1), critically damped (=1), overdamped (>1).
    """
    wn = 1.0 / np.sqrt(L * C)
    zeta = (R / 2.0) * np.sqrt(C / L)
    if zeta < 1.0:
        regime = "underdamped"
    elif np.isclose(zeta, 1.0):
        regime = "critically damped"
    else:
        regime = "overdamped"
    return {"wn": float(wn), "zeta": float(zeta), "regime": regime}
