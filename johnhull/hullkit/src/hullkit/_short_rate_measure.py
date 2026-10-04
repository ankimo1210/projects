"""Private Hull §31.3 affine short-rate P/Q conversion and bond premium."""

import numpy as np


def short_rate_measure_change(
    which, mean_reversion, constant_drift, volatility, risk_price, direction="q_to_p"
):
    """Convert drift c-a*r in Hull's Pdrift=Qdrift+lambda*s convention.

    Vasicek: lambda=risk_price, cP=cQ+lambda*sigma, a unchanged.
    CIR: lambda=k*sqrt(r), aP=aQ-k*sigma, cP=cQ (a*b invariant).
    Return c explicitly; a=0 has no finite long-run level and b=None. Signed
    a can represent a nonstationary process; conversion is not a calibration
    claim that both measures are mean reverting. CIR immigration c must be
    nonnegative. No empirical universal sign is imposed on risk_price.
    """
    if which not in ("vasicek", "cir") or direction not in ("q_to_p", "p_to_q"):
        raise ValueError("valid model and q_to_p/p_to_q direction required")
    if volatility < 0 or (which == "cir" and constant_drift < 0):
        raise ValueError("nonnegative volatility and CIR immigration required")
    sign = 1 if direction == "q_to_p" else -1
    a = mean_reversion - (sign * risk_price * volatility if which == "cir" else 0)
    c = constant_drift + (sign * risk_price * volatility if which == "vasicek" else 0)
    return {"a": a, "constant_drift": c, "b": c / a if a != 0 else None, "sigma": volatility}


def physical_bond_return(which, rate, volatility, short_rate_duration, risk_price):
    """Expected instantaneous P return r + lambda*(signed bond diffusion).

    The Q return is r. Signed relative bond diffusion is -sigma*B for Vas
    and -sigma*sqrt(r)*B for CIR. Together with CIR lambda=k*sqrt(r), this
    yields r-k*sigma*B*r, not r-k*sigma*B*sqrt(r).
    """
    if which not in ("vasicek", "cir") or volatility < 0 or short_rate_duration < 0:
        raise ValueError("valid model and nonnegative volatility/duration required")
    r = np.asarray(rate, dtype=float)
    if which == "cir" and np.any(r < 0):
        raise ValueError("nonnegative CIR rates required")
    state_factor = r if which == "cir" else 1
    return r - risk_price * volatility * short_rate_duration * state_factor
