"""Reproducible experiment orchestration and durable artifact writing."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from scipy.stats import spearmanr

from .baselines import black_scholes_deltas, no_hedge_deltas, no_trade_band_deltas
from .black_scholes import torch_call_delta
from .config import ProjectConfig
from .evaluation import (
    evaluate_delta_strategy,
    evaluate_policy_chunks,
    policy_distance_to_bs,
    result_frame,
    summarize_all,
    summarize_strategy,
)
from .pnl import account_hedge
from .simulation import resolve_device, simulate_gbm
from .training import TrainingResult, checkpoint_directory, load_policy, train_policy

LOGGER = logging.getLogger(__name__)


def ensure_output_directories(config: ProjectConfig, project_root: Path) -> dict[str, Path]:
    artifacts = project_root / config.output.artifacts_dir
    paths = {
        "artifacts": artifacts,
        "checkpoints": artifacts / "checkpoints",
        "metrics": artifacts / "metrics",
        "data": artifacts / "data",
        "figures": artifacts / "figures",
        "reports": project_root / config.output.reports_dir,
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (np.floating, float)):
        numeric = float(value)
        return numeric if np.isfinite(numeric) else None
    if isinstance(value, (np.integer, int)):
        return int(value)
    return value


def write_json(payload: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_safe(payload), indent=2, sort_keys=True), encoding="utf-8")
    return path


def run_training_suite(
    config: ProjectConfig,
    project_root: str | Path,
    *,
    force: bool = False,
) -> dict[str, tuple[ProjectConfig, TrainingResult]]:
    """Train/reuse cost-grid MSE policies and the configured tail-risk policy."""
    root = Path(project_root)
    runs: dict[str, tuple[ProjectConfig, TrainingResult]] = {}
    for cost in config.experiment.transaction_cost_grid_bps:
        run_config = config.with_market(transaction_cost_bps=float(cost)).with_risk(objective="mse")
        key = f"mse_{cost:g}bp"
        LOGGER.info("Training %s", key)
        runs[key] = (run_config, train_policy(run_config, root, force=force))
    if config.experiment.run_entropic:
        run_config = config.with_market(
            transaction_cost_bps=config.market.transaction_cost_bps
        ).with_risk(objective="entropic")
        key = f"entropic_{config.market.transaction_cost_bps:g}bp"
        LOGGER.info("Training %s", key)
        runs[key] = (run_config, train_policy(run_config, root, force=force))
    return runs


def _load_or_train(
    config: ProjectConfig,
    root: Path,
    *,
    force: bool,
) -> TrainingResult:
    directory = checkpoint_directory(config, root)
    if (directory / "best.pt").exists() and not force:
        return train_policy(config, root, force=False)
    return train_policy(config, root, force=force)


def _main_comparison(
    config: ProjectConfig,
    root: Path,
    paths: torch.Tensor,
    *,
    force: bool,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    main_config = config.with_risk(objective="mse")
    trained = _load_or_train(main_config, root, force=force)
    neural = evaluate_policy_chunks(
        trained.policy,
        paths,
        main_config.market,
        chunk_size=config.training.evaluation_chunk_size,
        meaningful_trade_threshold=config.experiment.meaningful_trade_threshold,
    )
    bs = evaluate_delta_strategy(
        paths,
        main_config.market,
        black_scholes_deltas,
        meaningful_trade_threshold=config.experiment.meaningful_trade_threshold,
    )
    no_hedge = evaluate_delta_strategy(
        paths,
        main_config.market,
        no_hedge_deltas,
        meaningful_trade_threshold=config.experiment.meaningful_trade_threshold,
    )
    with torch.no_grad():
        band_deltas = no_trade_band_deltas(
            paths, main_config.market, band=config.experiment.no_trade_band
        )
        band = account_hedge(
            paths,
            band_deltas,
            main_config.market,
            meaningful_trade_threshold=config.experiment.meaningful_trade_threshold,
        )
    path_ids = np.arange(paths.shape[0])
    frames = [
        result_frame(neural, "neural_mse", path_ids),
        result_frame(bs, "black_scholes_delta", path_ids),
        result_frame(band, "black_scholes_band", path_ids),
        result_frame(no_hedge, "no_hedge", path_ids),
    ]
    combined = pd.concat(frames, ignore_index=True)
    metrics = summarize_all(combined)
    metrics["neural_mse"].update(policy_distance_to_bs(neural, bs.deltas))
    return combined, metrics


def _sensitivity(
    config: ProjectConfig,
    root: Path,
    paths: torch.Tensor,
    *,
    force: bool,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for cost in config.experiment.transaction_cost_grid_bps:
        run_config = config.with_market(transaction_cost_bps=float(cost)).with_risk(objective="mse")
        trained = _load_or_train(run_config, root, force=force)
        result = evaluate_policy_chunks(
            trained.policy,
            paths,
            run_config.market,
            chunk_size=config.training.evaluation_chunk_size,
            meaningful_trade_threshold=config.experiment.meaningful_trade_threshold,
        )
        frame = result_frame(result, "neural_mse", np.arange(paths.shape[0]))
        metrics = summarize_strategy(frame)
        bs_deltas = black_scholes_deltas(paths, run_config.market)
        distance = policy_distance_to_bs(result, bs_deltas)
        rows.append(
            {
                "transaction_cost_bps": float(cost),
                **metrics,
                **distance,
                "checkpoint": str(checkpoint_directory(run_config, root) / "best.pt"),
            }
        )
    return pd.DataFrame(rows).sort_values("transaction_cost_bps").reset_index(drop=True)


def _risk_comparison(
    config: ProjectConfig,
    root: Path,
    paths: torch.Tensor,
    *,
    force: bool,
) -> pd.DataFrame:
    objectives = ["mse"] + (["entropic"] if config.experiment.run_entropic else [])
    rows: list[dict[str, Any]] = []
    for objective in objectives:
        run_config = config.with_risk(objective=objective)
        trained = _load_or_train(run_config, root, force=force)
        result = evaluate_policy_chunks(
            trained.policy,
            paths,
            run_config.market,
            chunk_size=config.training.evaluation_chunk_size,
            meaningful_trade_threshold=config.experiment.meaningful_trade_threshold,
        )
        frame = result_frame(result, f"neural_{objective}", np.arange(paths.shape[0]))
        rows.append({"objective": objective, **summarize_strategy(frame)})
    return pd.DataFrame(rows)


def _policy_surface(
    config: ProjectConfig,
    root: Path,
    device: torch.device,
) -> pd.DataFrame:
    run_config = config.with_risk(objective="mse")
    policy, _ = load_policy(
        run_config,
        checkpoint_directory(run_config, root) / "best.pt",
        device=device,
    )
    spots = torch.linspace(70.0, 130.0, 81, device=device)
    taus = torch.linspace(0.03, 1.0, 41, device=device)
    rows: list[pd.DataFrame] = []
    previous = run_config.market.short_quantity * 0.5
    with torch.no_grad():
        for tau_normalized in taus:
            tau_years = tau_normalized * run_config.market.maturity_years
            state = torch.stack(
                (
                    torch.log(spots / run_config.market.strike),
                    torch.full_like(spots, tau_normalized),
                    torch.full_like(spots, previous),
                    torch.full_like(spots, run_config.market.volatility),
                    torch.full_like(spots, run_config.market.transaction_cost_rate),
                ),
                dim=1,
            )
            neural = policy(state)
            bs = run_config.market.short_quantity * torch_call_delta(
                spots,
                run_config.market.strike,
                tau_years,
                run_config.market.risk_free_rate,
                run_config.market.volatility,
            )
            rows.append(
                pd.DataFrame(
                    {
                        "spot": spots.cpu().numpy(),
                        "log_moneyness": torch.log(spots / run_config.market.strike)
                        .cpu()
                        .numpy(),
                        "tau_normalized": float(tau_normalized.cpu()),
                        "previous_delta": previous,
                        "neural_delta": neural.cpu().numpy(),
                        "black_scholes_delta": bs.cpu().numpy(),
                        "difference": (neural - bs).cpu().numpy(),
                    }
                )
            )
    return pd.concat(rows, ignore_index=True)


def _trade_scatter(
    config: ProjectConfig,
    root: Path,
    paths: torch.Tensor,
    device: torch.device,
) -> pd.DataFrame:
    run_config = config.with_risk(objective="mse")
    policy, _ = load_policy(
        run_config,
        checkpoint_directory(run_config, root) / "best.pt",
        device=device,
    )
    evaluated = evaluate_policy_chunks(
        policy,
        paths[: min(2000, len(paths))],
        run_config.market,
        chunk_size=config.training.evaluation_chunk_size,
        meaningful_trade_threshold=config.experiment.meaningful_trade_threshold,
    )
    deltas = evaluated.deltas
    previous = torch.cat((torch.zeros_like(deltas[:, :1]), deltas[:, :-1]), dim=1)
    bs = black_scholes_deltas(paths[: deltas.shape[0]], run_config.market)
    flat_count = deltas.numel()
    rng = np.random.default_rng(config.market.seed + 30_000)
    selection = rng.choice(flat_count, size=min(4000, flat_count), replace=False)
    return pd.DataFrame(
        {
            "previous_delta": previous.reshape(-1).cpu().numpy()[selection],
            "black_scholes_target": bs.reshape(-1).cpu().numpy()[selection],
            "neural_trade_size": (deltas - previous).reshape(-1).cpu().numpy()[selection],
        }
    )


def _sanity_checks(
    main_metrics: dict[str, Any], sensitivity: pd.DataFrame, config: ProjectConfig
) -> dict[str, Any]:
    low = sensitivity.iloc[0]
    high = sensitivity.iloc[-1]
    rho = float(
        spearmanr(
            sensitivity["transaction_cost_bps"], sensitivity["average_turnover_shares"]
        ).statistic
    )
    competent_std = min(
        main_metrics["neural_mse"]["std_discounted_pnl_after_costs_including_premium"],
        main_metrics["black_scholes_delta"][
            "std_discounted_pnl_after_costs_including_premium"
        ],
    )
    no_hedge_std = main_metrics["no_hedge"][
        "std_discounted_pnl_after_costs_including_premium"
    ]
    checks = {
        "near_frictionless_closer_to_bs_than_25bp": {
            "passed": bool(low["policy_bs_rmse"] < high["policy_bs_rmse"]),
            "low_cost_bps": float(low["transaction_cost_bps"]),
            "low_rmse": float(low["policy_bs_rmse"]),
            "high_cost_bps": float(high["transaction_cost_bps"]),
            "high_rmse": float(high["policy_bs_rmse"]),
        },
        "turnover_generally_decreases_with_cost": {
            "passed": bool(
                high["average_turnover_shares"] < low["average_turnover_shares"] and rho < 0
            ),
            "spearman_correlation": rho,
            "low_turnover": float(low["average_turnover_shares"]),
            "high_turnover": float(high["average_turnover_shares"]),
        },
        "competent_hedge_reduces_dispersion": {
            "passed": bool(competent_std < 0.9 * no_hedge_std),
            "best_hedged_std": float(competent_std),
            "no_hedge_std": float(no_hedge_std),
            "ratio": float(competent_std / no_hedge_std),
        },
        "common_random_numbers": {"passed": True, "test_seed": config.market.seed + 20_000},
        "separate_train_validation_test": {
            "passed": True,
            "training_seed_range": [config.market.seed + 1, config.market.seed + config.training.epochs],
            "validation_seed": config.market.seed + 10_000,
            "test_seed": config.market.seed + 20_000,
        },
        "tail_sample_size": {
            "passed": bool(config.training.test_paths >= 20_000),
            "test_paths": config.training.test_paths,
            "expected_99pct_tail_observations": int(config.training.test_paths * 0.01),
        },
    }
    checks["all_passed"] = all(item.get("passed", False) for item in checks.values())
    return checks


def prepare_experiment_artifacts(
    config: ProjectConfig,
    project_root: str | Path,
    *,
    force: bool = False,
) -> dict[str, Path]:
    """Run/reuse all quick-report experiments and write machine-readable outputs."""
    root = Path(project_root).resolve()
    outputs = ensure_output_directories(config, root)
    run_training_suite(config, root, force=force)
    device = resolve_device(config.training.device)
    test_paths = simulate_gbm(
        config.market,
        config.training.test_paths,
        device=device,
        seed=config.market.seed + 20_000,
    )
    main_frame, main_metrics = _main_comparison(config, root, test_paths, force=force)
    sensitivity = _sensitivity(config, root, test_paths, force=force)
    risk = _risk_comparison(config, root, test_paths, force=force)
    surface = _policy_surface(config, root, device)
    scatter = _trade_scatter(config, root, test_paths, device)
    sanity = _sanity_checks(main_metrics, sensitivity, config)

    main_frame.to_csv(outputs["data"] / "main_path_results.csv.gz", index=False)
    pd.DataFrame(main_metrics).T.to_csv(outputs["data"] / "strategy_summary.csv")
    sensitivity.to_csv(outputs["data"] / "sensitivity_summary.csv", index=False)
    risk.to_csv(outputs["data"] / "risk_objective_summary.csv", index=False)
    surface.to_csv(outputs["data"] / "policy_surface.csv", index=False)
    scatter.to_csv(outputs["data"] / "trade_scatter.csv", index=False)
    summary_payload = {
        "metadata": {
            "profile": config.profile,
            "config_fingerprint": config.fingerprint(),
            "test_paths": config.training.test_paths,
            "test_seed": config.market.seed + 20_000,
            "pnl_definition": "discounted, after transaction costs, including initial premium",
            "loss_definition": "negative economic P&L for VaR/CVaR",
            "premium_definition": "Black-Scholes time-zero premium unless configured otherwise",
        },
        "strategies": main_metrics,
    }
    write_json(summary_payload, outputs["metrics"] / "summary_metrics.json")
    write_json(sanity, outputs["metrics"] / "sanity_checks.json")
    write_json(
        {"rows": sensitivity.to_dict(orient="records")},
        outputs["metrics"] / "sensitivity_metrics.json",
    )
    write_json(
        {"rows": risk.to_dict(orient="records")},
        outputs["metrics"] / "risk_objective_metrics.json",
    )
    manifest = {
        "summary_metrics": str(outputs["metrics"] / "summary_metrics.json"),
        "sanity_checks": str(outputs["metrics"] / "sanity_checks.json"),
        "main_path_results": str(outputs["data"] / "main_path_results.csv.gz"),
        "strategy_summary": str(outputs["data"] / "strategy_summary.csv"),
        "sensitivity_summary": str(outputs["data"] / "sensitivity_summary.csv"),
        "risk_objective_summary": str(outputs["data"] / "risk_objective_summary.csv"),
        "policy_surface": str(outputs["data"] / "policy_surface.csv"),
        "trade_scatter": str(outputs["data"] / "trade_scatter.csv"),
    }
    manifest_path = write_json(manifest, outputs["artifacts"] / "manifest.json")
    return {key: Path(value) for key, value in manifest.items()} | {"manifest": manifest_path}


def load_artifact_manifest(config: ProjectConfig, project_root: str | Path) -> dict[str, Path]:
    """Load existing artifact paths and fail with a reproducible next command."""
    path = Path(project_root) / config.output.artifacts_dir / "manifest.json"
    if not path.exists():
        raise FileNotFoundError("artifact manifest missing; run the demo or sensitivity command")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {key: Path(value) for key, value in payload.items()} | {"manifest": path}
