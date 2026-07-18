"""CPU-quick reference bundles for John Hull volumes 19 and 20.

The public builders return JSON-serializable metrics plus finite numeric NumPy
arrays.  They do not write files, so the John Hull release builder can own the
serialization contract without duplicating research-model calculations.
"""

from __future__ import annotations

import hashlib
import json
import time as wall_time
from typing import Any

import numpy as np
import torch

from .feature_diagnostics import (
    diagnostic_rank_stability,
    integrated_gradients,
    occlusion_importance,
    permutation_importance,
)
from .hedge_capstone import DEFAULT_NO_TRADE_WIDTH, DEFAULT_TRANSACTION_COST
from .pricing_calibration import (
    CalibrationResult,
    calibrate_parameters,
    calibration_error_metrics,
    fit_direct_inverse_ridge,
)
from .surface_data import joint_surface_pareto
from .surface_hedge_pipeline import run_synthetic_surface_hedge_pipeline
from .volatility_data import (
    TrainWindowPCA,
    TrainWindowStandardizer,
    build_volatility_targets,
    purged_walk_forward_splits,
)
from .walk_forward import (
    SequenceForecaster,
    block_bootstrap_metric_ci,
    ewma_forecast,
    fit_garch11,
    fit_regularized_linear,
    fit_sequence_forecaster,
    forecast_metrics,
    garch11_aggregate_forecast,
    garch11_variance_forecast,
)

ReferenceBundle = tuple[dict[str, Any], dict[str, np.ndarray]]


def _array_fingerprint(arrays: dict[str, np.ndarray]) -> str:
    digest = hashlib.sha256()
    for name, array in sorted(arrays.items()):
        value = np.ascontiguousarray(array)
        digest.update(name.encode())
        digest.update(str(value.shape).encode())
        digest.update(value.dtype.str.encode())
        digest.update(value.tobytes(order="C"))
    return "sha256:" + digest.hexdigest()


def _finalize(
    metrics: dict[str, Any],
    arrays: dict[str, np.ndarray],
    units: dict[str, str],
) -> ReferenceBundle:
    normalized: dict[str, np.ndarray] = {}
    schema = {}
    for name, array in sorted(arrays.items()):
        value = np.ascontiguousarray(np.asarray(array))
        if value.size == 0 or value.dtype.kind not in "biuf" or not np.all(np.isfinite(value)):
            raise ValueError(f"reference array {name} must be non-empty, finite, and numeric")
        normalized[name] = value
        schema[name] = {
            "shape": list(value.shape),
            "dtype": value.dtype.str,
            "unit": units.get(name, "dimensionless"),
        }
    metrics["array_schema"] = schema
    metrics["array_fingerprint"] = _array_fingerprint(normalized)
    # Reject NumPy scalars, NaNs, and any other non-portable JSON values here.
    json.dumps(metrics, allow_nan=False, sort_keys=True)
    return metrics, normalized


def _teacher_surface(
    model: str,
    strikes: np.ndarray,
    maturities: np.ndarray,
    parameters: dict[str, float | int],
    *,
    seed: int,
    rbergomi_paths: int,
) -> dict[str, Any]:
    try:
        from hullkit.surrogate_data import forward_surface_teacher
    except ImportError as exc:  # pragma: no cover - isolated install contract
        raise RuntimeError("hullkit is required to build frontier reference bundles") from exc
    return forward_surface_teacher(
        model,
        1.0,
        strikes,
        maturities,
        0.0,
        parameters,
        seed=seed,
        n_paths=rbergomi_paths,
    )


def _sabr_forward(
    strikes: np.ndarray,
    maturities: np.ndarray,
    parameters: np.ndarray,
) -> np.ndarray:
    values = np.asarray(parameters, dtype=float)
    result = _teacher_surface(
        "sabr",
        strikes,
        maturities,
        {
            "alpha": values[0],
            "beta": values[1],
            "rho": values[2],
            "nu": values[3],
        },
        seed=0,
        rbergomi_paths=100,
    )
    return np.asarray(result["implied_volatility"], dtype=float).reshape(-1)


def _surface_hard_report(
    prices: np.ndarray,
    strikes: np.ndarray,
    maturities: np.ndarray,
    *,
    tolerance: float = 1e-7,
) -> dict[str, Any]:
    try:
        from hullkit.surrogate_validation import (
            check_calendar_monotonicity,
            check_price_bounds,
            check_strike_convexity,
            check_strike_monotonicity,
            validation_report,
        )
    except ImportError as exc:  # pragma: no cover - isolated install contract
        raise RuntimeError("hullkit is required to validate frontier surfaces") from exc
    values = np.asarray(prices, dtype=float)
    strike_grid = np.broadcast_to(strikes, values.shape)
    maturity_grid = np.broadcast_to(maturities[:, None], values.shape)
    return validation_report(
        check_price_bounds(
            values,
            np.ones_like(values),
            strike_grid,
            0.0,
            maturity_grid,
            tolerance=tolerance,
        ),
        check_strike_monotonicity(values, strikes, tolerance=tolerance),
        check_strike_convexity(values, strikes, tolerance=tolerance),
        check_calendar_monotonicity(values.T, maturities, tolerance=tolerance),
    ).to_dict()


def _constraint_comparison(seed: int) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    try:
        from hullkit.vol_surface import compare_surface_constraints
    except ImportError as exc:  # pragma: no cover - isolated install contract
        raise RuntimeError("hullkit is required to compare surface constraints") from exc
    strikes = np.linspace(0.82, 1.18, 9)
    maturities = np.array([0.15, 0.40, 0.80, 1.25])
    clean = np.asarray(
        _teacher_surface(
            "heston",
            strikes,
            maturities,
            {"v0": 0.04, "kappa": 1.5, "theta": 0.04, "xi": 0.30, "rho": -0.60},
            seed=seed,
            rbergomi_paths=100,
        )["price"],
        dtype=float,
    )
    # Reproducible quote contamination, not a fabricated model output.  It
    # creates both butterfly and calendar violations for repair diagnostics.
    raw = clean.copy()
    raw[0, 4] += 0.008
    raw[1, 5] += 0.006
    raw[2, 3] = raw[1, 3] - 0.003
    raw[3, 6] -= 0.003
    lower = np.maximum(1.0 - strikes, 0.0)
    upper = np.ones_like(strikes)
    soft_slices = []
    hard_slices = []
    for row in raw:
        comparison = compare_surface_constraints(
            strikes,
            row,
            soft_weight=100.0,
            lower_bound=lower,
            upper_bound=upper,
            tolerance=1e-7,
        )
        soft_slices.append(comparison.soft_penalty)
        hard_slices.append(comparison.hard_constrained)
    soft = np.stack(soft_slices)
    # Cumulative maximum is a deterministic feasible calendar repair on this
    # ordered grid after every strike slice is hard-convex.
    hard = np.maximum.accumulate(np.stack(hard_slices), axis=0)
    routes = {"raw": raw, "soft": soft, "hard": hard}
    reports = {
        name: _surface_hard_report(value, strikes, maturities) for name, value in routes.items()
    }
    return (
        {
            "source": "Heston/COS prices with deterministic quote contamination",
            "soft_objective_is_not_an_arbitrage_free_claim": True,
            "hard_arbitrage_label_source": "complete hullkit hard report",
            "reports": reports,
            "rmse_to_clean_teacher": {
                name: float(np.sqrt(np.mean((value - clean) ** 2)))
                for name, value in routes.items()
            },
        },
        {
            "constraint_strikes": strikes,
            "constraint_maturities": maturities,
            "constraint_clean_teacher_price": clean,
            "constraint_raw_price": raw,
            "constraint_soft_price": soft,
            "constraint_hard_price": hard,
        },
    )


def _joint_refits(
    base_iv: np.ndarray,
    strikes: np.ndarray,
    maturities: np.ndarray,
    *,
    seed: int,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    fixed = {"kappa": 1.5, "xi": 0.30, "rho": -0.60}

    def forward(parameters: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        v0, theta = np.asarray(parameters, dtype=float)
        surface = _teacher_surface(
            "heston",
            strikes,
            maturities,
            {"v0": v0, "theta": theta, **fixed},
            seed=seed,
            rbergomi_paths=100,
        )
        variance = theta + (v0 - theta) * np.exp(-fixed["kappa"] * maturities)
        return np.asarray(surface["implied_volatility"], dtype=float), variance

    iv_perturbation = np.array(
        [
            [-0.0010, 0.0000, 0.0010, 0.0015],
            [0.0000, 0.0000, 0.0010, 0.0020],
            [0.0010, 0.0010, 0.0020, 0.0025],
        ]
    )
    target_iv = base_iv + iv_perturbation
    _, target_variance = forward(np.array([0.055, 0.030]))
    lambdas = np.array([0.0, 10.0, 100.0])
    candidates: dict[float, tuple[np.ndarray, np.ndarray]] = {}
    parameters = []
    evaluations = []
    repricing_rmse = []
    for index, lambda_var in enumerate(lambdas):
        target = np.concatenate((target_iv.reshape(-1), target_variance))

        def combined(candidate: np.ndarray) -> np.ndarray:
            predicted_iv, predicted_variance = forward(candidate)
            return np.concatenate((predicted_iv.reshape(-1), predicted_variance))

        weights = np.concatenate(
            (np.ones(target_iv.size), np.full(target_variance.size, lambda_var))
        )
        fitted = calibrate_parameters(
            combined,
            target,
            np.array([0.045, 0.038]),
            (np.array([0.015, 0.015]), np.array([0.090, 0.090])),
            n_starts=3,
            seed=seed + index,
            weights=weights,
        )
        predicted = forward(fitted.parameters)
        candidates[float(lambda_var)] = predicted
        parameters.append(fitted.parameters)
        evaluations.append(sum(start.evaluations for start in fitted.starts))
        repricing_rmse.append(fitted.repricing_rmse)
    points, frontier = joint_surface_pareto(candidates, target_iv, target_variance)
    frontier_lambdas = {point.lambda_var for point in frontier}
    predicted_iv = np.stack([candidates[float(value)][0] for value in lambdas])
    predicted_variance = np.stack([candidates[float(value)][1] for value in lambdas])
    return (
        {
            "actual_refit_per_lambda": True,
            "forward_teacher": "Heston/COS",
            "optimized_parameters": ["v0", "theta"],
            "fixed_parameters": fixed,
            "n_starts_per_lambda": 3,
            "fit_evaluations": [int(value) for value in evaluations],
            "repricing_rmse": [float(value) for value in repricing_rmse],
            "candidate_parameter_unique_count": len(
                np.unique(np.round(np.stack(parameters), 10), axis=0)
            ),
            "points": [
                {
                    "lambda_var": point.lambda_var,
                    "total_loss": point.total_loss,
                    "iv_loss": point.iv_loss,
                    "variance_loss": point.variance_loss,
                    "pareto_nondominated": point.lambda_var in frontier_lambdas,
                }
                for point in points
            ],
        },
        {
            "pareto_lambdas": lambdas,
            "pareto_fit_parameters": np.stack(parameters),
            "pareto_target_iv": target_iv,
            "pareto_target_variance": target_variance,
            "pareto_predicted_iv": predicted_iv,
            "pareto_predicted_variance": predicted_variance,
            "pareto_losses": np.array(
                [[point.total_loss, point.iv_loss, point.variance_loss] for point in points]
            ),
            "pareto_nondominated": np.array(
                [point.lambda_var in frontier_lambdas for point in points], dtype=np.int8
            ),
        },
    )


def build_vol19_reference(*, seed: int = 1900, rbergomi_paths: int = 2_048) -> ReferenceBundle:
    """Build actual-teacher calibration/surface artifacts for volume 19."""

    if seed < 0 or rbergomi_paths < 100:
        raise ValueError("seed must be non-negative and rbergomi_paths at least 100")
    strikes = np.exp(np.array([-0.02, 0.0, 0.02, 0.05]))
    maturities = np.array([0.25, 0.75, 1.25])
    definitions: list[tuple[str, dict[str, float | int], list[str]]] = [
        (
            "heston",
            {"v0": 0.04, "kappa": 1.5, "theta": 0.04, "xi": 0.30, "rho": -0.60},
            ["v0", "kappa", "theta", "xi", "rho"],
        ),
        (
            "sabr",
            {"alpha": 0.20, "beta": 0.70, "rho": -0.25, "nu": 0.50},
            ["alpha", "beta", "rho", "nu"],
        ),
        (
            "rbergomi",
            {"xi0": 0.04, "eta": 0.60, "hurst": 0.12, "rho": -0.60, "n_steps": 12},
            ["xi0", "eta", "hurst", "rho", "n_steps"],
        ),
    ]
    teacher_results = [
        _teacher_surface(
            model,
            strikes,
            maturities,
            parameters,
            seed=seed + 100 * index,
            rbergomi_paths=rbergomi_paths,
        )
        for index, (model, parameters, _names) in enumerate(definitions)
    ]
    parameter_values = np.zeros((len(definitions), 5))
    parameter_mask = np.zeros_like(parameter_values, dtype=np.int8)
    for index, (_model, parameters, names) in enumerate(definitions):
        parameter_values[index, : len(names)] = [float(parameters[name]) for name in names]
        parameter_mask[index, : len(names)] = 1
    teacher_iv = np.stack([result["implied_volatility"] for result in teacher_results])

    sabr_truth = parameter_values[1, :4]
    sabr_lower = np.array([0.08, 0.20, -0.80, 0.10])
    sabr_upper = np.array([0.40, 0.95, 0.40, 1.00])

    def sabr_forward(values: np.ndarray) -> np.ndarray:
        return _sabr_forward(strikes, maturities, values)

    calibration = calibrate_parameters(
        sabr_forward,
        teacher_iv[1].reshape(-1),
        np.array([0.18, 0.60, -0.10, 0.35]),
        (sabr_lower, sabr_upper),
        n_starts=4,
        seed=seed + 10,
    )

    rng = np.random.default_rng(seed + 11)
    inverse_parameters = rng.uniform(
        np.array([0.12, 0.40, -0.60, 0.20]),
        np.array([0.30, 0.90, 0.20, 0.80]),
        size=(32, 4),
    )
    inverse_features = np.stack([sabr_forward(values) for values in inverse_parameters])
    inverse_model = fit_direct_inverse_ridge(
        inverse_features[:24], inverse_parameters[:24], ridge=1e-3
    )
    inverse_prediction = np.clip(
        inverse_model.predict(inverse_features[24:]), sabr_lower, sabr_upper
    )
    inverse_repricing = np.stack([sabr_forward(values) for values in inverse_prediction])

    constraint_metrics, constraint_arrays = _constraint_comparison(seed + 20)
    pareto_metrics, pareto_arrays = _joint_refits(
        teacher_iv[0], strikes, maturities, seed=seed + 30
    )
    starts = calibration.starts
    arrays = {
        "teacher_model_code": np.arange(len(definitions), dtype=np.int16),
        "teacher_strikes": strikes,
        "teacher_maturities": maturities,
        "teacher_parameter_values": parameter_values,
        "teacher_parameter_mask": parameter_mask,
        "teacher_price": np.stack([result["price"] for result in teacher_results]),
        "teacher_implied_volatility": teacher_iv,
        "teacher_standard_error": np.stack(
            [result["standard_error"] for result in teacher_results]
        ),
        "calibration_truth": sabr_truth,
        "calibration_parameters": calibration.parameters,
        "calibration_start_initial": np.stack([start.initial for start in starts]),
        "calibration_start_parameters": np.stack([start.parameters for start in starts]),
        "calibration_start_repricing_rmse": np.array([start.repricing_rmse for start in starts]),
        "calibration_parameter_dispersion": calibration.parameter_dispersion,
        "direct_inverse_test_truth": inverse_parameters[24:],
        "direct_inverse_test_prediction": inverse_prediction,
        "direct_inverse_test_quote": inverse_features[24:],
        "direct_inverse_test_repricing": inverse_repricing,
        **constraint_arrays,
        **pareto_arrays,
    }
    metrics: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": "johnhull_frontier_reference",
        "volume": 19,
        "seed": seed,
        "execution_profile": "cpu_quick",
        "data_policy": "synthetic_offline_actual_numerical_teachers",
        "teachers": [
            {
                "model_code": index,
                "model": model,
                "method": teacher_results[index]["method"],
                "parameter_names": names,
                "path_count": rbergomi_paths if model == "rbergomi" else 0,
            }
            for index, (model, _parameters, names) in enumerate(definitions)
        ],
        "common_teacher_schema": {
            "axes": ["model", "maturity", "strike"],
            "fields": ["price", "implied_volatility", "standard_error"],
            "same_grid_for_all_models": True,
        },
        "forward_calibration": {
            "primary_method": "multi_start_forward_calibration",
            "model": "SABR/Hagan",
            "n_starts": len(starts),
            "all_starts_successful": all(start.success for start in starts),
            "evaluations": [int(start.evaluations) for start in starts],
            **calibration_error_metrics(calibration, sabr_truth),
        },
        "direct_inverse": {
            "role": "ablation_only",
            "train_rows": 24,
            "test_rows": 8,
            "parameter_rmse": float(
                np.sqrt(np.mean((inverse_prediction - inverse_parameters[24:]) ** 2))
            ),
            "repricing_rmse": float(
                np.sqrt(np.mean((inverse_repricing - inverse_features[24:]) ** 2))
            ),
        },
        "surface_constraints": constraint_metrics,
        "joint_variance_refits": pareto_metrics,
        "limitations": [
            "rough-Bergomi reference uses a small antithetic Monte Carlo path count",
            "direct inverse ridge is diagnostic and is not the primary calibration route",
            "quote contamination is deterministic stress data, not observed market data",
        ],
    }
    units = {
        "teacher_strikes": "spot_units",
        "teacher_maturities": "years",
        "teacher_price": "spot_units",
        "teacher_implied_volatility": "annualized_volatility",
        "teacher_standard_error": "spot_units",
        "calibration_start_repricing_rmse": "annualized_volatility",
        "constraint_strikes": "spot_units",
        "constraint_maturities": "years",
        "constraint_clean_teacher_price": "spot_units",
        "constraint_raw_price": "spot_units",
        "constraint_soft_price": "spot_units",
        "constraint_hard_price": "spot_units",
        "pareto_target_iv": "annualized_volatility",
        "pareto_predicted_iv": "annualized_volatility",
        "pareto_target_variance": "annualized_variance",
        "pareto_predicted_variance": "annualized_variance",
    }
    return _finalize(metrics, arrays, units)


def benchmark_vol19_calibration(
    *,
    repeats: int = 3,
    warmup: int = 1,
    seed: int = 1900,
) -> dict[str, Any]:
    """Measure the vol-19 SABR calibration without mutating reference data.

    Wall-clock measurements are intentionally kept out of
    :func:`build_vol19_reference`; otherwise byte-identical committed artifacts
    could not be rebuilt.  A validation report may record this separately with
    the environment and command that produced it.
    """

    if repeats < 1 or warmup < 0 or seed < 0:
        raise ValueError("repeats must be positive and warmup/seed non-negative")
    strikes = np.exp(np.array([-0.02, 0.0, 0.02, 0.05]))
    maturities = np.array([0.25, 0.75, 1.25])
    truth = np.array([0.20, 0.70, -0.25, 0.50])
    target = _sabr_forward(strikes, maturities, truth)
    lower = np.array([0.08, 0.20, -0.80, 0.10])
    upper = np.array([0.40, 0.95, 0.40, 1.00])
    initial = np.array([0.18, 0.60, -0.10, 0.35])

    def execute() -> CalibrationResult:
        return calibrate_parameters(
            lambda values: _sabr_forward(strikes, maturities, values),
            target,
            initial,
            (lower, upper),
            n_starts=4,
            seed=seed,
        )

    for _ in range(warmup):
        execute()
    samples = []
    last: CalibrationResult | None = None
    for _ in range(repeats):
        start = wall_time.perf_counter_ns()
        last = execute()
        samples.append((wall_time.perf_counter_ns() - start) / 1e6)
    assert last is not None
    values = np.asarray(samples)
    return {
        "benchmark_kind": "wall_clock_validation_only",
        "device": "cpu",
        "timer": "time.perf_counter_ns",
        "unit": "milliseconds",
        "repeats": repeats,
        "warmup": warmup,
        "median_ms": float(np.median(values)),
        "minimum_ms": float(np.min(values)),
        "maximum_ms": float(np.max(values)),
        "quote_count": int(target.size),
        "n_starts": len(last.starts),
        "objective_evaluations": int(sum(item.evaluations for item in last.starts)),
        "repricing_rmse": last.repricing_rmse,
        "artifact_inclusion": "excluded_to_preserve_byte_reproducibility",
    }


def _volatility_features(
    *, seed: int, n_observations: int, horizon: int
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
]:
    rng = np.random.default_rng(seed)
    long_run = np.log(0.04 / 252.0)
    log_variance = np.empty(n_observations)
    log_variance[0] = long_run
    for index in range(1, n_observations):
        log_variance[index] = (
            0.97 * log_variance[index - 1] + 0.03 * long_run + rng.normal(0.0, 0.12)
        )
    returns = np.sqrt(np.exp(log_variance)) * rng.standard_normal(n_observations)
    squared = returns**2
    ewma_prior = ewma_forecast(squared, decay=0.94)
    ewma_current = 0.94 * ewma_prior + 0.06 * squared
    surface_latents = np.column_stack(
        [
            log_variance,
            -0.40 * np.sqrt(np.exp(log_variance)) + 0.10 * returns,
            0.10 + 0.25 * np.exp(log_variance),
        ]
    )
    target_families = build_volatility_targets(returns, surface_latents, (horizon,))
    log_targets = target_families.log_realized_variance[horizon]
    times = np.arange(22, n_observations - horizon)
    tiny = 1e-12
    features = []
    sequences = []
    for time in times:
        daily = squared[time]
        weekly = squared[time - 4 : time + 1].sum()
        monthly = squared[time - 21 : time + 1].sum()
        features.append(
            [
                np.log(max(daily, tiny)),
                np.log(max(weekly, tiny)),
                np.log(max(monthly, tiny)),
                np.log(max(horizon * ewma_current[time], tiny)),
                *surface_latents[time],
            ]
        )
        sequences.append(np.log(np.maximum(squared[time - 21 : time + 1], tiny)))
    target = np.exp(log_targets[times])
    if np.any(~np.isfinite(target)) or np.any(target <= 0):
        raise RuntimeError("volatility target generation produced invalid rows")
    return (
        np.asarray(features),
        target,
        log_targets[times],
        target_families.surface_latent[horizon][times],
        times,
        returns,
        np.asarray(sequences),
    )


def _qlike_losses(actual: np.ndarray, predicted: np.ndarray) -> np.ndarray:
    ratio = np.asarray(actual, dtype=float) / np.asarray(predicted, dtype=float)
    return ratio - np.log(ratio) - 1.0


def _ci_dict(values: np.ndarray, *, seed: int) -> dict[str, float]:
    mean, lower, upper = block_bootstrap_metric_ci(
        values,
        block_size=min(8, len(values)),
        n_bootstrap=160,
        seed=seed,
    )
    return {
        "mean": mean,
        "lower_95": min(mean, lower),
        "upper_95": max(mean, upper),
    }


def _forecast_intervals(
    actual: np.ndarray,
    predicted: np.ndarray,
    *,
    seed: int,
) -> dict[str, dict[str, float]]:
    errors = np.asarray(predicted) - np.asarray(actual)
    qlike = _qlike_losses(actual, predicted)
    squared = _ci_dict(errors**2, seed=seed)
    absolute = _ci_dict(np.abs(errors), seed=seed + 1)
    qlike_interval = _ci_dict(qlike, seed=seed + 2)
    return {
        "rmse": {
            "estimate": float(np.sqrt(squared["mean"])),
            "lower_95": float(np.sqrt(max(squared["lower_95"], 0.0))),
            "upper_95": float(np.sqrt(max(squared["upper_95"], 0.0))),
        },
        "mae": {
            "estimate": absolute["mean"],
            "lower_95": absolute["lower_95"],
            "upper_95": absolute["upper_95"],
        },
        "qlike": {
            "estimate": qlike_interval["mean"],
            "lower_95": qlike_interval["lower_95"],
            "upper_95": qlike_interval["upper_95"],
        },
    }


def _model_forecast_report(
    actual: np.ndarray,
    predicted: np.ndarray,
    regime: np.ndarray,
    *,
    seed: int,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        **forecast_metrics(actual, predicted),
        "intervals_95": _forecast_intervals(actual, predicted, seed=seed),
    }
    result["qlike_block_bootstrap_ci"] = {
        "mean": result["intervals_95"]["qlike"]["estimate"],
        "lower_95": result["intervals_95"]["qlike"]["lower_95"],
        "upper_95": result["intervals_95"]["qlike"]["upper_95"],
    }
    by_regime = {}
    for code, name in enumerate(("low", "middle", "high")):
        selected = regime == code
        if np.count_nonzero(selected) < 2:
            raise RuntimeError(f"regime {name} has too few walk-forward observations")
        by_regime[name] = {
            "n_observations": int(np.count_nonzero(selected)),
            **forecast_metrics(actual[selected], predicted[selected]),
            "intervals_95": _forecast_intervals(
                actual[selected], predicted[selected], seed=seed + 10 * (code + 1)
            ),
        }
    result["by_regime"] = by_regime
    return result


def _attention_diagnostics(
    model: SequenceForecaster,
    features: np.ndarray,
    targets: np.ndarray,
    *,
    seed: int,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    model.eval()
    tensor = torch.as_tensor(features, dtype=torch.float32)

    def predict(values: np.ndarray) -> np.ndarray:
        with torch.no_grad():
            return model(torch.as_tensor(values, dtype=torch.float32)).cpu().numpy()

    with torch.no_grad():
        model(tensor)
    if model.last_attention is None:
        raise RuntimeError("transformer did not expose diagnostic attention weights")
    attention = model.last_attention.cpu().numpy().mean(axis=(0, 1, 2))
    attention = attention / attention.sum()
    permutation = permutation_importance(predict, features, targets, seed=seed)
    permutation_repeat = permutation_importance(predict, features, targets, seed=seed + 1)
    occlusion = occlusion_importance(predict, features, targets)
    attribution = integrated_gradients(model, tensor, steps=16).detach().cpu().numpy()
    integrated = np.mean(np.abs(attribution), axis=0)
    return (
        {
            "role": "non_causal_diagnostic_not_feature_explanation",
            "horizon": 5,
            "methods": ["attention", "permutation", "occlusion", "integrated_gradients"],
            "minimum_pairwise_rank_correlation": diagnostic_rank_stability(
                attention, permutation, occlusion, integrated
            ),
            "permutation_seed_rank_stability": diagnostic_rank_stability(
                permutation, permutation_repeat
            ),
            "attention_claim": "diagnostic_only",
        },
        {
            "attention_lag": np.arange(1, features.shape[1] + 1),
            "attention_importance": attention,
            "permutation_importance": permutation,
            "permutation_repeat_importance": permutation_repeat,
            "occlusion_importance": occlusion,
            "integrated_gradients_importance": integrated,
        },
    )


def _walk_forward_horizon(
    *,
    seed: int,
    horizon: int,
) -> tuple[
    dict[str, Any], dict[str, np.ndarray], tuple[dict[str, Any], dict[str, np.ndarray]] | None
]:
    embargo = 2
    (
        features,
        target,
        log_target,
        latent_target,
        time_index,
        returns,
        sequences,
    ) = _volatility_features(seed=seed, n_observations=420, horizon=horizon)
    splits = purged_walk_forward_splits(
        len(features),
        min_train=160,
        test_size=28,
        horizon=horizon,
        step=70,
        embargo=embargo,
        max_train=220,
    )
    model_names = (
        "persistence",
        "ewma",
        "garch11",
        "log_har",
        "regularized_linear",
        "pca_ridge_challenger",
        "harnet",
        "tcn",
        "lstm",
        "transformer",
    )
    prediction_rows = {name: [] for name in model_names}
    actual_rows: list[np.ndarray] = []
    test_rows: list[np.ndarray] = []
    fold_rows: list[np.ndarray] = []
    regime_rows: list[np.ndarray] = []
    scaler_mean = []
    scaler_scale = []
    pca_mean = []
    pca_components = []
    pca_variance = []
    sequence_mean = []
    sequence_scale = []
    garch_parameters = []
    regime_thresholds = []
    fold_bounds = []
    diagnostic_inputs: tuple[SequenceForecaster, np.ndarray, np.ndarray] | None = None
    persistence_column = {1: 0, 5: 1, 21: 2}[horizon]

    for fold, split in enumerate(splits):
        standardizer = TrainWindowStandardizer.fit(features, split.train)
        standardized = standardizer.transform(features)
        pca = TrainWindowPCA.fit(standardized, split.train, n_components=4)
        projected = pca.transform(standardized)
        regularized = fit_regularized_linear(
            standardized[split.train], log_target[split.train], ridge=1e-3
        )
        pca_model = fit_regularized_linear(
            projected[split.train], log_target[split.train], ridge=1e-3
        )
        log_har = fit_regularized_linear(
            features[split.train, :3], log_target[split.train], ridge=1e-3
        )

        return_start = max(0, int(time_index[split.train[0]]) - 22)
        return_end = int(time_index[split.train[-1]]) + 1
        garch = fit_garch11(returns[return_start:return_end])
        filter_end = int(time_index[split.test[-1]]) + 1
        filter_returns = returns[return_start : filter_end + 1]
        initial_variance = max(float(np.mean(returns[return_start:return_end] ** 2)), 1e-12)
        filtered = garch11_variance_forecast(
            filter_returns,
            omega=garch.omega,
            alpha=garch.alpha,
            beta=garch.beta,
            initial_variance=initial_variance,
        )
        garch_prediction = []
        for row in split.test:
            source_time = int(time_index[row])
            local = source_time - return_start
            one_step = (
                garch.omega
                + garch.alpha * filter_returns[local] ** 2
                + garch.beta * filtered[local]
            )
            garch_prediction.append(
                garch11_aggregate_forecast(
                    one_step,
                    horizon=horizon,
                    omega=garch.omega,
                    alpha=garch.alpha,
                    beta=garch.beta,
                )
            )

        predictions: dict[str, np.ndarray] = {
            "persistence": np.exp(features[split.test, persistence_column]),
            "ewma": np.exp(features[split.test, 3]),
            "garch11": np.asarray(garch_prediction),
            "log_har": np.exp(log_har.predict(features[split.test, :3])),
            "regularized_linear": np.exp(regularized.predict(standardized[split.test])),
            "pca_ridge_challenger": np.exp(pca_model.predict(projected[split.test])),
        }

        sequence_standardizer = TrainWindowStandardizer.fit(sequences, split.train)
        standardized_sequences = sequence_standardizer.transform(sequences)
        target_mean = float(log_target[split.train].mean())
        target_scale = float(log_target[split.train].std())
        if target_scale <= 0.0:
            target_scale = 1.0
        train_x = torch.as_tensor(standardized_sequences[split.train], dtype=torch.float32)
        train_y = torch.as_tensor(
            (log_target[split.train] - target_mean) / target_scale,
            dtype=torch.float32,
        )
        test_x = torch.as_tensor(standardized_sequences[split.test], dtype=torch.float32)
        for model_index, kind in enumerate(("harnet", "tcn", "lstm", "transformer")):
            torch.manual_seed(seed + horizon * 1_000 + fold * 100 + model_index)
            model = SequenceForecaster(kind, hidden=8)
            fit_sequence_forecaster(model, train_x, train_y, epochs=5, learning_rate=0.01)
            model.eval()
            with torch.no_grad():
                normalized_prediction = model(test_x).cpu().numpy()
            predictions[kind] = np.exp(target_mean + target_scale * normalized_prediction)
            if horizon == 5 and kind == "transformer" and fold == len(splits) - 1:
                diagnostic_inputs = (
                    model,
                    standardized_sequences[split.test],
                    (log_target[split.test] - target_mean) / target_scale,
                )

        origin_variance = np.exp(features[:, 4])
        thresholds = np.quantile(origin_variance[split.train], [1 / 3, 2 / 3])
        regime = np.digitize(origin_variance[split.test], thresholds).astype(np.int8)
        for name, prediction in predictions.items():
            prediction_rows[name].append(np.clip(prediction, 1e-12, 1.0))
        actual_rows.append(target[split.test])
        test_rows.append(split.test)
        fold_rows.append(np.full(len(split.test), fold, dtype=np.int16))
        regime_rows.append(regime)
        scaler_mean.append(standardizer.mean)
        scaler_scale.append(standardizer.scale)
        pca_mean.append(pca.mean)
        pca_components.append(pca.components)
        pca_variance.append(pca.explained_variance)
        sequence_mean.append(sequence_standardizer.mean)
        sequence_scale.append(sequence_standardizer.scale)
        garch_parameters.append([garch.omega, garch.alpha, garch.beta])
        regime_thresholds.append(thresholds)
        fold_bounds.append([split.train[0], split.train[-1] + 1, split.test[0], split.test[-1] + 1])

    actual = np.concatenate(actual_rows)
    predictions = {name: np.concatenate(rows) for name, rows in prediction_rows.items()}
    regime = np.concatenate(regime_rows)
    losses = {name: _qlike_losses(actual, prediction) for name, prediction in predictions.items()}
    model_metrics = {
        name: _model_forecast_report(
            actual,
            prediction,
            regime,
            seed=seed + 1_000 * horizon + 100 * index,
        )
        for index, (name, prediction) in enumerate(predictions.items())
    }
    paired = {
        name: _ci_dict(losses[name] - losses["log_har"], seed=seed + 20_000 + index)
        for index, name in enumerate(model_names)
        if name != "log_har"
    }
    fold_bounds_array = np.asarray(fold_bounds, dtype=np.int64)
    horizon_arrays = {
        "features": features,
        "target_variance": target,
        "target_log_variance": log_target,
        "target_surface_latent": latent_target,
        "source_time_index": time_index,
        "returns": returns,
        "sequence_features": sequences,
        "fold_bounds": fold_bounds_array,
        "test_row": np.concatenate(test_rows),
        "prediction_fold": np.concatenate(fold_rows),
        "regime_code": regime,
        "actual": actual,
        "scaler_mean": np.stack(scaler_mean),
        "scaler_scale": np.stack(scaler_scale),
        "pca_mean": np.stack(pca_mean),
        "pca_components": np.stack(pca_components),
        "pca_explained_variance": np.stack(pca_variance),
        "sequence_scaler_mean": np.stack(sequence_mean),
        "sequence_scaler_scale": np.stack(sequence_scale),
        "garch_parameters": np.asarray(garch_parameters),
        "regime_thresholds": np.asarray(regime_thresholds),
        **{f"prediction_{name}": value for name, value in predictions.items()},
        **{f"qlike_{name}": value for name, value in losses.items()},
    }
    diagnostics = (
        _attention_diagnostics(*diagnostic_inputs, seed=seed + 90_000)
        if diagnostic_inputs is not None
        else None
    )
    return (
        {
            "target": f"future realized variance sum over t+1...t+{horizon}",
            "horizon": horizon,
            "embargo": embargo,
            "n_folds": len(splits),
            "preprocessing_fit_scope": "train_only_each_fold",
            "pca_components": 4,
            "purge_rule": "train_end + horizon + embargo < test_start",
            "minimum_observed_purge_gap": int(
                np.min(fold_bounds_array[:, 2] - (fold_bounds_array[:, 1] - 1))
            ),
            "regime_definition": {
                "observable": "origin latent variance",
                "thresholds": "within-fold training-window terciles",
                "codes": {"0": "low", "1": "middle", "2": "high"},
            },
            "models": model_metrics,
            "paired_qlike_difference_model_minus_log_har": paired,
            "block_bootstrap": {"maximum_block_size": 8, "replications": 160, "confidence": 0.95},
        },
        horizon_arrays,
        diagnostics,
    )


def _walk_forward_reference(seed: int) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    horizons = (1, 5, 21)
    metrics_by_horizon: dict[str, Any] = {}
    arrays: dict[str, np.ndarray] = {}
    horizon_five: dict[str, np.ndarray] | None = None
    attention_metrics: dict[str, Any] | None = None
    for horizon in horizons:
        horizon_metrics, horizon_arrays, diagnostics = _walk_forward_horizon(
            seed=seed,
            horizon=horizon,
        )
        metrics_by_horizon[str(horizon)] = horizon_metrics
        arrays.update(
            {f"walk_forward_h{horizon}_{name}": value for name, value in horizon_arrays.items()}
        )
        if horizon == 5:
            horizon_five = horizon_arrays
            if diagnostics is None:
                raise RuntimeError("five-day transformer diagnostics were not produced")
            attention_metrics, diagnostic_arrays = diagnostics
            arrays.update(diagnostic_arrays)
    if horizon_five is None or attention_metrics is None:  # pragma: no cover
        raise RuntimeError("five-day compatibility reference is missing")

    five_metrics = metrics_by_horizon["5"]
    compatibility_models = {
        "persistence": five_metrics["models"]["persistence"],
        "ewma": five_metrics["models"]["ewma"],
        "har_ridge": five_metrics["models"]["log_har"],
        "pca_ridge_challenger": five_metrics["models"]["pca_ridge_challenger"],
    }
    arrays.update(
        {
            "dynamics_features": horizon_five["features"],
            "dynamics_target_variance": horizon_five["target_variance"],
            "dynamics_source_time_index": horizon_five["source_time_index"],
            "dynamics_returns": horizon_five["returns"],
            "walk_forward_fold_bounds": horizon_five["fold_bounds"],
            "walk_forward_test_row": horizon_five["test_row"],
            "walk_forward_prediction_fold": horizon_five["prediction_fold"],
            "walk_forward_actual": horizon_five["actual"],
            "walk_forward_prediction_persistence": horizon_five["prediction_persistence"],
            "walk_forward_prediction_ewma": horizon_five["prediction_ewma"],
            "walk_forward_prediction_har_ridge": horizon_five["prediction_log_har"],
            "walk_forward_prediction_challenger": horizon_five["prediction_pca_ridge_challenger"],
            "walk_forward_qlike_persistence": horizon_five["qlike_persistence"],
            "walk_forward_qlike_ewma": horizon_five["qlike_ewma"],
            "walk_forward_qlike_har_ridge": horizon_five["qlike_log_har"],
            "walk_forward_qlike_challenger": horizon_five["qlike_pca_ridge_challenger"],
            "walk_forward_scaler_mean": horizon_five["scaler_mean"],
            "walk_forward_scaler_scale": horizon_five["scaler_scale"],
            "walk_forward_pca_mean": horizon_five["pca_mean"],
            "walk_forward_pca_components": horizon_five["pca_components"],
            "walk_forward_pca_explained_variance": horizon_five["pca_explained_variance"],
        }
    )
    return (
        {
            "target": five_metrics["target"],
            "target_families": {
                "log_realized_variance_horizons": list(horizons),
                "future_realized_variance_horizons": list(horizons),
                "surface_latent_horizons": list(horizons),
                "surface_latent_dimension": int(horizon_five["target_surface_latent"].shape[1]),
            },
            "horizon": 5,
            "horizons": list(horizons),
            "embargo": five_metrics["embargo"],
            "n_folds": five_metrics["n_folds"],
            "preprocessing_fit_scope": five_metrics["preprocessing_fit_scope"],
            "pca_components": five_metrics["pca_components"],
            "purge_rule": five_metrics["purge_rule"],
            "minimum_observed_purge_gap": five_metrics["minimum_observed_purge_gap"],
            "models": compatibility_models,
            "model_comparison_by_horizon": metrics_by_horizon,
            "attention_diagnostics": attention_metrics,
            "research_track": {
                "foundation_model": "local_optional_adapter_only",
                "conditional_diffusion": "scenario_diagnostic_only",
                "core_gate_dependency": False,
                "default_download": False,
            },
            "block_bootstrap": five_metrics["block_bootstrap"],
        },
        arrays,
    )


def build_vol20_reference(
    *,
    seed: int = 2000,
    hedge_paths: int = 512,
    hedge_steps: int = 12,
    phase1_positions: np.ndarray | None = None,
) -> ReferenceBundle:
    """Build purged forecasting and common-path hedge artifacts for volume 20."""

    if seed < 0 or hedge_paths < 100 or hedge_steps < 2:
        raise ValueError("invalid vol-20 quick reference configuration")
    if phase1_positions is not None:
        supplied = np.asarray(phase1_positions, dtype=float)
        if supplied.shape != (hedge_paths, hedge_steps) or np.any(~np.isfinite(supplied)):
            raise ValueError(
                "phase1_positions must be finite with shape [hedge_paths, hedge_steps]"
            )
    else:
        supplied = None
    dynamics_metrics, dynamics_arrays = _walk_forward_reference(seed + 10)
    pipeline = run_synthetic_surface_hedge_pipeline(
        seed=seed + 20,
        n_paths=hedge_paths,
        n_steps=hedge_steps,
        deep_policy_positions=supplied,
    )
    strategy_names = sorted(pipeline.hedge.pnl)
    hedge_pnl = np.stack([pipeline.hedge.pnl[name] for name in strategy_names])
    hedge_turnover = np.stack([pipeline.hedge.turnover[name] for name in strategy_names])
    phase1_status = "evaluated_external_positions" if supplied is not None else "not_evaluated"
    arrays = {
        **dynamics_arrays,
        "e2e_true_parameters": pipeline.true_parameters,
        "e2e_calibrated_parameters": pipeline.calibration.parameters,
        "e2e_path_ids": pipeline.hedge.path_ids,
        "e2e_hedge_pnl": hedge_pnl,
        "e2e_hedge_turnover": hedge_turnover,
    }
    if supplied is not None:
        arrays["e2e_phase1_positions"] = supplied
    metrics: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": "johnhull_frontier_reference",
        "volume": 20,
        "seed": seed,
        "execution_profile": "cpu_quick",
        "data_policy": "synthetic_offline_actual_pipeline_execution",
        "walk_forward": dynamics_metrics,
        "end_to_end": {
            "chain": ["surrogate", "multi_start_calibration", "forecast", "common_path_hedge"],
            "surrogate_kind": "deterministic polynomial quote surrogate",
            "calibration_n_starts": len(pipeline.calibration.starts),
            "calibration_repricing_rmse": pipeline.calibration.repricing_rmse,
            "calibration_parameter_rmse": float(
                np.sqrt(np.mean((pipeline.calibration.parameters - pipeline.true_parameters) ** 2))
            ),
            "forecast_variance": pipeline.forecast_variance,
            "forecast_volatility": pipeline.forecast_volatility,
            "common_path_count": hedge_paths,
            "common_path_id_fingerprint": "sha256:"
            + hashlib.sha256(pipeline.hedge.path_ids.tobytes()).hexdigest(),
            "strategy_order": strategy_names,
            "strategy_metrics": pipeline.hedge.metrics,
            "comparison_controls": {
                "paths": "common",
                "premium": "common_zero_rate_BSM_at_scenario_volatility",
                "transaction_cost_rate": DEFAULT_TRANSACTION_COST,
                "transaction_cost_convention": "common_proportional_notional",
                "pathwise_pairing": True,
            },
            "no_trade_region": {
                "strategy": "no-trade",
                "delta_width": DEFAULT_NO_TRADE_WIDTH,
                "units": "stock_delta",
                "observed_no_change_fraction": pipeline.hedge.metrics["no-trade"][
                    "no_change_fraction"
                ],
            },
        },
        "phase1_deep_policy": {
            "status": phase1_status,
            "reason": (
                "external positions supplied"
                if supplied is not None
                else "no real Phase-1 checkpoint positions were supplied to the core reference run"
            ),
            "positions_adapter_contract": {
                "argument": "phase1_positions",
                "dtype": "finite float64-compatible",
                "shape": [hedge_paths, hedge_steps],
                "units": "stock units held at each trade time",
                "path_alignment": "row i must match e2e_path_ids[i] under the documented seed",
                "evaluation_route": "run_synthetic_surface_hedge_pipeline(deep_policy_positions=...)",
            },
            "evaluated_on_common_path_ids": supplied is not None,
            "common_premium_and_cost_convention": supplied is not None,
        },
        "limitations": [
            "forecast inputs and returns are synthetic and offline",
            "quick block-bootstrap intervals are methodological references, not production estimates",
            "Phase-1 is not represented unless real externally generated positions are supplied",
        ],
    }
    units = {
        "dynamics_target_variance": "future_variance_sum",
        "dynamics_returns": "log_return",
        "walk_forward_actual": "future_variance_sum",
        "walk_forward_prediction_persistence": "future_variance_sum",
        "walk_forward_prediction_ewma": "future_variance_sum",
        "walk_forward_prediction_har_ridge": "future_variance_sum",
        "walk_forward_prediction_challenger": "future_variance_sum",
        "e2e_hedge_pnl": "currency_units",
        "e2e_hedge_turnover": "currency_notional",
    }
    return _finalize(metrics, arrays, units)


def build_frontier_reference(volume: int, **kwargs: Any) -> ReferenceBundle:
    """Dispatch a volume-specific reference builder for central integration."""

    if volume == 19:
        return build_vol19_reference(**kwargs)
    if volume == 20:
        return build_vol20_reference(**kwargs)
    raise ValueError("frontier reference volume must be 19 or 20")
