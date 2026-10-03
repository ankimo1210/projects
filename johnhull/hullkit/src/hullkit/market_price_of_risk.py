"""Market price of risk for one source of uncertainty (Hull 11e GE §28.1, pp.671–674).

A derivative f on u follows df/f = m dt + s dz with the same dz as u. The
loading s is signed: it is negative when f falls as u rises, and the
volatility of f is |s|. No arbitrage gives (m - r)/s = lambda for every
non-income derivative on u (eq. 28.8), so m = r + lambda*s (eqs. 28.9–28.10).
Choosing lambda chooses the measure: growth rates change, loadings do not.

All functions accept finite real values that broadcast and return float for
scalar inputs, otherwise ndarray. Invalid inputs raise ValueError.
"""

import numpy as np


def _arrays(*values):
    arrays = []
    for value in values:
        try:
            array = np.asarray(value)
            if np.iscomplexobj(array) or (
                array.dtype.kind == "O" and any(np.iscomplexobj(item) for item in array.flat)
            ):
                raise ValueError("market price of risk inputs must be real")
            array = np.asarray(array, dtype=float)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("market price of risk inputs must be finite real values") from exc
        if np.any(~np.isfinite(array)):
            raise ValueError("market price of risk inputs must be finite real values")
        arrays.append(array)
    return np.broadcast_arrays(*arrays)


def _result(out):
    if not np.all(np.isfinite(out)):
        raise ValueError("market price of risk calculation is not representable")
    return float(out) if out.shape == () else out


def market_price_of_risk(m, s, r):
    """lambda = (m - r)/s for a non-income security with signed loading s (eq. 28.8)."""
    m, s, r = _arrays(m, s, r)
    if np.any(s == 0):
        raise ValueError("the loading s must be nonzero to identify lambda")
    with np.errstate(over="ignore"):
        return _result((m - r) / s)


def required_growth(r, lam, s):
    """Expected growth m = r + lambda*s of a security with signed loading s (eq. 28.9)."""
    r, lam, s = _arrays(r, lam, s)
    with np.errstate(over="ignore"):
        return _result(r + lam * s)


def riskless_holdings(f1, s1, f2, s2):
    """Units (s2*f2, -s1*f1) of f1 and f2 whose dz exposure cancels (eq. 28.4).

    The portfolio value is Pi = s2*f2*f1 - s1*f1*f2. Prices must be positive,
    and the two loadings must differ so that Pi is not identically zero.
    """
    f1, s1, f2, s2 = _arrays(f1, s1, f2, s2)
    if np.any((f1 <= 0) | (f2 <= 0)):
        raise ValueError("derivative prices must be positive")
    if np.any(s1 == s2):
        raise ValueError("equal loadings give a zero-value portfolio")
    with np.errstate(over="ignore"):
        return _result(s2 * f2), _result(-s1 * f1)


def ito_growth_and_loading(f, f_t, f_u, f_uu, u, m, s):
    """Growth and signed loading of f(u,t) when du/u = m dt + s dz (Itô's lemma).

    growth = (f_t + m*u*f_u + s**2*u**2*f_uu/2)/f and loading = s*u*f_u/f.
    The price f and the variable u must be positive.
    """
    f, f_t, f_u, f_uu, u, m, s = _arrays(f, f_t, f_u, f_uu, u, m, s)
    if np.any((f <= 0) | (u <= 0)):
        raise ValueError("f and u must be positive")
    with np.errstate(over="ignore", invalid="ignore"):
        growth = (f_t + m * u * f_u + 0.5 * s * s * u * u * f_uu) / f
        loading = s * u * f_u / f
    return _result(growth), _result(loading)
