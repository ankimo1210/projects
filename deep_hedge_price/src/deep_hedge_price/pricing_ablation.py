"""Reproducible quick ablations for Phase 2 pricing surrogates.

The ablation deliberately reuses one fixed dataset split across every model
variant and changes only model initialization/batch-order seeds.  Analytic
Greeks are labels for losses and evaluation; no analytic pricing or Greek
formula is imported into the learned policy.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import torch

from .arbitrage import price_bound_penalty, structured_surface_penalty
from .greeks import autodiff_greeks
from .pricing_artifacts import fingerprint_rows, load_pricing_dataset
from .pricing_config import PricingConfig
from .pricing_evaluation import _hard_report
from .pricing_losses import price_and_greek_loss
from .pricing_policy import GREEK_NAMES, PricingMLP, dimensionless_features_numpy


@dataclass(frozen=True)
class PricingAblationProtocol:
    """Small, explicit CPU protocol suitable for a committed reference JSON."""

    model_seeds: tuple[int, int, int] = (1729, 2718, 3141)
    train_rows: int = 512
    validation_rows: int = 192
    test_rows: int = 192
    epochs: int = 24
    batch_size: int = 128
    hidden_layers: int = 2
    hidden_units: int = 32
    positive_penalty_weight: float = 0.1
    material_price_degradation_ratio: float = 1.10

    def validate(self) -> None:
        if len(self.model_seeds) != 3 or len(set(self.model_seeds)) != 3:
            raise ValueError("pricing ablation requires exactly three distinct model seeds")
        if min(self.model_seeds) < 0:
            raise ValueError("model seeds must be non-negative")
        if (
            min(
                self.train_rows,
                self.validation_rows,
                self.test_rows,
                self.epochs,
                self.batch_size,
                self.hidden_layers,
                self.hidden_units,
            )
            <= 0
        ):
            raise ValueError("ablation sizes, epochs, and model dimensions must be positive")
        if self.positive_penalty_weight <= 0:
            raise ValueError("positive_penalty_weight must be positive")
        if self.material_price_degradation_ratio < 1.0:
            raise ValueError("material_price_degradation_ratio must be at least one")


_VARIANTS = {
    "price_only": {
        "direct_greek_heads": False,
        "greek_weight": 0.0,
        "differential_weight": 0.0,
        "greek_route": "price_head_autodiff",
    },
    "direct_multi_task": {
        "direct_greek_heads": True,
        "greek_weight": 1.0,
        "differential_weight": 0.0,
        "greek_route": "direct_heads",
    },
    "differential_ml": {
        "direct_greek_heads": False,
        "greek_weight": 0.0,
        "differential_weight": 1.0,
        "greek_route": "price_head_autodiff",
    },
}


def _fixed_subset(arrays, split: str, n_rows: int, *, selection_seed: int):
    inputs = np.asarray(arrays[f"{split}_inputs"], dtype=np.float64)
    if n_rows > len(inputs):
        raise ValueError(f"requested {n_rows} {split} rows but dataset has {len(inputs)}")
    rng = np.random.default_rng(selection_seed)
    indices = np.sort(rng.choice(len(inputs), size=n_rows, replace=False))
    names = ("inputs", "price", *GREEK_NAMES)
    return {
        name: np.asarray(arrays[f"{split}_{name}"][indices], dtype=np.float64) for name in names
    }


def _seed_torch(seed: int) -> torch.Generator:
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)
    return torch.Generator(device="cpu").manual_seed(seed + 1_000_003)


def _error_metrics(prediction, target):
    prediction = np.asarray(prediction, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    error = prediction - target
    return {
        "mae": float(np.mean(np.abs(error))),
        "rmse": float(np.sqrt(np.mean(error**2))),
    }


def _soft_arbitrage_penalty(model, batch_prices, batch_inputs):
    """Bounds plus explicit strike/calendar/spot grids used only in soft loss."""
    dtype = batch_prices.dtype
    spots = torch.linspace(0.7, 1.3, 25, dtype=dtype)
    spot_inputs = torch.column_stack(
        (
            spots,
            torch.ones_like(spots),
            torch.full_like(spots, 0.02),
            torch.full_like(spots, 0.01),
            torch.full_like(spots, 0.25),
        )
    )
    strikes = torch.linspace(0.7, 1.3, 25, dtype=dtype)
    strike_inputs = torch.column_stack(
        (
            1.0 / strikes,
            torch.ones_like(strikes),
            torch.full_like(strikes, 0.02),
            torch.full_like(strikes, 0.01),
            torch.full_like(strikes, 0.25),
        )
    )
    maturities = torch.linspace(0.03, 2.0, 25, dtype=dtype)
    maturity_inputs = torch.column_stack(
        (
            torch.ones_like(maturities),
            maturities,
            torch.full_like(maturities, 0.02),
            torch.full_like(maturities, 0.01),
            torch.full_like(maturities, 0.25),
        )
    )
    return (
        price_bound_penalty(batch_prices, batch_inputs)
        + structured_surface_penalty(model(spot_inputs), spots=spots)
        + structured_surface_penalty(model(strike_inputs) * strikes, strikes=strikes)
        + structured_surface_penalty(model(maturity_inputs), maturities=maturities)
    )


def _fit_one(
    config: PricingConfig,
    protocol: PricingAblationProtocol,
    data: dict[str, dict[str, np.ndarray]],
    *,
    variant_name: str,
    model_seed: int,
    penalty_weight: float,
):
    variant = _VARIANTS[variant_name]
    model_config = replace(
        config.model,
        hidden_layers=protocol.hidden_layers,
        hidden_units=protocol.hidden_units,
        direct_greek_heads=variant["direct_greek_heads"],
    )
    generator = _seed_torch(model_seed)
    model = PricingMLP(model_config)
    mapped_train = dimensionless_features_numpy(data["train"]["inputs"])
    model.set_normalization(mapped_train.mean(axis=0), np.maximum(mapped_train.std(axis=0), 1e-12))
    price_scale = max(float(data["train"]["price"].std()), 1e-8)
    train_greeks = np.column_stack([data["train"][name] for name in GREEK_NAMES])
    greek_scales = np.maximum(train_greeks.std(axis=0), 1e-8)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.training.learning_rate,
        weight_decay=config.training.weight_decay,
    )
    best_validation_mae = float("inf")
    best_state = None
    train_inputs = data["train"]["inputs"]
    n_rows = len(train_inputs)
    for _epoch in range(protocol.epochs):
        model.train()
        permutation = torch.randperm(n_rows, generator=generator).numpy()
        for start in range(0, n_rows, protocol.batch_size):
            indices = permutation[start : start + protocol.batch_size]
            inputs = torch.as_tensor(train_inputs[indices], dtype=torch.float64)
            inputs.requires_grad_(variant["differential_weight"] > 0)
            target_price = torch.as_tensor(data["train"]["price"][indices], dtype=torch.float64)
            target_greeks = torch.as_tensor(train_greeks[indices], dtype=torch.float64)
            price, direct_greeks = model.components(inputs)
            losses = price_and_greek_loss(
                price,
                target_price,
                price_scale=price_scale,
                direct_greeks=direct_greeks,
                target_greeks=target_greeks,
                greek_scales=greek_scales,
                inputs=inputs,
                target_delta=target_greeks[:, 0],
                price_weight=1.0,
                greek_weight=variant["greek_weight"],
                differential_weight=variant["differential_weight"],
            )
            total = losses["total"]
            if penalty_weight:
                total = total + penalty_weight * _soft_arbitrage_penalty(model, price, inputs)
            optimizer.zero_grad(set_to_none=True)
            total.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 10.0)
            optimizer.step()
        model.eval()
        with torch.no_grad():
            validation_prediction = model(
                torch.as_tensor(data["validation"]["inputs"], dtype=torch.float64)
            ).numpy()
        validation_mae = _error_metrics(validation_prediction, data["validation"]["price"])["mae"]
        if validation_mae < best_validation_mae:
            best_validation_mae = validation_mae
            best_state = copy.deepcopy(model.state_dict())
    if best_state is None:  # pragma: no cover - validation plus positive epochs guarantee a state
        raise RuntimeError("ablation training did not produce a model state")
    model.load_state_dict(best_state)
    model.eval()

    test_tensor = torch.as_tensor(data["test"]["inputs"], dtype=torch.float64)
    autodiff = autodiff_greeks(model, test_tensor)
    with torch.no_grad():
        price, direct = model.components(test_tensor)
    autodiff_metrics = {
        name: _error_metrics(autodiff[name].numpy(), data["test"][name]) for name in GREEK_NAMES
    }
    direct_metrics = (
        {
            name: _error_metrics(direct[:, index].numpy(), data["test"][name])
            for index, name in enumerate(GREEK_NAMES)
        }
        if direct is not None
        else None
    )
    intended_metrics = (
        direct_metrics if variant["greek_route"] == "direct_heads" else autodiff_metrics
    )
    return {
        "model_seed": model_seed,
        "parameter_count": model.parameter_count,
        "best_validation_price_mae": best_validation_mae,
        "test": {
            "price": _error_metrics(price.numpy(), data["test"]["price"]),
            "greek_route": variant["greek_route"],
            "greeks": intended_metrics,
            "autodiff_greeks": autodiff_metrics,
            "direct_greeks": direct_metrics,
        },
        "hard_validation": _hard_report(model, torch.device("cpu")),
    }


def _stats(values):
    array = np.asarray(values, dtype=np.float64)
    return {
        "n": int(array.size),
        "mean": float(array.mean()),
        "standard_deviation_population": float(array.std(ddof=0)),
        "min": float(array.min()),
        "max": float(array.max()),
    }


def _aggregate(seed_runs):
    checks = {check["name"] for run in seed_runs for check in run["hard_validation"]["checks"]}
    return {
        "best_validation_price_mae": _stats(
            [run["best_validation_price_mae"] for run in seed_runs]
        ),
        "test": {
            "price_mae": _stats([run["test"]["price"]["mae"] for run in seed_runs]),
            "greek_mae": {
                name: _stats([run["test"]["greeks"][name]["mae"] for run in seed_runs])
                for name in GREEK_NAMES
            },
        },
        "hard_validation": {
            "arbitrage_free_rate": float(
                np.mean([run["hard_validation"]["arbitrage_free"] for run in seed_runs])
            ),
            "checks": {
                name: {
                    "n_checked": sorted(
                        {
                            check["n_checked"]
                            for run in seed_runs
                            for check in run["hard_validation"]["checks"]
                            if check["name"] == name
                        }
                    ),
                    "n_violations": _stats(
                        [
                            check["n_violations"]
                            for run in seed_runs
                            for check in run["hard_validation"]["checks"]
                            if check["name"] == name
                        ]
                    ),
                    "max_violation": _stats(
                        [
                            check["max_violation"]
                            for run in seed_runs
                            for check in run["hard_validation"]["checks"]
                            if check["name"] == name
                        ]
                    ),
                    "tolerances": sorted(
                        {
                            check["tolerance"]
                            for run in seed_runs
                            for check in run["hard_validation"]["checks"]
                            if check["name"] == name
                        }
                    ),
                }
                for name in sorted(checks)
            },
        },
    }


def _protocol_id(subset_fingerprints: dict[str, str]) -> str:
    canonical = json.dumps(subset_fingerprints, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


def run_pricing_ablation(
    config: PricingConfig,
    manifest_path: str | Path,
    output_path: str | Path,
    *,
    protocol: PricingAblationProtocol | None = None,
) -> tuple[Path, dict]:
    """Run the fixed-split 3-seed quick ablation and save stable JSON.

    The function creates no model checkpoint.  Only the requested JSON report
    is persisted, so repeated runs with the same dataset/config/protocol are
    byte-for-byte stable.
    """

    config.validate()
    protocol = protocol or PricingAblationProtocol()
    protocol.validate()
    manifest, arrays = load_pricing_dataset(Path(manifest_path))
    source_config_fingerprint = manifest.metadata.get("config_fingerprint")
    if source_config_fingerprint != config.fingerprint():
        raise ValueError("ablation config fingerprint does not match the pricing dataset")
    selection_seeds = {
        "train": config.data.seed + 700_001,
        "validation": config.data.seed + 700_002,
        "test": config.data.seed + 700_003,
    }
    requested_rows = {
        "train": protocol.train_rows,
        "validation": protocol.validation_rows,
        "test": protocol.test_rows,
    }
    data = {
        split: _fixed_subset(
            arrays, split, requested_rows[split], selection_seed=selection_seeds[split]
        )
        for split in requested_rows
    }
    subset_fingerprints = {
        split: fingerprint_rows(data[split]["inputs"]) for split in requested_rows
    }
    data_protocol_id = _protocol_id(subset_fingerprints)

    variants = {}
    for variant_name in _VARIANTS:
        seed_runs = [
            _fit_one(
                config,
                protocol,
                data,
                variant_name=variant_name,
                model_seed=model_seed,
                penalty_weight=0.0,
            )
            for model_seed in protocol.model_seeds
        ]
        variants[variant_name] = {
            "training_definition": {
                "price_weight": 1.0,
                "direct_greek_weight": _VARIANTS[variant_name]["greek_weight"],
                "differential_delta_weight": _VARIANTS[variant_name]["differential_weight"],
                "soft_arbitrage_penalty_weight": 0.0,
                "direct_greek_heads": _VARIANTS[variant_name]["direct_greek_heads"],
                "intended_greek_route": _VARIANTS[variant_name]["greek_route"],
            },
            "data_protocol_id": data_protocol_id,
            "seed_runs": seed_runs,
            "aggregate": _aggregate(seed_runs),
        }

    penalized_runs = [
        _fit_one(
            config,
            protocol,
            data,
            variant_name="price_only",
            model_seed=model_seed,
            penalty_weight=protocol.positive_penalty_weight,
        )
        for model_seed in protocol.model_seeds
    ]
    penalty_zero = {
        "weight": 0.0,
        "source_variant": "price_only",
        "data_protocol_id": data_protocol_id,
        "seed_runs": variants["price_only"]["seed_runs"],
        "aggregate": variants["price_only"]["aggregate"],
    }
    penalty_positive = {
        "weight": protocol.positive_penalty_weight,
        "source_variant": "price_only",
        "data_protocol_id": data_protocol_id,
        "seed_runs": penalized_runs,
        "aggregate": _aggregate(penalized_runs),
    }

    baseline = variants["price_only"]["aggregate"]["test"]
    candidate_summary = {}
    for name in ("direct_multi_task", "differential_ml"):
        candidate = variants[name]["aggregate"]["test"]
        improved_greeks = [
            greek
            for greek in GREEK_NAMES
            if candidate["greek_mae"][greek]["mean"] < baseline["greek_mae"][greek]["mean"]
        ]
        price_ratio = candidate["price_mae"]["mean"] / max(baseline["price_mae"]["mean"], 1e-15)
        candidate_summary[name] = {
            "price_mae_ratio_to_price_only": price_ratio,
            "improved_greeks": improved_greeks,
            "improves_a_greek_without_material_price_degradation": bool(improved_greeks)
            and price_ratio <= protocol.material_price_degradation_ratio,
        }

    zero_violations = sum(
        value["n_violations"]["mean"]
        for value in penalty_zero["aggregate"]["hard_validation"]["checks"].values()
    )
    positive_violations = sum(
        value["n_violations"]["mean"]
        for value in penalty_positive["aggregate"]["hard_validation"]["checks"].values()
    )
    penalty_price_ratio = penalty_positive["aggregate"]["test"]["price_mae"]["mean"] / max(
        penalty_zero["aggregate"]["test"]["price_mae"]["mean"], 1e-15
    )
    result = {
        "schema_version": 1,
        "artifact_kind": "pricing_quick_ablation",
        "config_fingerprint": config.fingerprint(),
        "dataset": {
            "model": manifest.model,
            "teacher_method": manifest.teacher_method,
            "manifest_locator": (
                f"{config.output.namespace}/{config.fingerprint()}/{Path(manifest_path).name}"
            ),
            "arrays_sha256": manifest.arrays_sha256,
            "full_split_fingerprints": manifest.split_fingerprints,
            "fixed_subset_fingerprints": subset_fingerprints,
            "fixed_subset_rows": requested_rows,
            "selection_seeds": selection_seeds,
            "data_protocol_id": data_protocol_id,
            "same_fixed_split_for_every_variant_and_model_seed": True,
        },
        "protocol": {
            "profile": "quick_ablation",
            "device": "cpu",
            "model_seeds": list(protocol.model_seeds),
            "epochs": protocol.epochs,
            "batch_size": protocol.batch_size,
            "hidden_layers": protocol.hidden_layers,
            "hidden_units": protocol.hidden_units,
            "activation": config.model.activation,
            "output_mode": config.model.output_mode,
            "dispersion_definition": "population standard deviation across three model seeds",
            "analytic_label_usage": "training losses and evaluation targets only",
            "analytic_delta_embedded_in_model_or_inference": False,
            "hard_validation_authority": "hullkit.surrogate_validation",
            "soft_penalty_does_not_define_arbitrage_free": True,
            "soft_penalty_components": [
                "price_bounds_on_training_batch",
                "spot_monotonicity_on_explicit_grid",
                "strike_monotonicity_and_convexity_on_explicit_grid",
                "calendar_monotonicity_on_explicit_grid",
            ],
            "material_price_degradation_ratio": protocol.material_price_degradation_ratio,
        },
        "variants": variants,
        "penalty_ablation": {
            "comparison_model": "price_only",
            "zero": penalty_zero,
            "positive": penalty_positive,
        },
        "conclusions": {
            "variant_comparison": candidate_summary,
            "delta_mae_below_2e-3_by_variant": {
                name: value["aggregate"]["test"]["greek_mae"]["delta"]["mean"] < 2e-3
                for name, value in variants.items()
            },
            "penalty_comparison": {
                "mean_total_hard_violations_weight_0": zero_violations,
                "mean_total_hard_violations_positive_weight": positive_violations,
                "positive_vs_zero_price_mae_ratio": penalty_price_ratio,
                "positive_penalty_improves_hard_checks_without_material_price_degradation": (
                    positive_violations < zero_violations
                    and penalty_price_ratio <= protocol.material_price_degradation_ratio
                ),
            },
        },
    }
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output, result
