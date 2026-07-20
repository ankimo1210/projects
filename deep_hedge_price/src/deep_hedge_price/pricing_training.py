"""Deterministic Phase 2 pricing training, isolated from hedge checkpoints."""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import torch

from .arbitrage import price_bound_penalty
from .pricing_artifacts import load_pricing_dataset
from .pricing_config import PricingConfig, pricing_run_directory
from .pricing_losses import price_and_greek_loss
from .pricing_policy import (
    GREEK_NAMES,
    PolynomialRidge,
    PricingMLP,
    dimensionless_features_numpy,
)


@dataclass
class PricingTrainingResult:
    """Trained model with checkpoint/baseline/history paths and reuse flag."""

    model: PricingMLP
    checkpoint_path: Path
    polynomial_path: Path
    history_path: Path
    reused: bool
    best_validation_mae: float


def _device(requested: str):
    if requested == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested for pricing but is unavailable")
    return torch.device(requested)


def _seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def _split(arrays, split, name):
    return np.asarray(arrays[f"{split}_{name}"], dtype=np.float64)


def _model_from_payload(payload, device):
    from .pricing_config import PricingModelConfig

    model = PricingMLP(PricingModelConfig(**payload["model_config"])).to(device)
    model.load_state_dict(payload["model_state_dict"])
    model.eval()
    return model


def load_pricing_model(checkpoint_path: str | Path, *, device="cpu"):
    """Load a schema-checked pricing checkpoint and its payload."""
    payload = torch.load(checkpoint_path, map_location=device, weights_only=False)
    if payload.get("schema_version") != 1 or payload.get("artifact_kind") != "pricing_checkpoint":
        raise ValueError("incompatible pricing checkpoint")
    return _model_from_payload(payload, torch.device(device)), payload


def train_pricing_model(
    config: PricingConfig,
    manifest_path: str | Path,
    project_root: str | Path,
    *,
    force=False,
):
    """Fit the polynomial baseline and best-reloaded neural pricing model."""
    config.validate()
    manifest, arrays = load_pricing_dataset(Path(manifest_path))
    output = pricing_run_directory(config, project_root)
    output.mkdir(parents=True, exist_ok=True)
    checkpoint = output / "pricing_best.pt"
    polynomial_path = output / "polynomial_baseline.npz"
    history_path = output / "pricing_history.json"
    target_device = _device(config.training.device)
    if checkpoint.exists() and history_path.exists() and not force:
        model, payload = load_pricing_model(checkpoint, device=target_device)
        if (
            payload.get("config_fingerprint") == config.fingerprint()
            and payload.get("dataset_fingerprints") == manifest.split_fingerprints
        ):
            history = json.loads(history_path.read_text(encoding="utf-8"))
            return PricingTrainingResult(
                model,
                checkpoint,
                polynomial_path,
                history_path,
                True,
                float(min(row["validation_price_mae"] for row in history)),
            )

    train_x = _split(arrays, "train", "inputs")
    train_price = _split(arrays, "train", "price")
    validation_x = _split(arrays, "validation", "inputs")
    validation_price = _split(arrays, "validation", "price")
    greek_targets = np.column_stack([_split(arrays, "train", name) for name in GREEK_NAMES])
    mapped_train = dimensionless_features_numpy(train_x)
    mean = mapped_train.mean(axis=0)
    scale = np.maximum(mapped_train.std(axis=0), 1e-12)
    price_scale = max(float(train_price.std()), 1e-8)
    greek_scales = np.maximum(greek_targets.std(axis=0), 1e-8)

    PolynomialRidge().fit(train_x, train_price).save(polynomial_path)
    _seed(config.data.seed + 100_000)
    model = PricingMLP(config.model).to(target_device)
    model.set_normalization(mean, scale)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.training.learning_rate,
        weight_decay=config.training.weight_decay,
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        factor=0.5,
        patience=max(2, config.training.early_stopping_patience // 4),
        min_lr=1e-5,
    )
    generator = torch.Generator(device="cpu").manual_seed(config.data.seed + 200_000)
    best = float("inf")
    stale = 0
    history: list[dict[str, float | int]] = []
    n_rows = len(train_x)
    for epoch in range(1, config.training.epochs + 1):
        model.train()
        permutation = torch.randperm(n_rows, generator=generator).numpy()
        epoch_loss = 0.0
        batches = 0
        for start in range(0, n_rows, config.training.batch_size):
            indices = permutation[start : start + config.training.batch_size]
            batch_x = torch.as_tensor(train_x[indices], dtype=torch.float64, device=target_device)
            needs_grad = config.training.differential_weight > 0
            batch_x.requires_grad_(needs_grad)
            target_price = torch.as_tensor(
                train_price[indices], dtype=torch.float64, device=target_device
            )
            target_greeks = torch.as_tensor(
                greek_targets[indices], dtype=torch.float64, device=target_device
            )
            price, direct = model.components(batch_x)
            losses = price_and_greek_loss(
                price,
                target_price,
                price_scale=price_scale,
                direct_greeks=direct,
                target_greeks=target_greeks,
                greek_scales=greek_scales,
                inputs=batch_x,
                target_delta=target_greeks[:, 0],
                price_weight=config.training.price_weight,
                greek_weight=config.training.greek_weight if direct is not None else 0.0,
                differential_weight=config.training.differential_weight,
            )
            total = losses["total"]
            if config.training.penalty_weight:
                total = total + config.training.penalty_weight * price_bound_penalty(price, batch_x)
            optimizer.zero_grad(set_to_none=True)
            total.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 10.0)
            optimizer.step()
            epoch_loss += float(total.detach().cpu())
            batches += 1
        model.eval()
        with torch.no_grad():
            validation_tensor = torch.as_tensor(
                validation_x, dtype=torch.float64, device=target_device
            )
            validation_prediction = model(validation_tensor)
            validation_target = torch.as_tensor(
                validation_price, dtype=torch.float64, device=target_device
            )
            validation_mae = float(
                torch.mean(torch.abs(validation_prediction - validation_target)).cpu()
            )
        scheduler.step(validation_mae)
        history.append(
            {
                "epoch": epoch,
                "train_loss": epoch_loss / max(batches, 1),
                "validation_price_mae": validation_mae,
                "learning_rate": float(optimizer.param_groups[0]["lr"]),
            }
        )
        if validation_mae < best - 1e-10:
            best = validation_mae
            stale = 0
            torch.save(
                {
                    "schema_version": 1,
                    "artifact_kind": "pricing_checkpoint",
                    "config_fingerprint": config.fingerprint(),
                    "dataset_fingerprints": manifest.split_fingerprints,
                    "model_config": asdict(config.model),
                    "model_state_dict": model.state_dict(),
                    "feature_names": manifest.metadata.get("feature_names"),
                    "price_scale": price_scale,
                    "greek_scales": greek_scales.tolist(),
                    "loss_weights": {
                        "price": config.training.price_weight,
                        "direct_greek": config.training.greek_weight,
                        "differential": config.training.differential_weight,
                        "arbitrage_penalty": config.training.penalty_weight,
                    },
                    "train_seed": config.data.seed + 100_000,
                    "validation_seed": config.data.seed + 10_000,
                    "test_seed": config.data.seed + 20_000,
                    "epoch": epoch,
                    "validation_price_mae": best,
                },
                checkpoint,
            )
        else:
            stale += 1
        if stale >= config.training.early_stopping_patience:
            break
    history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    model, _payload = load_pricing_model(checkpoint, device=target_device)
    return PricingTrainingResult(model, checkpoint, polynomial_path, history_path, False, best)
