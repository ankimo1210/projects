"""Private RB-F07 single-curve calibration and market-quote risk research.

Rates are simple annual quotes; pillars are continuously compounded zeros.
An exact square calibration solves m(z) = q using analytic derivatives.
The quote gradient solves J.T @ lambda = grad_z rather than bumping quotes.
This v1 has no direct quote dependence, multi-curve or least-squares model.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Quote:
    """Deposit, FRA, par swap or cashflow price, with times in years.

    Deposit: one positive end time. FRA: nonnegative start and later end.
    Swap: increasing positive payment times, accruals measured from zero.
    Bond: payment times and matching cashflows, with price in face units.
    Rate quote steps are 1bp; a bond price step is 1.00 currency unit.
    """

    kind: str
    value: float
    times: tuple[float, ...]
    cashflows: tuple[float, ...] = ()

    def __post_init__(self):
        times = tuple(float(t) for t in self.times)
        cashflows = tuple(float(c) for c in self.cashflows)
        value = float(self.value)
        if self.kind not in {"deposit", "fra", "swap", "bond"}:
            raise ValueError("unknown quote kind")
        if not times or not np.isfinite(times).all() or not np.isfinite(value):
            raise ValueError("quotes require finite values and nonempty times")
        if times[0] < 0 or np.any(np.diff(times) <= 0):
            raise ValueError("quote times must be nonnegative and strictly increasing")
        if self.kind == "fra":
            if len(times) != 2 or 1 + value * (times[1] - times[0]) <= 0:
                raise ValueError("FRA requires two times and a positive discount ratio")
        elif times[0] <= 0:
            raise ValueError("payment times must be positive")
        if self.kind == "deposit" and (len(times) != 1 or 1 + value * times[0] <= 0):
            raise ValueError("deposit requires one time and a positive discount factor")
        if self.kind == "bond":
            if len(cashflows) != len(times) or not np.isfinite(cashflows).all():
                raise ValueError("bond times and finite cashflows must match")
        elif cashflows:
            raise ValueError("cashflows belong to bond quotes")
        object.__setattr__(self, "times", times)
        object.__setattr__(self, "cashflows", cashflows)
        object.__setattr__(self, "value", value)


@dataclass(frozen=True)
class Calibration:
    """Exact fitted zeros, quote Jacobian and diagnostics in input quote order.

    Rank uses J normalized to quote steps and zero-rate bp. condition_number
    is the raw J condition number and is informational, not a rejection gate.
    amplification is max absolute zero-rate bp per one declared quote step.
    """

    times: np.ndarray
    zeros: np.ndarray
    jacobian: np.ndarray
    quote_steps: np.ndarray
    quote_units: tuple[str, ...]
    interpolation: str
    iterations: int
    scaled_residual_norm: float
    rank: int
    condition_number: float
    amplification: float
    solve_relative_residual: float
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class QuoteRisk:
    """Portfolio derivative per raw quote unit and per labeled quote step.

    gradient_method records whether the supplied parameter gradient is
    analytic or a finite-difference approximation; this function does not
    estimate that gradient. No direct dependence of value on q is included.
    """

    per_unit: np.ndarray
    per_step: np.ndarray
    steps: np.ndarray
    units: tuple[str, ...]
    gradient_method: str
    solve_relative_residual: float


def _curve_inputs(pillar_times, zeros):
    times = np.asarray(pillar_times, dtype=float)
    z = np.asarray(zeros)
    if (
        times.ndim != 1
        or times.size == 0
        or not np.isfinite(times).all()
        or times[0] <= 0
        or np.any(np.diff(times) <= 0)
    ):
        raise ValueError("pillars must be finite, positive and strictly increasing")
    if z.shape != times.shape or not np.isfinite(z).all():
        raise ValueError("finite zeros must match the pillar dimension")
    return times, z


def _zero_weights(payment_times, pillars, interpolation):
    if interpolation not in {"zero_linear", "logdf_linear"}:
        raise ValueError("unknown interpolation")
    weights = np.zeros((payment_times.size, pillars.size))
    for row, t in enumerate(payment_times):
        if t <= pillars[0]:
            weights[row, 0] = 1
        elif t >= pillars[-1]:
            weights[row, -1] = 1
        else:
            right = np.searchsorted(pillars, t)
            left = right - 1
            alpha = (t - pillars[left]) / (pillars[right] - pillars[left])
            weights[row, left], weights[row, right] = 1 - alpha, alpha
            if interpolation == "logdf_linear":
                weights[row] *= pillars / t
    return weights


def discount_factors(payment_times, pillar_times, zeros, *, interpolation="zero_linear"):
    """Return discount factors and analytic gradients with respect to zeros.

    Both interpolation choices extrapolate flat zero rates. Within pillars,
    logdf_linear linearly interpolates t*z(t), so forwards are piecewise
    constant. Complex zeros are supported only for smooth-kernel validation.
    """
    pillars, z = _curve_inputs(pillar_times, zeros)
    times = np.asarray(payment_times, dtype=float)
    if times.ndim != 1 or not np.isfinite(times).all() or np.any(times < 0):
        raise ValueError("cashflow times must be finite and nonnegative")
    loading = times[:, None] * _zero_weights(times, pillars, interpolation)
    dfs = np.exp(-(loading @ z))
    return dfs, -dfs[:, None] * loading


def model_quotes(quotes, pillar_times, zeros, *, interpolation="zero_linear"):
    """Return model quotes and analytic dm/dz in the original quote order."""
    pillars, z = _curve_inputs(pillar_times, zeros)
    values, rows = [], []
    for quote in quotes:
        dfs, gradients = discount_factors(quote.times, pillars, z, interpolation=interpolation)
        if quote.kind == "deposit":
            tau = quote.times[0]
            value = (1 / dfs[0] - 1) / tau
            gradient = -gradients[0] / (tau * dfs[0] ** 2)
        elif quote.kind == "fra":
            tau = quote.times[1] - quote.times[0]
            value = (dfs[0] / dfs[1] - 1) / tau
            gradient = (gradients[0] / dfs[1] - dfs[0] * gradients[1] / dfs[1] ** 2) / tau
        elif quote.kind == "swap":
            accruals = np.diff((0.0, *quote.times))
            annuity = accruals @ dfs
            annuity_gradient = accruals @ gradients
            value = (1 - dfs[-1]) / annuity
            gradient = (-gradients[-1] * annuity - (1 - dfs[-1]) * annuity_gradient) / annuity**2
        else:
            value = np.dot(quote.cashflows, dfs)
            gradient = np.asarray(quote.cashflows) @ gradients
        values.append(value)
        rows.append(gradient)
    return np.asarray(values), np.asarray(rows)


def _rank(jacobian, steps):
    normalized = jacobian * 1e-4 / steps[:, None]
    if not np.isfinite(normalized).all():
        raise ValueError("nonfinite calibration Jacobian")
    singular_values = np.linalg.svd(normalized, compute_uv=False)
    threshold = normalized.shape[0] * np.finfo(float).eps * singular_values[0]
    rank = int(np.sum(singular_values > threshold))
    if rank != normalized.shape[0]:
        raise ValueError("calibration Jacobian is numerically rank deficient or singular")
    return rank


def _solve(matrix, rhs):
    try:
        solution = np.linalg.solve(matrix, rhs)
    except np.linalg.LinAlgError as exc:
        raise ValueError("singular calibration solve") from exc
    if not np.isfinite(solution).all():
        raise ValueError("nonfinite calibration solve")
    scale = np.linalg.norm(matrix, np.inf) * np.linalg.norm(solution, np.inf) + np.linalg.norm(
        rhs, np.inf
    )
    residual = np.linalg.norm(matrix @ solution - rhs, np.inf)
    return solution, float(residual / scale if scale else 0.0)


def calibrate(
    quotes,
    *,
    pillar_times=None,
    interpolation="zero_linear",
    initial_zeros=None,
    tolerance=1e-10,
    max_iterations=40,
):
    """Fit square market equations using damped Newton and analytic Jacobian.

    Default pillars are sorted quote maturities; quote ordering is preserved.
    Explicit pillars support the weak-coverage experiment, not overdetermined
    calibration. tolerance is residual / quote-step infinity norm (default
    1e-14 absolute for rates, 1e-10 for prices). Raises ValueError for invalid
    dimensions/rank and RuntimeError for nonconvergence. No partial fit returns.
    """
    quotes = tuple(quotes)
    if not quotes or max_iterations < 1 or not np.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("nonempty quotes, positive tolerance and iterations are required")
    times = (
        np.array(sorted(q.times[-1] for q in quotes))
        if pillar_times is None
        else np.asarray(pillar_times, dtype=float)
    )
    zeros = (
        np.full(len(quotes), 0.03)
        if initial_zeros is None
        else np.asarray(initial_zeros, dtype=float).copy()
    )
    times, zeros = _curve_inputs(times, zeros)
    if times.size != len(quotes):
        raise ValueError("square calibration requires one quote per pillar")
    steps = np.array([1.0 if q.kind == "bond" else 1e-4 for q in quotes])
    units = tuple(
        "currency / price 1.00" if q.kind == "bond" else "currency / quote 1bp" for q in quotes
    )
    targets = np.array([q.value for q in quotes])
    for iteration in range(max_iterations + 1):
        with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
            values, jacobian = model_quotes(quotes, times, zeros, interpolation=interpolation)
        rank = _rank(jacobian, steps)
        residual = values - targets
        norm = float(np.max(np.abs(residual / steps)))
        if not np.isfinite(norm):
            raise RuntimeError("Newton did not converge: nonfinite quote residual")
        if norm <= tolerance:
            response, solve_residual = _solve(jacobian, np.diag(steps))
            amplification = float(np.max(np.abs(response / 1e-4)))
            warnings = (
                ("zero-rate amplification exceeds 10 bp per quote step",)
                if amplification > 10
                else ()
            )
            return Calibration(
                times.copy(),
                zeros.copy(),
                jacobian,
                steps,
                units,
                interpolation,
                iteration,
                norm,
                rank,
                float(np.linalg.cond(jacobian)),
                amplification,
                solve_residual,
                warnings,
            )
        if iteration == max_iterations:
            break
        delta, _ = _solve(jacobian, -residual)
        accepted = False
        for backtrack in range(24):
            candidate = zeros + delta * 0.5**backtrack
            with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
                candidate_values, _ = model_quotes(
                    quotes, times, candidate, interpolation=interpolation
                )
            candidate_norm = np.max(np.abs((candidate_values - targets) / steps))
            if np.isfinite(candidate_norm) and candidate_norm < norm:
                zeros, accepted = candidate, True
                break
        if not accepted:
            raise RuntimeError("Newton did not converge: line search failed")
    raise RuntimeError(f"Newton did not converge within {max_iterations} iterations")


def cashflow_value(calibration, payment_times, cashflows):
    """Discount signed cashflows and return value plus analytic zero gradient."""
    flows = np.asarray(cashflows, dtype=float)
    dfs, gradients = discount_factors(
        payment_times,
        calibration.times,
        calibration.zeros,
        interpolation=calibration.interpolation,
    )
    if flows.shape != dfs.shape or not np.isfinite(flows).all():
        raise ValueError("finite cashflows must match payment times")
    return float(flows @ dfs), flows @ gradients


def receiver_swap_value(calibration, notional, fixed_rate, payment_times):
    """Receive-fixed swap at reset: N*(fixed annuity + final DF - 1)."""
    times = tuple(payment_times)
    quote = Quote("swap", fixed_rate, times)
    if not np.isfinite(notional):
        raise ValueError("notional must be finite")
    cashflows = notional * fixed_rate * np.diff((0.0, *quote.times))
    cashflows[-1] += notional
    value, gradient = cashflow_value(calibration, quote.times, cashflows)
    return value - notional, gradient


def quote_sensitivity(calibration, grad_theta, *, gradient_method="analytic"):
    """Solve the adjoint for quote risk; rates per bp, bond prices per 1.00.

    grad_theta is currency per one absolute zero-rate change. A supplied
    finite-difference gradient must be labeled by the caller; its provenance
    cannot be inferred from the supplied numbers.
    Direct quote dependence of portfolio value is outside this v1 scope.
    """
    gradient = np.asarray(grad_theta, dtype=float)
    if gradient.shape != calibration.zeros.shape or not np.isfinite(gradient).all():
        raise ValueError("finite portfolio gradient must match the pillars")
    if gradient_method not in {"analytic", "finite_difference"}:
        raise ValueError("unknown gradient method")
    _rank(calibration.jacobian, calibration.quote_steps)
    per_unit, residual = _solve(calibration.jacobian.T, gradient)
    return QuoteRisk(
        per_unit,
        per_unit * calibration.quote_steps,
        calibration.quote_steps.copy(),
        calibration.quote_units,
        gradient_method,
        residual,
    )
