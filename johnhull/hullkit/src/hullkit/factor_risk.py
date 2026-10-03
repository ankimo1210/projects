"""Signed factor risk premiums in a consistent risk basis (Hull GE §28.2)."""

import numpy as np

from .risk_premium import _real_inputs, _result


def factor_contributions(risk_prices, loadings):
    """Return lambda_i*s_i, retaining the final factor axis.

    Both inputs must have a final nonempty factor axis of equal length.
    Leading batch dimensions broadcast. Coefficients and risk prices are signed,
    finite real values in year**-1/2, in the SAME chosen risk basis; contributions
    have units year**-1. This is not a correlation/whitening or estimation API.
    Empty batches are valid, empty factor axes are not. Invalid inputs, mismatched
    shapes or unrepresentable calculations raise ValueError.
    """
    lam, signed = _real_inputs(risk_prices, loadings)
    if lam.ndim == 0 or signed.ndim == 0:
        raise ValueError("a final factor axis is required")
    if lam.shape[-1] == 0 or lam.shape[-1] != signed.shape[-1]:
        raise ValueError("factor axes must have equal positive length")
    lam, signed = np.broadcast_arrays(lam, signed)
    try:
        with np.errstate(over="raise", invalid="raise", under="ignore"):
            return _result(lam * signed)
    except FloatingPointError as exc:
        raise ValueError("factor calculation is not representable") from exc


def factor_excess_return(risk_prices, loadings):
    """Return sum_i lambda_i*s_i (mu-r), reducing only the final factor axis.

    The return is an annual EXCESS return, not the total expected return.
    A single market returns float; leading batches return ndarray. Negative and
    zero premiums are valid. See factor_contributions for the input convention.
    """
    contributions = factor_contributions(risk_prices, loadings)
    try:
        with np.errstate(over="raise", invalid="raise", under="ignore"):
            return _result(np.sum(contributions, axis=-1))
    except FloatingPointError as exc:
        raise ValueError("factor calculation is not representable") from exc


def factor_required_return(r, risk_prices, loadings):
    """Return r + sum_i lambda_i*s_i, an instantaneous annual total return.

    r broadcasts against the REDUCED leading batch axes, never the factor axis.
    Input validation precedes broadcasting, even alongside an empty batch.
    This is the no-income traded-claim drift identity, not a market estimator.
    """
    rate = _real_inputs(r)[0]
    excess = factor_excess_return(risk_prices, loadings)
    rate, excess = np.broadcast_arrays(rate, excess)
    try:
        with np.errstate(over="raise", invalid="raise", under="ignore"):
            return _result(rate + excess)
    except FloatingPointError as exc:
        raise ValueError("factor calculation is not representable") from exc
