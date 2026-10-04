"""Private finite-GBM factor experiment for Hull GE §28.5.

Signed loadings share a final factor axis. C is a correlation matrix,
C=L L.T, and correlated row loading s becomes s@L in independent coordinates.
No inverse/whitening is needed at rank deficiency. Rates are year^-1,
loadings year^-1/2, and horizons years. Zero relative drift is a true
martingale here because finite-time constant GBMs have finite moments.
"""

import numpy as np


def _contains_bool(value):
    if isinstance(value, (bool, np.bool_)):
        return True
    if isinstance(value, (list, tuple)):
        return any(_contains_bool(item) for item in value)
    return isinstance(value, np.ndarray) and value.dtype.kind == "b"


def _real(value, name):
    try:
        if _contains_bool(value):
            raise ValueError(f"{name} must not contain boolean inputs")
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf" or not np.all(np.isfinite(raw)):
            raise ValueError(f"{name} must contain finite real numbers, with years explicit")
        result = raw.astype(float)
        if not np.all(np.isfinite(result)):
            raise ValueError(f"{name} is not representable")
        return result
    except (TypeError, OverflowError, FloatingPointError) as exc:
        raise ValueError(f"{name} must contain representable finite real numbers") from exc


def _result(value):
    if not np.all(np.isfinite(value)):
        raise ValueError("factor result is not representable")
    return float(value) if np.ndim(value) == 0 else value


def correlation_factor(correlation):
    """Return L with L@L.T=C, for one finite symmetric unit-diagonal PSD C.

    The factor is nonunique. Only negative eigenvalues at scaled roundoff
    are clipped, and the reconstruction is checked; invalid C is rejected.
    Singular positive-semidefinite correlations (including rho=+/-1) are valid.
    """
    c = _real(correlation, "correlation")
    if c.ndim != 2 or c.shape[0] == 0 or c.shape[0] != c.shape[1]:
        raise ValueError("one nonempty square correlation matrix required")
    n = c.shape[0]
    eps = 64 * np.finfo(float).eps * n
    if (
        np.max(np.abs(c)) > 1 + eps
        or not np.allclose(c, c.T, rtol=0, atol=eps)
        or not np.allclose(np.diag(c), 1, rtol=0, atol=eps)
    ):
        raise ValueError("symmetric unit-diagonal correlation with entries in [-1,1] required")
    try:
        eigenvalues, vectors = np.linalg.eigh((c + c.T) / 2)
        tolerance = eps * max(1.0, float(np.max(np.abs(eigenvalues))))
        if np.min(eigenvalues) < -tolerance:
            raise ValueError("correlation must be positive semidefinite")
        factor = vectors * np.sqrt(np.maximum(eigenvalues, 0))[None, :]
        if np.max(np.abs(factor @ factor.T - c)) > tolerance:
            raise ValueError("correlation factor reconstruction exceeds roundoff")
        return _result(factor)
    except np.linalg.LinAlgError as exc:
        raise ValueError("correlation factor is not representable") from exc


def _factor_inputs(s_f, s_g, correlation):
    sf, sg = _real(s_f, "f loading"), _real(s_g, "g loading")
    if sf.ndim == 0 or sg.ndim == 0 or sf.shape[-1] == 0 or sf.shape[-1] != sg.shape[-1]:
        raise ValueError("loadings require a matching nonempty final factor axis")
    n = sf.shape[-1]
    if correlation is None:
        L = np.eye(n)
    else:
        L = correlation_factor(correlation)
        if L.shape != (n, n):
            raise ValueError("correlation dimension must match final factor axis")
    try:
        with np.errstate(over="raise", invalid="raise", under="ignore"):
            sf, sg = np.broadcast_arrays(sf, sg)
            return _result(sf @ L), _result(sg @ L)
    except (FloatingPointError, ValueError) as exc:
        raise ValueError("factor loadings cannot be broadcast or represented") from exc


def _pair_products(sf, sg):
    with np.errstate(over="raise", invalid="raise", under="ignore"):
        return _result(np.sum(sf * sg, axis=-1)), _result(np.sum(sg * sg, axis=-1))


def factor_ratio_drift(mu_f, mu_g, s_f, s_g, correlation=None):
    """Return relative Ito drift mu_f-mu_g+s_g C s_g-s_f C s_g.

    This is not the log drift. Leading batch dimensions broadcast after
    reduction of the final factor axis; scalar loading is not a 1-factor vector.
    """
    mf, mg = _real(mu_f, "f drift"), _real(mu_g, "g drift")
    sf, sg = _factor_inputs(s_f, s_g, correlation)
    try:
        with np.errstate(over="raise", invalid="raise", under="ignore"):
            cov, vg = _pair_products(sf, sg)
            return _result(mf - mg + vg - cov)
    except (FloatingPointError, ValueError) as exc:
        raise ValueError("factor ratio drift cannot be broadcast or represented") from exc


def factor_numeraire_drifts(rate, s_f, s_g, correlation=None):
    """Return drifts under positive no-income g: r+s_f C s_g, r+s_g C s_g.

    Independent risk loading is s_g@L. In correlated coordinates the
    ordinary-dot-product risk vector would be C@s_g, not s_g itself.
    """
    r = _real(rate, "rate")
    sf, sg = _factor_inputs(s_f, s_g, correlation)
    try:
        with np.errstate(over="raise", invalid="raise", under="ignore"):
            cov, vg = _pair_products(sf, sg)
            return _result(r + cov), _result(r + vg)
    except (FloatingPointError, ValueError) as exc:
        raise ValueError("factor numeraire drift cannot be broadcast or represented") from exc


def factor_ratio_conditional_mean(value, mu_f, mu_g, s_f, s_g, horizon, correlation=None):
    """Return E[X_(t+h)|F_t]=X_t*exp(relative_drift*h) for constant GBM.

    The observed value must be positive and h>=0 before batch broadcast,
    including empty batches. Finite output and positive representability
    are required. Signed rates/loadings and rank-deficient C are supported.
    Distinct time-zero or deterministic observed values mean separate
    initial markets, not impossible observations from one fixed market.
    """
    observed, h = _real(value, "observed ratio"), _real(horizon, "horizon")
    if np.any(observed <= 0) or np.any(h < 0):
        raise ValueError("positive ratio and nonnegative horizon required")
    drift = factor_ratio_drift(mu_f, mu_g, s_f, s_g, correlation)
    try:
        with np.errstate(over="raise", invalid="raise", under="ignore"):
            mean = observed * np.exp(drift * h)
            if np.any(mean <= 0):
                raise ValueError("positive conditional mean underflowed")
            return _result(mean)
    except (FloatingPointError, ValueError) as exc:
        raise ValueError("conditional mean cannot be broadcast or represented") from exc
