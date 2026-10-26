"""Private DSINC early-exercise recursion (Eq. (57)) and nodal exercise boundary (Eq. (58)).

Prices are divided by the strike, ``x = log(S/K)``, ``s = i*omega - chi`` and the exercise region
of the put is ``x <= x*(t, zeta)``.  With ``g(x) = rd - rf*exp(x)`` the early-exercise premium is
the time integral of ``exp(-rd*(u - t)) E[g(X_u) 1{X_u <= x*_u}]``, evaluated by a trapezoid rule
on ``t_n = n*T/N`` with a half weight at ``t_N`` and none at ``t_0`` (the premium is queried
outside the exercise region).  ``g 1{x <= x*} - rd`` has the transform
``exp(s x*) (rd/s - rf exp(x*)/(1+s))``; the constant ``rd`` is summed in closed form (``D_n``).
The transforms are carried backwards by the one-step propagators ``M`` of ``_dsinc_spectral``,
``Q_n = exp(-rd dt) M (w P(x*_{n+1}) + Q_{n+1})`` and ``E_n = M E_{n+1}``, in one batched matmul
per step, so the European leg ``E`` comes for free.

At every ``(t_n, zeta_i)`` the boundary is the root of the residual ``R_n(x)`` = payoff minus
continuation, where the continuation holds the European leg, the premium from ``t_{n+1}`` on and
the boundary-only endpoint term ``dt*g(x)/4``.  ``R_n`` is positive below ``x*`` and negative
above it.  The root search follows the last accepted boundary: a bracket
``[p - w, min(0, p + w)]`` with ``R(lo) > 0 > R(hi)``, a scan on a grid of spacing
``scan_spacing`` below the Gibbs scale of the frequency cutoff, the uppermost (or, as a
sensitivity, lowermost) positive-to-negative crossing, then bisection.  Several crossings are
kept and recorded (``multiple_crossings``); a missing or reversed bracket, a zero run, a
non-finite residual or an exhausted bisection fails the whole time slice, which is reported with
the status of every node.  Nothing is clipped or replaced.  No RNG, no I/O, no public API.
"""

import math
import time
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from ._dsinc_spectral import (
    Propagators,
    _log_v0_in_grid,
    _spot_array,
    build_propagators,
    check_propagators,
    generator_diagnostics,
    interpolate_at_variance,
    inverse_sum,
    variance_grid,
)
from ._dsinc_types import (
    BOUNDARY_STATUS,
    FAILURE_CODES,
    PricingFailure,
    PricingResult,
    PutContract,
    SpectralConfig,
    VarianceModel,
)

_NOT_RUN = BOUNDARY_STATUS["not_run"]
_SINGLE = BOUNDARY_STATUS["single"]
_MULTIPLE = BOUNDARY_STATUS["multiple_crossings"]
_MISSING = BOUNDARY_STATUS["missing_sign_change"]
_WRONG = BOUNDARY_STATUS["wrong_orientation"]
_AMBIGUOUS = BOUNDARY_STATUS["ambiguous_contact"]
_NONFINITE = BOUNDARY_STATUS["nonfinite"]
_MAXITER = BOUNDARY_STATUS["maxiter"]
_TERMINAL = BOUNDARY_STATUS["terminal"]
_FAILURE_CODES = np.array(sorted(FAILURE_CODES), dtype=np.int8)
_STATUS_NAMES = {code: name for name, code in BOUNDARY_STATUS.items()}


def payoff_transform(
    omega: np.ndarray, chi: float, log_boundary: np.ndarray, contract: PutContract
) -> np.ndarray:
    """Return the transform of ``(rd - rf e^x) 1{x <= Kb} - rd`` at ``s = i*omega - chi``.

    The result is ``exp(s Kb) (rd/s - rf exp(Kb)/(1+s))`` with shape ``(n_omega, n_var)``: row
    ``j`` is the frequency ``omega[j]`` and column ``i`` uses the boundary ``log_boundary[i]``
    (``Kb``).  Subtracting ``rd`` makes the function decay at both ends; ``rd`` is summed apart.
    """
    s = 1j * np.asarray(omega, dtype=float)[:, None] - chi
    boundary = np.asarray(log_boundary, dtype=float)[None, :]
    return np.exp(s * boundary) * (
        contract.domestic_rate / s - contract.foreign_rate * np.exp(boundary) / (1.0 + s)
    )


class BoundaryResidual(Protocol):
    """Residual ``R`` of the boundary equation at every variance node (positive below the root)."""

    def at(self, x: np.ndarray) -> np.ndarray:
        """Return ``R_i(x[i])`` for each node ``i``: shape ``(n_var,) -> (n_var,)``."""
        ...

    def on_grid(self, grid: np.ndarray) -> np.ndarray:
        """Return ``R_i(grid[k])`` for every grid point and node: ``(m,) -> (m, n_var)``."""
        ...


@dataclass(frozen=True, eq=False)
class BoundarySlice:
    """Boundary roots of one time slice, one entry per variance node.

    ``roots`` holds the log-boundary (``nan`` where the node failed), ``status`` the
    ``BOUNDARY_STATUS`` code as ``int8``, ``crossings`` the number of sign changes inside the
    adopted bracket as ``int16`` (``0`` without a bracket or when its scan failed), ``spread``
    the distance between the uppermost and the lowermost positive-to-negative crossing (``0`` for
    one crossing; cells are located to the scan spacing), ``width`` the adopted bracket half
    width (``nan`` without a bracket) and ``iterations`` the bisection steps as ``int16``.  ``==``
    and ``hash`` are by identity (the fields are arrays).
    """

    roots: np.ndarray
    status: np.ndarray
    crossings: np.ndarray
    spread: np.ndarray
    width: np.ndarray
    iterations: np.ndarray


def scan_spacing(config: SpectralConfig) -> float:
    """Return the scan step ``min(pi / (2 panels[-1]), root_widths[0] / 64)`` of the root search.

    The first term is half the Gibbs scale ``pi / cutoff`` of the frequency cutoff, the second
    puts at least 64 steps into the narrowest bracket.
    """
    return min(math.pi / (2.0 * config.panels[-1]), config.root_widths[0] / 64.0)


def _positions(rows: np.ndarray, grid: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    """Return the abscissa of sample ``rows[k]`` of node ``k`` in ``[lo, grid clipped, hi]``."""
    clipped = np.clip(grid[np.clip(rows - 1, 0, grid.size - 1)], lo, hi)
    return np.where(rows == 0, lo, np.where(rows == grid.size + 1, hi, clipped))


def _scan_cells(
    residual: BoundaryResidual,
    config: SpectralConfig,
    nodes: np.ndarray,
    lo: np.ndarray,
    hi: np.ndarray,
    r_lo: np.ndarray,
    r_hi: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Scan the adopted brackets of ``nodes`` and pick one sign-change cell ``[a, b]`` per node.

    One ``residual.on_grid`` call covers all nodes.  The samples of node ``k`` are ``lo[k]``, the
    grid points strictly inside ``(lo[k], hi[k])`` and ``hi[k]``; outside the bracket the grid
    rows repeat the nearest end sample, which adds neither a zero nor a sign change.  ``|R|`` up
    to ``root_residual_tol`` has sign ``0``.  Returns ``(failure, crossings, spread, a, b)``:
    ``failure`` is ``nonfinite`` or ``ambiguous_contact`` for a failed node and ``not_run``
    otherwise, ``crossings`` the number of sign changes once zero samples are dropped, ``spread``
    the distance between the uppermost and lowermost cell and ``(a, b)`` the cell of the
    configured crossing, whose ``+`` end is ``a`` and ``-`` end ``b``.
    """
    tol = config.root_residual_tol
    delta = scan_spacing(config)
    grid = delta * np.arange(math.floor(lo.min() / delta), 1)
    values = np.empty((grid.size + 2, nodes.size))
    values[0], values[-1] = r_lo, r_hi
    values[1:-1] = np.asarray(residual.on_grid(grid), dtype=float)[:, nodes]
    np.copyto(values[1:-1], r_lo, where=grid[:, None] <= lo)
    np.copyto(values[1:-1], r_hi, where=grid[:, None] >= hi)
    finite = np.isfinite(values).all(axis=0)
    sign = np.zeros(values.shape, dtype=np.int8)
    sign[values > tol] = 1
    sign[values < -tol] = -1
    zero = sign == 0
    ambiguous = (zero[1:] & zero[:-1]).any(axis=0)
    # A cell is a + sample followed by a - sample, either adjacent or across one zero sample.
    cell = (sign[:-1] == 1) & (sign[1:] == -1)
    cell[:-1] |= (sign[:-2] == 1) & zero[1:-1] & (sign[2:] == -1)
    crossings = ((sign[:-1] * sign[1:]) == -1).sum(axis=0)
    crossings += (zero[1:-1] & ((sign[:-2] * sign[2:]) == -1)).sum(axis=0)
    first = cell.argmax(axis=0)
    last = cell.shape[0] - 1 - cell[::-1].argmax(axis=0)
    column = np.arange(nodes.size)

    def span(left: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        right = left + 1 + zero[left + 1, column]
        return _positions(left, grid, lo, hi), _positions(right, grid, lo, hi)

    (low_a, low_b), (high_a, high_b) = span(first), span(last)
    spread = 0.5 * (high_a + high_b) - 0.5 * (low_a + low_b)
    a, b = (high_a, high_b) if config.crossing == "upper" else (low_a, low_b)
    failure = np.full(nodes.size, _NOT_RUN, dtype=np.int8)
    failure[ambiguous] = _AMBIGUOUS
    failure[~finite] = _NONFINITE
    return failure, crossings, spread, a, b


def _bisect(
    residual: BoundaryResidual,
    config: SpectralConfig,
    start: np.ndarray,
    nodes: np.ndarray,
    a: np.ndarray,
    b: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Bisect ``[a, b]`` (``R > 0`` at ``a``) for ``nodes``; return ``(roots, failure, iterations)``.

    All nodes share one ``residual.at`` call per step; nodes outside ``nodes`` and nodes that are
    done keep a finite dummy abscissa.  A node stops when ``b - a <= root_x_tol`` and
    ``|R(mid)| <= root_residual_tol``; the root is that ``mid``.  A non-finite residual fails the
    node as ``nonfinite``, ``root_maxiter`` steps without stopping as ``maxiter``.
    """
    left, right = start.copy(), start.copy()
    left[nodes], right[nodes] = a, b
    active = np.zeros(start.size, dtype=bool)
    active[nodes] = True
    roots = np.full(start.size, np.nan)
    failure = np.full(start.size, _NOT_RUN, dtype=np.int8)
    iterations = np.zeros(start.size, dtype=np.int16)
    for step in range(1, config.root_maxiter + 1):
        mid = 0.5 * (left + right)
        r = np.asarray(residual.at(mid), dtype=float)
        broken = active & ~np.isfinite(r)
        failure[broken], iterations[broken] = _NONFINITE, step
        active &= ~broken
        positive = r > 0.0
        left = np.where(active & positive, mid, left)
        right = np.where(active & ~positive, mid, right)
        done = (
            active & (right - left <= config.root_x_tol) & (np.abs(r) <= config.root_residual_tol)
        )
        roots[done], iterations[done] = mid[done], step
        active &= ~done
        if not active.any():
            break
    failure[active], iterations[active] = _MAXITER, config.root_maxiter
    return roots, failure, iterations


def local_boundary(
    residual: BoundaryResidual, predictor: np.ndarray, config: SpectralConfig
) -> BoundarySlice:
    """Find the exercise boundary of every variance node near ``predictor`` (the next boundary).

    Per node, the first half width ``w`` of ``config.root_widths`` with ``R(lo) > tol`` and
    ``R(hi) < -tol`` on ``[predictor - w, min(0, predictor + w)]`` is adopted (``tol`` is
    ``root_residual_tol``).  The opposite signs fail as ``wrong_orientation``, a non-finite end
    as ``nonfinite``, and no accepted width as ``missing_sign_change``.  The adopted bracket is
    scanned once per call on the grid of :func:`scan_spacing`: a non-finite sample fails as
    ``nonfinite`` (before any zero check), two or more consecutive zero samples as
    ``ambiguous_contact``, while a single zero sample counts as a crossing.  The uppermost
    (``crossing="upper"``) or lowermost positive-to-negative cell is bisected; one sign change is
    ``single``, three or more ``multiple_crossings``.  A bisection that meets a non-finite value
    fails as ``nonfinite`` and one that does not stop within ``root_maxiter`` steps as
    ``maxiter``.  Failed nodes have a ``nan`` root.
    """
    start = np.asarray(predictor, dtype=float)
    n = start.size
    tol = config.root_residual_tol
    status = np.full(n, _NOT_RUN, dtype=np.int8)
    lo, hi = np.full(n, np.nan), np.full(n, np.nan)
    r_lo, r_hi = np.full(n, np.nan), np.full(n, np.nan)
    width = np.full(n, np.nan)
    pending = np.ones(n, dtype=bool)
    for half_width in config.root_widths:
        if not pending.any():
            break
        lo_w, hi_w = start - half_width, np.minimum(0.0, start + half_width)
        left = np.asarray(residual.at(lo_w), dtype=float)
        right = np.asarray(residual.at(hi_w), dtype=float)
        finite = np.isfinite(left) & np.isfinite(right)
        take = pending & finite & (left > tol) & (right < -tol)
        wrong = pending & finite & (left < -tol) & (right > tol)
        status[pending & ~finite] = _NONFINITE
        status[wrong] = _WRONG
        lo[take], hi[take], r_lo[take], r_hi[take] = lo_w[take], hi_w[take], left[take], right[take]
        width[take] = half_width
        pending &= finite & ~take & ~wrong
    status[pending] = _MISSING

    roots = np.full(n, np.nan)
    crossings = np.zeros(n, dtype=np.int16)
    spread = np.zeros(n)
    iterations = np.zeros(n, dtype=np.int16)
    adopted = np.flatnonzero(~np.isnan(width))
    if adopted.size:
        failure, count, gap, a, b = _scan_cells(
            residual, config, adopted, lo[adopted], hi[adopted], r_lo[adopted], r_hi[adopted]
        )
        usable = failure == _NOT_RUN
        status[adopted] = failure
        nodes = adopted[usable]
        crossings[nodes], spread[nodes] = count[usable], gap[usable]
        status[nodes] = np.where(count[usable] == 1, _SINGLE, _MULTIPLE)
        if nodes.size:
            roots, stopped, iterations = _bisect(
                residual, config, start, nodes, a[usable], b[usable]
            )
            status[stopped != _NOT_RUN] = stopped[stopped != _NOT_RUN]
    return BoundarySlice(roots, status, crossings, spread, width, iterations)


def _march(
    propagators: Propagators,
    contract: PutContract,
    boundary_next: np.ndarray,
    weight: float,
    q: np.ndarray,
    e: np.ndarray | None,
    d: float,
) -> tuple[np.ndarray, np.ndarray | None, float]:
    """Carry ``Q``, ``E`` and ``D`` from ``t_{n+1}`` to ``t_n`` with one batched matmul.

    ``Q' = exp(-rd dt) M (Q + weight P(boundary_next))``, ``E' = M E`` (skipped if ``e`` is
    ``None``) and ``D' = exp(-rd dt) (rd weight + D)``.
    """
    rate = contract.domestic_rate
    state = np.empty((*q.shape, 1 if e is None else 2), dtype=complex)
    transform = payoff_transform(propagators.omega, propagators.chi, boundary_next, contract)
    state[:, :, 0] = weight * transform + q
    if e is not None:
        state[:, :, 1] = e
    carried = propagators.matrices @ state
    discount = math.exp(-rate * propagators.dt)
    return (
        carried[:, :, 0] * discount,
        None if e is None else carried[:, :, 1],
        discount * (rate * weight + d),
    )


def premium_with_boundary(
    contract: PutContract, propagators: Propagators, log_boundary: np.ndarray, spots: np.ndarray
) -> np.ndarray:
    """Return the ``t_0`` early-exercise premium divided by the strike for a given boundary.

    ``log_boundary`` has shape ``(n_time + 1, n_var)`` (row ``n`` is ``t_n``, row ``n_time`` the
    terminal boundary, row ``0`` is not used) and the result ``(n_spots, n_var)``: the trapezoid
    sum of ``exp(-rd t) E[(rd - rf e^X) 1{X <= boundary}]`` over ``t_1 .. t_N`` with half weights
    at ``t_N`` and none at ``t_0``, started from ``x = log(spots/strike)`` at each variance node.
    """
    spot_array = _spot_array(spots)
    boundary = np.asarray(log_boundary, dtype=float)
    shape = (propagators.n_time + 1, propagators.log_variances.size)
    if boundary.shape != shape:
        raise ValueError(f"log_boundary must have shape {shape}, got {boundary.shape}")
    q = np.zeros(propagators.matrices.shape[:2], dtype=complex)
    d = 0.0
    for n in range(propagators.n_time - 1, -1, -1):
        weight = propagators.dt / 2 if n + 1 == propagators.n_time else propagators.dt
        q, _, d = _march(propagators, contract, boundary[n + 1], weight, q, None, d)
    return d + inverse_sum(propagators, np.log(spot_array / contract.strike), q)


class _SliceResidual:
    """Boundary residual ``R_n`` of one time slice from the damped Fourier sum of ``W_n``.

    ``R_n(x) = (1 - e^x) - [constant + dt (rd - rf e^x)/4 + (1/pi) Re sum_j weights_j
    exp((chi - i omega_j) x) W_j]`` for every variance node; ``constant`` is
    ``exp(-rd (T - t_n)) + D_n``.  ``at`` takes the diagonal (node ``i`` at ``x[i]``), ``on_grid``
    one pair of real matrix products for all nodes.
    """

    def __init__(
        self,
        propagators: Propagators,
        contract: PutContract,
        coefficients: np.ndarray,
        constant: float,
    ) -> None:
        self.omega, self.chi = propagators.omega, propagators.chi
        self.rd, self.rf = contract.domestic_rate, contract.foreign_rate
        self.constant = constant
        self.endpoint = propagators.dt / 4.0
        weighted = propagators.weights[:, None] * coefficients
        self.real, self.imag = (
            np.ascontiguousarray(weighted.real),
            np.ascontiguousarray(weighted.imag),
        )
        self.real_t, self.imag_t = (
            np.ascontiguousarray(self.real.T),
            np.ascontiguousarray(self.imag.T),
        )

    def _residual(self, x: np.ndarray, transform: np.ndarray) -> np.ndarray:
        """Combine payoff, constants, endpoint term and the Fourier sum ``transform``."""
        exercise = np.exp(x)
        flow = self.rd - self.rf * exercise
        return (1.0 - exercise) - (self.constant + self.endpoint * flow + transform / math.pi)

    def at(self, x: np.ndarray) -> np.ndarray:
        """Return the residual of node ``i`` at ``x[i]``."""
        x = np.asarray(x, dtype=float)
        angle = np.multiply.outer(x, self.omega)
        series = (np.cos(angle) * self.real_t + np.sin(angle) * self.imag_t).sum(axis=1)
        return self._residual(x, np.exp(self.chi * x) * series)

    def on_grid(self, grid: np.ndarray) -> np.ndarray:
        """Return the residual of every node at every grid point, shape ``(m, n_var)``."""
        x = np.asarray(grid, dtype=float)[:, None]
        angle = x * self.omega
        damping = np.exp(self.chi * x)
        series = (damping * np.cos(angle)) @ self.real + (damping * np.sin(angle)) @ self.imag
        return self._residual(x, series)


def _status_counts(status: np.ndarray) -> dict[str, int]:
    """Return how many entries of ``status`` carry each ``BOUNDARY_STATUS`` name."""
    return {name: int(np.count_nonzero(status == code)) for name, code in BOUNDARY_STATUS.items()}


def _bounds_diagnostics(
    contract: PutContract, spots: np.ndarray, european: np.ndarray, american: np.ndarray
) -> dict[str, float]:
    """Return the raw price-bound gaps (price/K) over all queried spots; nothing is clipped."""
    moneyness = spots / contract.strike
    discount = math.exp(-contract.domestic_rate * contract.expiry)
    forward = moneyness * math.exp(-contract.foreign_rate * contract.expiry)
    return {
        "american_minus_payoff_min": float(np.min(american - np.maximum(1.0 - moneyness, 0.0))),
        "american_minus_european_min": float(np.min(american - european)),
        "american_minus_strike_max": float(np.max(american - 1.0)),
        "european_lower_gap_min": float(np.min(european - np.maximum(discount - forward, 0.0))),
        "european_upper_gap_max": float(np.max(european - discount)),
    }


def _boundary_failure(
    n: int,
    n_time: int,
    dt: float,
    slice_status: np.ndarray,
    status: np.ndarray,
    log_boundary: np.ndarray,
) -> PricingFailure:
    """Return the failure of time slice ``n``, which is recorded in ``status`` and ``log_boundary``.

    Rows below ``n`` were never computed (``not_run`` / ``nan``); ``last_completed_time_index`` is
    the row above, the last one whose boundary is complete.
    """
    failed = slice_status[np.isin(slice_status, _FAILURE_CODES)]
    names = ", ".join(
        f"{int((failed == code).sum())} node(s) {_STATUS_NAMES[int(code)]}"
        for code in np.unique(failed)
    )
    return PricingFailure(
        "boundary_failure",
        f"no exercise boundary at time index {n} of {n_time} (t = {n * dt:.6g}): {names}",
        {
            "time_index": n,
            "boundary_status": status,
            "log_boundary": log_boundary,
            "status_counts": _status_counts(status),
            "last_completed_time_index": n + 1,
        },
    )


def _zero_expiry(contract: PutContract, spots: np.ndarray, config: SpectralConfig) -> PricingResult:
    """Return the exact payoff at ``T = 0``: no times, variance grid or boundary exist."""
    payoff = np.maximum(1.0 - spots / contract.strike, 0.0)
    diagnostics = {
        "boundary_status": "not_applicable",
        "status_counts": _status_counts(np.empty(0, dtype=np.int8)),
        "multiple_crossings_max_variance": None,
        "max_crossing_spread": 0.0,
        "scan_spacing": scan_spacing(config),
        "max_root_residual": None,
        "generator": None,
        "bounds": _bounds_diagnostics(contract, spots, payoff, payoff),
        "setup_seconds": 0.0,
        "recursion_seconds": 0.0,
        "query_seconds": 0.0,
        "propagator_bytes": 0,
    }
    return PricingResult(
        european=payoff.copy(),
        american=payoff.copy(),
        early_exercise_premium=np.zeros_like(payoff),
        times=np.empty(0),
        log_variances=np.empty(0),
        log_boundary=np.empty((0, 0)),
        boundary_status=np.empty((0, 0), dtype=np.int8),
        diagnostics=diagnostics,
    )


def american_put(
    contract: PutContract,
    model: VarianceModel,
    spots: np.ndarray,
    config: SpectralConfig,
    *,
    propagators: Propagators | None = None,
) -> PricingResult:
    """Return the American and European put prices, premium and boundary at ``t_0`` for ``spots``.

    Prices are divided by the strike and follow the order of ``spots`` (a non-empty 1-D array of
    finite positive values; ``v0`` must lie inside the variance grid, both checked before
    anything is built).  Given ``propagators`` they are checked against the inputs, otherwise
    they are built.  At ``T = 0`` the exact payoff is returned with empty times, variance grid
    and boundary arrays and ``diagnostics["boundary_status"] == "not_applicable"``.

    The recursion runs from ``t_{N-1}`` down to ``t_0``; row ``N`` of ``log_boundary`` is ``0``
    (status ``terminal``).  If any node of a slice fails, a :class:`PricingFailure` with code
    ``boundary_failure`` is raised once the whole slice is recorded.  Its ``details`` hold
    ``time_index``, the arrays ``boundary_status`` and ``log_boundary`` (rows below the failed one
    are ``not_run`` / ``nan``), ``status_counts`` and ``last_completed_time_index`` (the row above).

    At ``t_0`` a node is worth the payoff for ``x <= x*_0(zeta_i)`` and the continuation value
    otherwise (no endpoint term); the nodes and the European leg are interpolated to ``v0``, and
    the premium is their difference.  ``diagnostics`` holds ``boundary_status`` (``"ok"``),
    ``status_counts``, ``multiple_crossings_max_variance`` (``None`` without such a node),
    ``max_crossing_spread``, ``scan_spacing``, ``max_root_residual``, ``generator``, ``bounds``
    (raw gaps to the payoff, European, strike and European bounds over all spots, never clipped)
    and ``setup_seconds`` (build time of the propagators used), ``recursion_seconds``,
    ``query_seconds`` and ``propagator_bytes``.
    """
    spot_array = _spot_array(spots)
    if spot_array.size == 0:
        raise ValueError("spots must not be empty")
    z = variance_grid(config)
    _log_v0_in_grid(z, model.v0)
    if propagators is not None:
        check_propagators(propagators, contract, model, config)
    if contract.expiry == 0.0:
        return _zero_expiry(contract, spot_array, config)
    if propagators is None:
        propagators = build_propagators(contract, model, config)

    n_time, dt, rate = propagators.n_time, propagators.dt, contract.domestic_rate
    s = 1j * propagators.omega - propagators.chi
    inverse_s = (1.0 / (s * (1.0 + s)))[:, None]
    log_boundary = np.full((n_time + 1, z.size), np.nan)
    status = np.full((n_time + 1, z.size), _NOT_RUN, dtype=np.int8)
    log_boundary[n_time], status[n_time] = 0.0, _TERMINAL
    q = np.zeros(propagators.matrices.shape[:2], dtype=complex)
    e: np.ndarray | None = np.ones(propagators.matrices.shape[:2], dtype=complex)
    d = 0.0
    max_residual, max_spread = 0.0, 0.0
    started = time.perf_counter()
    for n in range(n_time - 1, -1, -1):
        weight = dt / 2 if n + 1 == n_time else dt
        q, e, d = _march(propagators, contract, log_boundary[n + 1], weight, q, e, d)
        remaining = math.exp(-rate * (n_time - n) * dt)
        coefficients = remaining * e * inverse_s + q
        residual = _SliceResidual(propagators, contract, coefficients, remaining + d)
        found = local_boundary(residual, log_boundary[n + 1], config)
        status[n], log_boundary[n] = found.status, found.roots
        if np.isin(found.status, _FAILURE_CODES).any():
            raise _boundary_failure(n, n_time, dt, found.status, status, log_boundary)
        max_residual = max(max_residual, float(np.abs(residual.at(found.roots)).max()))
        max_spread = max(max_spread, float(found.spread.max()))
    recursion_seconds = time.perf_counter() - started

    # The loop ended at n = 0: ``coefficients`` is W_0, ``e`` is E_0 and ``d`` is D_0.
    started = time.perf_counter()
    x = np.log(spot_array / contract.strike)
    discount = math.exp(-rate * contract.expiry)
    continuation = discount + d + inverse_sum(propagators, x, coefficients)
    exercised = x[:, None] <= log_boundary[0][None, :]
    american_nodes = np.where(exercised, (1.0 - np.exp(x))[:, None], continuation)
    european_nodes = discount * (1.0 + inverse_sum(propagators, x, e * inverse_s))
    american = interpolate_at_variance(american_nodes, propagators.log_variances, model.v0)
    european = interpolate_at_variance(european_nodes, propagators.log_variances, model.v0)
    bounds = _bounds_diagnostics(contract, spot_array, european, american)
    query_seconds = time.perf_counter() - started

    multiple = (status[:-1] == _MULTIPLE).any(axis=0)
    diagnostics = {
        "boundary_status": "ok",
        "status_counts": _status_counts(status),
        "multiple_crossings_max_variance": float(np.exp(z[multiple].max()))
        if multiple.any()
        else None,
        "max_crossing_spread": max_spread,
        "scan_spacing": scan_spacing(config),
        "max_root_residual": max_residual,
        "generator": generator_diagnostics(contract, model, config),
        "bounds": bounds,
        "setup_seconds": propagators.setup_seconds,
        "recursion_seconds": recursion_seconds,
        "query_seconds": query_seconds,
        "propagator_bytes": propagators.nbytes,
    }
    return PricingResult(
        european=european,
        american=american,
        early_exercise_premium=american - european,
        times=np.linspace(0.0, contract.expiry, n_time + 1),
        log_variances=propagators.log_variances.copy(),
        log_boundary=log_boundary,
        boundary_status=status,
        diagnostics=diagnostics,
    )
