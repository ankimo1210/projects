"""Private DSINC fixed-frequency propagators and the Eq. (61) European put.

For every reflected frequency ``k = -omega - i*chi`` the log-variance operator ``A_k`` of the
Heston or the 3/2 model is assembled by central differences on a uniform ``zeta = log v`` grid,
with ghost-reflection Neumann ends, and propagated over one time step with one
``scipy.linalg.expm``.  The discount ``-rd`` is not part of ``A_k``; prices apply it once.  Both
models take the same assembly path and differ only in the ``zeta`` coefficients.

Time is in years, rates are continuously compounded, ``v`` is a variance rate and prices are
divided by the strike.  Every invalid input raises ``ValueError``; nothing is clipped or
replaced.  Propagators are bound to the inputs they were built for by a digest.  No RNG, no I/O,
no public API.
"""

import math
import time
from dataclasses import dataclass

import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.interpolate import CubicSpline
from scipy.linalg import expm

from ._dsinc_types import PutContract, SpectralConfig, VarianceModel, canonical_digest

_LOG_V0_SLACK = 1e-12  # log v0 may sit this far outside the grid ends (roundoff of log(exp(z)))
_NONMONOTONE_ENTRY = -1e-10  # a zero-frequency propagator entry below this is a negative weight
_FLUSH_BELOW = 1e-200  # smaller parts cannot move a price; their products would go subnormal


def frequency_rule(config: SpectralConfig) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(omega, weights)`` of the panelwise Gauss-Legendre rule, ascending in ``omega``.

    Each panel ``[p, q]`` of ``config.panels`` gets ``config.points_per_panel`` Gauss-Legendre
    nodes mapped to ``(q - p)/2 * g + (q + p)/2`` with weights ``(q - p)/2 * w``.  The weights sum
    to the cutoff ``panels[-1]`` and integrate polynomials up to degree ``2*points_per_panel - 1``
    exactly on each panel.
    """
    nodes, base_weights = leggauss(config.points_per_panel)
    edges = np.asarray(config.panels, dtype=float)
    half_width = 0.5 * np.diff(edges)
    centre = 0.5 * (edges[1:] + edges[:-1])
    omega = (half_width[:, None] * nodes[None, :] + centre[:, None]).ravel()
    weights = (half_width[:, None] * base_weights[None, :]).ravel()
    return omega, weights


def variance_grid(config: SpectralConfig) -> np.ndarray:
    """Return the uniform ``zeta = log v`` grid, both ends of ``log_var_bounds`` included."""
    low, high = config.log_var_bounds
    return np.linspace(low, high, config.n_var)


def coefficient_arrays(
    model: VarianceModel, variance: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return ``(a, b, sqrt_v_a)`` of ``d zeta = b dt + a dW_v`` with ``zeta = log v``.

    Ito's formula on the variance SDE gives, for the 3/2 model ``dv = kappa v (theta - v) dt +
    xi v^{3/2} dW``, ``a = xi sqrt(v)``, ``b = kappa theta - (kappa + xi^2/2) v`` and
    ``sqrt_v_a = xi v``; for Heston ``dv = kappa (theta - v) dt + xi sqrt(v) dW``,
    ``a = xi / sqrt(v)``, ``b = kappa theta / v - kappa - xi^2 / (2 v)`` and ``sqrt_v_a = xi``.
    ``sqrt_v_a`` is the product ``sqrt(v) * a`` that multiplies the spot/variance correlation.
    """
    v = np.asarray(variance, dtype=float)
    if not np.all(np.isfinite(v)) or np.any(v <= 0.0):
        raise ValueError("variance must be positive and finite")
    kappa, theta, xi = model.kappa, model.theta, model.xi
    if model.kind == "three_halves":
        return xi * np.sqrt(v), kappa * theta - (kappa + 0.5 * xi**2) * v, xi * v
    if model.kind == "heston":
        return xi / np.sqrt(v), kappa * theta / v - kappa - xi**2 / (2.0 * v), np.full_like(v, xi)
    raise ValueError(f"unsupported model kind {model.kind!r}")


def _grid_step(log_variances: np.ndarray) -> float:
    """Return the step of a uniform increasing 1-D grid of at least three nodes."""
    if log_variances.ndim != 1 or log_variances.size < 3:
        raise ValueError("log_variances must be a 1-D grid of at least three nodes")
    step = (log_variances[-1] - log_variances[0]) / (log_variances.size - 1)
    if not step > 0.0 or not np.allclose(np.diff(log_variances), step, rtol=1e-6, atol=0.0):
        raise ValueError("log_variances must be a uniform increasing grid")
    return float(step)


def _assemble_generator(
    log_variances: np.ndarray,
    a: np.ndarray,
    b: np.ndarray,
    sqrt_v_a: np.ndarray,
    variance: np.ndarray,
    frequency: complex,
    domestic_rate: float,
    foreign_rate: float,
    rho: float,
) -> np.ndarray:
    """Assemble ``A_k`` (without the ``-rd`` discount) as a dense ``(n_var, n_var)`` matrix.

    ``A_k f = d f'' + c f' + z f`` with ``d = a^2/2``, ``c = b + i k rho sqrt_v_a`` and
    ``z = i k (rd - rf) - (k^2 + i k) v / 2``, by central differences.  The two ends reflect
    through a ghost node (``f'`` = 0, ``f'' = 2 (f_neighbour - f_end) / h^2``).
    """
    n = log_variances.size
    h = _grid_step(log_variances)
    k = complex(frequency)
    diffusion = 0.5 * a * a
    convection = b + 1j * k * rho * sqrt_v_a
    reaction = 1j * k * (domestic_rate - foreign_rate) - 0.5 * (k * k + 1j * k) * variance
    lower = diffusion / h**2 - convection / (2.0 * h)
    centre = -2.0 * diffusion / h**2 + reaction
    upper = diffusion / h**2 + convection / (2.0 * h)
    index = np.arange(n)
    matrix = np.zeros((n, n), dtype=complex)
    matrix[index, index] = centre
    matrix[index[1:], index[:-1]] = lower[1:]
    matrix[index[:-1], index[1:]] = upper[:-1]
    matrix[0, 1] = 2.0 * diffusion[0] / h**2
    matrix[n - 1, n - 2] = 2.0 * diffusion[n - 1] / h**2
    return matrix


def frequency_generator(
    contract: PutContract, model: VarianceModel, log_variances: np.ndarray, frequency: complex
) -> np.ndarray:
    """Return the non-discounted operator ``A_k`` of ``model`` on the ``log_variances`` grid.

    ``frequency`` is the complex ``k`` (``-omega - i*chi`` for a reflected frequency, ``0`` for the
    plain log-variance generator).  The matrix is ``(n_var, n_var)`` complex.  Heston and 3/2 differ
    only in :func:`coefficient_arrays`.
    """
    z = np.asarray(log_variances, dtype=float)
    variance = np.exp(z)
    a, b, sqrt_v_a = coefficient_arrays(model, variance)
    return _assemble_generator(
        z,
        a,
        b,
        sqrt_v_a,
        variance,
        frequency,
        contract.domestic_rate,
        contract.foreign_rate,
        model.rho,
    )


@dataclass(frozen=True, eq=False)
class Propagators:
    """One-step propagators ``expm(dt * A_k)`` at every reflected frequency, bound to their inputs.

    ``matrices[j]`` is ``expm(dt * A_k)`` for ``k = -omega[j] - i*chi`` on the ``log_variances``
    grid (``variance`` holds the node variances used in ``A_k``), ``dt = T / n_time``, with parts
    below ``1e-200`` in magnitude stored as 0 (see :func:`build_propagators`).
    ``coefficients_tag`` is ``"model"`` or ``"fixture:<sha256 of the four coefficient arrays>"``
    and ``digest`` binds the risk-free rates, the expiry, the model, the config and the tag (the
    strike is not bound).  ``setup_seconds`` is the build wall time and ``nbytes`` the size of
    ``matrices``.  The arrays are read-only.  ``==`` and ``hash`` are by identity (comparing
    array fields element-wise would not give a truth value); compare propagators by ``digest``.
    """

    omega: np.ndarray
    weights: np.ndarray
    chi: float
    log_variances: np.ndarray
    variance: np.ndarray
    dt: float
    n_time: int
    matrices: np.ndarray
    coefficients_tag: str
    digest: str
    setup_seconds: float
    nbytes: int


def _inputs_digest(
    contract: PutContract, model: VarianceModel, config: SpectralConfig, coefficients_tag: str
) -> str:
    """Return the digest of everything the propagators depend on (the strike is excluded)."""
    return canonical_digest(
        contract.domestic_rate,
        contract.foreign_rate,
        contract.expiry,
        model,
        config,
        coefficients_tag,
    )


def _fixture_array(name: str, values: object, n_var: int) -> np.ndarray:
    """Return ``values`` as a finite float64 vector of ``n_var`` nodes (a private copy)."""
    try:
        array = np.array(values, dtype=float)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a real vector, got {values!r}") from None
    if array.shape != (n_var,):
        raise ValueError(f"{name} must have shape ({n_var},), got {array.shape}")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be finite")
    return array


def _read_only(array: np.ndarray) -> np.ndarray:
    """Mark ``array`` read-only and return it; only arrays owned by the builder are passed."""
    array.flags.writeable = False
    return array


def build_propagators(
    contract: PutContract,
    model: VarianceModel,
    config: SpectralConfig,
    *,
    coefficients: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None = None,
) -> Propagators:
    """Build ``expm(dt * A_k)`` for every reflected frequency ``k = -omega - i*chi``.

    ``coefficients`` is a test fixture ``(a, b, sqrt_v_a, variance)`` of four vectors with
    ``n_var`` nodes that replaces the model coefficients (``variance`` is then the node ``v`` in
    ``A_k``); the tag records their hash.  The expiry must be positive: at ``T = 0`` the payoff is
    exact and no propagator exists.  One ``scipy.linalg.expm`` per frequency, no loop over matrix
    entries.  Real and imaginary parts of ``expm`` below ``1e-200`` in magnitude (``_FLUSH_BELOW``)
    are set to exactly 0 in place: they cannot move a price at double precision, and keeping them
    would let their products in the batched matmul of the recursion go subnormal, which is slow.
    Most of them are normal numbers between about 1e-308 and 1e-200; only some are subnormal
    themselves.  NaN and infinity are not touched.
    """
    started = time.perf_counter()
    if contract.expiry <= 0.0:
        raise ValueError("propagators need a positive expiry; at T = 0 the payoff is exact")
    omega, weights = frequency_rule(config)
    z = variance_grid(config)
    if coefficients is None:
        variance = np.exp(z)
        a, b, sqrt_v_a = coefficient_arrays(model, variance)
        tag = "model"
    else:
        if len(coefficients) != 4:
            raise ValueError("coefficients must be (a, b, sqrt_v_a, variance)")
        names = ("a", "b", "sqrt_v_a", "variance")
        a, b, sqrt_v_a, variance = (
            _fixture_array(name, values, config.n_var)
            for name, values in zip(names, coefficients, strict=True)
        )
        tag = "fixture:" + canonical_digest(a, b, sqrt_v_a, variance)
    dt = contract.expiry / config.n_time
    matrices = np.empty((omega.size, config.n_var, config.n_var), dtype=complex)
    for j, frequency in enumerate(-omega - 1j * config.chi):
        generator = _assemble_generator(
            z,
            a,
            b,
            sqrt_v_a,
            variance,
            frequency,
            contract.domestic_rate,
            contract.foreign_rate,
            model.rho,
        )
        block = expm(dt * generator)
        block.real[np.abs(block.real) < _FLUSH_BELOW] = 0.0  # NaN and inf compare False: kept
        block.imag[np.abs(block.imag) < _FLUSH_BELOW] = 0.0
        matrices[j] = block
    return Propagators(
        omega=_read_only(omega),
        weights=_read_only(weights),
        chi=config.chi,
        log_variances=_read_only(z),
        variance=_read_only(variance),
        dt=dt,
        n_time=config.n_time,
        matrices=_read_only(matrices),
        coefficients_tag=tag,
        digest=_inputs_digest(contract, model, config, tag),
        setup_seconds=time.perf_counter() - started,
        nbytes=int(matrices.nbytes),
    )


def check_propagators(
    propagators: Propagators, contract: PutContract, model: VarianceModel, config: SpectralConfig
) -> None:
    """Raise ``ValueError`` unless ``propagators`` were built for these inputs.

    The digest is recomputed from ``contract`` (rates and expiry, not the strike), ``model``,
    ``config`` and the stored ``coefficients_tag``.  It binds the inputs, it does not re-verify
    the matrices.
    """
    if _inputs_digest(contract, model, config, propagators.coefficients_tag) != propagators.digest:
        raise ValueError("propagators were built for different inputs")


def inverse_sum(
    propagators: Propagators, log_spots: np.ndarray, coefficients: np.ndarray
) -> np.ndarray:
    """Return ``(1/pi) Re sum_j weights_j exp((chi - i omega_j) x) coefficients_j`` for each ``x``.

    ``log_spots`` has shape ``(n_x,)`` and ``coefficients`` ``(n_omega, n_var)``; the result is
    ``(n_x, n_var)``.  This is the quadrature of the damped inverse Fourier transform.
    """
    x = np.asarray(log_spots, dtype=float)
    phase = np.exp(np.multiply.outer(x, propagators.chi - 1j * propagators.omega))
    return ((phase * propagators.weights) @ np.asarray(coefficients)).real / math.pi


def _log_v0_in_grid(log_variances: np.ndarray, v0: float) -> float:
    """Return ``log v0``, refusing a ``v0`` outside the variance grid (no extrapolation)."""
    if not (math.isfinite(v0) and v0 > 0.0):
        raise ValueError(f"v0 must be positive and finite, got {v0!r}")
    log_v0 = math.log(v0)
    low, high = float(log_variances[0]), float(log_variances[-1])
    if not low - _LOG_V0_SLACK <= log_v0 <= high + _LOG_V0_SLACK:
        raise ValueError(
            f"v0={v0!r} is outside the variance grid [{math.exp(low):.6g}, {math.exp(high):.6g}]"
        )
    return log_v0


def interpolate_at_variance(
    node_values: np.ndarray, log_variances: np.ndarray, v0: float
) -> np.ndarray:
    """Evaluate ``node_values`` (variance on the last axis) at ``v0`` by a not-a-knot cubic spline.

    The spline runs in ``zeta = log v``.  A ``v0`` outside the grid, beyond a ``1e-12`` slack in
    ``log v0``, raises ``ValueError`` ("outside the variance grid"); nothing is extrapolated.
    """
    z = np.asarray(log_variances, dtype=float)
    log_v0 = _log_v0_in_grid(z, v0)
    return CubicSpline(z, node_values, axis=-1, bc_type="not-a-knot")(log_v0)


def _spot_array(spots: np.ndarray) -> np.ndarray:
    """Return ``spots`` as a 1-D finite positive float vector."""
    try:
        array = np.asarray(spots, dtype=float)
    except (TypeError, ValueError):
        raise ValueError(f"spots must be a real vector, got {spots!r}") from None
    if array.ndim != 1 or not np.all(np.isfinite(array)) or np.any(array <= 0.0):
        raise ValueError("spots must be a 1-D array of finite positive values")
    return array


def european_put(
    contract: PutContract,
    model: VarianceModel,
    spots: np.ndarray,
    config: SpectralConfig,
    *,
    propagators: Propagators | None = None,
) -> np.ndarray:
    """Return the Eq. (61) European put price divided by the strike, one value per spot.

    With ``s = i*omega - chi`` the node value is ``exp(-rd T) [1 + (1/pi) Re sum_j weights_j
    exp((chi - i omega_j) x) E_j / (s_j (1 + s_j))]`` where ``E_j = M_j^N 1`` and ``x = log(S/K)``;
    the result is interpolated to ``v0`` by :func:`interpolate_at_variance`.  ``spots`` must be a
    1-D array of finite positive values and ``v0`` must lie inside the variance grid, both checked
    before any propagator is built.  Given ``propagators`` they are checked against the inputs,
    also at ``T = 0``, where none exist and a passed object is therefore rejected with
    ``ValueError``; they do not depend on the strike.  At ``T = 0`` the exact payoff
    ``max(1 - S/K, 0)`` is returned without propagating.  Violated price bounds are not clipped.
    """
    spot_array = _spot_array(spots)
    z = variance_grid(config)
    _log_v0_in_grid(z, model.v0)
    if propagators is not None:
        check_propagators(propagators, contract, model, config)
    if contract.expiry == 0.0:
        return np.maximum(1.0 - spot_array / contract.strike, 0.0)
    if propagators is None:
        propagators = build_propagators(contract, model, config)
    state = np.ones((propagators.omega.size, config.n_var, 1), dtype=complex)
    for _ in range(propagators.n_time):
        state = propagators.matrices @ state
    s = 1j * propagators.omega - propagators.chi
    coefficients = state[:, :, 0] / (s * (1.0 + s))[:, None]
    log_spots = np.log(spot_array / contract.strike)
    discount = math.exp(-contract.domestic_rate * contract.expiry)
    nodes = discount * (1.0 + inverse_sum(propagators, log_spots, coefficients))
    return interpolate_at_variance(nodes, propagators.log_variances, model.v0)


def generator_diagnostics(
    contract: PutContract, model: VarianceModel, config: SpectralConfig
) -> dict:
    """Return the monotonicity diagnostics of the discretised log-variance generator.

    ``peclet_max`` and ``peclet_above_one`` are the largest cell Peclet number ``|b| h / a^2`` and
    the number of nodes where it exceeds one.  ``zero_frequency_min_entry`` is the smallest entry
    of ``M0 = expm(dt A_0)`` (``A_0`` is the real generator at ``k = 0``),
    ``zero_frequency_row_sum_error`` is ``max |M0 1 - 1|`` and ``scheme_nonmonotone`` is true when
    the smallest entry is below ``-1e-10``.  A negative entry means the scheme does not preserve
    positivity; the values are plain Python ``float``, ``int`` and ``bool``.
    """
    z = variance_grid(config)
    a, b, _ = coefficient_arrays(model, np.exp(z))
    peclet = np.abs(b) * _grid_step(z) / a**2
    generator = frequency_generator(contract, model, z, 0.0).real
    propagator = expm((contract.expiry / config.n_time) * generator)
    min_entry = float(propagator.min())
    return {
        "peclet_max": float(peclet.max()),
        "peclet_above_one": int(np.count_nonzero(peclet > 1.0)),
        "zero_frequency_min_entry": min_entry,
        "zero_frequency_row_sum_error": float(np.max(np.abs(propagator.sum(axis=1) - 1.0))),
        "scheme_nonmonotone": bool(min_entry < _NONMONOTONE_ENTRY),
    }
