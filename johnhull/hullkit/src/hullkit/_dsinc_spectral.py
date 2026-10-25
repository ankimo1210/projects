"""Private nodal fixed-frequency engine (Itkin 2610.28847v1, Eq.53/61)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from itertools import pairwise
from time import perf_counter

import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.interpolate import CubicSpline
from scipy.linalg import expm

from hullkit._dsinc_types import PricingFailure, PutContract, SpectralConfig, VarianceModel


@dataclass(frozen=True)
class Propagators:
    """One-step transforms bound to the complete immutable pricing inputs."""

    matrices: np.ndarray
    omega: np.ndarray
    weights: np.ndarray
    log_variances: np.ndarray
    dt: float
    input_hash: str
    setup_seconds: float
    diagnostics: dict


def _input_hash(contract, model, config):
    inputs = [asdict(value) for value in (contract, model, config)]
    return hashlib.sha256(json.dumps(inputs, sort_keys=True, allow_nan=False).encode()).hexdigest()


def frequency_rule(config: SpectralConfig) -> tuple[np.ndarray, np.ndarray]:
    """Positive composite Gauss–Legendre rule; endpoints are not sampled."""
    nodes, weights = leggauss(config.points_per_panel)
    omega, quadrature = [], []
    for lo, hi in pairwise(config.panels):
        omega.append((hi + lo) / 2 + (hi - lo) * nodes / 2)
        quadrature.append(weights * (hi - lo) / 2)
    return np.concatenate(omega), np.concatenate(quadrature)


def variance_grid(config: SpectralConfig) -> np.ndarray:
    """Return the inclusive, uniform log-variance node grid."""
    return np.linspace(*config.log_var_bounds, config.n_var)


def _generator_matrix(z, variance, a, b, covariance, frequency, carry):
    z = np.asarray(z, dtype=float)
    if z.ndim != 1 or z.size < 3 or not np.all(np.isfinite(z)):
        raise ValueError("log-variance grid must contain at least three finite nodes")
    h = z[1] - z[0]
    if h <= 0 or not np.allclose(np.diff(z), h, rtol=1e-10, atol=1e-12):
        raise ValueError("log-variance grid must be uniform and increasing")
    variance, a, b, covariance = [
        np.broadcast_to(np.asarray(v, dtype=float), z.shape) for v in (variance, a, b, covariance)
    ]
    if not all(np.all(np.isfinite(v)) for v in (variance, a, b, covariance)) or np.any(
        variance <= 0
    ):
        raise ValueError("variance and transformed coefficients must be finite")
    k = complex(frequency)
    if not np.isfinite(k):
        raise ValueError("frequency must be finite")
    diffusion = 0.5 * a**2 / h**2
    drift = (b + 1j * k * covariance) / (2 * h)
    potential = 1j * k * carry - 0.5 * (k * k + 1j * k) * variance
    matrix = np.diag(potential - 2 * diffusion).astype(np.complex128)
    matrix += np.diag((diffusion + drift)[:-1], 1)
    matrix += np.diag((diffusion - drift)[1:], -1)
    matrix[0, 1] = 2 * diffusion[0]
    matrix[-1, -2] = 2 * diffusion[-1]
    return matrix


def frequency_generator(
    contract: PutContract, model: VarianceModel, log_variances: np.ndarray, frequency: complex
) -> np.ndarray:
    """Non-discounted log-variance generator; models share its matrix assembly."""
    z = np.asarray(log_variances, dtype=float)
    with np.errstate(over="ignore", under="ignore", divide="ignore", invalid="ignore"):
        v = np.exp(z)
        if model.kind == "heston":
            a = model.xi / np.sqrt(v)
            b = model.kappa * model.theta / v - model.kappa - model.xi**2 / (2 * v)
        else:
            a = model.xi * np.sqrt(v)
            b = model.kappa * model.theta - (model.kappa + model.xi**2 / 2) * v
        covariance = model.rho * np.sqrt(v) * a
    return _generator_matrix(
        z, v, a, b, covariance, frequency, contract.domestic_rate - contract.foreign_rate
    )


def _validate_model_grid(model, config):
    if not config.log_var_bounds[0] <= np.log(model.v0) <= config.log_var_bounds[1]:
        raise ValueError("initial variance is outside the log-variance grid")


def build_propagators(
    contract: PutContract, model: VarianceModel, config: SpectralConfig
) -> Propagators:
    """Build one complex matrix exponential per reflected frequency, Eq.53."""
    _validate_model_grid(model, config)
    started = perf_counter()
    z = variance_grid(config)
    omega, weights = frequency_rule(config)
    dt = contract.expiry / config.n_time
    matrices = np.empty((len(omega), len(z), len(z)), dtype=np.complex128)
    for j, frequency in enumerate(-omega - 1j * config.chi):
        matrices[j] = expm(dt * frequency_generator(contract, model, z, frequency))
    a0 = frequency_generator(contract, model, z, 0j).real
    m0 = expm(dt * a0)
    v = np.exp(z)
    if model.kind == "heston":
        drift = model.kappa * model.theta / v - model.kappa - model.xi**2 / (2 * v)
        variance_diffusion = model.xi**2 / v
    else:
        drift = model.kappa * model.theta - (model.kappa + model.xi**2 / 2) * v
        variance_diffusion = model.xi**2 * v
    pe = np.abs(drift) * (z[1] - z[0]) / variance_diffusion
    diagnostics = {
        "propagator_bytes": int(matrices.nbytes),
        "max_peclet": float(np.max(pe)),
        "zero_frequency_min_entry": float(m0.min()),
        "zero_frequency_row_error": float(np.max(np.abs(m0.sum(axis=1) - 1))),
        "scheme_nonmonotone": bool(m0.min() < -1e-10),
    }
    for array in (matrices, omega, weights, z):
        array.setflags(write=False)
    return Propagators(
        matrices,
        omega,
        weights,
        z,
        dt,
        _input_hash(contract, model, config),
        perf_counter() - started,
        diagnostics,
    )


def _apply(propagators, vector):
    return np.einsum("qij,qj->qi", propagators.matrices, vector, optimize=True)


def _terminal_vector(propagators, steps):
    vector = np.ones((len(propagators.omega), len(propagators.log_variances)), dtype=np.complex128)
    for _ in range(steps):
        vector = _apply(propagators, vector)
    return vector


def _put_at_nodes(contract, log_spots, omega, weights, chi, vector, *, tau=None):
    tau = contract.expiry if tau is None else tau
    denominator = (1j * omega - chi) * (1 + 1j * omega - chi)
    phase = np.exp(np.outer(np.asarray(log_spots), chi - 1j * omega))
    paired = (phase * (weights / denominator)[None, :]) @ vector
    return contract.strike * np.exp(-contract.domestic_rate * tau) * (1 + paired.real / np.pi)


def _spot_vector(spots):
    spots = np.asarray(spots, dtype=float)
    if spots.ndim != 1 or not spots.size or np.any(~np.isfinite(spots)) or np.any(spots <= 0):
        raise ValueError("spots must be a nonempty positive finite vector")
    return spots


def european_put(
    contract: PutContract,
    model: VarianceModel,
    spots: np.ndarray,
    config: SpectralConfig,
    *,
    propagators: Propagators | None = None,
) -> np.ndarray:
    """Evaluate raw European puts via the positive-strip residue formula, Eq.61."""
    spots = _spot_vector(spots)
    if propagators is not None and propagators.input_hash != _input_hash(contract, model, config):
        raise ValueError("propagator cache input mismatch")
    if contract.expiry == 0:
        return np.maximum(contract.strike - spots, 0.0)
    _validate_model_grid(model, config)
    prop = build_propagators(contract, model, config) if propagators is None else propagators
    vector = _terminal_vector(prop, config.n_time)
    values = _put_at_nodes(
        contract, np.log(spots / contract.strike), prop.omega, prop.weights, config.chi, vector
    )
    result = np.asarray(
        CubicSpline(prop.log_variances, values, axis=1, extrapolate=False)(np.log(model.v0)),
        dtype=float,
    )
    if np.any(~np.isfinite(result)):
        raise PricingFailure(
            "nonfinite_european",
            "nonfinite European integration result",
            {"prices": result.tolist()},
        )
    return result
