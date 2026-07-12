"""End-to-end experiment orchestration and machine-readable artifacts.

The functions in this module are intentionally thin orchestration layers over
the reusable model modules.  Every comparison uses common random numbers, and
all plots/reports read the saved outputs rather than rerunning simulations.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

from .almgren_chriss import ac_inventory, efficient_frontier, kappa_for_lambda
from .config import Config
from .environment import ABLATION_FEATURES, OBS_DIM
from .evaluation import classical_world_run, lob_world_run
from .impact import (
    ImpactChannels,
    classical_execution,
    sqrt_impact,
    transient_decay_curve,
)
from .liquidity import spread_paths
from .plotting import (
    generate_classical_figures,
    generate_evaluation_figures,
    generate_lob_figures,
)
from .price_process import simulate_mid_paths
from .provenance import (
    artifact_dirs,
    ensure_artifact_dirs,
    generated_at,
    provenance,
    sha256_file,
    write_frame,
    write_json,
)
from .random import stream_rng
from .resilience import resilience_sweep
from .rl_policy import RLPolicy, load_checkpoint
from .rl_training import train_ppo
from .strategies import classical_schedules, lob_policies, schedule_ac, schedule_twap
from .tca import summarize
from .volume import simulate_step_volumes


def _log(message: str) -> None:
    print(f"[optimal_execution] {message}", flush=True)


def _snapshot(cfg: Config, timestamp: str) -> Path:
    paths = ensure_artifact_dirs(cfg)
    payload = {
        **provenance(cfg, model_parameters=cfg.raw, timestamp=timestamp),
        "config": cfg.raw,
        "derived": {
            "dt_seconds": cfg.dt,
            "sigma_abs_per_sqrt_second": cfg.sigma_abs,
            "notional": cfg.notional,
            "expected_interval_volume": cfg.expected_interval_volume,
            "kappa": cfg.kappa,
        },
    }
    return write_json(paths["metrics"] / "config_snapshot.json", payload)


def _summary_frame(frames: dict[str, pd.DataFrame], cfg: Config) -> pd.DataFrame:
    return pd.DataFrame([summarize(frame, cfg, name) for name, frame in frames.items()])


def _combine_frames(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    parts = []
    for name, frame in frames.items():
        part = frame.copy()
        part["strategy_id"] = name
        parts.append(part)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def _ac_sensitivity(cfg: Config) -> pd.DataFrame:
    base = {
        "risk_aversion_lambda": cfg.risk_aversion_lambda,
        "annualized_volatility": cfg.annualized_volatility,
        "temporary_eta": cfg.impact.temporary_eta,
        "horizon_seconds": cfg.horizon_seconds,
        "initial_inventory": cfg.initial_inventory,
    }
    grids: dict[str, Iterable[float]] = {
        "risk_aversion_lambda": (
            0.0,
            base["risk_aversion_lambda"] * 0.1,
            base["risk_aversion_lambda"],
            base["risk_aversion_lambda"] * 10.0,
        ),
        "annualized_volatility": (
            base["annualized_volatility"] * 0.5,
            base["annualized_volatility"],
            base["annualized_volatility"] * 2.0,
        ),
        "temporary_eta": (
            base["temporary_eta"] * 0.25,
            base["temporary_eta"],
            base["temporary_eta"] * 4.0,
        ),
        "horizon_seconds": (
            base["horizon_seconds"] * 0.5,
            base["horizon_seconds"],
            base["horizon_seconds"] * 2.0,
        ),
        "initial_inventory": (
            base["initial_inventory"] * 0.5,
            base["initial_inventory"],
            base["initial_inventory"] * 2.0,
        ),
    }
    rows: list[dict[str, float | str]] = []
    for parameter, values in grids.items():
        for value in values:
            if parameter == "temporary_eta":
                trial = cfg.with_overrides({"impact": {"temporary_eta": value}})
            else:
                trial = cfg.with_overrides({parameter: value})
            kappa = kappa_for_lambda(trial, trial.risk_aversion_lambda)
            inventory = ac_inventory(
                trial.initial_inventory,
                trial.horizon_seconds,
                kappa,
                trial.n_decision_steps,
            )
            for k, x in enumerate(inventory):
                rows.append(
                    {
                        "parameter": parameter,
                        "value": float(value),
                        "step": k,
                        "time_s": k * trial.horizon_seconds / trial.n_decision_steps,
                        "time_fraction": k / trial.n_decision_steps,
                        "inventory": float(x),
                        "inventory_fraction": float(x / trial.initial_inventory),
                        "kappa_T": float(kappa * trial.horizon_seconds),
                    }
                )
    return pd.DataFrame(rows)


def _schedule_frame(cfg: Config) -> pd.DataFrame:
    volumes = np.broadcast_to(
        cfg.expected_interval_volume / cfg.n_decision_steps,
        (1, cfg.n_decision_steps),
    ).copy()
    schedules = classical_schedules(cfg, volumes)
    rows: list[dict[str, Any]] = []
    for strategy_id, matrix in schedules.items():
        q = matrix[0]
        inventory = np.concatenate([[cfg.initial_inventory], cfg.initial_inventory - np.cumsum(q)])
        for k, x in enumerate(inventory):
            rows.append(
                {
                    "strategy_id": strategy_id,
                    "step": k,
                    "time_s": k * cfg.dt,
                    "inventory": float(x),
                    "inventory_fraction": float(x / cfg.initial_inventory),
                    "child_order": float(q[k]) if k < len(q) else 0.0,
                }
            )
    return pd.DataFrame(rows)


def _impact_frames(cfg: Config) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    q = schedule_ac(cfg)[None, :]
    mids = np.full((1, cfg.n_decision_steps + 1), cfg.arrival_price)
    spreads = np.full((1, cfg.n_decision_steps), 2.0 * cfg.half_spread)
    presets = {
        "temporary_only": ImpactChannels(True, False, False),
        "permanent_only": ImpactChannels(False, True, False),
        "transient_only": ImpactChannels(False, False, True),
        "all": ImpactChannels(True, True, True),
    }
    rows: list[dict[str, Any]] = []
    for name, channels in presets.items():
        result = classical_execution(cfg, q, mids, spreads, channels)
        for k in range(cfg.n_decision_steps):
            rows.append(
                {
                    "impact_model": name,
                    "step": k,
                    "time_s": k * cfg.dt,
                    "child_order": float(q[0, k]),
                    "execution_price": float(result["exec_price"][0, k]),
                    "impacted_mid": float(result["impacted_mid"][0, k]),
                    "temporary": float(result["temporary"][0, k]),
                    "permanent": float(result["permanent"][0, k]),
                    "transient": float(result["transient"][0, k]),
                    "transient_state": float(result["d_pre"][0, k]),
                }
            )

    recovery_rows = []
    for rho in (0.001, 0.01, 0.1):
        dt = min(cfg.dt, 10.0)
        curve = transient_decay_curve(
            cfg.impact.transient_eta * cfg.initial_inventory,
            rho,
            dt,
            int(cfg.horizon_seconds / dt),
        )
        for k, value in enumerate(curve):
            recovery_rows.append({"rho": rho, "time_after_s": k * dt, "displacement": float(value)})

    quantities = cfg.average_daily_volume * np.logspace(-4, np.log10(0.3), 80)
    sqrt_rows = pd.DataFrame(
        {
            "quantity": quantities,
            "participation_adv": quantities / cfg.average_daily_volume,
            "impact_price": sqrt_impact(quantities, cfg),
        }
    )
    sqrt_rows["impact_bps"] = sqrt_rows["impact_price"] / cfg.arrival_price * 1e4
    return pd.DataFrame(rows), pd.DataFrame(recovery_rows), sqrt_rows


def run_classical(cfg: Config) -> dict[str, Any]:
    """Run Experiments A--E and save classical-world artifacts."""
    paths = ensure_artifact_dirs(cfg)
    stamp = generated_at()
    _snapshot(cfg, stamp)
    _log(f"classical experiments start ({cfg.n_test_scenarios} CRN paths)")

    sensitivity = _ac_sensitivity(cfg)
    write_frame(sensitivity, paths["data"] / "ac_sensitivity.csv", cfg, timestamp=stamp)

    frontier = pd.DataFrame(efficient_frontier(cfg))
    write_frame(frontier, paths["data"] / "efficient_frontier.csv", cfg, timestamp=stamp)

    impact, recovery, sqrt_frame = _impact_frames(cfg)
    write_frame(impact, paths["data"] / "impact_model_comparison.csv", cfg, timestamp=stamp)
    write_frame(recovery, paths["data"] / "impact_recovery.csv", cfg, timestamp=stamp)
    write_frame(sqrt_frame, paths["data"] / "sqrt_impact.csv", cfg, timestamp=stamp)

    schedules = _schedule_frame(cfg)
    write_frame(schedules, paths["data"] / "classical_schedules.csv", cfg, timestamp=stamp)

    sweep_rows: list[dict[str, Any]] = []
    for rho, result in resilience_sweep(cfg).items():
        for label in ("closed_form", "numeric"):
            for k, q in enumerate(np.asarray(result[label])):
                sweep_rows.append(
                    {
                        "rho": rho,
                        "method": label,
                        "step": k,
                        "time_s": k * cfg.dt,
                        "child_order": float(q),
                        "cost": float(result[f"cost_{label}"]),
                        "twap_cost": float(result["cost_twap"]),
                    }
                )
    write_frame(
        pd.DataFrame(sweep_rows), paths["data"] / "resilience_sweep.csv", cfg, timestamp=stamp
    )

    frames = classical_world_run(
        cfg,
        purpose=f"{cfg.profile}_classical_test",
        n_paths=cfg.n_test_scenarios,
    )
    combined = _combine_frames(frames)
    write_frame(
        combined,
        paths["data"] / "classical_path_tca.parquet",
        cfg,
        timestamp=stamp,
        parquet=True,
    )
    summary = _summary_frame(frames, cfg)
    write_frame(summary, paths["metrics"] / "classical_strategy_summary.csv", cfg, timestamp=stamp)
    write_json(
        paths["metrics"] / "classical_strategy_summary.json",
        {
            **provenance(cfg, model_parameters=cfg.raw, timestamp=stamp),
            "strategies": summary.to_dict(orient="records"),
        },
    )

    n_sample = min(64, cfg.n_scenarios)
    rng_price = stream_rng(cfg.seed, "artifact_sample", "price")
    rng_volume = stream_rng(cfg.seed, "artifact_sample", "volume")
    rng_spread = stream_rng(cfg.seed, "artifact_sample", "spread")
    sample_mids = simulate_mid_paths(cfg, rng_price, n_sample)
    sample_volumes = simulate_step_volumes(cfg, rng_volume, n_sample)
    sample_spreads = spread_paths(cfg, rng_spread, n_sample)
    np.savez_compressed(
        paths["data"] / "scenario_sample.npz",
        unaffected_mid=sample_mids,
        step_volume=sample_volumes,
        spread=sample_spreads,
        metadata_json=np.asarray(
            json.dumps(
                provenance(cfg, model_parameters=cfg.raw, timestamp=stamp),
                ensure_ascii=False,
                sort_keys=True,
            )
        ),
    )

    figures = generate_classical_figures(cfg)
    _log(f"classical experiments complete ({len(figures)} static files)")
    return {"summary": summary, "figures": figures}


def _flatten_traces(traces: dict[str, list[list[dict[str, Any]]]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for strategy_id, episodes in traces.items():
        for episode, trace in enumerate(episodes):
            for step, state in enumerate(trace):
                rows.append(
                    {
                        "strategy_id": strategy_id,
                        "episode": episode,
                        "step": step,
                        "time_s": state["t"],
                        "inventory": state["inventory"],
                        "market_qty": state["q_market"],
                        "limit_fill_qty": state["q_limit_fill"],
                        "spread": state["spread"],
                        "bid_depth": state["bid_depth"],
                        "ask_depth": state["ask_depth"],
                        "imbalance": state["imbalance"],
                        "transient_impact": state["D"],
                        "impacted_mid": state["mid"],
                        "unaffected_mid": state["s0"],
                        "best_bid": state["best_bid"],
                        "best_ask": state["best_ask"],
                        "market_volume": state["market_volume"],
                        "execution_price": state["exec_price"],
                    }
                )
    return pd.DataFrame(rows)


def run_lob(cfg: Config) -> dict[str, Any]:
    """Run Experiments F--G in the reactive and replay-style books."""
    paths = ensure_artifact_dirs(cfg)
    stamp = generated_at()
    _log(f"LOB experiments start ({cfg.lob_eval_episodes} CRN episodes/strategy)")
    policies = lob_policies(cfg)
    frames, traces = lob_world_run(
        cfg,
        policies,
        purpose=f"{cfg.profile}_lob_test",
        n_episodes=cfg.lob_eval_episodes,
        reactive=True,
        n_traces=cfg.lob_example_episodes,
    )
    combined = _combine_frames(frames)
    write_frame(
        combined, paths["data"] / "lob_path_tca.parquet", cfg, timestamp=stamp, parquet=True
    )
    summary = _summary_frame(frames, cfg)
    write_frame(summary, paths["metrics"] / "lob_strategy_summary.csv", cfg, timestamp=stamp)

    trace_frame = _flatten_traces(traces)
    write_frame(trace_frame, paths["data"] / "lob_trace_sample.csv", cfg, timestamp=stamp)

    # Exact CRN comparison: the same TWAP market policy in a reactive book and
    # in replay mode where the agent leaves no footprint.
    comparison_frames: dict[str, pd.DataFrame] = {}
    comparison_traces: dict[str, list[list[dict[str, Any]]]] = {}
    for mode, reactive in (("reactive", True), ("replay", False)):
        policy = {"twap_mkt": lob_policies(cfg)["twap_mkt"]}
        result, trace = lob_world_run(
            cfg,
            policy,
            purpose=f"{cfg.profile}_reactivity",
            n_episodes=cfg.lob_eval_episodes,
            reactive=reactive,
            n_traces=1,
        )
        comparison_frames[mode] = result["twap_mkt"]
        comparison_traces[mode] = trace["twap_mkt"]
    comparison_summary = pd.DataFrame(
        [
            {"mode": mode, **summarize(frame, cfg, f"twap_{mode}")}
            for mode, frame in comparison_frames.items()
        ]
    )
    write_frame(
        comparison_summary, paths["metrics"] / "reactive_comparison.csv", cfg, timestamp=stamp
    )
    replay_trace = _flatten_traces(
        {f"twap_{mode}": value for mode, value in comparison_traces.items()}
    )
    write_frame(replay_trace, paths["data"] / "reactive_trace_comparison.csv", cfg, timestamp=stamp)

    write_json(
        paths["metrics"] / "lob_strategy_summary.json",
        {
            **provenance(cfg, model_parameters=cfg.raw, timestamp=stamp),
            "strategies": summary.to_dict(orient="records"),
            "reactive_comparison": comparison_summary.to_dict(orient="records"),
        },
    )
    figures = generate_lob_figures(cfg)
    _log(f"LOB experiments complete ({len(figures)} static files)")
    return {"summary": summary, "reactive": comparison_summary, "figures": figures}


ABLATION_REFERENCE = "ablation_ref"


def _run_tag(cfg: Config, variant: str, seed: int, feature: str | None = None) -> str:
    if feature == ABLATION_REFERENCE:
        middle = "_ablation_ref"
    else:
        middle = f"_no_{feature}" if feature else ""
    return f"{variant}_{cfg.profile}{middle}_s{seed}"


def _checkpoint_path(cfg: Config, variant: str, seed: int, feature: str | None = None) -> Path:
    return (
        artifact_dirs(cfg)["checkpoints"] / f"ppo_{_run_tag(cfg, variant, seed, feature)}_best.pt"
    )


def _history_path(cfg: Config, run_id: str) -> Path:
    return artifact_dirs(cfg)["metrics"] / f"rl_history_{run_id}.csv"


def _enrich_checkpoint(
    cfg: Config,
    checkpoint: Path,
    *,
    run_id: str,
    feature_mask: np.ndarray | None,
    timestamp: str,
) -> dict[str, Any]:
    blob = torch.load(checkpoint, map_location="cpu", weights_only=False)
    meta = dict(blob.get("meta") or {})
    meta.update(
        {
            **provenance(
                cfg,
                strategy_id=run_id,
                model_parameters={
                    "algorithm": "PPO",
                    "hidden_size": cfg.rl.hidden_size,
                    "learning_rate": cfg.rl.learning_rate,
                    "gamma": cfg.rl.gamma,
                    "gae_lambda": cfg.rl.gae_lambda,
                    "clip_epsilon": cfg.rl.clip_epsilon,
                    "feature_mask": None if feature_mask is None else feature_mask.tolist(),
                },
                timestamp=timestamp,
            ),
            "run_id": run_id,
        }
    )
    blob["meta"] = meta
    torch.save(blob, checkpoint)
    return meta


def _train_or_reuse(
    cfg: Config,
    *,
    variant: str,
    seed: int,
    feature: str | None,
    feature_mask: np.ndarray | None,
    episodes: int,
    force: bool,
    timestamp: str,
) -> tuple[Path, pd.DataFrame, dict[str, Any]]:
    paths = artifact_dirs(cfg)
    run_id = _run_tag(cfg, variant, seed, feature)
    checkpoint = _checkpoint_path(cfg, variant, seed, feature)
    history_path = _history_path(cfg, run_id)
    if checkpoint.exists() and history_path.exists() and not force:
        _log(f"reuse checkpoint {checkpoint.name}")
        history = pd.read_csv(history_path)
        _, meta = load_checkpoint(checkpoint)
        return checkpoint, history, meta

    _log(f"train PPO {run_id} ({episodes} episodes)")
    result = train_ppo(
        cfg,
        variant=variant,
        seed=seed,
        feature_mask=feature_mask,
        episodes=episodes,
        out_dir=paths["checkpoints"],
        tag=run_id,
    )
    checkpoint = result.checkpoint
    history = pd.DataFrame(result.history)
    history["run_id"] = run_id
    history["variant"] = variant
    history["training_seed"] = seed
    history["feature_removed"] = feature or "none"
    write_frame(
        history,
        history_path,
        cfg,
        strategy_id=run_id,
        model_parameters={
            "algorithm": "PPO",
            "episodes": episodes,
            "feature_removed": feature,
        },
        timestamp=timestamp,
    )
    meta = _enrich_checkpoint(
        cfg,
        checkpoint,
        run_id=run_id,
        feature_mask=feature_mask,
        timestamp=timestamp,
    )
    return checkpoint, history, meta


def train_rl(cfg: Config, *, force: bool = False) -> dict[str, Path]:
    """Train residual/free PPO and residual feature-ablation policies."""
    paths = ensure_artifact_dirs(cfg)
    stamp = generated_at()
    _log("RL training stage start")
    checkpoints: dict[str, Path] = {}
    histories: list[pd.DataFrame] = []
    runs: list[dict[str, Any]] = []
    for seed in cfg.rl.seeds:
        for variant in ("residual", "free"):
            checkpoint, history, meta = _train_or_reuse(
                cfg,
                variant=variant,
                seed=int(seed),
                feature=None,
                feature_mask=None,
                episodes=cfg.rl.training_episodes,
                force=force,
                timestamp=stamp,
            )
            run_id = _run_tag(cfg, variant, int(seed))
            checkpoints[run_id] = checkpoint
            histories.append(history)
            runs.append({"run_id": run_id, "checkpoint": str(checkpoint), **meta})

    # Quick profile uses one seed; full retains multi-seed main policies while
    # ablations use the first seed to keep CPU cost bounded and interpretable.
    # The full-feature ablation REFERENCE is retrained at the same (usually
    # shorter) ablation budget so feature-removal deltas are not confounded
    # with training length.
    ablation_seed = int(cfg.rl.seeds[0])
    for feature in (ABLATION_REFERENCE, *cfg.ablation.features):
        if feature == ABLATION_REFERENCE:
            mask = None
        else:
            mask = np.ones(OBS_DIM, dtype=float)
            mask[list(ABLATION_FEATURES[feature])] = 0.0
        checkpoint, history, meta = _train_or_reuse(
            cfg,
            variant="residual",
            seed=ablation_seed,
            feature=feature,
            feature_mask=mask,
            episodes=cfg.ablation.training_episodes,
            force=force,
            timestamp=stamp,
        )
        run_id = _run_tag(cfg, "residual", ablation_seed, feature)
        checkpoints[run_id] = checkpoint
        histories.append(history)
        runs.append({"run_id": run_id, "checkpoint": str(checkpoint), **meta})

    combined = pd.concat(histories, ignore_index=True)
    write_frame(combined, paths["metrics"] / "rl_training_history.csv", cfg, timestamp=stamp)
    write_json(
        paths["metrics"] / "rl_training_summary.json",
        {
            **provenance(cfg, model_parameters=asdict(cfg.rl), timestamp=stamp),
            "runs": runs,
            "seed_count": len(cfg.rl.seeds),
            "quick_profile_single_seed_warning": len(cfg.rl.seeds) == 1,
        },
    )
    _log(f"RL training stage complete ({len(checkpoints)} checkpoints)")
    return checkpoints


def _main_eval_policies(
    train_cfg: Config, eval_cfg: Config
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    scripted = lob_policies(eval_cfg)
    policies: dict[str, Any] = {
        "twap_mkt": scripted["twap_mkt"],
        "ac_mkt": scripted["ac_mkt"],
        "heuristic": scripted["heuristic"],
    }
    baselines: dict[str, np.ndarray] = {}
    for seed in train_cfg.rl.seeds:
        residual_id = f"rl_residual_s{seed}"
        free_id = f"rl_free_s{seed}"
        policies[residual_id] = RLPolicy.from_checkpoint(
            _checkpoint_path(train_cfg, "residual", int(seed))
        )
        policies[free_id] = RLPolicy.from_checkpoint(_checkpoint_path(train_cfg, "free", int(seed)))
        # Baselines are frozen at training-time parameters for a genuine
        # distribution-shift test rather than silently recalibrated in stress.
        baselines[residual_id] = schedule_ac(train_cfg)
        baselines[free_id] = schedule_twap(train_cfg)
    return policies, baselines


def _evaluate_regime(
    train_cfg: Config,
    eval_cfg: Config,
    *,
    regime: str,
    episodes: int,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    policies, baselines = _main_eval_policies(train_cfg, eval_cfg)
    # Regime-independent scenario stream: every regime (and the misspecified
    # simulator) draws the SAME scenario seeds, so a regime only rescales/​
    # perturbs identical underlying draws. Cross-regime deltas are then paired
    # (common random numbers *across* regimes), not confounded by sample drift.
    frames, _ = lob_world_run(
        eval_cfg,
        policies,
        purpose=f"{train_cfg.profile}_rl_paired",
        n_episodes=episodes,
        baselines=baselines,
    )
    summary = _summary_frame(frames, eval_cfg)
    summary["regime"] = regime
    summary["evaluation_episodes"] = episodes
    return summary, frames


def evaluate(cfg: Config, *, force_train: bool = False) -> dict[str, pd.DataFrame]:
    """Run Experiments H--J: OOS, stress, ablation, and misspecification."""
    paths = ensure_artifact_dirs(cfg)
    stamp = generated_at()
    if force_train or not all(
        _checkpoint_path(cfg, variant, int(seed)).exists()
        for seed in cfg.rl.seeds
        for variant in ("residual", "free")
    ):
        train_rl(cfg, force=force_train)

    _log("RL evaluation stage start")
    summaries: list[pd.DataFrame] = []
    path_parts: list[pd.DataFrame] = []
    regimes: list[tuple[str, Config, int]] = [("in_distribution", cfg, cfg.rl.test_episodes)]
    regimes.extend(
        (name, regime_cfg, cfg.lob_stress_episodes)
        for name, regime_cfg in cfg.stress_regimes().items()
    )
    for name, eval_cfg, episodes in regimes:
        _log(f"evaluate regime {name} ({episodes} episodes/strategy)")
        summary, frames = _evaluate_regime(cfg, eval_cfg, regime=name, episodes=episodes)
        summaries.append(summary)
        combined = _combine_frames(frames)
        combined["regime"] = name
        path_parts.append(combined)

    stress = pd.concat(summaries, ignore_index=True)
    write_frame(stress, paths["metrics"] / "stress_summary.csv", cfg, timestamp=stamp)
    write_json(
        paths["metrics"] / "stress_summary.json",
        {
            **provenance(cfg, model_parameters=cfg.raw, timestamp=stamp),
            "results": stress.to_dict(orient="records"),
            "common_random_numbers_within_regime": True,
            "common_random_numbers_across_regimes": True,
        },
    )
    write_frame(
        pd.concat(path_parts, ignore_index=True),
        paths["data"] / "rl_evaluation_path_tca.parquet",
        cfg,
        timestamp=stamp,
        parquet=True,
    )

    # Ablation policies share exact held-out scenario seeds. The full-feature
    # reference is trained at the SAME ablation budget (not the main policy's
    # longer budget) so deltas isolate the feature removal.
    seed = int(cfg.rl.seeds[0])
    full_id = "full_model"
    reference_checkpoint = _checkpoint_path(cfg, "residual", seed, ABLATION_REFERENCE)
    if not reference_checkpoint.exists():
        train_rl(cfg)
    policies: dict[str, Any] = {full_id: RLPolicy.from_checkpoint(reference_checkpoint)}
    baselines = {full_id: schedule_ac(cfg)}
    masks = {full_id: np.ones(OBS_DIM)}
    for feature in cfg.ablation.features:
        strategy_id = f"without_{feature}"
        checkpoint = _checkpoint_path(cfg, "residual", seed, feature)
        if not checkpoint.exists():
            train_rl(cfg)
        policies[strategy_id] = RLPolicy.from_checkpoint(checkpoint)
        baselines[strategy_id] = schedule_ac(cfg)
        mask = np.ones(OBS_DIM)
        mask[list(ABLATION_FEATURES[feature])] = 0.0
        masks[strategy_id] = mask
    ablation_frames, _ = lob_world_run(
        cfg,
        policies,
        purpose=f"{cfg.profile}_ablation_test",
        n_episodes=cfg.lob_stress_episodes,
        baselines=baselines,
        feature_masks=masks,
    )
    full_mean = float(ablation_frames[full_id]["is_bps"].mean())
    ablation_rows = []
    for strategy_id, frame in ablation_frames.items():
        feature = "none" if strategy_id == full_id else strategy_id.removeprefix("without_")
        row = summarize(frame, cfg, strategy_id)
        row["feature_removed"] = feature
        row["delta_vs_full_bps"] = float(frame["is_bps"].mean() - full_mean)
        ablation_rows.append(row)
    ablation = pd.DataFrame(ablation_rows)
    write_frame(ablation, paths["metrics"] / "ablation_summary.csv", cfg, timestamp=stamp)
    write_json(
        paths["metrics"] / "ablation_summary.json",
        {
            **provenance(
                cfg, model_parameters={"features": list(cfg.ablation.features)}, timestamp=stamp
            ),
            "results": ablation.to_dict(orient="records"),
        },
    )

    miss_cfg = cfg.misspecification_config()
    miss, _ = _evaluate_regime(
        cfg,
        miss_cfg,
        regime="misspecified_simulator",
        episodes=cfg.lob_stress_episodes,
    )
    write_frame(miss, paths["metrics"] / "misspecification_summary.csv", cfg, timestamp=stamp)
    write_json(
        paths["metrics"] / "misspecification_summary.json",
        {
            **provenance(
                cfg,
                model_parameters={
                    "train_config": cfg.raw,
                    "test_overrides": (cfg.raw.get("misspecification") or {}).get(
                        "test_overrides", {}
                    ),
                },
                timestamp=stamp,
            ),
            "results": miss.to_dict(orient="records"),
        },
    )

    figures = generate_evaluation_figures(cfg)
    _log(f"RL evaluation stage complete ({len(figures)} static files)")
    return {"stress": stress, "ablation": ablation, "misspecification": miss}


def build_manifest(cfg: Config, *, locales: Iterable[str] = ("en", "ja")) -> Path:
    """Hash generated artifacts and reports into the report manifest."""
    paths = ensure_artifact_dirs(cfg)
    manifest_path = paths["metrics"] / "report_manifest.json"
    files: list[dict[str, Any]] = []
    roots = [
        paths["data"],
        paths["metrics"],
        paths["checkpoints"],
        paths["figures"],
        paths["reports"],
    ]
    for root in roots:
        for path in sorted(root.glob("**/*")):
            if not path.is_file() or path == manifest_path:
                continue
            files.append(
                {
                    "path": str(
                        path.relative_to(
                            paths["root"].parent
                            if path.is_relative_to(paths["root"])
                            else paths["reports"].parent
                        )
                    ),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    required = {
        "notebook_html": paths["reports"] / "01_optimal_execution_visual_lab.html",
        "notebook_html_ja": paths["reports"] / "01_optimal_execution_visual_lab_ja.html",
        "report_en": paths["reports"] / "optimal_execution_report_en.html",
        "report_ja": paths["reports"] / "optimal_execution_report_ja.html",
        "classical_tca": paths["data"] / "classical_path_tca.parquet",
        "lob_tca": paths["data"] / "lob_path_tca.parquet",
        "rl_history": paths["metrics"] / "rl_training_history.csv",
    }
    payload = {
        **provenance(cfg, model_parameters=cfg.raw),
        "locales": list(locales),
        "required_outputs": {
            key: {"path": str(path), "exists": path.exists()} for key, path in required.items()
        },
        "files": files,
    }
    return write_json(manifest_path, payload)


def run_all(cfg: Config, *, force_train: bool = False) -> None:
    """Run all numerical stages. Reports/notebook are built by their modules."""
    run_classical(cfg)
    run_lob(cfg)
    train_rl(cfg, force=force_train)
    evaluate(cfg)
