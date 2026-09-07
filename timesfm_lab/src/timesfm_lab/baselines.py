"""Classical forecasting baselines, each producing a point path *and* quantiles.

The point of this module is to make the comparison hard to win.  A foundation
model that only beats "repeat the last value" has shown nothing; the bar here is
a seasonal-naive with *empirical* residual quantiles, damped Holt-Winters, Theta
and a Fourier regression — the methods that actually win M-competitions on
seasonal data.

Every baseline returns the same shapes as the TimesFM wrapper: ``point`` of
shape ``(H,)`` and ``quantiles`` of shape ``(H, len(QUANTILE_LEVELS))``, so the
scoring code never has to special-case a model.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable

import numpy as np

QUANTILE_LEVELS = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
_N_BOOT = 1000
_RNG_SEED = 12345


class Forecast:
    """A point path plus a quantile fan, with a note about how it was made."""

    __slots__ = ("fallback", "point", "quantiles")

    def __init__(self, point: np.ndarray, quantiles: np.ndarray, fallback: str = ""):
        self.point = np.asarray(point, dtype=np.float64)
        self.quantiles = np.asarray(quantiles, dtype=np.float64)
        self.fallback = fallback


def _sort_fan(q: np.ndarray) -> np.ndarray:
    """Enforce monotone quantiles. Crossing is a scoring artefact, not a signal."""
    return np.sort(q, axis=1)


def _empirical_fan(point: np.ndarray, steps_ahead: np.ndarray, resid: np.ndarray) -> np.ndarray:
    """Quantiles from bootstrapped sums of ``k`` i.i.d. one-step residuals.

    ``steps_ahead[h]`` is how many *model* steps forward point ``h`` is — 1 per
    period for a random walk, 1 per season for a seasonal naive.  Bootstrapping
    the sum rather than assuming normality matters on the heavy-tailed series
    (river flow), where a Gaussian band is badly too narrow.
    """
    rng = np.random.default_rng(_RNG_SEED)
    r = resid[np.isfinite(resid)]
    n_h = len(point)
    if r.size < 8:
        return np.repeat(point[:, None], len(QUANTILE_LEVELS), axis=1)
    kmax = int(steps_ahead.max())
    draws = rng.choice(r, size=(_N_BOOT, kmax), replace=True)
    cum = np.cumsum(draws, axis=1)  # (B, kmax) — cumulative k-step error
    fan = np.empty((n_h, len(QUANTILE_LEVELS)))
    for h in range(n_h):
        k = int(steps_ahead[h])
        fan[h] = point[h] + np.quantile(cum[:, k - 1], QUANTILE_LEVELS)
    return _sort_fan(fan)


def _gaussian_fan(point: np.ndarray, sigma: np.ndarray) -> np.ndarray:
    from scipy.stats import norm

    z = norm.ppf(QUANTILE_LEVELS)
    return _sort_fan(point[:, None] + sigma[:, None] * z[None, :])


# --------------------------------------------------------------------------- #
# baselines
# --------------------------------------------------------------------------- #


def naive(context: np.ndarray, horizon: int, season: int) -> Forecast:
    """Random walk: repeat the last observation; error grows as a random walk."""
    x = np.asarray(context, float)
    point = np.repeat(x[-1], horizon)
    resid = np.diff(x)
    steps = np.arange(1, horizon + 1)
    return Forecast(point, _empirical_fan(point, steps, resid))


def seasonal_naive(context: np.ndarray, horizon: int, season: int) -> Forecast:
    """Repeat the last full season; the textbook bar for anything seasonal.

    Uncertainty follows Hyndman's construction: the h-step error accumulates one
    seasonal-difference residual per *season* elapsed, not per step, which is why
    the fan is flat within a season and widens at each seasonal boundary.
    """
    x = np.asarray(context, float)
    m = season if len(x) > season else 1
    last = x[-m:]
    idx = np.arange(horizon) % m
    point = last[idx]
    resid = x[m:] - x[:-m]
    steps = np.arange(horizon) // m + 1
    return Forecast(point, _empirical_fan(point, steps, resid))


def theta(context: np.ndarray, horizon: int, season: int) -> Forecast:
    """The Theta method (M3 winner), via statsmodels."""
    from statsmodels.tsa.forecasting.theta import ThetaModel

    x = np.asarray(context, float)
    m = season if len(x) >= 2 * season else 1
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = ThetaModel(x, period=m, deseasonalize=m > 1).fit()
            point = np.asarray(res.forecast(horizon), float)
        if not np.isfinite(point).all():
            raise ValueError("non-finite theta forecast")
    except Exception as exc:
        fb = seasonal_naive(context, horizon, season)
        return Forecast(fb.point, fb.quantiles, fallback=f"theta->snaive ({type(exc).__name__})")

    sd = float(np.std(x[m:] - x[:-m])) / np.sqrt(2.0) if m > 1 else float(np.std(np.diff(x)))
    sigma = sd * np.sqrt(np.arange(1, horizon + 1) / max(m, 1) + 1.0)
    return Forecast(point, _gaussian_fan(point, sigma))


def ets(context: np.ndarray, horizon: int, season: int) -> Forecast:
    """Damped-trend Holt-Winters, with simulated paths for the quantile fan.

    Seasonality is dropped when the period exceeds ``_ETS_MAX_SEASON``: fitting
    144 seasonal states is both very slow and badly overparameterised, and the
    Fourier regression covers that regime instead.  Such runs are marked as a
    fallback so the report can say where ETS was handicapped.
    """
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    x = np.asarray(context, float)
    seasonal_ok = 1 < season <= _ETS_MAX_SEASON and len(x) >= 3 * season
    note = "" if seasonal_ok or season <= 1 else f"ETS non-seasonal (m={season} > {_ETS_MAX_SEASON})"
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = ExponentialSmoothing(
                x,
                trend="add",
                damped_trend=True,
                seasonal="add" if seasonal_ok else None,
                seasonal_periods=season if seasonal_ok else None,
                initialization_method="estimated",
            )
            res = model.fit(optimized=True)
            point = np.asarray(res.forecast(horizon), float)
            sims = res.simulate(horizon, repetitions=200, error="add", random_errors="bootstrap")
            sims = np.asarray(sims, float).reshape(horizon, -1)
            fan = _sort_fan(np.quantile(sims, QUANTILE_LEVELS, axis=1).T)
        if not (np.isfinite(point).all() and np.isfinite(fan).all()):
            raise ValueError("non-finite ETS output")
    except Exception as exc:
        fb = seasonal_naive(context, horizon, season)
        return Forecast(fb.point, fb.quantiles, fallback=f"ets->snaive ({type(exc).__name__})")
    return Forecast(point, fan, fallback=note)


_ETS_MAX_SEASON = 48


def fourier_ols(context: np.ndarray, horizon: int, season: int) -> Forecast:
    """Linear trend + Fourier harmonics, fitted by least squares.

    Handles long seasonal periods that state-space seasonality cannot, at the
    cost of a homoskedastic error band that does not widen with the horizon.
    """
    x = np.asarray(context, float)
    n = len(x)
    k = int(min(10, max(1, season // 2)))
    t = np.arange(n, dtype=float)
    tf = np.arange(n, n + horizon, dtype=float)

    def design(tt: np.ndarray) -> np.ndarray:
        cols = [np.ones_like(tt), (tt - n / 2.0) / max(n, 1)]
        if season > 1:
            for j in range(1, k + 1):
                cols.append(np.sin(2 * np.pi * j * tt / season))
                cols.append(np.cos(2 * np.pi * j * tt / season))
        return np.column_stack(cols)

    xd, xf = design(t), design(tf)
    try:
        beta, *_ = np.linalg.lstsq(xd, x, rcond=None)
        point = xf @ beta
        resid = x - xd @ beta
        if not np.isfinite(point).all():
            raise ValueError("non-finite OLS forecast")
    except Exception as exc:
        fb = seasonal_naive(context, horizon, season)
        return Forecast(fb.point, fb.quantiles, fallback=f"ols->snaive ({type(exc).__name__})")
    sigma = np.repeat(float(np.std(resid)), horizon)
    return Forecast(point, _gaussian_fan(point, sigma))


def _har_features(buf: np.ndarray, end: int) -> np.ndarray:
    """[1, last, mean of last 5, mean of last 22] over ``buf[:end]``."""
    return np.array(
        [1.0, buf[end - 1], buf[end - 5 : end].mean(), buf[end - 22 : end].mean()]
    )


def _har_roll(buf: np.ndarray, start: int, steps: int, beta: np.ndarray,
              shocks: np.ndarray | None) -> np.ndarray:
    """Iterate the HAR recursion forward in a preallocated buffer."""
    out = np.empty(steps)
    for h in range(steps):
        v = float(_har_features(buf, start + h) @ beta)
        if shocks is not None:
            v += shocks[h]
        buf[start + h] = v
        out[h] = v
    return out


def har(context: np.ndarray, horizon: int, season: int) -> Forecast:
    """Corsi's HAR: regress on the last value and its 5- and 22-period averages.

    The standard bar for realised volatility, and the one a comparison that skips
    it will quietly lose to on any clustered series. Iterated forward for
    multi-step, with the band from bootstrapping one-step residuals through the
    same recursion, so the uncertainty compounds the way the point forecast does.
    """
    x = np.asarray(context, float)
    if len(x) < 22 + 60:
        fb = seasonal_naive(context, horizon, season)
        return Forecast(fb.point, fb.quantiles, fallback="har->snaive (context too short)")

    n = len(x)
    xd = np.stack([_har_features(x, i) for i in range(22, n)])
    yd = x[22:]
    try:
        beta, *_ = np.linalg.lstsq(xd, yd, rcond=None)
        resid = yd - xd @ beta
        buf = np.empty(n + horizon)
        buf[:n] = x
        point = _har_roll(buf, n, horizon, beta, None)
        if not np.isfinite(point).all():
            raise ValueError("non-finite HAR forecast")
    except Exception as exc:
        fb = seasonal_naive(context, horizon, season)
        return Forecast(fb.point, fb.quantiles, fallback=f"har->snaive ({type(exc).__name__})")

    rng = np.random.default_rng(_RNG_SEED)
    r = resid[np.isfinite(resid)]
    n_paths = 300
    draws = rng.choice(r, size=(n_paths, horizon), replace=True)
    paths = np.empty((n_paths, horizon))
    buf = np.empty(n + horizon)
    for b in range(n_paths):
        buf[:n] = x
        paths[b] = _har_roll(buf, n, horizon, beta, draws[b])
    if not np.isfinite(paths).all():
        # An explosive fitted recursion can blow up under shocks even when the
        # point path is finite; fall back to a flat band rather than emit inf.
        return Forecast(point, _empirical_fan(point, np.arange(1, horizon + 1), r),
                        fallback="har fan->empirical (explosive paths)")
    fan = _sort_fan(np.quantile(paths, QUANTILE_LEVELS, axis=0).T)
    return Forecast(point, fan)


def ewma(context: np.ndarray, horizon: int, season: int) -> Forecast:
    """Flat forecast from an exponentially weighted mean, with lambda fit in-sample.

    Deliberately the simplest adaptive-level method there is. It is here to catch
    the case where a series has no exploitable structure beyond "recent values
    matter more" — which is most of finance.
    """
    x = np.asarray(context, float)

    def run(lam: float) -> tuple[float, np.ndarray]:
        m = x[0]
        err = np.empty(len(x) - 1)
        for i, v in enumerate(x[1:]):
            err[i] = v - m
            m = lam * m + (1 - lam) * v
        return m, err

    best_mse, best = np.inf, run(0.94)
    for lam in (0.80, 0.90, 0.94, 0.97, 0.99):
        m, err = run(lam)
        mse = float(np.mean(np.square(err)))
        if mse < best_mse:
            best_mse, best = mse, (m, err)
    m, resid = best
    point = np.repeat(m, horizon)
    return Forecast(point, _empirical_fan(point, np.arange(1, horizon + 1), resid))


BASELINES: dict[str, Callable[[np.ndarray, int, int], Forecast]] = {
    "naive": naive,
    "seasonal_naive": seasonal_naive,
    "theta": theta,
    "ets": ets,
    "fourier_ols": fourier_ols,
    "har": har,
    "ewma": ewma,
}

DISPLAY_NAMES = {
    "naive": "Naive (random walk)",
    "seasonal_naive": "Seasonal naive",
    "theta": "Theta",
    "ets": "ETS (damped Holt-Winters)",
    "fourier_ols": "Fourier + trend OLS",
    "har": "HAR (Corsi)",
    "ewma": "EWMA",
    "timesfm_3.0": "TimesFM 3.0 (zero-shot)",
}
