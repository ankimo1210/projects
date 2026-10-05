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
