"""Independent 3/2 finite-difference reference for the DSINC American put.

Nothing here comes from the spectral solver: the module imports only the input contracts
(``PutContract``, ``VarianceModel``) and solves the backward equation for the put price per unit
strike in ``x = log(S/K)`` and ``zeta = log v`` on uniform grids,

    V_tau = (rd - rf - v/2) V_x + v/2 V_xx + b V_zeta + a V_zeta_zeta + c V_x_zeta - rd V,

where ``tau`` is the time to maturity and the 3/2 coefficients are ``v = e^zeta``,
``b = kappa*theta - (kappa + xi^2/2) v``, ``a = xi^2 v/2`` and ``c = rho*xi*v`` (Ito on
``dv = kappa v (theta - v) dt + xi v^(3/2) dW``).  Other coefficients can be passed in, which is how
the tests check the machinery against Black-Scholes-Merton and the CRR tree.

All derivatives are central differences.  The x ends are Dirichlet (the deep in-the-money value on
the left, 0 on the right); the zeta ends reflect through ghost nodes (``V_zeta = 0``, so the drift
and the mixed term drop out and ``V_zeta_zeta = 2 (V_neighbour - V_end) / h^2``).  Time stepping
is four implicit-Euler half steps (the Rannacher start) followed by Crank-Nicolson; both use the
matrix ``I - dtau/2 A`` of one sparse LU.  The American constraint uses the Ikonen-Toivanen
splitting with the multiplier ``lam`` of ``V >= payoff``.  Prices come from not-a-knot cubic
splines in zeta (at ``log v0``) and then in x; nothing is extrapolated.  Units follow the rest of
the research: years, continuously compounded rates, variance rates, prices divided by the strike.
"""

import math
import numbers
import resource
import time
from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp
from hullkit._dsinc_types import PutContract, VarianceModel
from scipy.interpolate import CubicSpline
from scipy.sparse.linalg import SuperLU, splu

EXERCISES = ("european", "american")
EULER_HALF_STEPS = 4  # implicit-Euler half steps before Crank-Nicolson (Rannacher start)
CONTACT_MULTIPLIER = 1e-10  # a node is in contact when its multiplier exceeds this ...
CONTACT_GAP = 1e-8  # ... and its value is within this of the payoff
VARIANCE_TOLERANCE = 1e-12  # slack for log v0 against the zeta bounds


def _real(name: str, value: object) -> float:
    """Return ``value`` as a finite float; bool, non-real and non-finite are rejected."""
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise ValueError(f"{name} must be a real number, got {value!r}")
    try:
        number = float(value)
    except OverflowError:
        number = math.inf
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return number


def _integer(name: str, value: object, minimum: int) -> int:
    """Return ``value`` as an int >= ``minimum``; bool and non-integers are rejected."""
    if isinstance(value, bool) or not isinstance(value, numbers.Integral):
        raise ValueError(f"{name} must be an int, got {value!r}")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value!r}")
    return int(value)


def _bounds(name: str, value: object) -> tuple[float, float]:
    """Return ``value`` (a list or tuple) as an ascending ``(low, high)`` pair of finite floats."""
    try:
        items = tuple(value)
    except TypeError:
        raise ValueError(f"{name} must be a (low, high) pair, got {value!r}") from None
    if len(items) != 2:
        raise ValueError(f"{name} must be a (low, high) pair, got {value!r}")
    low, high = (_real(f"{name}[{i}]", item) for i, item in enumerate(items))
    if not low < high:
        raise ValueError(f"{name} must be ascending, got {value!r}")
    return low, high


def _grid(name: str, grid: object, minimum: int) -> tuple[np.ndarray, float]:
    """Return a finite, strictly increasing, uniform 1-D grid as floats together with its step."""
    nodes = np.asarray(grid, dtype=float)
    if nodes.ndim != 1 or nodes.size < minimum or not np.all(np.isfinite(nodes)):
        raise ValueError(f"{name} must be a finite 1-D array of at least {minimum} nodes")
    step = (nodes[-1] - nodes[0]) / (nodes.size - 1)
    if not step > 0.0 or not np.allclose(np.diff(nodes), step, rtol=1e-8, atol=0.0):
        raise ValueError(f"{name} must be strictly increasing and uniformly spaced")
    return nodes, step


@dataclass(frozen=True)
class FDConfig:
    """Grid sizes, domain and outputs of one finite-difference solve.

    ``n_x`` x nodes on ``log_spot_bounds`` and ``n_var`` zeta nodes on ``log_var_bounds`` (both
    ends included), ``n_time`` time steps of ``T/n_time``.  The x domain has to contain the strike
    (``x = 0``) strictly inside.  ``exercises`` is a non-empty subset of ``european`` and
    ``american``; ``record_boundary`` stores the contact edge of every ``zeta`` row at every
    time level and needs ``american``.  Lists (from JSON) are stored as tuples.
    """

    n_x: int
    n_var: int
    n_time: int
    log_spot_bounds: tuple[float, float]
    log_var_bounds: tuple[float, float]
    exercises: tuple[str, ...] = ("european", "american")
    record_boundary: bool = False

    def __post_init__(self) -> None:
        for name, minimum in (("n_x", 5), ("n_var", 4), ("n_time", 3)):
            object.__setattr__(self, name, _integer(name, getattr(self, name), minimum))
        for name in ("log_spot_bounds", "log_var_bounds"):
            object.__setattr__(self, name, _bounds(name, getattr(self, name)))
        low, high = self.log_spot_bounds
        if not low < 0.0 < high:
            raise ValueError(
                f"log_spot_bounds must contain the strike (x = 0) strictly inside, got {(low, high)!r}"
            )
        if isinstance(self.exercises, str):
            raise ValueError(f"exercises must be a tuple of names, got {self.exercises!r}")
        try:
            exercises = tuple(self.exercises)
        except TypeError:
            raise ValueError(
                f"exercises must be a tuple of names, got {self.exercises!r}"
            ) from None
        if not exercises or any(item not in EXERCISES for item in exercises):
            raise ValueError(
                f"exercises must be a non-empty subset of {EXERCISES}, got {exercises!r}"
            )
        if len(set(exercises)) != len(exercises):
            raise ValueError(f"exercises must not repeat an entry, got {exercises!r}")
        object.__setattr__(self, "exercises", exercises)
        if not isinstance(self.record_boundary, bool):
            raise ValueError(f"record_boundary must be a bool, got {self.record_boundary!r}")
        if self.record_boundary and "american" not in exercises:
            raise ValueError("record_boundary needs 'american' in exercises")


@dataclass(frozen=True)
class FDCoefficients:
    """Coefficients of the operator along the zeta grid, each of shape ``(n_var,)``.

    ``variance`` is the ``v`` of the x terms, and ``var_drift``, ``var_diffusion`` and ``cross``
    multiply ``V_zeta``, ``V_zeta_zeta`` and ``V_x_zeta``.
    """

    variance: np.ndarray
    var_drift: np.ndarray
    var_diffusion: np.ndarray
    cross: np.ndarray


def three_halves_coefficients(model: VarianceModel, log_variances: np.ndarray) -> FDCoefficients:
    """Return the 3/2 coefficients on the zeta grid ``log_variances``.

    With ``v = e^zeta``: ``variance = v``, ``var_drift = kappa*theta - (kappa + xi^2/2) v``,
    ``var_diffusion = xi^2 v/2`` and ``cross = rho*xi*v``.  ``model`` has to be of kind
    ``three_halves``; anything else raises ValueError.
    """
    if model.kind != "three_halves":
        raise ValueError(f"the 3/2 coefficients need kind 'three_halves', got {model.kind!r}")
    v = np.exp(np.asarray(log_variances, dtype=float))
    return FDCoefficients(
        variance=v,
        var_drift=model.kappa * model.theta - (model.kappa + 0.5 * model.xi**2) * v,
        var_diffusion=0.5 * model.xi**2 * v,
        cross=model.rho * model.xi * v,
    )


def assemble_operator(
    contract: PutContract,
    coefficients: FDCoefficients,
    log_spots: np.ndarray,
    log_variances: np.ndarray,
) -> tuple[sp.csc_matrix, np.ndarray, np.ndarray]:
    """Return ``(A, left, right)``, the central-difference operator on the interior x nodes.

    The unknowns are ``V[i, j]`` for the interior x nodes ``i = 1..n_x-2`` and every zeta node
    ``j``, ordered ``(i-1)*n_var + j`` (zeta innermost).  ``A`` holds the whole operator including
    ``-rd``.  ``left`` and ``right`` are the vectors, one entry per unknown, of the coefficients
    that multiply the boundary values ``V[0, :]`` and ``V[-1, :]``: ``left`` is non-zero in the
    first x row only and ``right`` in the last.  The left value does not depend on zeta, so the
    mixed-term contributions from it cancel and are left out; the right value is 0 in this
    reference, so only ``left`` is used for stepping.  At the zeta ends the drift and the mixed term
    vanish and the second derivative reflects through a ghost node.
    """
    x, dx = _grid("log_spots", log_spots, 3)
    z, h = _grid("log_variances", log_variances, 2)
    n_in, n_var = x.size - 2, z.size
    v, drift, diffusion, mixed = (
        np.asarray(getattr(coefficients, name), dtype=float)
        for name in ("variance", "var_drift", "var_diffusion", "cross")
    )
    for name, array in (
        ("variance", v),
        ("var_drift", drift),
        ("var_diffusion", diffusion),
        ("cross", mixed),
    ):
        if array.shape != (n_var,) or not np.all(np.isfinite(array)):
            raise ValueError(f"coefficients.{name} must be finite with shape ({n_var},)")
    rd, rf = contract.domestic_rate, contract.foreign_rate

    mu = rd - rf - 0.5 * v
    x_up = mu / (2.0 * dx) + 0.5 * v / dx**2  # multiplies V[i+1, j]
    x_down = -mu / (2.0 * dx) + 0.5 * v / dx**2  # multiplies V[i-1, j]
    z_up = drift / (2.0 * h) + diffusion / h**2  # multiplies V[i, j+1]
    z_down = -drift / (2.0 * h) + diffusion / h**2  # multiplies V[i, j-1]
    # Ghost reflection at the zeta ends: V_zeta = 0 and V_zeta_zeta = 2 (V_neighbour - V_end) / h^2.
    z_up[0] = 2.0 * diffusion[0] / h**2
    z_down[-1] = 2.0 * diffusion[-1] / h**2
    diagonal = -v / dx**2 - 2.0 * diffusion / h**2 - rd
    cross = mixed / (4.0 * dx * h)

    rows, cols, data = [], [], []

    def add(di: int, dj: int, coefficient: np.ndarray, j_first: int, j_last: int) -> None:
        """Add ``coefficient[j] * V[i+di, j+dj]`` to the equation of every ``(i, j)`` in range."""
        i = np.arange(max(0, -di), n_in - max(0, di))
        j = np.arange(j_first, j_last + 1)
        ii, jj = np.meshgrid(i, j, indexing="ij")
        rows.append((ii * n_var + jj).ravel())
        cols.append(((ii + di) * n_var + jj + dj).ravel())
        data.append(np.broadcast_to(coefficient[j], ii.shape).ravel())

    add(0, 0, diagonal, 0, n_var - 1)
    add(1, 0, x_up, 0, n_var - 1)
    add(-1, 0, x_down, 0, n_var - 1)
    add(0, 1, z_up, 0, n_var - 2)
    add(0, -1, z_down, 1, n_var - 1)
    for di, dj, sign in ((1, 1, 1.0), (1, -1, -1.0), (-1, 1, -1.0), (-1, -1, 1.0)):
        add(di, dj, sign * cross, 1, n_var - 2)  # interior zeta rows only

    size = n_in * n_var
    operator = sp.coo_matrix(
        (np.concatenate(data), (np.concatenate(rows), np.concatenate(cols))), shape=(size, size)
    ).tocsc()
    operator.eliminate_zeros()  # e.g. rho = 0 or a constant-variance fixture: no explicit zeros in the LU
    left, right = np.zeros(size), np.zeros(size)
    left[:n_var] = x_down
    right[-n_var:] = x_up
    return operator, left, right


@dataclass(frozen=True)
class FDResult:
    """Prices, grids, contact edge and costs of one finite-difference solve.

    ``european`` and ``american`` are price divided by the strike at the input spots (``None``
    when that style was not asked for).  ``contact_edge`` has shape ``(n_time+1, n_var)``: row
    ``k`` is the calendar time ``t_k = k*T/n_time`` and holds, for every zeta node, the largest log
    spot ``x`` in contact with the payoff; ``NaN`` where there is no contact and in row
    ``n_time`` (maturity, not recorded); ``None`` unless ``record_boundary``.  ``complementarity``
    is measured at the last American step (``min_payoff_gap``, ``min_multiplier``,
    ``max_complementarity_product``, ``solve_residual``) and is empty without ``american``.
    ``setup_seconds`` covers the operator and the LU, ``solve_seconds`` each style's stepping and
    interpolation, ``lu_nnz`` is ``L.nnz + U.nnz`` and ``maxrss_bytes`` the peak RSS of the process.
    """

    european: np.ndarray | None
    american: np.ndarray | None
    log_spots: np.ndarray
    log_variances: np.ndarray
    contact_edge: np.ndarray | None
    complementarity: dict
    setup_seconds: float
    solve_seconds: dict[str, float]
    lu_nnz: int
    maxrss_bytes: int


@dataclass(frozen=True)
class _Problem:
    """Grids, operator and the single LU of ``I - dtau/2 A`` shared by both exercise styles."""

    contract: PutContract
    config: FDConfig
    log_spots: np.ndarray
    log_variances: np.ndarray
    operator: sp.csc_matrix
    left: np.ndarray
    system: sp.csc_matrix
    lu: SuperLU


def _left_value(american: bool, x_min: float, rd: float, rf: float, tau: float) -> float:
    """Return the Dirichlet value (price/K) at the left end of the x domain at time ``tau``."""
    if american:
        return 1.0 - math.exp(x_min)
    return max(math.exp(-rd * tau) - math.exp(x_min) * math.exp(-rf * tau), 0.0)


def _contact_edge(
    values: np.ndarray,
    multiplier: np.ndarray,
    payoff: np.ndarray,
    x_interior: np.ndarray,
    n_var: int,
) -> np.ndarray:
    """Return, per zeta node, the largest interior x in contact (NaN without contact)."""
    in_contact = (multiplier > CONTACT_MULTIPLIER) & (np.abs(values - payoff) <= CONTACT_GAP)
    contact = in_contact.reshape(-1, n_var)
    last = contact.shape[0] - 1 - np.argmax(contact[::-1], axis=0)
    return np.where(contact.any(axis=0), x_interior[last], np.nan)


def _march(
    problem: _Problem, american: bool, record: bool
) -> tuple[np.ndarray, dict, np.ndarray | None]:
    """Step from the payoff to maturity; return ``(values, complementarity, contact_edge)``.

    Four implicit-Euler half steps of ``dtau/2`` and then ``n_time - 2`` Crank-Nicolson steps of
    ``dtau`` cover ``T = n_time*dtau``.  After the 2nd and 4th half step and after every
    Crank-Nicolson step the elapsed time is a whole number ``m`` of ``dtau`` (``m = 1, 2, ...,
    n_time``); the contact edge of that level goes to calendar row ``n_time - m``.
    """
    config, contract = problem.config, problem.contract
    rd, rf = contract.domestic_rate, contract.foreign_rate
    n_time, n_var = config.n_time, config.n_var
    x_min, x_interior = problem.log_spots[0], problem.log_spots[1:-1]
    dtau = contract.expiry / n_time

    def left_value(half_steps: int) -> float:
        """Return the left Dirichlet value after ``half_steps`` half steps of ``dtau/2``."""
        return _left_value(american, x_min, rd, rf, contract.expiry * half_steps / (2 * n_time))

    payoff = np.repeat(np.maximum(1.0 - np.exp(x_interior), 0.0), n_var)
    values, multiplier = payoff.copy(), np.zeros_like(payoff)
    edge = np.full((n_time + 1, n_var), np.nan) if record else None
    complementarity = {}
    n_steps = EULER_HALF_STEPS + (n_time - 2)
    for step in range(n_steps):
        euler = step < EULER_HALF_STEPS
        size = dtau / 2.0 if euler else dtau  # the step size k
        done = step + 1 if euler else 2 * step - 2  # half steps of dtau/2 elapsed after this step
        if euler:
            rhs = values + size * problem.left * left_value(done)
        else:
            boundary = left_value(done - 2) + left_value(done)
            rhs = values + 0.5 * size * (problem.operator @ values + problem.left * boundary)
        if american:
            lagged = multiplier
            tilde = problem.lu.solve(rhs + size * lagged)  # the intermediate V~ of the splitting
            values = np.maximum(tilde - size * lagged, payoff)
            multiplier = np.maximum(0.0, lagged + (payoff - tilde) / size)
            if step == n_steps - 1:
                residual = np.max(np.abs(problem.system @ tilde - (rhs + size * lagged)))
                gap = values - payoff
                complementarity = {
                    "min_payoff_gap": float(gap.min()),
                    "min_multiplier": float(multiplier.min()),
                    "max_complementarity_product": float((multiplier * gap).max()),
                    "solve_residual": float(residual / max(1.0, np.max(np.abs(rhs)))),
                }
            if record and done % 2 == 0:
                level = done // 2
                edge[n_time - level] = _contact_edge(values, multiplier, payoff, x_interior, n_var)
        else:
            values = problem.lu.solve(rhs)
    return values, complementarity, edge


def _prices(
    problem: _Problem,
    values: np.ndarray,
    american: bool,
    log_v0: float,
    log_query: np.ndarray,
) -> np.ndarray:
    """Return price/K at ``log_v0`` and the log spots, by splines over the grid with its ends.

    The left row holds the Dirichlet value at maturity ``T`` and the right row 0.  The spline runs
    along zeta first (evaluated at ``log_v0``), then along x.
    """
    config, contract = problem.config, problem.contract
    full = np.zeros((config.n_x, config.n_var))
    full[1:-1] = values.reshape(config.n_x - 2, config.n_var)
    full[0] = _left_value(
        american,
        problem.log_spots[0],
        contract.domestic_rate,
        contract.foreign_rate,
        contract.expiry,
    )
    along_variance = CubicSpline(problem.log_variances, full, axis=1, bc_type="not-a-knot")(log_v0)
    return CubicSpline(problem.log_spots, along_variance, bc_type="not-a-knot")(log_query)


def _check_inputs(
    contract: PutContract,
    model: VarianceModel,
    spots: np.ndarray,
    config: FDConfig,
    coefficients: FDCoefficients | None,
) -> tuple[np.ndarray, float]:
    """Validate the arguments of ``reference_put``; return ``(log(S/K), log v0)``."""
    if contract.expiry <= 0.0:
        raise ValueError(
            f"expiry must be > 0 for the finite-difference reference, got {contract.expiry!r}"
        )
    if coefficients is None and model.kind != "three_halves":
        raise ValueError(
            f"without coefficients the model has to be 'three_halves', got {model.kind!r}"
        )
    try:
        query = np.asarray(spots, dtype=float)
    except (TypeError, ValueError):
        query = np.empty((0, 0))  # reported below with the other malformed spots
    if query.ndim != 1 or query.size == 0 or not np.all(np.isfinite(query)) or np.any(query <= 0.0):
        raise ValueError(
            f"spots must be a non-empty 1-D array of positive finite numbers, got {spots!r}"
        )
    log_query = np.log(query / contract.strike)
    x_low, x_high = config.log_spot_bounds
    if log_query.min() < x_low or log_query.max() > x_high:
        raise ValueError(
            f"log(S/K) must lie inside the x bounds {(x_low, x_high)!r}, got {log_query!r}"
        )
    z_low, z_high = config.log_var_bounds
    log_v0 = math.log(model.v0)
    if not z_low - VARIANCE_TOLERANCE <= log_v0 <= z_high + VARIANCE_TOLERANCE:
        raise ValueError(f"log v0={log_v0!r} must lie inside the zeta bounds {(z_low, z_high)!r}")
    return log_query, log_v0


def reference_put(
    contract: PutContract,
    model: VarianceModel,
    spots: np.ndarray,
    config: FDConfig,
    *,
    coefficients: FDCoefficients | None = None,
) -> FDResult:
    """Price the put at ``spots`` (stock prices, as many as given) by finite differences.

    The prices are per unit strike and at ``model.v0``.  Without ``coefficients`` the model has to
    be ``three_halves``.  ``contract.expiry`` has to be positive, ``spots`` a non-empty 1-D array of
    positive finite numbers with every ``log(S/K)`` inside ``log_spot_bounds``, and ``log v0``
    inside ``log_var_bounds`` (1e-12 slack), so that nothing is extrapolated; anything else raises
    ValueError.  One operator and one LU serve every style in ``config.exercises``.
    """
    log_query, log_v0 = _check_inputs(contract, model, spots, config, coefficients)

    started = time.perf_counter()
    x = np.linspace(*config.log_spot_bounds, config.n_x)
    z = np.linspace(*config.log_var_bounds, config.n_var)
    if coefficients is None:
        coefficients = three_halves_coefficients(model, z)
    operator, left, _ = assemble_operator(contract, coefficients, x, z)
    dtau = contract.expiry / config.n_time
    system = (sp.identity(operator.shape[0], format="csc") - 0.5 * dtau * operator).tocsc()
    lu = splu(system)
    lu_nnz = int(lu.L.nnz) + int(lu.U.nnz)  # one factor at a time keeps the temporary copy small
    setup_seconds = time.perf_counter() - started
    problem = _Problem(contract, config, x, z, operator, left, system, lu)

    prices, solve_seconds, complementarity, edge = {}, {}, {}, None
    for style in config.exercises:
        american = style == "american"
        started = time.perf_counter()
        values, measured, boundary = _march(problem, american, american and config.record_boundary)
        prices[style] = _prices(problem, values, american, log_v0, log_query)
        solve_seconds[style] = time.perf_counter() - started
        if american:
            complementarity, edge = measured, boundary
    return FDResult(
        european=prices.get("european"),
        american=prices.get("american"),
        log_spots=x,
        log_variances=z,
        contact_edge=edge,
        complementarity=complementarity,
        setup_seconds=setup_seconds,
        solve_seconds=solve_seconds,
        lu_nnz=lu_nnz,
        maxrss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,  # Linux: KiB
    )
