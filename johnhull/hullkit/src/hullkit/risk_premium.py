"""Instantaneous signed one-factor risk premiums (Hull GE §28.1)."""

import numpy as np


def _real_inputs(*values):
    arrays = []
    for value in values:
        try:
            array = np.asarray(value)
            if np.iscomplexobj(array) or (
                array.dtype.kind == "O" and any(np.iscomplexobj(item) for item in array.flat)
            ):
                raise ValueError("risk inputs must be real")
            array = np.asarray(array, dtype=float)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("risk inputs must be finite real values") from exc
        if not np.all(np.isfinite(array)):
            raise ValueError("risk inputs must be finite real values")
        arrays.append(array)
    return arrays


def _result(value):
    if not np.all(np.isfinite(value)):
        raise ValueError("risk calculation is not representable")
    return float(value) if value.ndim == 0 else value


def market_price_of_risk(mu, r, loading):
    """Return (mu-r)/loading for one common Wiener source and no income.

    mu,r are instantaneous annual returns (year**-1). loading is the
    SIGNED diffusion coefficient (year**-1/2); its absolute value is volatility.
    The returned lambda has units year**-1/2. Requires nonzero loading,
    even if mu=r: a deterministic asset cannot identify this risk price.

    Finite real inputs broadcast; scalar markets return float, others ndarray.
    Invalid/unrepresentable inputs or calculations raise ValueError, including
    invalid settings alongside an empty batch. This identity applies to traded
    no-income investment claims, not automatically to a consumption-asset spot.
    """
    inputs = _real_inputs(mu, r, loading)
    if np.any(inputs[2] == 0):
        raise ValueError("nonzero loading is required to identify risk price")
    mean, rate, signed = np.broadcast_arrays(*inputs)
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            return _result((mean - rate) / signed)
    except FloatingPointError as exc:
        raise ValueError("risk calculation is not representable") from exc


def required_return(r, risk_price, loading):
    """Return r+lambda*loading in the chosen one-factor probability measure.

    Rates use year**-1, risk_price and signed loading use year**-1/2.
    Zero loading returns r. Negative rates, risk prices and loadings are valid.
    Finite real inputs broadcast; scalar markets return float, others ndarray.
    Invalid inputs or unrepresentable calculations raise ValueError. This is
    a pointwise drift identity, not an estimator of real-world risk preferences.
    """
    rate, lam, signed = np.broadcast_arrays(*_real_inputs(r, risk_price, loading))
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            return _result(rate + lam * signed)
    except FloatingPointError as exc:
        raise ValueError("risk calculation is not representable") from exc
