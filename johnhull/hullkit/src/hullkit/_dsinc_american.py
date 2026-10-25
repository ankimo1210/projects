"""Private fixed-frequency EEP recursion and guarded nodal put boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import numpy as np
from scipy.interpolate import CubicSpline

from ._dsinc_spectral import (
    Propagators,
    _apply,
    _input_hash,
    _put_at_nodes,
    _spot_vector,
    _validate_model_grid,
    build_propagators,
)
from ._dsinc_types import PricingFailure, PricingResult, PutContract, SpectralConfig, VarianceModel


def payoff_transform(
    omega: np.ndarray, chi: float, boundary: np.ndarray, contract: PutContract
) -> np.ndarray:
    """Transform the residue-subtracted EEP source, with frequency first."""
    s = 1j * np.asarray(omega)[:, None] - chi
    boundary = np.asarray(boundary)[None, :]
    return np.exp(s * boundary) * (
        contract.domestic_rate / s - contract.foreign_rate * np.exp(boundary) / (1 + s)
    )


def _advance_history(prop, q, d, next_source, quadrature_weight, rd):
    discount = np.exp(-rd * prop.dt)
    return (
        discount * _apply(prop, q + quadrature_weight * next_source),
        discount * (d + rd * quadrature_weight),
    )


def _continuation_at_nodes(contract, log_spots, prop, chi, g, q, d, *, tau):
    european = _put_at_nodes(contract, log_spots, prop.omega, prop.weights, chi, g, tau=tau)
    phase = np.exp(np.outer(log_spots, chi - 1j * prop.omega))
    return european + contract.strike * (d + ((phase * prop.weights) @ q).real / np.pi)


def _boundary_residual(contract, prop, config, g, q, d, *, tau):
    s = 1j * prop.omega - config.chi
    coefficients = prop.weights[:, None] * (
        np.exp(-contract.domestic_rate * tau) * g / (s * (1 + s))[:, None] + q
    )
    constant = 1 - np.exp(-contract.domestic_rate * tau) - d

    def evaluate(x, node):
        x = np.asarray(x)
        source = contract.domestic_rate - contract.foreign_rate * np.exp(x)
        integral = (np.exp(-np.outer(x, s)) @ coefficients[:, node]).real / np.pi
        # This endpoint correction belongs only to value matching.
        return constant - np.exp(x) - prop.dt * source / 4 - integral

    return evaluate


def local_boundary(
    residual, predictor: np.ndarray, config: SpectralConfig
) -> tuple[np.ndarray, dict]:
    """Scan each node locally; residual(x, node) supports bounded memory use.

    Sampling diagnoses contact/orientation; it does not prove continuous
    uniqueness. Every node is completed even if another node fails.
    """
    predictor = np.asarray(predictor, dtype=float)
    if predictor.ndim != 1 or not np.all(np.isfinite(predictor)) or np.any(predictor > 0):
        raise ValueError("predictors must be a finite nonpositive vector")
    roots = np.full(predictor.shape, np.nan)
    statuses, records = [], []
    widths = []
    width = config.root_width
    while width < config.root_max_width - 1e-14:
        widths.append(width)
        width += config.root_width
    widths.append(config.root_max_width)
    for node, prediction in enumerate(predictor):
        status = "missing_sign_change"
        record = {
            "node": node,
            "iterations": 0,
            "scan_evaluations": 0,
            "residual": None,
            "bracket": None,
        }
        for width in widths:
            lo, hi = prediction - width, min(0.0, prediction + width)
            m = max(65, int(np.ceil(2 * config.panels[-1] * (hi - lo) / np.pi)) + 1)
            xs = np.linspace(lo, hi, m)
            values = np.concatenate(
                [
                    np.asarray(residual(xs[start : start + 64], node), dtype=float)
                    for start in range(0, m, 64)
                ]
            )
            record.update(
                bracket=[float(lo), float(hi)], scan_evaluations=record["scan_evaluations"] + m
            )
            if values.shape != xs.shape or not np.all(np.isfinite(values)):
                status = "nonfinite_residual"
                break
            zero = np.abs(values) <= config.root_residual_tol
            nonzero = np.flatnonzero(~zero)
            signs = np.sign(values[nonzero])
            changes = np.flatnonzero(signs[:-1] != signs[1:])
            record["sampled_sign_changes"] = len(changes)
            if len(changes) > 1:
                status = "multiple_roots"
                break
            if np.any(zero[:-1] & zero[1:]) or (np.any(zero) and not len(changes)):
                status = "ambiguous_contact"
                break
            if values[0] < 0 < values[-1] or (len(changes) == 1 and signs[changes[0]] < 0):
                status = "wrong_orientation"
                break
            if not (values[0] > 0 > values[-1] and len(changes) == 1):
                continue
            index = changes[0]
            lo, hi = xs[nonzero[index]], xs[nonzero[index + 1]]
            for iteration in range(1, config.root_maxiter + 1):
                mid = (lo + hi) / 2
                value = float(np.asarray(residual(np.array([mid]), node))[0])
                record.update(iterations=iteration, residual=value, bracket=[float(lo), float(hi)])
                if not np.isfinite(value):
                    status = "nonfinite_residual"
                    break
                if value == 0:
                    lo = hi = mid
                    record["bracket"] = [float(mid), float(mid)]
                if hi - lo <= config.root_x_tol and abs(value) <= config.root_residual_tol:
                    roots[node], status = mid, "ok"
                    break
                if value > 0:
                    lo = mid
                else:
                    hi = mid
            else:
                status = "max_iterations"
            break
        statuses.append(status)
        records.append(record)
    return roots, {
        "node_count": len(predictor),
        "statuses": statuses,
        "nodes": records,
        "uniqueness": "sampled local sign-change diagnostic only",
    }


@dataclass(frozen=True)
class PreparedAmerican:
    """Completed boundary/history solve reusable for genuine query-only timing."""

    contract: PutContract
    model: VarianceModel
    config: SpectralConfig
    propagators: Propagators | None
    european_vector: np.ndarray
    eep_vector: np.ndarray
    eep_residue: float
    times: np.ndarray
    log_variances: np.ndarray
    log_boundary: np.ndarray
    diagnostics: dict

    def price(self, spots: np.ndarray) -> PricingResult:
        """Query prices after one solve; exact payoff applies in exercise region."""
        started = perf_counter()
        spots = _spot_vector(spots)
        if self.contract.expiry == 0:
            value = np.maximum(self.contract.strike - spots, 0.0)
            return PricingResult(
                value.copy(),
                value,
                np.zeros_like(value),
                self.times,
                self.log_variances,
                self.log_boundary,
                dict(self.diagnostics),
            )
        prop, contract, config = self.propagators, self.contract, self.config
        log_spots = np.log(spots / contract.strike)
        eu_nodes = _put_at_nodes(
            contract, log_spots, prop.omega, prop.weights, config.chi, self.european_vector
        )
        continuation_nodes = _continuation_at_nodes(
            contract,
            log_spots,
            prop,
            config.chi,
            self.european_vector,
            self.eep_vector,
            self.eep_residue,
            tau=contract.expiry,
        )
        z0 = np.log(self.model.v0)
        european = CubicSpline(self.log_variances, eu_nodes, axis=1, extrapolate=False)(z0)
        continuation = CubicSpline(
            self.log_variances, continuation_nodes, axis=1, extrapolate=False
        )(z0)
        boundary = float(
            CubicSpline(self.log_variances, self.log_boundary[0], extrapolate=False)(z0)
        )
        exercise = log_spots <= boundary
        american = np.where(exercise, contract.strike - spots, continuation)
        if not np.all(np.isfinite(american)) or not np.all(np.isfinite(european)):
            raise PricingFailure("nonfinite_price", "nonfinite raw DSINC price", {})
        diagnostics = dict(self.diagnostics)
        diagnostics.update(
            query_seconds=perf_counter() - started,
            exercise_region=exercise.tolist(),
            raw_continuation=continuation.tolist(),
            initial_log_boundary=boundary,
        )
        return PricingResult(
            european,
            american,
            american - european,
            self.times,
            self.log_variances,
            self.log_boundary,
            diagnostics,
        )


def prepare_american(
    contract: PutContract,
    model: VarianceModel,
    config: SpectralConfig,
    *,
    propagators: Propagators | None = None,
) -> PreparedAmerican:
    """Solve Eq.57/58 once, retaining only final vectors and boundary evidence."""
    started = perf_counter()
    if propagators is not None and propagators.input_hash != _input_hash(contract, model, config):
        raise ValueError("propagator cache input mismatch")
    if contract.expiry == 0:
        return PreparedAmerican(
            contract,
            model,
            config,
            None,
            np.empty((0, 0)),
            np.empty((0, 0)),
            0.0,
            np.empty(0),
            np.empty(0),
            np.empty((0, 0)),
            {"boundary_status": "not_applicable", "setup_seconds": 0.0, "solve_seconds": 0.0},
        )
    _validate_model_grid(model, config)
    prop = build_propagators(contract, model, config) if propagators is None else propagators
    setup = perf_counter() - started
    nt, nv = config.n_time, config.n_var
    times = np.linspace(0, contract.expiry, nt + 1)
    boundary = np.full((nt + 1, nv), np.nan)
    boundary[-1] = 0.0
    statuses = np.full((nt + 1, nv), "not_run", dtype="U32")
    statuses[-1] = "maturity_limit"
    g = np.ones((len(prop.omega), nv), dtype=complex)
    q, d, maximum_residual, scan_evaluations = np.zeros_like(g), 0.0, 0.0, 0
    for n in range(nt - 1, -1, -1):
        next_source = payoff_transform(prop.omega, config.chi, boundary[n + 1], contract)
        q, d = _advance_history(
            prop, q, d, next_source, prop.dt / 2 if n == nt - 1 else prop.dt, contract.domestic_rate
        )
        g = _apply(prop, g)
        tau = (nt - n) * prop.dt
        residual = _boundary_residual(contract, prop, config, g, q, d, tau=tau)
        boundary[n], diagnostic = local_boundary(residual, boundary[n + 1], config)
        statuses[n] = diagnostic["statuses"]
        if np.any(statuses[n] != "ok"):
            raise PricingFailure(
                "boundary_failure",
                "guarded local boundary failed",
                {
                    "time_index": n,
                    "time": float(times[n]),
                    "statuses": statuses.tolist(),
                    "failed_slice": diagnostic,
                    "failed_boundary_propagated": False,
                    "q_updates": nt - n,
                    "setup_seconds": setup,
                    "solve_seconds": perf_counter() - started - setup,
                    "propagator_diagnostics": prop.diagnostics,
                },
            )
        maximum_residual = max(
            maximum_residual, max(abs(r["residual"]) for r in diagnostic["nodes"])
        )
        scan_evaluations += sum(r["scan_evaluations"] for r in diagnostic["nodes"])
    diagnostics = dict(prop.diagnostics)
    diagnostics.update(
        boundary_status="complete",
        statuses=statuses.tolist(),
        max_root_residual=maximum_residual,
        scan_evaluations=scan_evaluations,
        setup_seconds=setup,
        propagator_setup_seconds=prop.setup_seconds,
        solve_seconds=perf_counter() - started - setup,
        setup_reused=propagators is not None,
    )
    for value in (g, q, times, boundary):
        value.setflags(write=False)
    return PreparedAmerican(
        contract, model, config, prop, g, q, d, times, prop.log_variances, boundary, diagnostics
    )


def american_put(
    contract: PutContract,
    model: VarianceModel,
    spots: np.ndarray,
    config: SpectralConfig,
    *,
    propagators: Propagators | None = None,
) -> PricingResult:
    """Price American puts, preserving root failures and raw continuation values."""
    spots = _spot_vector(spots)
    return prepare_american(contract, model, config, propagators=propagators).price(spots)
