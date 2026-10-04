"""Private Hull §29.4 curve delta/gamma and volatility PCA sensitivities."""

import numpy as np


def _vector(values):
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or not x.size or not np.all(np.isfinite(x)):
        raise ValueError("nonempty finite vector required")
    return x


def _bump_size(bump):
    if not np.isfinite(bump) or bump <= 0:
        raise ValueError("positive finite bump required")
    return float(bump)


def _directions(values, size):
    p = np.asarray(values, dtype=float)
    if p.ndim != 2 or p.shape[0] != size or not p.shape[1] or not np.all(np.isfinite(p)):
        raise ValueError("directions must have one row per state variable")
    return p


def _cash_changes(value_function, point, directions, bump):
    return np.array(
        [
            (value_function(point + bump * d) - value_function(point - bump * d)) / 2
            for d in directions.T
        ]
    )


def finite_difference_sensitivities(value_function, point, bump):
    """Central gradient and full symmetric Hessian in the supplied coordinates."""
    x, h = _vector(point), _bump_size(bump)
    base = float(value_function(x))
    eye = np.eye(x.size) * h
    up = np.array([value_function(x + d) for d in eye])
    down = np.array([value_function(x - d) for d in eye])
    gradient = (up - down) / (2 * h)
    hessian = np.diag((up - 2 * base + down) / h**2)
    for i in range(x.size):
        for j in range(i):
            cross = (
                value_function(x + eye[i] + eye[j])
                - value_function(x + eye[i] - eye[j])
                - value_function(x - eye[i] + eye[j])
                + value_function(x - eye[i] - eye[j])
            ) / (4 * h**2)
            hessian[i, j] = hessian[j, i] = cross
    return {"value": base, "gradient": gradient, "hessian": hessian}


def rate_hedge_report(
    value_function, zero_rates, quote_values, rebuild_curve, pca_directions, *, bump=1e-4
):
    """Four rate deltas on one portfolio, with zero and rebuilt-quote gammas.

    Cash deltas are signed central price changes for a positive `bump`
    (one basis point by default), not derivatives per unit rate. Quote delta
    always rebuilds the curve. Sums of separate cash deltas match a parallel
    finite bump to first order only. PCA directions use zero-rate coordinates;
    their normalization is supplied by the caller. Gammas are per rate squared.
    """
    z, q, h = _vector(zero_rates), _vector(quote_values), _bump_size(bump)
    p = _directions(pca_directions, z.size)

    def quote_value(quotes):
        rebuilt = _vector(rebuild_curve(quotes))
        if rebuilt.shape != z.shape:
            raise ValueError("rebuilt curve must have the zero-rate shape")
        return value_function(rebuilt)

    zeros = finite_difference_sensitivities(value_function, z, h)
    quotes = finite_difference_sensitivities(quote_value, q, h)
    parallel = np.ones_like(z)
    dv01 = _cash_changes(value_function, z, parallel[:, None], h)[0]
    parallel_gamma = (value_function(z + h) - 2 * zeros["value"] + value_function(z - h)) / h**2
    return {
        "dv01_cash": dv01,
        "bucket_delta_cash": zeros["gradient"] * h,
        "quote_delta_cash": quotes["gradient"] * h,
        "quote_parallel_cash": _cash_changes(quote_value, q, np.ones((q.size, 1)), h)[0],
        "pca_delta_cash": _cash_changes(value_function, z, p, h),
        "hessian": zeros["hessian"],
        "quote_hessian": quotes["hessian"],
        "parallel_gamma": parallel_gamma,
        "pca_gamma": p.T @ zeros["hessian"] @ p,
        "unique_gamma_count": q.size * (q.size + 1) // 2,
    }


def pca_loadings(changes, count=2):
    """Sample-covariance PCA; eigenvector signs are intentionally unspecified."""
    x = np.asarray(changes, dtype=float)
    if x.ndim != 2 or x.shape[0] < 2 or not 1 <= count <= x.shape[1]:
        raise ValueError("at least two observations and a valid component count required")
    if not np.all(np.isfinite(x)):
        raise ValueError("finite changes required")
    centered = x - x.mean(axis=0)
    covariance = centered.T @ centered / (x.shape[0] - 1)
    eigenvalues, loadings = np.linalg.eigh(covariance)
    order = np.argsort(eigenvalues)[::-1][:count]
    return {"eigenvalues": eigenvalues[order], "loadings": loadings[:, order]}


def volatility_hedge_report(value_function, vol_values, pca_directions, *, bump=0.001):
    """Central parallel/PCA vegas per 0.01 relative or absolute vol unit.

    The caller chooses Black relative or normal absolute vol coordinates;
    this function does not mix their units. Factor amplitudes are scaled to
    0.01 in the supplied loading convention, not a 1% relative change in vol.
    """
    v, h = _vector(vol_values), _bump_size(bump)
    p = _directions(pca_directions, v.size)
    return {
        "parallel_vega_per_point": _cash_changes(value_function, v, np.ones((v.size, 1)), h)[0]
        / h
        * 0.01,
        "pca_vega_per_point": _cash_changes(value_function, v, p, h) / h * 0.01,
    }
