"""Private Hull Ch23 estimators with explicit forecast timing and units.

Conditional variances are daily return variances. Series have n+1 entries:
entry i forecasts return i before observing it; the last is the next forecast.
These historical P-distribution forecasts are not market Q implied volatilities.
"""

import math

import numpy as np


def _vector(values):
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or x.size < 1 or not np.isfinite(x).all():
        raise ValueError("finite nonempty vector required")
    return x


def price_returns(prices, *, kind="simple"):
    """Daily simple or logarithmic returns from consecutive strictly positive prices."""
    p = _vector(prices)
    if p.size < 2 or np.any(p <= 0):
        raise ValueError("at least two positive prices required")
    if kind == "simple":
        return p[1:] / p[:-1] - 1
    if kind == "log":
        return np.diff(np.log(p))
    raise ValueError("return kind must be simple or log")


def estimate_variance(returns, *, center=True, ddof=1):
    """Centered sample variance or zero-mean squared-return estimate."""
    u = _vector(returns)
    if ddof < 0 or int(ddof) != ddof or ddof >= u.size:
        raise ValueError("nonnegative integer ddof smaller than sample size required")
    residual = u - u.mean() if center else u
    return float(residual @ residual / (u.size - ddof))


def arch_forecast(history, weights, *, long_variance=0, long_weight=0):
    """Weighted past squared returns plus long_weight*long_variance.

    history and weights are chronological, oldest first. Only the last len(weights)
    history values are used. The caller passes observations available before the
    forecast day. All weights, including long_weight, must sum to one.
    """
    u, w = _vector(history), _vector(weights)
    if (
        u.size < w.size
        or np.any(w < 0)
        or not np.isfinite([long_variance, long_weight]).all()
        or long_variance < 0
        or long_weight < 0
        or not math.isclose(float(w.sum() + long_weight), 1, abs_tol=1e-12, rel_tol=1e-12)
    ):
        raise ValueError("nonnegative normalized weights/variance and sufficient history required")
    return float(w @ u[-w.size :] ** 2 + long_weight * long_variance)


def _ewma_inputs(decay, initial):
    if not np.isfinite([decay, initial]).all() or not 0 <= decay <= 1 or initial < 0:
        raise ValueError("decay in [0,1] and nonnegative finite initial variance required")


def ewma_forecasts(returns, *, initial, decay=0.94):
    """n+1 forecasts; forecast[0]=initial, forecast[i+1] incorporates return[i]."""
    from .volatility import ewma_variance

    u = _vector(returns)
    _ewma_inputs(decay, initial)
    return ewma_variance(np.append(u, 0), lam=decay, init=initial)


def ewma_expanded(history, *, initial, decay=0.94):
    """Next variance from the finite weighted history, including decay^m initial."""
    u = _vector(history)
    _ewma_inputs(decay, initial)
    powers = decay ** np.arange(u.size - 1, -1, -1)
    return float(decay**u.size * initial + (1 - decay) * (powers @ u**2))


def _garch_inputs(omega, alpha, beta, initial=0):
    if not np.isfinite([omega, alpha, beta, initial]).all() or min(omega, alpha, beta, initial) < 0:
        raise ValueError("nonnegative finite GARCH parameters/initial variance required")


def garch_characteristics(omega, alpha, beta):
    """Discrete persistence and Hull's approximate continuous variance coefficients."""
    _garch_inputs(omega, alpha, beta)
    persistence = alpha + beta
    gamma = 1 - persistence
    return {
        "persistence": persistence,
        "long_weight": gamma,
        "long_variance": omega / gamma if gamma > 0 else None,
        "diffusion_mean_reversion": gamma,
        "diffusion_vol_of_variance": alpha * math.sqrt(2),
    }


def garch_forecasts(returns, omega, alpha, beta, *, initial):
    """n+1 conditional forecasts with an explicit initial variance.

    Positivity is required; stationarity is required only when using a finite
    long-run variance, not for a finite conditional forecast recursion.
    """
    from .volatility import garch11_variance

    u = _vector(returns)
    _garch_inputs(omega, alpha, beta, initial)
    return garch11_variance(np.append(u, 0), omega, alpha, beta, init=initial)


def garch_expanded(history, omega, alpha, beta, *, initial):
    """Finite beta-weighted return history, intercept and initial variance."""
    u = _vector(history)
    _garch_inputs(omega, alpha, beta, initial)
    powers = beta ** np.arange(u.size - 1, -1, -1)
    return float(beta**u.size * initial + omega * powers.sum() + alpha * (powers @ u**2))


def bernoulli_mle(successes, observations):
    """Bernoulli success-probability MLE from integer success and observation counts."""
    if (
        int(observations) != observations
        or observations < 1
        or int(successes) != successes
        or not 0 <= successes <= observations
    ):
        raise ValueError("integer counts 0 <= successes <= observations required")
    return float(successes / observations)


def conditional_likelihood(returns, variances):
    """Per-observation Hull eq23.12 measure -log(v)-u^2/v, twice log PDF sans constant."""
    u, variance = _vector(returns), _vector(variances)
    if u.shape != variance.shape or np.any(variance <= 0):
        raise ValueError("matching returns and strictly positive conditional variances required")
    return -np.log(variance) - u * u / variance


def fit_ewma(returns, *, initial):
    """Conditional normal MLE candidate from multiple extrema and both endpoints.

    Uniform and logarithmic endpoint grids locate extrema for bounded refinement.
    This numerical multistart search does not prove uniqueness of an optimum.
    The best converged candidate/endpoints are compared by the same likelihood.
    """
    from scipy.optimize import minimize_scalar

    u = _vector(returns)
    _ewma_inputs(0.94, initial)
    if initial == 0:
        raise ValueError("positive initial variance required for normal likelihood")

    def objective(decay):
        variance = ewma_forecasts(u, initial=initial, decay=decay)[:-1]
        if np.any(variance <= 0):
            return np.inf
        return -float(conditional_likelihood(u, variance).sum())

    near = np.geomspace(1e-12, 0.01, 81)
    grid = np.unique(np.r_[np.linspace(0, 1, 513), near, 1 - near])
    variance = np.full(grid.shape, initial)
    scores = np.zeros(grid.shape)
    for move in u:
        valid = variance > 0
        term = np.full(grid.shape, np.inf)
        term[valid] = np.log(variance[valid]) + move * move / variance[valid]
        scores += term
        variance = grid * variance + (1 - grid) * move * move
    candidates = [(0.0, objective(0.0)), (1.0, objective(1.0))]
    for i in range(1, grid.size - 1):
        if (
            np.isfinite(scores[i])
            and scores[i] <= scores[i - 1]
            and scores[i] <= scores[i + 1]
            and (scores[i] < scores[i - 1] or scores[i] < scores[i + 1])
        ):
            fit = minimize_scalar(
                objective,
                bounds=(grid[i - 1], grid[i + 1]),
                method="bounded",
                options={"xatol": 1e-12},
            )
            if fit.success and np.isfinite(fit.fun):
                candidates.append((float(fit.x), float(fit.fun)))
    decay, score = min(candidates, key=lambda point: point[1])
    if not np.isfinite(score):
        raise ValueError("EWMA fit has no finite converged likelihood candidate")
    return {
        "decay": float(decay),
        "measure": -float(score),
        "success": True,
        "search_grid_size": int(grid.size),
    }


def fit_garch(returns, *, initial, target_variance=None, hull_start=False):
    """Stationary Gaussian GARCH MLE using three scaled, constrained starts.

    initial is supplied explicitly. hull_start drops the first supplied return:
    it is the observation used to set initial=u[0]^2 in Table23.1. Variance
    targeting fixes omega=(1-alpha-beta)*target_variance. No original-data fit
    can be inferred from a successful synthetic-data fit.
    """
    from scipy.optimize import minimize

    original = _vector(returns)
    u = original[1:] if hull_start else original
    if u.size < 2 or not np.isfinite(initial) or initial <= 0:
        raise ValueError(
            "at least two likelihood observations and positive initial variance required"
        )
    scale = float(np.mean(u * u))
    if scale <= 0 or (
        target_variance is not None and (not np.isfinite(target_variance) or target_variance <= 0)
    ):
        raise ValueError("positive sample/target variance required")
    scaled = u / math.sqrt(scale)
    init = initial / scale
    targeted = target_variance is not None
    target = target_variance / scale if targeted else None

    def parameters(point):
        if targeted:
            alpha, beta = point
            return (1 - alpha - beta) * target, alpha, beta
        return tuple(point)

    def objective(point):
        omega, alpha, beta = parameters(point)
        if omega <= 0 or alpha < 0 or beta < 0 or alpha + beta >= 1:
            return 1e100
        variances = garch_forecasts(scaled, omega, alpha, beta, initial=init)[:-1]
        return -float(conditional_likelihood(scaled, variances).sum()) / scaled.size

    bounds = [(0, 1), (0, 1)] if targeted else [(1e-10, 100), (0, 1), (0, 1)]

    def stationary(point):
        _, alpha, beta = parameters(point)
        return 0.999999 - alpha - beta

    results = []
    for alpha, beta in [(0.1, 0.8), (0.2, 0.6), (0.05, 0.93)]:
        start = [alpha, beta] if targeted else [1 - alpha - beta, alpha, beta]
        result = minimize(
            objective,
            start,
            method="SLSQP",
            bounds=bounds,
            constraints=[{"type": "ineq", "fun": stationary}],
            options={"ftol": 1e-12, "maxiter": 1000},
        )
        if result.success and np.isfinite(result.fun) and result.fun < 1e90:
            results.append(result)
    if not results:
        raise ValueError("GARCH fit failed to converge from all starts")
    chosen = min(results, key=lambda result: result.fun)
    omega, alpha, beta = parameters(chosen.x)
    omega *= scale
    variances = garch_forecasts(u, omega, alpha, beta, initial=initial)[:-1]
    return {
        "omega": float(omega),
        "alpha": float(alpha),
        "beta": float(beta),
        "measure": float(conditional_likelihood(u, variances).sum()),
        "success": True,
        "target_variance": target_variance,
        "hull_start": hull_start,
    }


def autocorrelations(series, lags, *, convention="hull"):
    """Hull pairwise Pearson correlations, or globally-centered classical ACF."""
    x = _vector(series)
    if int(lags) != lags or not 1 <= lags <= x.size - 2:
        raise ValueError("positive integer lags leaving at least two pairs required")
    if convention not in ("hull", "global"):
        raise ValueError("ACF convention must be hull or global")
    centered = x - x.mean()
    denominator = float(centered @ centered)
    if denominator == 0:
        raise ValueError("autocorrelation is undefined for a constant series")
    result = []
    for lag in range(1, int(lags) + 1):
        if convention == "global":
            result.append(float(centered[:-lag] @ centered[lag:] / denominator))
        else:
            left, right = x[:-lag], x[lag:]
            left, right = left - left.mean(), right - right.mean()
            divisor = math.sqrt(float(left @ left) * float(right @ right))
            if divisor == 0:
                raise ValueError("pairwise autocorrelation has a zero-variance slice")
            result.append(float(left @ right / divisor))
    return np.array(result)


def ljung_box_from_acf(acf, observations, *, estimated_parameters=0):
    """Ljung–Box Q with explicit observations and optional degrees-of-freedom reduction."""
    from scipy.stats import chi2

    coefficients = _vector(acf)
    if (
        int(observations) != observations
        or observations <= coefficients.size
        or np.any(abs(coefficients) > 1)
        or int(estimated_parameters) != estimated_parameters
        or not 0 <= estimated_parameters < coefficients.size
    ):
        raise ValueError("valid ACF, sample length and positive residual test degrees required")
    lags = np.arange(1, coefficients.size + 1)
    statistic = float(
        observations * (observations + 2) * np.sum(coefficients**2 / (observations - lags))
    )
    degrees = coefficients.size - int(estimated_parameters)
    return {
        "statistic": statistic,
        "degrees": degrees,
        "p_value": float(chi2.sf(statistic, degrees)),
    }


def _forecast_inputs(initial, days, omega, alpha, beta):
    _garch_inputs(omega, alpha, beta, initial)
    p = alpha + beta
    if not np.isfinite(days) or days < 0 or not 0 < p <= 1 or (p == 1 and omega != 0):
        raise ValueError("nonnegative horizon and stationary GARCH (or driftless EWMA) required")
    return p


def expected_variance(initial, days, omega, alpha, beta):
    """E[v(day)] under GARCH; real days use the exponential interpolation in §23.6."""
    p = _forecast_inputs(initial, days, omega, alpha, beta)
    if p == 1:
        return float(initial)
    long = omega / (1 - p)
    return float(long + math.exp(math.log(p) * days) * (initial - long))


def garch_term_vol(initial, days, omega, alpha, beta, *, trading_days=252):
    """Annualized sqrt of average expected daily variance, Hull eq23.14.

    This is a historical P-variance term structure. It is not a Q market
    calibration, nor is sqrt(E[v]) the expectation of sqrt(v).
    """
    p = _forecast_inputs(initial, days, omega, alpha, beta)
    if not np.isfinite(trading_days) or trading_days <= 0:
        raise ValueError("positive trading days per year required")
    if days == 0 or p == 1:
        weight, average = 1.0, float(initial)
    else:
        rate = -math.log(p)
        weight = -math.expm1(-rate * days) / (rate * days)
        long = omega / (1 - p)
        average = long + (initial - long) * weight
    return {
        "average_variance": float(average),
        "annual_vol": math.sqrt(trading_days * max(average, 0)),
        "initial_weight": weight,
    }


def garch_vol_sensitivity(initial, days, omega, alpha, beta, *, trading_days=252):
    """Derivative of term annual vol with respect to instantaneous annual vol.

    Multiplying by .01 propagates one percentage point, not a relative 1%.
    """
    result = garch_term_vol(initial, days, omega, alpha, beta, trading_days=trading_days)
    if result["annual_vol"] == 0:
        return math.sqrt(result["initial_weight"])
    return float(
        result["initial_weight"] * math.sqrt(trading_days * initial) / result["annual_vol"]
    )


def covariance_diagnostics(covariance):
    """Diagnose a symmetric finite matrix without silently repairing negative eigenvalues."""
    matrix = np.asarray(covariance, dtype=float)
    if (
        matrix.ndim != 2
        or matrix.shape[0] != matrix.shape[1]
        or matrix.shape[0] < 1
        or not np.isfinite(matrix).all()
        or not np.allclose(matrix, matrix.T, atol=1e-14, rtol=1e-12)
    ):
        raise ValueError("finite symmetric nonempty square covariance required")
    eigenvalues = np.linalg.eigvalsh(matrix)
    tolerance = 1e-12 * max(float(abs(matrix).max()), 1e-30)
    return {
        "eigenvalues": eigenvalues,
        "minimum_eigenvalue": float(eigenvalues[0]),
        "is_psd": bool(eigenvalues[0] >= -tolerance),
    }


def correlation_from_covariance(covariance):
    """Correlation of a PSD covariance; every zero-variance row/column is NaN."""
    report = covariance_diagnostics(covariance)
    if not report["is_psd"]:
        raise ValueError("covariance is not positive semidefinite")
    matrix = np.asarray(covariance, dtype=float)
    scales = np.sqrt(np.maximum(np.diag(matrix), 0))
    divisor = np.outer(scales, scales)
    result = np.full_like(matrix, np.nan)
    np.divide(matrix, divisor, out=result, where=divisor > 0)
    return result


def covariance_forecasts(returns, initial, *, decay=0.94, omega=None, alpha=None, beta=None):
    """n+1 matrix forecasts using identical weights for all aligned return pairs.

    EWMA is the default. Passing omega/alpha/beta together selects a GARCH
    matrix recursion. A PSD intercept and common nonnegative coefficients
    preserve PSD; fitting separate pair coefficients offers no such guarantee.
    """
    from ._market_risk import _covariance

    x = np.asarray(returns, dtype=float)
    if x.ndim != 2 or min(x.shape) < 1 or not np.isfinite(x).all():
        raise ValueError("finite observations-by-assets returns required")
    matrix = _covariance(initial, x.shape[1])
    if omega is None and alpha is None and beta is None:
        _ewma_inputs(decay, 0)
        intercept, a, b = np.zeros_like(matrix), 1 - decay, decay
    elif omega is not None and alpha is not None and beta is not None:
        _garch_inputs(0, alpha, beta)
        intercept, a, b = _covariance(omega, x.shape[1]), alpha, beta
    else:
        raise ValueError("specify all GARCH covariance parameters together")
    result = np.empty((x.shape[0] + 1, x.shape[1], x.shape[1]))
    result[0] = matrix
    for i, move in enumerate(x):
        result[i + 1] = intercept + a * np.outer(move, move) + b * result[i]
    return result
