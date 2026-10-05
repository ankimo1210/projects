"""Private Hull GE Ch14 stochastic processes; supplied noise and MC references."""

import math

import numpy as np


def wiener_moments(initial, drift, diffusion, maturity):
    """Exact normal mean, variance and standard deviation for constant a,b."""
    if not all(math.isfinite(x) for x in (initial, drift, diffusion, maturity)) or maturity < 0:
        raise ValueError("finite coefficients and nonnegative maturity required")
    return initial+drift*maturity, diffusion**2*maturity, abs(diffusion)*math.sqrt(maturity)


def _time_grid(times):
    times = np.asarray(times, dtype=float)
    if times.ndim != 1 or len(times) < 2 or times[0] != 0 or not np.all(np.isfinite(times)) or np.any(np.diff(times) <= 0):
        raise ValueError("time grid must start at zero and increase strictly")
    return times


def wiener_paths(initial, drift, diffusion, times, normals):
    """Generalized Wiener paths on any increasing grid, from caller iid normals."""
    times = _time_grid(times)
    wiener_moments(initial, drift, diffusion, times[-1])
    normals = np.atleast_2d(np.asarray(normals, dtype=float))
    if normals.ndim != 2 or normals.shape[1] != len(times)-1 or not np.all(np.isfinite(normals)):
        raise ValueError("one finite normal increment per time interval required")
    increments = normals*np.sqrt(np.diff(times))
    brownian = np.column_stack((np.zeros(len(normals)), np.cumsum(increments, axis=1)))
    return initial+drift*times+diffusion*brownian


def brownian_bridge_refine(times, paths, midpoint_normals):
    """Insert conditional Brownian midpoints while preserving coarse nodes.

    Paths are standard Brownian motion (diffusion one). The new midpoint
    given both endpoints has their average and conditional variance dt/4.
    """
    times = _time_grid(times)
    paths = np.atleast_2d(np.asarray(paths, dtype=float))
    normals = np.atleast_2d(np.asarray(midpoint_normals, dtype=float))
    if paths.shape[1] != len(times) or normals.shape != (len(paths), len(times)-1) or not np.all(np.isfinite(paths)) or not np.all(np.isfinite(normals)):
        raise ValueError("coarse paths and matching midpoint normals required")
    fine_times = np.empty(2*len(times)-1)
    fine_times[::2] = times
    fine_times[1::2] = (times[:-1]+times[1:])/2
    fine = np.empty((len(paths), len(fine_times)))
    fine[:, ::2] = paths
    fine[:, 1::2] = (paths[:, :-1]+paths[:, 1:])/2+normals*np.sqrt(np.diff(times)/4)
    return fine_times, fine


def brownian_path_length_mean(maturity, steps):
    """Expected summed absolute vertical increments on a uniform Brownian grid."""
    if not math.isfinite(maturity) or maturity < 0 or steps < 1 or int(steps) != steps:
        raise ValueError("nonnegative time and positive integer steps required")
    return math.sqrt(2*maturity*steps/math.pi)


def _stock_inputs(spot, drift, sigma, time):
    if not all(math.isfinite(x) for x in (spot, drift, sigma, time)) or spot <= 0 or sigma < 0 or time < 0:
        raise ValueError("positive spot, nonnegative volatility/time and finite drift required")


def stock_paths(spot, drift, sigma, dt, normals, *, scheme="euler", step_coefficients=None):
    """Replay supplied shocks by stock Euler (14.8) or exact log increments.

    Euler may create negative stocks and does not clip them. Optional step
    coefficients explicitly reproduce the printed .00288/.0416 Table 14.1
    track; accumulation keeps full precision, with rounding left to display.
    """
    _stock_inputs(spot, drift, sigma, dt)
    normals = np.atleast_2d(np.asarray(normals, dtype=float))
    if normals.ndim != 2 or not np.all(np.isfinite(normals)):
        raise ValueError("finite one- or two-dimensional shocks required")
    if scheme == "euler":
        a, b = (drift*dt, sigma*math.sqrt(dt)) if step_coefficients is None else step_coefficients
        if not math.isfinite(a) or not math.isfinite(b):
            raise ValueError("finite step coefficients required")
        multipliers = 1+a+b*normals
    elif scheme == "exact" and step_coefficients is None:
        multipliers = np.exp((drift-sigma*sigma/2)*dt+sigma*math.sqrt(dt)*normals)
    else:
        raise ValueError("scheme must be euler or exact; step coefficients are Euler-only")
    return spot*np.column_stack((np.ones(len(normals)), np.cumprod(multipliers, axis=1)))


def euler_stock_moments(spot, drift, sigma, maturity, steps):
    """Exact first two moments of the discrete iid Euler-product process."""
    _stock_inputs(spot, drift, sigma, maturity)
    if steps < 1 or int(steps) != steps:
        raise ValueError("positive integer steps required")
    dt = maturity/steps
    mean = spot*(1+drift*dt)**steps
    second = spot**2*((1+drift*dt)**2+sigma*sigma*dt)**steps
    return mean, max(second-mean*mean, 0.0)


def correlated_wiener_increments(normals, rho, dt=1):
    """Hull's u, rho*u+sqrt(1-rho**2)*v construction, scaled by sqrt(dt).

    Caller normals' final dimension is the independent pair (u,v). Endpoints
    rho = +/-1 are permitted and give singular, perfectly correlated pairs.
    """
    normals = np.asarray(normals, dtype=float)
    if not math.isfinite(rho) or abs(rho) > 1 or not math.isfinite(dt) or dt < 0 or normals.ndim < 1 or normals.shape[-1] != 2 or not np.all(np.isfinite(normals)):
        raise ValueError("finite paired normals, rho in [-1,1] and nonnegative dt required")
    return math.sqrt(dt)*np.stack((normals[..., 0], rho*normals[..., 0]+math.sqrt(1-rho*rho)*normals[..., 1]), axis=-1)


def ito_coefficients(drift, diffusion, g_time, g_x, g_xx):
    """Local drift/diffusion of G(X,t) from supplied derivatives (14.12).

    The returned diffusion multiplies the same Brownian increment as X.
    Derivatives are caller inputs; this helper performs no differentiation.
    """
    a, b, gt, gx, gxx = np.broadcast_arrays(*[np.asarray(x, dtype=float) for x in (drift, diffusion, g_time, g_x, g_xx)])
    if not all(np.all(np.isfinite(x)) for x in (a, b, gt, gx, gxx)):
        raise ValueError("finite coefficients and derivatives required")
    return gx*a+gt+.5*gxx*b*b, gx*b


def forward_ito(spot, drift, sigma, rate, time, expiry):
    """Constant-rate, no-dividend forward F=S*exp(r*(T-t)) (14.15–16).

    Forward PRICE, rather than the value of an existing forward contract.
    Its physical growth rate is mu-r; under Q its level drift is zero while
    its log drift still contains the -sigma**2/2 correction.
    """
    _stock_inputs(spot, drift, sigma, time)
    if not math.isfinite(rate) or not math.isfinite(expiry) or expiry < time:
        raise ValueError("finite rate and expiry at or after current time required")
    forward = spot*math.exp(rate*(expiry-time))
    a, b = ito_coefficients(drift*spot, sigma*spot, -rate*forward, forward/spot, 0)
    return dict(forward=forward, drift=float(a), diffusion=float(b), log_drift=drift-rate-sigma*sigma/2)
