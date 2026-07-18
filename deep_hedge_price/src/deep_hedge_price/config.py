"""Validated configuration objects and YAML loading."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class MarketConfig:
    """GBM market, short-call contract, and transaction-cost parameters."""

    seed: int = 1210
    s0: float = 100.0
    strike: float = 100.0
    maturity_years: float = 30 / 252
    n_steps: int = 30
    mu: float = 0.05
    risk_free_rate: float = 0.0
    volatility: float = 0.20
    transaction_cost_bps: float = 5.0
    option_position: float = -1.0
    antithetic_sampling: bool = True
    reporting_premium: float | None = None

    def validate(self) -> None:
        """Reject non-positive market inputs and non-short option positions."""
        if self.s0 <= 0 or self.strike <= 0:
            raise ValueError("s0 and strike must be positive")
        if self.maturity_years <= 0 or self.n_steps <= 0:
            raise ValueError("maturity_years and n_steps must be positive")
        if self.volatility <= 0:
            raise ValueError("volatility must be positive")
        if self.transaction_cost_bps < 0:
            raise ValueError("transaction_cost_bps cannot be negative")
        if self.option_position >= 0:
            raise ValueError("Phase 1 supports a short option position only")
        if self.reporting_premium is not None and self.reporting_premium < 0:
            raise ValueError("reporting_premium cannot be negative")

    @property
    def dt(self) -> float:
        """Hedging interval in years."""
        return self.maturity_years / self.n_steps

    @property
    def transaction_cost_rate(self) -> float:
        """Proportional cost rate converted from basis points."""
        return self.transaction_cost_bps * 1e-4

    @property
    def short_quantity(self) -> float:
        """Positive number of options sold short."""
        return -self.option_position


@dataclass(frozen=True)
class PolicyConfig:
    """MLP hedge-policy architecture and action clamp bounds."""

    hidden_layers: int = 3
    hidden_units: int = 64
    activation: str = "silu"
    layer_norm: bool = False
    action_min: float = -0.25
    action_max: float = 1.25

    def validate(self) -> None:
        """Reject non-positive dimensions, unknown activations, and bad clamps."""
        if self.hidden_layers <= 0 or self.hidden_units <= 0:
            raise ValueError("policy dimensions must be positive")
        if self.activation not in {"silu", "tanh"}:
            raise ValueError("activation must be 'silu' or 'tanh'")
        if self.action_min >= self.action_max:
            raise ValueError("action_min must be below action_max")


@dataclass(frozen=True)
class RiskConfig:
    """Training risk objective: mse, entropic, or CVaR with its parameters."""

    objective: str = "mse"
    entropic_gamma: float = 10.0
    cvar_alpha: float = 0.95

    def validate(self) -> None:
        """Reject unknown objectives and out-of-range gamma/alpha."""
        if self.objective not in {"mse", "entropic", "cvar"}:
            raise ValueError("objective must be mse, entropic, or cvar")
        if self.entropic_gamma <= 0:
            raise ValueError("entropic_gamma must be positive")
        if not 0 < self.cvar_alpha < 1:
            raise ValueError("cvar_alpha must lie in (0, 1)")


@dataclass(frozen=True)
class TrainingConfig:
    """Optimizer, batching, early-stopping, and device settings."""

    device: str = "auto"
    batch_size: int = 4096
    epochs: int = 200
    learning_rate: float = 0.001
    weight_decay: float = 0.000001
    gradient_clip_norm: float = 5.0
    validation_paths: int = 50000
    test_paths: int = 100000
    early_stopping_patience: int = 25
    scheduler: str = "reduce_on_plateau"
    evaluation_chunk_size: int = 8192
    deterministic: bool = True

    def validate(self) -> None:
        """Reject unknown devices/schedulers and non-positive counts."""
        if self.device not in {"auto", "cpu", "cuda"}:
            raise ValueError("device must be auto, cpu, or cuda")
        positive = (
            self.batch_size,
            self.epochs,
            self.learning_rate,
            self.gradient_clip_norm,
            self.validation_paths,
            self.test_paths,
            self.early_stopping_patience,
            self.evaluation_chunk_size,
        )
        if any(value <= 0 for value in positive):
            raise ValueError("training counts and rates must be positive")
        if self.weight_decay < 0:
            raise ValueError("weight_decay cannot be negative")
        if self.scheduler not in {"reduce_on_plateau", "none"}:
            raise ValueError("unsupported scheduler")


@dataclass(frozen=True)
class ExperimentConfig:
    """Cost-grid sweep, no-trade band, and optional entropic run switches."""

    transaction_cost_grid_bps: tuple[float, ...] = (0.0, 1.0, 5.0, 10.0, 25.0)
    no_trade_band: float = 0.05
    meaningful_trade_threshold: float = 0.001
    run_entropic: bool = True

    def validate(self) -> None:
        """Reject an empty cost grid and negative costs/bands."""
        if not self.transaction_cost_grid_bps:
            raise ValueError("transaction cost grid cannot be empty")
        if any(cost < 0 for cost in self.transaction_cost_grid_bps):
            raise ValueError("transaction costs cannot be negative")
        if self.no_trade_band < 0 or self.meaningful_trade_threshold < 0:
            raise ValueError("band and trade threshold cannot be negative")


@dataclass(frozen=True)
class OutputConfig:
    """Artifact and report output directories."""

    artifacts_dir: str = "artifacts"
    reports_dir: str = "reports"


@dataclass(frozen=True)
class ProjectConfig:
    """Complete validated experiment configuration with a stable fingerprint."""

    profile: str = "default"
    market: MarketConfig = field(default_factory=MarketConfig)
    policy: PolicyConfig = field(default_factory=PolicyConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    experiment: ExperimentConfig = field(default_factory=ExperimentConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    def validate(self) -> None:
        """Validate every sub-configuration."""
        self.market.validate()
        self.policy.validate()
        self.risk.validate()
        self.training.validate()
        self.experiment.validate()

    def to_dict(self) -> dict[str, Any]:
        """Plain-dict view used for YAML export and fingerprinting."""
        return asdict(self)

    def fingerprint(self, length: int = 12) -> str:
        """Deterministic SHA-256 prefix of the sorted configuration JSON."""
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]

    def with_market(self, **changes: Any) -> ProjectConfig:
        """Copy with market-field overrides."""
        return replace(self, market=replace(self.market, **changes))

    def with_risk(self, **changes: Any) -> ProjectConfig:
        """Copy with risk-field overrides."""
        return replace(self, risk=replace(self.risk, **changes))


def _construct(raw: dict[str, Any]) -> ProjectConfig:
    experiment_raw = dict(raw.get("experiment", {}))
    if "transaction_cost_grid_bps" in experiment_raw:
        experiment_raw["transaction_cost_grid_bps"] = tuple(
            float(value) for value in experiment_raw["transaction_cost_grid_bps"]
        )
    config = ProjectConfig(
        profile=str(raw.get("profile", "default")),
        market=MarketConfig(**raw.get("market", {})),
        policy=PolicyConfig(**raw.get("policy", {})),
        risk=RiskConfig(**raw.get("risk", {})),
        training=TrainingConfig(**raw.get("training", {})),
        experiment=ExperimentConfig(**experiment_raw),
        output=OutputConfig(**raw.get("output", {})),
    )
    config.validate()
    return config


def load_config(path: str | Path) -> ProjectConfig:
    """Load and validate a project YAML configuration."""
    config_path = Path(path)
    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise ValueError("configuration root must be a mapping")
    return _construct(raw)


def save_config(config: ProjectConfig, path: str | Path) -> Path:
    """Save a complete resolved configuration next to an artifact."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(config.to_dict(), sort_keys=False), encoding="utf-8")
    return output
