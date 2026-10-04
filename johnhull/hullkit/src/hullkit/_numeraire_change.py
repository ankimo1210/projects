"""Private Hull §28.8 change of numeraire with signed correlated loadings.

The ratio is new/old (h/g). In correlated coordinates the instantaneous
correction is b_v C (s_h-s_g). b_v may be a relative loading or an absolute
loading; the supplied drift must use the same convention. Absolute loadings
allow nontraded variables at zero or negative states. State-dependent inputs
are local coefficients, not a claim of a global lognormal distribution.
"""

import numpy as np

from ._multi_factor_martingales import correlation_factor


def _factors(variable, old, new, correlation):
    b, g, h = [np.asarray(x, dtype=float) for x in (variable, old, new)]
    if any(x.ndim == 0 or x.shape[-1] == 0 or not np.all(np.isfinite(x)) for x in (b, g, h)):
        raise ValueError("finite nonempty final factor axis required")
    if b.shape[-1] != g.shape[-1] or b.shape[-1] != h.shape[-1]:
        raise ValueError("matching factor dimensions required")
    C = np.eye(b.shape[-1]) if correlation is None else np.asarray(correlation, dtype=float)
    if C.shape != (b.shape[-1], b.shape[-1]):
        raise ValueError("one correlation matrix matching the factors required")
    correlation_factor(C)
    b, g, h = np.broadcast_arrays(b, g, h)
    return b, g, h, C


def _out(value):
    if not np.all(np.isfinite(value)):
        raise ValueError("measure result is not representable")
    return float(value) if np.ndim(value) == 0 else value


def _horizon(value):
    t = np.asarray(value, dtype=float)
    if not np.all(np.isfinite(t)) or np.any(t < 0):
        raise ValueError("finite nonnegative horizon in years required")
    return t


def numeraire_drift_change(
    old_drift, variable_loading, old_numeraire_loading, new_numeraire_loading, correlation=None
):
    """Return old drift + b_v C (s_new-s_old), Hull 28.33–28.35.

    Loadings share their final factor axis; leading dimensions broadcast.
    Positive tradable numeraires must include income reinvestment. Applying
    an arbitrary state's coefficient here does not make its Q drift r.
    """
    b, g, h, C = _factors(
        variable_loading, old_numeraire_loading, new_numeraire_loading, correlation
    )
    drift = np.asarray(old_drift, dtype=float)
    return _out(drift + np.sum((b @ C) * (h - g), axis=-1))


def physical_to_q_drift(physical_drift, variable_loading, risk_prices, correlation=None):
    """Return mu_P-b C lambda; independent factors use C=I.

    Correlated lambda denotes its loading representation: the Brownian
    P-to-Q shift is C lambda. Singular null directions have no drift effect.
    Nontraded state variables retain their own risk-adjusted drift.
    """
    risk = np.asarray(risk_prices, dtype=float)
    return numeraire_drift_change(
        physical_drift, variable_loading, risk, np.zeros_like(risk), correlation
    )


def new_measure_brownian_increment(
    old_increment, old_numeraire_loading, new_numeraire_loading, horizon, correlation=None
):
    """dW_new = dW_old-C(s_new-s_old)dt, with sign opposite the drift change."""
    t = _horizon(horizon)
    W, g, h, C = _factors(old_increment, old_numeraire_loading, new_numeraire_loading, correlation)
    return _out(W - ((h - g) @ C) * t[..., None])


def numeraire_density(
    old_increment, old_numeraire_loading, new_numeraire_loading, horizon, correlation=None
):
    """Raw dQ_h/dQ_g for finite constant GBMs: exp(delta_s*dW-.5*variance*T).

    This is the normalized h/g ratio relative to its current value. It is
    never divided by the realized sample mean. General predictable loading
    processes require their stochastic integrals and martingale conditions.
    """
    t = _horizon(horizon)
    W, g, h, C = _factors(old_increment, old_numeraire_loading, new_numeraire_loading, correlation)
    delta = h - g
    variance = np.sum((delta @ C) * delta, axis=-1)
    return _out(np.exp(np.sum(W * delta, axis=-1) - 0.5 * variance * t))
