"""Configuration for the Phase 2 neural-pricing pipeline.

The pricing namespace is intentionally independent from the Phase 1
``ProjectConfig`` used by the hedging experiment.  This prevents a pricing
dataset or checkpoint from being mistaken for a hedge-policy artifact.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class PricingDataConfig:
    """Latin-hypercube sampling design and dimensionless parameter bounds."""

    seed: int = 1210
    train_size: int = 8192
    validation_size: int = 2048
    test_size: int = 2048
    ood_size: int = 2048
    sampling: str = "latin_hypercube"
    bounds: dict[str, tuple[float, float]] = field(
        default_factory=lambda: {
            "x": (0.6, 1.4),
            "tau": (1.0 / 365.0, 2.0),
            "r": (-0.02, 0.10),
            "q": (0.0, 0.08),
            "sigma": (0.05, 0.80),
        }
    )

    def validate(self) -> None:
        """Reject bad seeds, sizes, sampling kinds, and parameter bounds."""
        if self.seed < 0:
            raise ValueError("data.seed must be non-negative")
        if min(self.train_size, self.validation_size, self.test_size, self.ood_size) <= 0:
            raise ValueError("all pricing split sizes must be positive")
        if self.sampling != "latin_hypercube":
            raise ValueError("sampling must be latin_hypercube")
        expected = {"x", "tau", "r", "q", "sigma"}
        if set(self.bounds) != expected:
            raise ValueError(f"data.bounds must contain exactly {sorted(expected)}")
        for name, pair in self.bounds.items():
            if len(pair) != 2 or not pair[0] < pair[1]:
                raise ValueError(f"invalid bounds for {name}")
        if self.bounds["x"][0] <= 0 or self.bounds["tau"][0] <= 0:
            raise ValueError("x and tau bounds must be positive")
        if self.bounds["sigma"][0] <= 0:
            raise ValueError("sigma bounds must be positive")


@dataclass(frozen=True)
class PricingModelConfig:
    """Pricing MLP architecture, output mode, and optional Greek heads."""

    hidden_layers: int = 3
    hidden_units: int = 64
    activation: str = "silu"
    output_mode: str = "price"
    direct_greek_heads: bool = False

    def validate(self) -> None:
        """Reject non-positive dimensions and unknown activation/output modes."""
        if self.hidden_layers <= 0 or self.hidden_units <= 0:
            raise ValueError("pricing model dimensions must be positive")
        if self.activation not in {"silu", "tanh"}:
            raise ValueError("pricing activation must be silu or tanh")
        if self.output_mode not in {"price", "time_value"}:
            raise ValueError("pricing output_mode must be price or time_value")


@dataclass(frozen=True)
class PricingTrainingConfig:
    """Optimizer settings and price/Greek/differential/penalty loss weights."""

    device: str = "cpu"
    batch_size: int = 1024
    epochs: int = 150
    learning_rate: float = 0.002
    weight_decay: float = 1e-6
    early_stopping_patience: int = 20
    price_weight: float = 1.0
    greek_weight: float = 0.1
    differential_weight: float = 0.1
    penalty_weight: float = 0.0

    def validate(self) -> None:
        """Reject unknown devices, non-positive counts, and negative weights."""
        if self.device not in {"cpu", "cuda", "auto"}:
            raise ValueError("pricing device must be cpu, cuda, or auto")
        positive = (
            self.batch_size,
            self.epochs,
            self.learning_rate,
            self.early_stopping_patience,
            self.price_weight,
        )
        if any(value <= 0 for value in positive):
            raise ValueError("pricing training counts/rates must be positive")
        if (
            min(self.weight_decay, self.greek_weight, self.differential_weight, self.penalty_weight)
            < 0
        ):
            raise ValueError("pricing weights cannot be negative")


@dataclass(frozen=True)
class PricingOutputConfig:
    """Namespaced artifact and report output locations."""

    artifacts_dir: str = "artifacts/pricing"
    reports_dir: str = "reports"
    namespace: str = "default"

    def validate(self) -> None:
        """Require a safe relative namespace (no absolute paths or '..')."""
        if (
            not self.namespace
            or Path(self.namespace).is_absolute()
            or ".." in Path(self.namespace).parts
        ):
            raise ValueError("output.namespace must be a safe relative name")


@dataclass(frozen=True)
class PricingConfig:
    """Complete Phase-2 pricing configuration with a stable fingerprint."""

    profile: str = "default"
    data: PricingDataConfig = field(default_factory=PricingDataConfig)
    model: PricingModelConfig = field(default_factory=PricingModelConfig)
    training: PricingTrainingConfig = field(default_factory=PricingTrainingConfig)
    output: PricingOutputConfig = field(default_factory=PricingOutputConfig)

    def validate(self) -> None:
        """Require a profile name and validate every sub-configuration."""
        if not self.profile:
            raise ValueError("profile must be non-empty")
        self.data.validate()
        self.model.validate()
        self.training.validate()
        self.output.validate()

    def to_dict(self) -> dict[str, Any]:
        """Plain-dict view used for JSON export and fingerprinting."""
        return asdict(self)

    def fingerprint(self, length: int = 16) -> str:
        """Deterministic SHA-256 prefix of the sorted configuration JSON."""
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()[:length]


def _bounds(raw: dict[str, Any]) -> dict[str, tuple[float, float]]:
    return {str(key): (float(value[0]), float(value[1])) for key, value in raw.items()}


def load_pricing_config(path: str | Path) -> PricingConfig:
    """Load and validate a pricing-only YAML profile."""
    with Path(path).open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise ValueError("pricing configuration root must be a mapping")
    data_raw = dict(raw.get("data", {}))
    if "bounds" in data_raw:
        data_raw["bounds"] = _bounds(data_raw["bounds"])
    config = PricingConfig(
        profile=str(raw.get("profile", "default")),
        data=PricingDataConfig(**data_raw),
        model=PricingModelConfig(**raw.get("model", {})),
        training=PricingTrainingConfig(**raw.get("training", {})),
        output=PricingOutputConfig(**raw.get("output", {})),
    )
    config.validate()
    return config


def pricing_run_directory(config: PricingConfig, project_root: str | Path) -> Path:
    """Return the isolated Phase 2 output directory."""
    return (
        Path(project_root)
        / config.output.artifacts_dir
        / config.output.namespace
        / config.fingerprint()
    )
