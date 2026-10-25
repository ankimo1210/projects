"""Independent log-spot/log-variance finite-difference obstacle reference.

Only input types are shared with DSINC.  The discounted backward generator is
derived directly from the SDE.  Four backward-Euler half-steps precede CN;
American exercise uses the Ikonen--Toivanen multiplier splitting.
"""

from __future__ import annotations

import hashlib
import json
import resource
from dataclasses import asdict, dataclass
from itertools import pairwise
from time import perf_counter
from typing import Literal

import numpy as np
from hullkit._dsinc_types import PricingFailure, PutContract
from scipy import sparse
from scipy.interpolate import CubicSpline
from scipy.optimize import brentq
from scipy.sparse.linalg import splu


@dataclass(frozen=True)
class FDConfig:
    """Uniform grids, full time steps and exercise style; bounds are logarithms."""

    n_x: int
    n_var: int
    n_time: int
    log_spot_bounds: tuple[float, float]
    log_var_bounds: tuple[float, float]
    exercise: Literal["european", "american"]

    def __post_init__(self):
        for name, minimum in (("n_x", 5), ("n_var", 4), ("n_time", 2)):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise ValueError(f"{name} must be an integer >= {minimum}")
        for name in ("log_spot_bounds", "log_var_bounds"):
            bounds = getattr(self, name)
            if len(bounds) != 2 or not np.all(np.isfinite(bounds)) or bounds[0] >= bounds[1]:
                raise ValueError(f"invalid {name}")
        if self.exercise not in ("european", "american"):
            raise ValueError("invalid exercise style")


@dataclass(frozen=True)
class FDResult:
    """Small prices/boundary evidence; the full FD surface is never retained."""

    prices: np.ndarray
    x: np.ndarray
    log_variances: np.ndarray
    times: np.ndarray
    boundary_brackets: np.ndarray
    boundary_valid: np.ndarray
    diagnostics: dict
    config: FDConfig
    contract: PutContract
    problem_hash: str


def _sde_coefficients(contract, model, z):
    v = np.exp(z)
    return {
        "variance": v,
        "x_drift": contract.domestic_rate - contract.foreign_rate - v / 2,
        "z_variance": model.xi**2 * v,
        "z_drift": model.kappa * model.theta - (model.kappa + model.xi**2 / 2) * v,
        "cross": model.rho * model.xi * v,
    }


def _assemble_operator(contract, x, z, coefficients):
    """Return interior generator and the two omitted Dirichlet boundary blocks."""
    nx, nz = len(x) - 2, len(z)
    hx, hz = x[1] - x[0], z[1] - z[0]
    dx = sparse.diags([-np.ones(nx - 1), np.ones(nx - 1)], [-1, 1]) / (2 * hx)
    dxx = sparse.diags([np.ones(nx - 1), -2 * np.ones(nx), np.ones(nx - 1)], [-1, 0, 1]) / hx**2
    dz = sparse.diags([-np.ones(nz - 1), np.ones(nz - 1)], [-1, 1], format="lil") / (2 * hz)
    dzz = (
        sparse.diags([np.ones(nz - 1), -2 * np.ones(nz), np.ones(nz - 1)], [-1, 0, 1], format="lil")
        / hz**2
    )
    # Reflecting ghost nodes: zero first derivative, doubled inward curvature.
    dz[0, :] = 0
    dz[-1, :] = 0
    dzz[0, 1] = 2 / hz**2
    dzz[-1, -2] = 2 / hz**2
    dz, dzz = dz.tocsr(), dzz.tocsr()
    v = np.asarray(coefficients["variance"])
    bx = np.asarray(coefficients["x_drift"])
    cross = sparse.diags(coefficients["cross"]) @ dz
    az = (
        sparse.diags(np.asarray(coefficients["z_variance"]) / 2) @ dzz
        + sparse.diags(coefficients["z_drift"]) @ dz
        - contract.domestic_rate * sparse.eye(nz)
    )
    matrix = (
        sparse.kron(dxx, sparse.diags(v / 2))
        + sparse.kron(dx, sparse.diags(bx))
        + sparse.kron(sparse.eye(nx), az)
        + sparse.kron(dx, cross)
    ).tocsr()
    left = sparse.diags(v / (2 * hx**2) - bx / (2 * hx)) - cross / (2 * hx)
    right = sparse.diags(v / (2 * hx**2) + bx / (2 * hx)) + cross / (2 * hx)
    return matrix, left.tocsr(), right.tocsr()


def _boundary_brackets(values, multiplier, payoff, x, strike):
    """Bracket the last contiguous IT contact cell before continuation."""
    contact = (multiplier > 1e-10 * strike) & (np.abs(values - payoff) <= 1e-8 * strike)
    contact &= x[1:-1, None] < 0
    brackets = np.full((values.shape[1], 2), np.nan)
    valid = np.zeros(values.shape[1], dtype=bool)
    for j in range(values.shape[1]):
        continuation = np.flatnonzero(~contact[:, j])
        if not len(continuation):
            continue
        first = int(continuation[0])
        if first < 1 or np.any(contact[first:, j]):
            continue
        brackets[j] = [x[first], x[first + 1]]
        valid[j] = True
    return brackets, valid


def _solve_fd(
    contract,
    spots,
    v0,
    config,
    coefficients,
    *,
    time_limit_seconds=180,
    memory_limit_bytes=2 * 1024**3,
    problem_hash="constant-coefficient-control",
):
    started = perf_counter()

    def budget():
        elapsed = perf_counter() - started
        if elapsed >= time_limit_seconds:
            raise PricingFailure(
                "time_budget_exceeded", "FD wall-time budget exceeded", {"elapsed_seconds": elapsed}
            )
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        if peak > memory_limit_bytes:
            raise PricingFailure(
                "memory_budget_exceeded", "FD RSS budget exceeded", {"peak_rss_bytes": peak}
            )

    budget()
    nx, nz, nt = config.n_x, config.n_var, config.n_time
    states = (nx - 2) * nz
    estimated = states * min(nx - 2, nz) * 24 + states * 256
    if estimated > memory_limit_bytes:
        raise PricingFailure(
            "memory_budget_exceeded",
            "conservative FD factor estimate exceeds budget",
            {"estimated_bytes": estimated},
        )
    x = np.linspace(*config.log_spot_bounds, nx)
    z = np.linspace(*config.log_var_bounds, nz)
    times = np.linspace(0, contract.expiry, nt + 1)
    brackets = np.full((nt + 1, nz, 2), np.nan)
    boundary_valid = np.zeros((nt + 1, nz), dtype=bool)
    spot_array = np.asarray(spots, dtype=float)
    log_spots = np.log(spot_array / contract.strike)
    if np.any(log_spots < x[0]) or np.any(log_spots > x[-1]) or not z[0] <= np.log(v0) <= z[-1]:
        raise ValueError("FD query would extrapolate")
    if contract.expiry == 0:
        return FDResult(
            np.maximum(contract.strike - spot_array, 0),
            x,
            z,
            np.empty(0),
            np.empty((0, nz, 2)),
            np.empty((0, nz), dtype=bool),
            {"expiry_payoff": True},
            config,
            contract,
            problem_hash,
        )
    operator, left, right = _assemble_operator(contract, x, z, coefficients)
    # Short dimension innermost before sparse factorization.
    ordering = "z_fast" if nz <= nx - 2 else "x_fast"
    permutation = np.arange(states)
    if ordering == "x_fast":
        permutation = permutation.reshape(nx - 2, nz).T.ravel()
    inverse = np.argsort(permutation)
    operator = operator[permutation][:, permutation].tocsc()
    dt = contract.expiry / nt
    implicit = sparse.eye(states, format="csc") - dt / 2 * operator
    budget()
    factor = splu(implicit)
    budget()
    lu_bytes = sum(
        a.nbytes
        for block in (factor.L, factor.U)
        for a in (block.data, block.indices, block.indptr)
    )
    payoff = contract.strike * np.maximum(1 - np.exp(x[1:-1]), 0)[:, None] * np.ones((1, nz))
    value = payoff.ravel()[permutation].copy()
    lam = np.zeros(states)
    obstacle = value.copy()
    setup_seconds = perf_counter() - started
    maximum_defect, predictor_minimum, projected_count = 0.0, float("inf"), 0

    def source(tau):
        if config.exercise == "american":
            low = contract.strike * (1 - np.exp(x[0]))
        else:
            low = max(
                contract.strike
                * (
                    np.exp(-contract.domestic_rate * tau)
                    - np.exp(x[0] - contract.foreign_rate * tau)
                ),
                0,
            )
        output = np.zeros((nx - 2, nz))
        output[0] = left @ np.full(nz, low)
        output[-1] += right @ np.zeros(nz)
        return output.ravel()[permutation]

    tau = 0.0
    for step in range(1, nt + 1):
        half_steps = 2 if step <= 2 else 1
        increment = dt / half_steps
        theta = 1.0 if step <= 2 else 0.5
        for _ in range(half_steps):
            budget()
            forcing = (1 - theta) * source(tau) + theta * source(tau + increment)
            old = value
            rhs = old + (1 - theta) * increment * (operator @ old) + increment * (forcing + lam)
            predictor = factor.solve(rhs)
            predictor_minimum = min(predictor_minimum, float(np.min(predictor)))
            if not np.all(np.isfinite(predictor)):
                raise PricingFailure("nonfinite_fd", "nonfinite FD predictor", {"time_step": step})
            if config.exercise == "american":
                projected_count += int(np.count_nonzero(predictor - increment * lam < obstacle))
                value = np.maximum(predictor - increment * lam, obstacle)
                lam = np.maximum(0, lam + (obstacle - predictor) / increment)
            else:
                value = predictor
            defect = (
                (value - old) / increment
                - theta * (operator @ value)
                - (1 - theta) * (operator @ old)
                - forcing
                - lam
            )
            maximum_defect = max(maximum_defect, float(np.max(np.abs(defect))))
            tau += increment
        if config.exercise == "american":
            brackets[nt - step], boundary_valid[nt - step] = _boundary_brackets(
                value[inverse].reshape(nx - 2, nz),
                lam[inverse].reshape(nx - 2, nz),
                payoff,
                x,
                contract.strike,
            )
    solved = perf_counter()
    final = np.empty((nx, nz))
    final[1:-1] = value[inverse].reshape(nx - 2, nz)
    final[0] = (
        contract.strike * (1 - np.exp(x[0]))
        if config.exercise == "american"
        else max(
            contract.strike
            * (np.exp(-contract.domestic_rate * tau) - np.exp(x[0] - contract.foreign_rate * tau)),
            0,
        )
    )
    final[-1] = 0
    at_variance = CubicSpline(z, final, axis=1)(np.log(v0))
    prices = CubicSpline(x, at_variance)(log_spots)
    gap = value - obstacle
    diagnostics = {
        "ordering": ordering,
        "estimated_bytes": estimated,
        "lu_bytes": lu_bytes,
        "minimum_payoff_gap": float(np.min(gap)),
        "minimum_lambda": float(np.min(lam)),
        "max_complementarity": float(np.max(np.abs(gap * lam))),
        "positive_lambda_count": int(np.count_nonzero(lam > 1e-10 * contract.strike)),
        "positive_time_value_count": int(np.count_nonzero(gap > 1e-8 * contract.strike)),
        "max_equation_defect": maximum_defect,
        "predictor_minimum": predictor_minimum,
        "projected_node_steps": projected_count,
        "setup_seconds": setup_seconds,
        "solve_seconds": solved - started - setup_seconds,
        "query_seconds": perf_counter() - solved,
        "total_seconds": perf_counter() - started,
        "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "interpolation": "cubic zeta then cubic log-spot, no extrapolation",
    }
    budget()
    if not np.all(np.isfinite(prices)):
        raise PricingFailure("nonfinite_fd", "nonfinite FD query", {})
    return FDResult(
        prices, x, z, times, brackets, boundary_valid, diagnostics, config, contract, problem_hash
    )


def reference_put(
    contract, model, spots, config, *, time_limit_seconds=180, memory_limit_bytes=2 * 1024**3
):
    """Price a constant-coefficient 3/2 put without DSINC implementation helpers."""
    if model.kind != "three_halves":
        raise ValueError("independent reference supports three_halves only")
    spots = np.asarray(spots, dtype=float)
    if spots.ndim != 1 or not len(spots) or not np.all(np.isfinite(spots)) or np.any(spots <= 0):
        raise ValueError("spots must be a nonempty positive finite vector")
    z = np.linspace(*config.log_var_bounds, config.n_var)
    payload = {"contract": asdict(contract), "model": asdict(model), "spots": spots.tolist()}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return _solve_fd(
        contract,
        spots,
        model.v0,
        config,
        _sde_coefficients(contract, model, z),
        time_limit_seconds=time_limit_seconds,
        memory_limit_bytes=memory_limit_bytes,
        problem_hash=digest,
    )


def assess_refinement(results, tolerance=5e-6):
    """Assess one predeclared refinement axis, not global reference accuracy."""
    if len(results) != 3 or len({r.problem_hash for r in results}) != 1:
        raise ValueError("three results of the same physical problem are required")
    configs = [asdict(r.config) for r in results]
    varying = [key for key in configs[0] if any(c[key] != configs[0][key] for c in configs[1:])]
    if len(varying) != 1 or varying[0] not in ("n_x", "n_var", "n_time"):
        raise ValueError("refine exactly one grid axis")
    axis = varying[0]
    if not configs[0][axis] < configs[1][axis] < configs[2][axis]:
        raise ValueError("refinement must be increasing")
    changes = [
        float(np.max(np.abs(b.prices - a.prices)) / a.contract.strike) for a, b in pairwise(results)
    ]
    counts = np.array([c[axis] for c in configs], dtype=float)
    h = 1 / (counts if axis == "n_time" else counts - 1)
    orders, extrapolations = [], []
    for i in range(len(results[0].prices)):
        values = np.array([r.prices[i] for r in results])
        differences = values[:-1] - values[1:]
        order = None
        if np.prod(differences) > 0:
            ratio = differences[0] / differences[1]

            def objective(p, ratio=ratio):
                return (h[0] ** p - h[1] ** p) / (h[1] ** p - h[2] ** p) - ratio

            if objective(0.1) * objective(6) < 0:
                order = float(brentq(objective, 0.1, 6))
        orders.append(order)
        extrapolations.append(
            float((h[1] ** 2 * values[2] - h[2] ** 2 * values[1]) / (h[1] ** 2 - h[2] ** 2))
            if order is not None and 1.5 <= order <= 2.5
            else None
        )
    return {
        "scope": "single_axis",
        "axis": axis,
        "changes": changes,
        "tolerance": tolerance,
        "supported": changes[-1] <= tolerance and changes[-1] < changes[0],
        "observed_orders": orders,
        "second_order_extrapolations": extrapolations,
        "interpretation": "observed final change, not a rigorous error bound",
    }


def boundary_comparison(
    spectral_times, spectral_z, spectral_boundary, reference, *, coverage_threshold=0.9
):
    """Compare brackets only at integer-mapped times and selected variances."""
    if not 0 < coverage_threshold <= 1:
        raise ValueError("coverage threshold must lie in (0,1]")
    ns, nf = len(spectral_times) - 1, reference.config.n_time
    if ns < 1 or reference.contract.expiry <= 0:
        return {"target_count": 0, "coverage": 0.0, "accepted": False, "reasons": {}}
    if not np.allclose(
        spectral_times, np.linspace(0, reference.contract.expiry, ns + 1), atol=1e-14, rtol=0
    ):
        raise ValueError("spectral times must be the uniform physical time grid")
    z_indices = np.flatnonzero(
        (np.exp(spectral_z) >= 0.01 - 1e-15) & (np.exp(spectral_z) <= 0.16 + 1e-15)
    )
    time_indices = [j for j in range(ns + 1) if 0.1 <= j / ns <= 0.9 and j * nf % ns == 0]
    total, valid_count, outside, max_distance = len(z_indices) * len(time_indices), 0, 0, 0.0
    reasons = {
        "invalid_fd_bracket": 0,
        "outside_variance_grid": 0,
        "near_x_edge": 0,
        "nonfinite_spectral": 0,
    }
    dx = reference.x[1] - reference.x[0]
    for j in time_indices:
        k = j * nf // ns
        for i in z_indices:
            zz = spectral_z[i]
            if not reference.log_variances[0] <= zz <= reference.log_variances[-1]:
                reasons["outside_variance_grid"] += 1
                continue
            upper = min(
                np.searchsorted(reference.log_variances, zz), len(reference.log_variances) - 1
            )
            if abs(reference.log_variances[upper] - zz) < 1e-14:
                indices, weight = [upper], 0.0
            else:
                indices = [upper - 1, upper]
                weight = (zz - reference.log_variances[upper - 1]) / (
                    reference.log_variances[upper] - reference.log_variances[upper - 1]
                )
            if not np.all(reference.boundary_valid[k, indices]):
                reasons["invalid_fd_bracket"] += 1
                continue
            bracket = reference.boundary_brackets[k, indices[0]].copy()
            if len(indices) == 2:
                bracket = (1 - weight) * bracket + weight * reference.boundary_brackets[
                    k, indices[1]
                ]
            value = spectral_boundary[j, i]
            if not np.isfinite(value):
                reasons["nonfinite_spectral"] += 1
                continue
            if (
                min(value, bracket[0]) <= reference.x[0] + 4 * dx
                or max(value, bracket[1]) >= reference.x[-1] - 4 * dx
            ):
                reasons["near_x_edge"] += 1
                continue
            valid_count += 1
            distance = max(bracket[0] - value, value - bracket[1], 0.0)
            max_distance = max(max_distance, distance)
            outside += int(distance > 2 * dx)
    coverage = valid_count / total if total else 0.0
    return {
        "target_count": total,
        "valid_count": valid_count,
        "coverage": coverage,
        "outside_count": outside,
        "max_distance": max_distance,
        "dx": dx,
        "accepted": total > 0
        and coverage >= coverage_threshold
        and outside == 0
        and reasons["nonfinite_spectral"] == 0,
        "numerical_failure": reasons["nonfinite_spectral"] > 0,
        "reasons": reasons,
    }
