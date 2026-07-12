"""Reproducible orchestration for experiments A--G and durable artifacts."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy.special import gamma as gamma_function

from rough_volatility.config import (
    BergomiConfig,
    ProjectConfig,
    provenance_stamp,
    save_config,
)
from rough_volatility.diagnostics import (
    acf_fft,
    log_spaced_lags,
    rolling_realized_variance,
    structure_function,
)
from rough_volatility.estimators import (
    ESTIMATORS,
    hurst_madogram,
    hurst_variogram,
    loglog_ols,
)
from rough_volatility.fbm import fbm_paths
from rough_volatility.fractional_ou import fou_euler, ou_exact
from rough_volatility.hawkes import (
    integrated_intensity,
    intensity_on_grid,
    make_scenario,
    simulate_thinning,
)
from rough_volatility.heston import (
    expected_variance,
)
from rough_volatility.heston import (
    simulate_given_normals as simulate_heston_given_normals,
)
from rough_volatility.microstructure import (
    bin_events,
    effective_hurst_of_log_rv,
    noise_fragility_study,
    price_from_events,
    rv_diagnostics,
)
from rough_volatility.option_pricing import smile_from_terminals, surface_from_terminals
from rough_volatility.random import stream
from rough_volatility.rough_bergomi import build_operators, simulate_chunked
from rough_volatility.skew import atm_skew, power_law_fit, skew_window

LOGGER = logging.getLogger(__name__)
FloatArray = NDArray[np.float64]


def ensure_output_directories(config: ProjectConfig, project_root: str | Path) -> dict[str, Path]:
    """Create and return the project output directories."""
    root = Path(project_root).resolve()
    artifacts = root / config.output.artifacts_dir
    paths = {
        "artifacts": artifacts,
        "data": artifacts / "data",
        "metrics": artifacts / "metrics",
        "figures": artifacts / "figures",
        "reports": root / config.output.reports_dir,
        "notebooks": root / Path(config.output.notebook_path).parent,
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        numeric = float(value)
        return numeric if np.isfinite(numeric) else None
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    return value


def write_json(
    payload: dict[str, Any],
    path: str | Path,
    *,
    config: ProjectConfig,
    sample_size: int,
) -> Path:
    """Write JSON with the seven common provenance fields at top level."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    stamped = {**payload, **provenance_stamp(config, sample_size)}
    output.write_text(json.dumps(_json_safe(stamped), indent=2, sort_keys=True), encoding="utf-8")
    return output


def _write_csv(
    frame: pd.DataFrame,
    path: Path,
    config: ProjectConfig,
) -> Path:
    """Write tabular data with repeated provenance columns for portability."""
    output = frame.copy()
    stamp = provenance_stamp(config, len(output))
    for key, value in reversed(list(stamp.items())):
        column = key if key not in output.columns else f"artifact_{key}"
        output.insert(0, column, value)
    path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(path, index=False)
    return path


def _reuse_marker(
    marker: Path,
    config: ProjectConfig,
    *,
    force: bool,
) -> dict[str, Path] | None:
    if force or not marker.exists():
        return None
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
        if payload.get("params_fingerprint") != config.fingerprint():
            return None
        artifacts = {key: Path(value) for key, value in payload.get("artifacts", {}).items()}
        if not artifacts or not all(path.exists() for path in artifacts.values()):
            return None
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None
    letter = str(payload.get("experiment", "")).lower()
    return artifacts | {f"experiment_{letter}_metrics": marker}


def _finish_experiment(
    letter: str,
    config: ProjectConfig,
    marker: Path,
    artifacts: dict[str, Path],
    metrics: dict[str, Any],
    *,
    sample_size: int,
) -> dict[str, Path]:
    write_json(
        {
            "experiment": letter.upper(),
            "artifacts": {key: str(path) for key, path in artifacts.items()},
            "metrics": metrics,
        },
        marker,
        config=config,
        sample_size=sample_size,
    )
    return artifacts | {f"experiment_{letter.lower()}_metrics": marker}


def _mean_acf(paths: FloatArray, max_lag: int) -> FloatArray:
    return np.mean([acf_fft(path, max_lag) for path in paths], axis=0)


def run_experiment_a(
    config: ProjectConfig,
    root: str | Path,
    *,
    force: bool = False,
) -> dict[str, Path]:
    """Run path, zoom, increment, ACF and structure-function comparisons."""
    config.validate()
    outputs = ensure_output_directories(config, root)
    marker = outputs["metrics"] / "experiment_a.json"
    reused = _reuse_marker(marker, config, force=force)
    if reused is not None:
        return reused
    LOGGER.info("Experiment A: fBM roughness comparison")

    path_frames: list[pd.DataFrame] = []
    increment_frames: list[pd.DataFrame] = []
    structure_rows: list[dict[str, Any]] = []
    acf_rows: list[dict[str, Any]] = []
    embedding_rows: list[dict[str, Any]] = []
    fit_metrics: list[dict[str, Any]] = []
    for h in config.fbm.h_values:
        result = fbm_paths(
            h,
            config.fbm.n_steps,
            config.fbm.n_paths,
            config.fbm.horizon,
            stream(config.seed, f"fbm_a_{h:g}"),
        )
        n_display = min(config.fbm.n_display_paths, config.fbm.n_paths)
        for path_id in range(n_display):
            path_frames.append(
                pd.DataFrame(
                    {
                        "h": h,
                        "path_id": path_id,
                        "time": result.times,
                        "value": result.paths[path_id],
                    }
                )
            )
            increment_frames.append(
                pd.DataFrame(
                    {
                        "h": h,
                        "path_id": path_id,
                        "time": result.times[1:],
                        "increment": np.diff(result.paths[path_id]),
                    }
                )
            )
        max_lag = min(60, max(2, config.fbm.n_steps // 20))
        increment_acf = _mean_acf(np.diff(result.paths, axis=1), max_lag)
        acf_rows.extend(
            {"h": h, "lag": lag, "acf": value} for lag, value in enumerate(increment_acf)
        )
        lags = log_spaced_lags(
            config.fbm.n_steps + 1,
            config.fbm.n_lags,
            config.fbm.max_lag_fraction,
        )
        moments = structure_function(result.paths, (1.0, 2.0), lags)
        for q_index, q in enumerate((1.0, 2.0)):
            fit = loglog_ols(lags, moments[q_index])
            h_hat = fit.slope / q
            fit_metrics.append(
                {
                    "true_h": h,
                    "q": q,
                    "slope": fit.slope,
                    "h_hat": h_hat,
                    "slope_se": fit.slope_se,
                    "r_squared": fit.r_squared,
                }
            )
            structure_rows.extend(
                {
                    "h": h,
                    "q": q,
                    "lag": int(lag),
                    "delta": float(lag * config.fbm.horizon / config.fbm.n_steps),
                    "moment": float(moment),
                    "fitted": float(np.exp(fit.intercept) * lag**fit.slope),
                }
                for lag, moment in zip(lags, moments[q_index], strict=True)
            )
        embedding_rows.append({"h": h, **asdict(result.diagnostics)})

    artifacts = {
        "fbm_paths": _write_csv(
            pd.concat(path_frames, ignore_index=True),
            outputs["data"] / "fbm_paths.csv",
            config,
        ),
        "fbm_increments": _write_csv(
            pd.concat(increment_frames, ignore_index=True),
            outputs["data"] / "fbm_increments.csv",
            config,
        ),
        "fbm_structure": _write_csv(
            pd.DataFrame(structure_rows), outputs["data"] / "fbm_structure.csv", config
        ),
        "fbm_acf": _write_csv(
            pd.DataFrame(acf_rows), outputs["data"] / "fbm_increment_acf.csv", config
        ),
    }
    return _finish_experiment(
        "a",
        config,
        marker,
        artifacts,
        {"structure_fits": fit_metrics, "embeddings": embedding_rows},
        sample_size=config.fbm.n_paths,
    )


def run_experiment_b(
    config: ProjectConfig,
    root: str | Path,
    *,
    force: bool = False,
) -> dict[str, Path]:
    """Run Hurst-estimator recovery across true H and sample size."""
    config.validate()
    outputs = ensure_output_directories(config, root)
    marker = outputs["metrics"] / "experiment_b.json"
    reused = _reuse_marker(marker, config, force=force)
    if reused is not None:
        return reused
    LOGGER.info("Experiment B: Hurst estimator recovery")

    rows: list[dict[str, Any]] = []
    maximum = max(config.hurst.sample_sizes)
    for h in config.hurst.h_values:
        paths = fbm_paths(
            h,
            maximum,
            config.hurst.n_replications,
            1.0,
            stream(config.seed, f"hurst_b_{h:g}"),
        ).paths
        for sample_size in config.hurst.sample_sizes:
            lags = log_spaced_lags(sample_size + 1, config.hurst.n_lags, 0.10)
            for replication, full_path in enumerate(paths):
                path = full_path[: sample_size + 1]
                for estimator_name in config.hurst.estimators:
                    try:
                        if estimator_name == "variogram":
                            estimate = hurst_variogram(path, lags)
                        elif estimator_name == "madogram":
                            estimate = hurst_madogram(path, lags)
                        else:
                            estimate = ESTIMATORS[estimator_name](np.diff(path))
                        h_hat = estimate.h_hat
                        se = estimate.se
                        ok = np.isfinite(h_hat) and np.isfinite(se)
                    except ValueError:
                        h_hat = float("nan")
                        se = float("nan")
                        ok = False
                    rows.append(
                        {
                            "true_h": h,
                            "sample_size": sample_size,
                            "replication": replication,
                            "estimator": estimator_name,
                            "h_hat": h_hat,
                            "se": se,
                            "ci_low": h_hat - 1.96 * se if ok else np.nan,
                            "ci_high": h_hat + 1.96 * se if ok else np.nan,
                            "covered": bool(ok and h_hat - 1.96 * se <= h <= h_hat + 1.96 * se),
                            "ok": bool(ok),
                        }
                    )
    recovery = pd.DataFrame(rows)
    valid = recovery[recovery["ok"]].copy()
    valid["error"] = valid["h_hat"] - valid["true_h"]
    summary = (
        valid.groupby(["true_h", "sample_size", "estimator"], as_index=False)
        .agg(
            mean_h_hat=("h_hat", "mean"),
            sd_h_hat=("h_hat", "std"),
            bias=("error", "mean"),
            mse=("error", lambda values: float(np.mean(values**2))),
            coverage=("covered", "mean"),
            n_valid=("h_hat", "size"),
        )
        .assign(rmse=lambda frame: np.sqrt(frame["mse"]))
        .drop(columns="mse")
    )
    artifacts = {
        "hurst_recovery": _write_csv(
            recovery, outputs["data"] / "hurst_estimator_recovery.csv", config
        ),
        "hurst_summary": _write_csv(
            summary, outputs["data"] / "hurst_estimator_summary.csv", config
        ),
    }
    return _finish_experiment(
        "b",
        config,
        marker,
        artifacts,
        {"summary": summary.to_dict(orient="records")},
        sample_size=len(recovery),
    )


def run_experiment_c(
    config: ProjectConfig,
    root: str | Path,
    *,
    force: bool = False,
) -> dict[str, Path]:
    """Compare matched-scale ordinary and fractional OU log-volatility."""
    config.validate()
    outputs = ensure_output_directories(config, root)
    marker = outputs["metrics"] / "experiment_c.json"
    reused = _reuse_marker(marker, config, force=force)
    if reused is not None:
        return reused
    LOGGER.info("Experiment C: OU versus fractional OU")

    dt = config.ou.horizon / config.ou.n_steps
    total_steps = config.ou.n_steps + config.ou.burn_in_steps
    total_horizon = dt * total_steps
    ou_sigma = config.ou.target_std * np.sqrt(2.0 * config.ou.kappa)
    standard_full = ou_exact(
        config.ou.kappa,
        config.ou.mean,
        ou_sigma,
        config.ou.x0,
        total_steps,
        total_horizon,
        config.ou.n_paths,
        stream(config.seed, "ou_c"),
    )
    standard = standard_full[:, config.ou.burn_in_steps :]
    fou_nu = config.ou.target_std * np.sqrt(
        2.0
        * config.ou.kappa ** (2.0 * config.ou.hurst)
        / gamma_function(2.0 * config.ou.hurst + 1.0)
    )
    fractional, embedding = fou_euler(
        config.ou.kappa,
        config.ou.mean,
        fou_nu,
        config.ou.hurst,
        config.ou.x0,
        config.ou.n_steps,
        config.ou.horizon,
        config.ou.n_paths,
        stream(config.seed, "fou_c"),
        burn_in_steps=config.ou.burn_in_steps,
    )
    times = np.linspace(0.0, config.ou.horizon, config.ou.n_steps + 1)
    path_frames: list[pd.DataFrame] = []
    diagnostic_rows: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {
        "ou_diffusion": ou_sigma,
        "fou_noise_scale": fou_nu,
        "fou_embedding": asdict(embedding),
    }
    for model, paths in (("OU (H=0.5)", standard), (f"fOU (H={config.ou.hurst:g})", fractional)):
        for path_id in range(min(config.fbm.n_display_paths, config.ou.n_paths)):
            path_frames.append(
                pd.DataFrame(
                    {
                        "model": model,
                        "path_id": path_id,
                        "time": times,
                        "log_volatility": paths[path_id],
                        "volatility": np.exp(paths[path_id]),
                    }
                )
            )
        max_lag = min(60, max(2, config.ou.n_steps // 20))
        level_acf = _mean_acf(paths, max_lag)
        increment_acf = _mean_acf(np.diff(paths, axis=1), max_lag)
        diagnostic_rows.extend(
            {"model": model, "metric": "level_acf", "x": lag, "value": value}
            for lag, value in enumerate(level_acf)
        )
        diagnostic_rows.extend(
            {"model": model, "metric": "increment_acf", "x": lag, "value": value}
            for lag, value in enumerate(increment_acf)
        )
        lags = log_spaced_lags(config.ou.n_steps + 1, config.fbm.n_lags, 0.05)
        sf = structure_function(paths, (2.0,), lags)[0]
        diagnostic_rows.extend(
            {"model": model, "metric": "structure_q2", "x": int(lag), "value": value}
            for lag, value in zip(lags, sf, strict=True)
        )
        rv_window = max(4, min(config.ou.n_steps // 20, 100))
        rv = rolling_realized_variance(np.diff(paths, axis=1), rv_window)
        mean_rv = np.full(rv.shape[1], np.nan)
        mean_rv[rv_window - 1 :] = np.mean(rv[:, rv_window - 1 :], axis=0)
        diagnostic_rows.extend(
            {
                "model": model,
                "metric": "rolling_rv_mean",
                "x": index + 1,
                "value": value,
            }
            for index, value in enumerate(mean_rv)
            if np.isfinite(value)
        )
        estimate = hurst_variogram(paths[0], lags)
        metrics[model] = {
            "mean": float(paths.mean()),
            "std": float(paths.std()),
            "local_h_hat": estimate.h_hat,
        }
    artifacts = {
        "ou_paths": _write_csv(
            pd.concat(path_frames, ignore_index=True),
            outputs["data"] / "ou_fou_paths.csv",
            config,
        ),
        "ou_diagnostics": _write_csv(
            pd.DataFrame(diagnostic_rows),
            outputs["data"] / "ou_fou_diagnostics.csv",
            config,
        ),
    }
    return _finish_experiment(
        "c",
        config,
        marker,
        artifacts,
        metrics,
        sample_size=config.ou.n_paths,
    )


@dataclass(frozen=True)
class _HestonChunkResult:
    terminals: dict[int, FloatArray]
    s_sample: FloatArray
    v_sample: FloatArray
    realized_variance: FloatArray
    checks: dict[str, Any]


def _simulate_heston_chunked(
    config: ProjectConfig,
    times: FloatArray,
    maturity_indices: tuple[int, ...],
) -> _HestonChunkResult:
    n_paths = config.bergomi.n_paths
    n_steps = config.bergomi.n_steps
    terminals = {index: np.empty(n_paths) for index in maturity_indices}
    variance_terminals = {index: np.empty(n_paths) for index in maturity_indices}
    n_keep = min(config.bergomi.keep_paths, n_paths)
    s_sample = np.empty((n_keep, n_steps + 1))
    v_sample = np.empty((n_keep, n_steps + 1))
    realized = np.empty(n_paths)
    z_generator = stream(config.seed, "asset_z")
    z_perp_generator = stream(config.seed, "asset_zperp")
    for start in range(0, n_paths, config.bergomi.chunk_size):
        stop = min(start + config.bergomi.chunk_size, n_paths)
        count = stop - start
        paths = simulate_heston_given_normals(
            config.heston,
            config.bergomi.s0,
            config.bergomi.r,
            times,
            z_generator.standard_normal((count, n_steps)),
            z_perp_generator.standard_normal((count, n_steps)),
        )
        for index in maturity_indices:
            terminals[index][start:stop] = paths.s[:, index]
            variance_terminals[index][start:stop] = paths.v[:, index]
        realized[start:stop] = np.sum(np.diff(np.log(paths.s), axis=1) ** 2, axis=1)
        sample_stop = min(stop, n_keep)
        if start < sample_stop:
            local = sample_stop - start
            s_sample[start:sample_stop] = paths.s[:local]
            v_sample[start:sample_stop] = paths.v[:local]
    all_times = np.r_[0.0, times]
    checks: list[dict[str, Any]] = []
    for index in maturity_indices:
        variance_values = variance_terminals[index]
        variance_se = variance_values.std(ddof=1) / np.sqrt(n_paths)
        variance_target = float(expected_variance(config.heston, all_times[index]))
        spot_values = terminals[index]
        spot_se = spot_values.std(ddof=1) / np.sqrt(n_paths)
        spot_target = config.bergomi.s0 * np.exp(config.bergomi.r * all_times[index])
        checks.append(
            {
                "index": index,
                "time": all_times[index],
                "variance_mean": variance_values.mean(),
                "variance_expected": variance_target,
                "variance_z": (variance_values.mean() - variance_target) / variance_se
                if variance_se > 0
                else 0.0,
                "spot_mean": spot_values.mean(),
                "spot_expected": spot_target,
                "spot_z": (spot_values.mean() - spot_target) / spot_se if spot_se > 0 else 0.0,
            }
        )
    return _HestonChunkResult(
        terminals=terminals,
        s_sample=s_sample,
        v_sample=v_sample,
        realized_variance=realized,
        checks={"moments": checks, "common_random_streams": True},
    )


def _maturity_indices(config: ProjectConfig) -> tuple[int, ...]:
    return tuple(
        round(maturity * config.bergomi.n_steps / config.bergomi.maturity_years)
        for maturity in config.options.maturities
    )


def _model_path_frame(
    model: str,
    times: FloatArray,
    spots: FloatArray,
    variances: FloatArray,
) -> pd.DataFrame:
    frames = []
    for path_id in range(spots.shape[0]):
        frames.append(
            pd.DataFrame(
                {
                    "model": model,
                    "path_id": path_id,
                    "time": times,
                    "spot": spots[path_id],
                    "variance": variances[path_id],
                }
            )
        )
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def run_experiment_d(
    config: ProjectConfig,
    root: str | Path,
    *,
    force: bool = False,
) -> dict[str, Path]:
    """Compare rough Bergomi and Heston under common Brownian normals."""
    config.validate()
    outputs = ensure_output_directories(config, root)
    marker = outputs["metrics"] / "experiment_d.json"
    reused = _reuse_marker(marker, config, force=force)
    if reused is not None:
        return reused
    LOGGER.info("Experiment D: rough Bergomi versus Heston")

    times = np.linspace(
        config.bergomi.maturity_years / config.bergomi.n_steps,
        config.bergomi.maturity_years,
        config.bergomi.n_steps,
    )
    indices = _maturity_indices(config)
    operators = build_operators(config.bergomi.h, times)
    rough = simulate_chunked(
        config.bergomi,
        operators,
        config.seed,
        maturity_indices=indices,
    )
    heston = _simulate_heston_chunked(config, times, indices)
    maturity_to_index = dict(zip(config.options.maturities, indices, strict=True))
    strike_grid = np.linspace(
        -config.options.log_moneyness_span,
        config.options.log_moneyness_span,
        config.options.n_strikes,
    )
    surface_frames = []
    for model, terminals in (
        ("rough_bergomi", rough.s_by_maturity),
        ("heston", heston.terminals),
    ):
        by_maturity = {maturity: terminals[index] for maturity, index in maturity_to_index.items()}
        surface = surface_from_terminals(
            by_maturity,
            config.bergomi.s0,
            strike_grid,
            r=config.bergomi.r,
        )
        surface.insert(0, "model", model)
        surface_frames.append(surface)
    option_surface = pd.concat(surface_frames, ignore_index=True)

    all_times = np.r_[0.0, times]
    model_paths = pd.concat(
        [
            _model_path_frame("rough_bergomi", all_times, rough.s_sample, rough.v_sample),
            _model_path_frame("heston", all_times, heston.s_sample, heston.v_sample),
        ],
        ignore_index=True,
    )
    terminal_frames = []
    for model, terminal, realized in (
        (
            "rough_bergomi",
            rough.s_by_maturity[indices[-1]],
            rough.realized_variance,
        ),
        ("heston", heston.terminals[indices[-1]], heston.realized_variance),
    ):
        terminal_frames.append(
            pd.DataFrame(
                {
                    "model": model,
                    "terminal_log_return": np.log(terminal / config.bergomi.s0),
                    "realized_variance": realized,
                }
            )
        )
    terminal_distribution = pd.concat(terminal_frames, ignore_index=True)

    leverage_frames = []
    for model, spots, variances in (
        ("rough_bergomi", rough.s_sample, rough.v_sample),
        ("heston", heston.s_sample, heston.v_sample),
    ):
        returns = np.diff(np.log(spots), axis=1).ravel()
        future_change = np.diff(variances, axis=1).ravel()
        count = min(50_000, returns.size)
        selection = stream(config.seed, f"leverage_{model}").choice(
            returns.size, count, replace=False
        )
        leverage_frames.append(
            pd.DataFrame(
                {
                    "model": model,
                    "return": returns[selection],
                    "future_variance_change": future_change[selection],
                }
            )
        )
    leverage = pd.concat(leverage_frames, ignore_index=True)
    metrics = {
        "rough_bergomi": rough.ev_check,
        "heston": heston.checks,
        "volterra_operator": {
            "diag_error": operators.diag_error,
            "jitter_used": operators.jitter_used,
        },
        "leverage_correlation": {
            model: float(group["return"].corr(group["future_variance_change"]))
            for model, group in leverage.groupby("model")
        },
    }
    artifacts = {
        "model_paths": _write_csv(model_paths, outputs["data"] / "model_paths.csv", config),
        "terminal_distributions": _write_csv(
            terminal_distribution,
            outputs["data"] / "terminal_distributions.csv",
            config,
        ),
        "option_surface": _write_csv(
            option_surface, outputs["data"] / "option_surface.csv", config
        ),
        "leverage_data": _write_csv(leverage, outputs["data"] / "leverage_relation.csv", config),
    }
    return _finish_experiment(
        "d",
        config,
        marker,
        artifacts,
        metrics,
        sample_size=config.bergomi.n_paths,
    )


def _forward_curve_for_horizon(
    config: BergomiConfig, horizon: float
) -> tuple[tuple[float, float], ...]:
    if not config.forward_variance:
        return ()
    points = np.asarray(config.forward_variance)
    value_at_horizon = float(np.interp(horizon, points[:, 0], points[:, 1]))
    kept = [(float(time), float(value)) for time, value in points if time < horizon]
    if not kept or kept[-1][0] != horizon:
        kept.append((horizon, value_at_horizon))
    return tuple(kept)


def run_experiment_e(
    config: ProjectConfig,
    root: str | Path,
    *,
    force: bool = False,
) -> dict[str, Path]:
    """Estimate short-maturity ATM skew and its H-dependent power law."""
    config.validate()
    outputs = ensure_output_directories(config, root)
    marker = outputs["metrics"] / "experiment_e.json"
    reused = _reuse_marker(marker, config, force=force)
    if reused is not None:
        return reused
    LOGGER.info("Experiment E: short-maturity skew scaling")

    smile_frames: list[pd.DataFrame] = []
    term_rows: list[dict[str, Any]] = []
    operator_rows: list[dict[str, Any]] = []
    for h in config.bergomi.h_grid:
        for maturity in config.options.maturities:
            local = replace(
                config.bergomi,
                h=h,
                maturity_years=maturity,
                n_steps=config.options.skew_maturity_steps,
                keep_paths=0,
                forward_variance=_forward_curve_for_horizon(config.bergomi, maturity),
            )
            times = np.linspace(maturity / local.n_steps, maturity, local.n_steps, dtype=np.float64)
            operators = build_operators(h, times)
            result = simulate_chunked(
                local,
                operators,
                config.seed + 7000,
                maturity_indices=(local.n_steps,),
                keep_paths=0,
            )
            window = skew_window(
                maturity,
                config.bergomi.xi0,
                config.options.skew_window_coeff,
                config.options.skew_window_cap,
                config.options.skew_window_floor,
            )
            k_grid = np.linspace(-window, window, 9)
            smile = smile_from_terminals(
                result.s_by_maturity[local.n_steps],
                config.bergomi.s0,
                k_grid,
                maturity=maturity,
                r=config.bergomi.r,
            )
            estimate = atm_skew(smile, window + 1e-12)
            smile.insert(0, "maturity", maturity)
            smile.insert(0, "h", h)
            smile_frames.append(smile)
            term_rows.append(
                {
                    "h": h,
                    "maturity": maturity,
                    "skew": estimate.slope,
                    "skew_se": estimate.se,
                    "n_used": estimate.n_used,
                    "window": window,
                    "r_squared": estimate.r_squared,
                    "ok": estimate.ok,
                }
            )
            operator_rows.append(
                {
                    "h": h,
                    "maturity": maturity,
                    "diag_error": operators.diag_error,
                    "jitter_used": operators.jitter_used,
                }
            )
    smiles = pd.concat(smile_frames, ignore_index=True)
    term = pd.DataFrame(term_rows)
    power_rows = []
    for h, group in term.groupby("h", sort=True):
        fit = power_law_fit(group)
        power_rows.append(
            {
                "h": h,
                "beta": fit.beta,
                "beta_se": fit.beta_se,
                "theoretical_beta": h - 0.5,
                "beta_error": fit.beta - (h - 0.5) if fit.ok else np.nan,
                "intercept": fit.intercept,
                "r_squared": fit.r_squared,
                "h_implied": fit.h_implied,
                "n_used": fit.n_used,
                "ok": fit.ok,
            }
        )
    powers = pd.DataFrame(power_rows)
    artifacts = {
        "skew_smiles": _write_csv(smiles, outputs["data"] / "skew_smiles.csv", config),
        "skew_term_structure": _write_csv(
            term, outputs["data"] / "skew_term_structure.csv", config
        ),
        "skew_power_law": _write_csv(powers, outputs["data"] / "skew_power_law.csv", config),
    }
    return _finish_experiment(
        "e",
        config,
        marker,
        artifacts,
        {
            "power_laws": powers.to_dict(orient="records"),
            "operators": operator_rows,
            "finite_sample_caveat": (
                "Fitted exponents are finite-maturity Monte Carlo diagnostics, not exact asymptotic proofs."
            ),
        },
        sample_size=config.bergomi.n_paths,
    )


def run_experiment_f(
    config: ProjectConfig,
    root: str | Path,
    *,
    force: bool = False,
) -> dict[str, Path]:
    """Compare Poisson, stable and near-critical Hawkes microstructure."""
    config.validate()
    outputs = ensure_output_directories(config, root)
    marker = outputs["metrics"] / "experiment_f.json"
    reused = _reuse_marker(marker, config, force=force)
    if reused is not None:
        return reused
    LOGGER.info("Experiment F: Hawkes microstructure")

    event_frames: list[pd.DataFrame] = []
    series_frames: list[pd.DataFrame] = []
    intensity_frames: list[pd.DataFrame] = []
    summaries: list[dict[str, Any]] = []
    for scenario in ("poisson", "stable", "critical"):
        model = make_scenario(scenario, config.hawkes)
        result = simulate_thinning(
            model,
            config.hawkes.horizon,
            stream(config.seed, f"hawkes_{scenario}"),
            max_events=config.hawkes.max_events,
        )
        event_frames.append(
            pd.DataFrame(
                {
                    "scenario": model.name,
                    "time": result.times,
                    "mark": result.marks,
                    "side": np.where(result.marks == 0, "buy", "sell"),
                }
            )
        )
        grid = np.linspace(0.0, config.hawkes.horizon, config.hawkes.intensity_grid_points)
        intensity = intensity_on_grid(model, result.times, result.marks, grid)
        intensity_frames.append(
            pd.DataFrame(
                {
                    "scenario": model.name,
                    "time": grid,
                    "buy_intensity": intensity[0],
                    "sell_intensity": intensity[1],
                    "total_intensity": intensity.sum(axis=0),
                }
            )
        )
        bins = bin_events(
            result.times,
            result.marks,
            config.hawkes.bin_width,
            config.hawkes.horizon,
        )
        priced = price_from_events(
            bins,
            config.microstructure.p0,
            config.microstructure.tick_eps,
            config.microstructure.observation_noise_std,
            stream(config.seed, f"microstructure_{scenario}"),
        )
        window = min(config.microstructure.rv_window, len(priced))
        diagnosed = rv_diagnostics(priced, max(2, window))
        diagnosed.insert(0, "scenario", model.name)
        series_frames.append(diagnosed)
        try:
            effective = effective_hurst_of_log_rv(
                diagnosed["rolling_rv"], config.microstructure.floor_quantile
            )
            effective_h = effective.h_hat
            effective_se = effective.se
        except ValueError:
            effective_h = float("nan")
            effective_se = float("nan")
        compensator = integrated_intensity(model, result.times, result.marks, config.hawkes.horizon)
        summaries.append(
            {
                "scenario": model.name,
                "branching_ratio": model.kernel.spectral_radius(),
                "baseline_per_side": model.mu[0],
                "event_count": result.times.size,
                "expected_event_count": 2 * config.hawkes.target_rate * config.hawkes.horizon,
                "realized_rate_per_side": result.realized_rate,
                "n_candidates": result.n_candidates,
                "truncated": result.truncated,
                "compensator_total": compensator.sum(),
                "compensator_relative_error": (compensator.sum() - result.times.size)
                / max(1, result.times.size),
                "effective_log_rv_h": effective_h,
                "effective_log_rv_h_se": effective_se,
                "effective_h_label": "empirical diagnostic only",
            }
        )
    events = pd.concat(event_frames, ignore_index=True)
    series = pd.concat(series_frames, ignore_index=True)
    intensity_data = pd.concat(intensity_frames, ignore_index=True)
    summary = pd.DataFrame(summaries)
    artifacts = {
        "hawkes_events": _write_csv(events, outputs["data"] / "hawkes_events.csv", config),
        "hawkes_series": _write_csv(
            series, outputs["data"] / "hawkes_microstructure_series.csv", config
        ),
        "hawkes_intensity": _write_csv(
            intensity_data, outputs["data"] / "hawkes_intensity.csv", config
        ),
        "hawkes_summary": _write_csv(summary, outputs["data"] / "hawkes_summary.csv", config),
    }
    return _finish_experiment(
        "f",
        config,
        marker,
        artifacts,
        {"scenarios": summaries, "structural_claim": False},
        sample_size=len(events),
    )


def run_experiment_g(
    config: ProjectConfig,
    root: str | Path,
    *,
    force: bool = False,
) -> dict[str, Path]:
    """Run observation-noise, sampling and estimator fragility analysis."""
    config.validate()
    outputs = ensure_output_directories(config, root)
    marker = outputs["metrics"] / "experiment_g.json"
    reused = _reuse_marker(marker, config, force=force)
    if reused is not None:
        return reused
    LOGGER.info("Experiment G: roughness-estimation fragility")
    study = noise_fragility_study(config.noise, config.seed)
    study["bias"] = study["h_hat_mean"] - config.noise.latent_h
    study["absolute_bias"] = study["bias"].abs()
    artifacts = {
        "noise_fragility": _write_csv(study, outputs["data"] / "noise_fragility.csv", config)
    }
    return _finish_experiment(
        "g",
        config,
        marker,
        artifacts,
        {
            "latent_h": config.noise.latent_h,
            "rows": study.to_dict(orient="records"),
            "interpretation": (
                "Estimator output changes with noise, sampling and preprocessing; H<1/2 alone does not identify a fractional data-generating process."
            ),
        },
        sample_size=len(study),
    )


def run_path_experiments(
    config: ProjectConfig,
    root: str | Path,
    *,
    force: bool = False,
) -> dict[str, Path]:
    """Run experiments A--C."""
    return (
        run_experiment_a(config, root, force=force)
        | run_experiment_b(config, root, force=force)
        | run_experiment_c(config, root, force=force)
    )


def run_option_experiments(
    config: ProjectConfig,
    root: str | Path,
    *,
    force: bool = False,
) -> dict[str, Path]:
    """Run experiments D--E."""
    return run_experiment_d(config, root, force=force) | run_experiment_e(config, root, force=force)


def run_microstructure_experiments(
    config: ProjectConfig,
    root: str | Path,
    *,
    force: bool = False,
) -> dict[str, Path]:
    """Run experiments F--G."""
    return run_experiment_f(config, root, force=force) | run_experiment_g(config, root, force=force)


def _read_experiment_metrics(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")).get("metrics", {})


def run_all(
    config: ProjectConfig,
    root: str | Path,
    *,
    force: bool = False,
) -> dict[str, Path]:
    """Run/reuse all experiments and write a fingerprinted artifact manifest."""
    config.validate()
    project_root = Path(root).resolve()
    outputs = ensure_output_directories(config, project_root)
    artifacts = (
        run_path_experiments(config, project_root, force=force)
        | run_option_experiments(config, project_root, force=force)
        | run_microstructure_experiments(config, project_root, force=force)
    )
    config_snapshot = save_config(config, outputs["artifacts"] / "resolved_config.yaml")
    artifacts["config_snapshot"] = config_snapshot

    experiment_metrics = {
        letter: _read_experiment_metrics(artifacts[f"experiment_{letter}_metrics"])
        for letter in "abcdefg"
    }
    d_metrics = experiment_metrics["d"]
    e_powers = experiment_metrics["e"].get("power_laws", [])
    target_power = next(
        (item for item in e_powers if np.isclose(item.get("h", np.nan), config.bergomi.h)),
        None,
    )
    checks = {
        "volterra_diagonal": {
            "passed": bool(
                d_metrics.get("volterra_operator", {}).get("diag_error", np.inf) <= 1e-10
            ),
            **d_metrics.get("volterra_operator", {}),
        },
        "rough_variance_and_spot_moments": {
            "passed": all(
                abs(item.get("z_score", np.inf)) < 5
                for category in ("variance", "spot")
                for item in d_metrics.get("rough_bergomi", {}).get(category, [])
            )
        },
        "heston_variance_and_spot_moments": {
            "passed": all(
                abs(item.get(key, np.inf)) < 5
                for item in d_metrics.get("heston", {}).get("moments", [])
                for key in ("variance_z", "spot_z")
            )
        },
        "rough_skew_power_law": {
            "passed": bool(
                target_power
                and target_power.get("ok")
                and -0.55 <= target_power.get("beta", np.inf) <= -0.22
            ),
            "fit": target_power,
            "reported_not_tightly_asserted": "beta - (H - 1/2)",
        },
        "hawkes_not_truncated": {
            "passed": all(
                not item.get("truncated", True)
                for item in experiment_metrics["f"].get("scenarios", [])
            )
        },
    }
    checks["all_passed"] = all(item.get("passed", False) for item in checks.values())
    validation_path = write_json(
        {"checks": checks},
        outputs["metrics"] / "validation_checks.json",
        config=config,
        sample_size=config.bergomi.n_paths,
    )
    artifacts["validation_checks"] = validation_path

    catalog_path = write_json(
        {
            "artifacts": {key: str(path) for key, path in artifacts.items()},
            "note": "CSV files repeat provenance columns; this catalog covers the resolved YAML snapshot.",
        },
        outputs["metrics"] / "artifact_metadata.json",
        config=config,
        sample_size=len(artifacts),
    )
    artifacts["artifact_metadata"] = catalog_path
    manifest_path = write_json(
        {"artifacts": {key: str(path) for key, path in artifacts.items()}},
        outputs["artifacts"] / "manifest.json",
        config=config,
        sample_size=len(artifacts),
    )
    return artifacts | {"manifest": manifest_path}


def load_artifact_manifest(
    config: ProjectConfig,
    project_root: str | Path,
) -> dict[str, Path]:
    """Load a matching artifact manifest or give an actionable re-run error."""
    path = Path(project_root).resolve() / config.output.artifacts_dir / "manifest.json"
    if not path.exists():
        raise FileNotFoundError(
            "artifact manifest is missing; run `python -m rough_volatility.cli all --config <profile>`"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("params_fingerprint") != config.fingerprint():
        raise ValueError(
            "artifact manifest fingerprint does not match this config; re-run experiments with the selected profile"
        )
    artifacts = {key: Path(value) for key, value in payload.get("artifacts", {}).items()}
    missing = [str(artifact) for artifact in artifacts.values() if not artifact.exists()]
    if missing:
        raise FileNotFoundError(
            "artifact manifest references missing files; re-run experiments: "
            + ", ".join(missing[:3])
        )
    return artifacts | {"manifest": path}
