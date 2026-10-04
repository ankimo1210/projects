"""Private constant-GBM ratio checks for Hull GE §28.3.

Coefficients share ONE Wiener source. Signed loadings use year**-1/2;
mu/r use year**-1, horizon years. These finite-time GBMs have finite
moments. Zero drift alone is not a general true-martingale guarantee.
"""

import numpy as np

from .risk_premium import _real_inputs, _result


def ratio_drift(mu_f, mu_g, s_f, s_g):
    """Return relative Ito drift mu_f-mu_g+s_g*(s_g-s_f), not log drift."""
    mf, mg, sf, sg = np.broadcast_arrays(*_real_inputs(mu_f, mu_g, s_f, s_g))
    try:
        with np.errstate(over="raise", invalid="raise", under="ignore"):
            return _result(mf - mg + sg * (sg - sf))
    except FloatingPointError as exc:
        raise ValueError("ratio drift is not representable") from exc


def numeraire_drifts(r, s_f, s_g):
    """Return (mu_f,mu_g) under positive no-income g's measure: lambda=s_g."""
    rate, sf, sg = np.broadcast_arrays(*_real_inputs(r, s_f, s_g))
    try:
        with np.errstate(over="raise", invalid="raise", under="ignore"):
            return _result(rate + sg * sf), _result(rate + sg * sg)
    except FloatingPointError as exc:
        raise ValueError("numeraire drifts are not representable") from exc


def ratio_conditional_mean(value, mu_f, mu_g, s_f, s_g, horizon):
    """Return E[X_(t+h)|F_t] for observed X_t=value>0 and constant GBM.

    The independent future Wiener increment yields value*exp(a*h).
    Validate value and h before broadcasting, including empty batches.
    Signed loading/rates are valid. Invalid real settings, nonfinite or
    unrepresentable results (including a positive mean underflowing to zero)
    raise ValueError. Scalars return float, other results ndarray.
    """
    inputs = _real_inputs(value, mu_f, mu_g, s_f, s_g, horizon)
    if np.any(inputs[0] <= 0) or np.any(inputs[-1] < 0):
        raise ValueError("positive ratio and nonnegative horizon required")
    observed, mf, mg, sf, sg, h = np.broadcast_arrays(*inputs)
    drift = ratio_drift(mf, mg, sf, sg)
    try:
        with np.errstate(over="raise", invalid="raise", under="ignore"):
            mean = observed * np.exp(drift * h)
            if np.any(mean <= 0):
                raise ValueError("positive conditional mean is not representable")
            return _result(mean)
    except FloatingPointError as exc:
        raise ValueError("conditional mean is not representable") from exc
