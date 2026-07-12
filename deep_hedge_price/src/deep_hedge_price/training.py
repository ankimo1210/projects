"""End-to-end deep hedging training with checkpoint reuse."""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

from .config import ProjectConfig, save_config
from .pnl import reporting_premium, rollout_policy
from .policy import MLPHedgePolicy
from .risks import RiskObjective
from .simulation import resolve_device, simulate_gbm

LOGGER = logging.getLogger(__name__)


@dataclass
class TrainingResult:
    """Best trained policy and its durable artifacts."""

    policy: MLPHedgePolicy
    risk_objective: RiskObjective
    history: pd.DataFrame
    checkpoint_path: Path
    reused: bool
    device: torch.device


def set_global_seed(seed: int, deterministic: bool = True) -> None:
    """Seed Python, NumPy and Torch without hiding global state changes."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    if deterministic:
        torch.use_deterministic_algorithms(True, warn_only=True)
        if torch.backends.cudnn.is_available():
            torch.backends.cudnn.benchmark = False
            torch.backends.cudnn.deterministic = True


def cost_label(cost_bps: float) -> str:
    """Create a deterministic filesystem-safe cost label."""
    return f"{cost_bps:g}".replace(".", "p") + "bp"


def run_label(config: ProjectConfig) -> str:
    """Return a stable human-readable run identifier."""
    objective = config.risk.objective
    if objective == "entropic":
        objective += f"_g{config.risk.entropic_gamma:g}".replace(".", "p")
    elif objective == "cvar":
        objective += f"_a{config.risk.cvar_alpha:g}".replace(".", "p")
    return f"{objective}_tc_{cost_label(config.market.transaction_cost_bps)}"


def checkpoint_directory(config: ProjectConfig, project_root: Path) -> Path:
    return (
        project_root
        / config.output.artifacts_dir
        / "checkpoints"
        / run_label(config)
        / config.fingerprint()
    )


def _validation_objective(
    policy: MLPHedgePolicy,
    risk: RiskObjective,
    validation_paths: torch.Tensor,
    config: ProjectConfig,
) -> tuple[float, float, float]:
    losses: list[torch.Tensor] = []
    turnovers: list[torch.Tensor] = []
    costs: list[torch.Tensor] = []
    with torch.no_grad():
        for chunk in validation_paths.split(config.training.evaluation_chunk_size):
            result = rollout_policy(
                policy,
                chunk,
                config.market,
                meaningful_trade_threshold=config.experiment.meaningful_trade_threshold,
            )
            losses.append(result.loss_excluding_premium)
            turnovers.append(result.turnover)
            costs.append(result.transaction_cost)
        all_losses = torch.cat(losses)
        value = float(risk(all_losses).detach().cpu())
        mean_turnover = float(torch.cat(turnovers).mean().cpu())
        mean_cost = float(torch.cat(costs).mean().cpu())
    return value, mean_turnover, mean_cost


def _checkpoint_payload(
    policy: MLPHedgePolicy,
    risk: RiskObjective,
    optimizer: torch.optim.Optimizer,
    config: ProjectConfig,
    epoch: int,
    validation_objective: float,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "config_fingerprint": config.fingerprint(),
        "config": config.to_dict(),
        "epoch": epoch,
        "validation_objective": validation_objective,
        "policy_state_dict": policy.state_dict(),
        "risk_state_dict": risk.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "torch_version": torch.__version__,
        "numpy_version": np.__version__,
    }


def train_policy(
    config: ProjectConfig,
    project_root: str | Path,
    *,
    force: bool = False,
) -> TrainingResult:
    """Train a policy from fresh paths and save/reuse the best checkpoint."""
    root = Path(project_root)
    directory = checkpoint_directory(config, root)
    checkpoint_path = directory / "best.pt"
    history_path = directory / "history.csv"
    device = resolve_device(config.training.device)
    if checkpoint_path.exists() and history_path.exists() and not force:
        payload = torch.load(checkpoint_path, map_location=device, weights_only=False)
        if payload.get("config_fingerprint") == config.fingerprint():
            policy, risk = load_policy(config, checkpoint_path, device=device)
            return TrainingResult(
                policy=policy,
                risk_objective=risk,
                history=pd.read_csv(history_path),
                checkpoint_path=checkpoint_path,
                reused=True,
                device=device,
            )

    directory.mkdir(parents=True, exist_ok=True)
    set_global_seed(config.market.seed, config.training.deterministic)
    policy = MLPHedgePolicy(config.market, config.policy).to(device)
    initial_q = config.market.short_quantity * reporting_premium(config.market) / config.market.s0
    risk = RiskObjective(config.risk, config.market.s0, initial_q=initial_q).to(device)
    parameters = list(policy.parameters()) + list(risk.parameters())
    optimizer = torch.optim.AdamW(
        parameters,
        lr=config.training.learning_rate,
        weight_decay=config.training.weight_decay,
    )
    scheduler: torch.optim.lr_scheduler.ReduceLROnPlateau | None = None
    if config.training.scheduler == "reduce_on_plateau":
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode="min",
            factor=0.5,
            patience=max(2, config.training.early_stopping_patience // 4),
            min_lr=1e-5,
        )
    validation_paths = simulate_gbm(
        config.market,
        config.training.validation_paths,
        device=device,
        seed=config.market.seed + 10_000,
    )
    rows: list[dict[str, float | int]] = []
    best_value = float("inf")
    stale_epochs = 0

    initial_value, initial_turnover, initial_cost = _validation_objective(
        policy, risk, validation_paths, config
    )
    rows.append(
        {
            "epoch": 0,
            "train_objective": float("nan"),
            "validation_objective": initial_value,
            "gradient_norm": float("nan"),
            "learning_rate": config.training.learning_rate,
            "validation_turnover": initial_turnover,
            "validation_transaction_cost": initial_cost,
        }
    )

    for epoch in range(1, config.training.epochs + 1):
        policy.train()
        paths = simulate_gbm(
            config.market,
            config.training.batch_size,
            device=device,
            seed=config.market.seed + epoch,
        )
        result = rollout_policy(
            policy,
            paths,
            config.market,
            meaningful_trade_threshold=config.experiment.meaningful_trade_threshold,
        )
        objective = risk(result.loss_excluding_premium)
        optimizer.zero_grad(set_to_none=True)
        objective.backward()
        gradient_norm = torch.nn.utils.clip_grad_norm_(
            parameters, config.training.gradient_clip_norm
        )
        optimizer.step()

        policy.eval()
        validation_value, validation_turnover, validation_cost = _validation_objective(
            policy, risk, validation_paths, config
        )
        if scheduler is not None:
            scheduler.step(validation_value)
        current_lr = optimizer.param_groups[0]["lr"]
        rows.append(
            {
                "epoch": epoch,
                "train_objective": float(objective.detach().cpu()),
                "validation_objective": validation_value,
                "gradient_norm": float(torch.as_tensor(gradient_norm).detach().cpu()),
                "learning_rate": current_lr,
                "validation_turnover": validation_turnover,
                "validation_transaction_cost": validation_cost,
            }
        )
        if validation_value < best_value - 1e-10:
            best_value = validation_value
            stale_epochs = 0
            torch.save(
                _checkpoint_payload(
                    policy, risk, optimizer, config, epoch, validation_value
                ),
                checkpoint_path,
            )
        else:
            stale_epochs += 1
        if stale_epochs >= config.training.early_stopping_patience:
            LOGGER.info("Early stopping %s at epoch %d", run_label(config), epoch)
            break

    history = pd.DataFrame(rows)
    history.to_csv(history_path, index=False)
    save_config(config, directory / "config.yaml")
    metadata = {
        "run_label": run_label(config),
        "config_fingerprint": config.fingerprint(),
        "best_validation_objective": best_value,
        "completed_epochs": int(history["epoch"].max()),
        "device": str(device),
        "premium_per_option": reporting_premium(config.market),
    }
    (directory / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
    )
    if not checkpoint_path.exists():
        raise RuntimeError("training completed without a checkpoint")
    policy, risk = load_policy(config, checkpoint_path, device=device)
    return TrainingResult(
        policy=policy,
        risk_objective=risk,
        history=history,
        checkpoint_path=checkpoint_path,
        reused=False,
        device=device,
    )


def load_policy(
    config: ProjectConfig,
    checkpoint_path: str | Path,
    *,
    device: str | torch.device | None = None,
) -> tuple[MLPHedgePolicy, RiskObjective]:
    """Restore policy and risk-objective state from a compatible checkpoint."""
    target = resolve_device(config.training.device) if device is None else torch.device(device)
    payload = torch.load(checkpoint_path, map_location=target, weights_only=False)
    if payload.get("config_fingerprint") != config.fingerprint():
        raise ValueError("checkpoint configuration fingerprint does not match")
    policy = MLPHedgePolicy(config.market, config.policy).to(target)
    risk = RiskObjective(config.risk, config.market.s0).to(target)
    policy.load_state_dict(payload["policy_state_dict"])
    risk.load_state_dict(payload["risk_state_dict"])
    policy.eval()
    risk.eval()
    return policy, risk
