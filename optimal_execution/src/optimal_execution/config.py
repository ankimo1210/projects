"""Configuration loading and typed access.

YAML profiles live in ``configs/``. A profile may declare ``extends: <file>``
(relative to its own directory); the child is deep-merged over the parent.
The raw merged dict is retained on :class:`Config` so that experiment-level
override patches (stress regimes, misspecification tests) can be applied with
:meth:`Config.with_overrides`.

Unit conventions are documented in ``docs/METHODOLOGY.md`` and in
``configs/default.yaml``.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

TRADING_DAY_SECONDS: float = 6.5 * 3600.0  # 23,400 s
TRADING_YEAR_SECONDS: float = 252.0 * TRADING_DAY_SECONDS  # 5,896,800 s


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Return ``base`` recursively updated with ``override`` (override wins)."""
    out = copy.deepcopy(base)
    for key, value in override.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _load_yaml_with_extends(path: Path, _depth: int = 0) -> dict[str, Any]:
    if _depth > 4:
        raise ValueError(f"extends chain too deep at {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    parent_name = data.pop("extends", None)
    if parent_name is not None:
        parent = _load_yaml_with_extends(path.parent / parent_name, _depth + 1)
        data = deep_merge(parent, data)
    return data


@dataclass(frozen=True)
class StochasticVolConfig:
    enabled: bool = False
    regime_vol_mult: float = 2.0
    switch_prob_per_step: float = 0.02


@dataclass(frozen=True)
class JumpConfig:
    enabled: bool = False
    intensity_per_hour: float = 1.0
    jump_sigma_bps: float = 15.0


@dataclass(frozen=True)
class AlphaConfig:
    enabled: bool = False
    drift_bps_per_hour: float = 0.0
    decay_seconds: float = 600.0


@dataclass(frozen=True)
class LiquidityConfig:
    spread_vol_beta: float = 0.5
    spread_stress_mult: float = 3.0
    stress_prob_per_step: float = 0.0
    depth_shares: float = 4000.0
    depth_sigma: float = 0.35
    deep_liquidity_mult: float = 5.0
    replenish_rate: float = 0.25


@dataclass(frozen=True)
class ImpactConfig:
    temporary_eta: float = 5.0e-5
    permanent_gamma: float = 2.5e-7
    transient_eta: float = 2.0e-6
    resilience_rho: float = 0.01
    propagator: str = "exponential"
    powerlaw_beta: float = 0.5
    powerlaw_tau0: float = 30.0
    sqrt_impact_Y: float = 0.8


@dataclass(frozen=True)
class LOBConfig:
    sub_steps_per_decision: int = 15
    flow_scale: float = 1.0
    market_order_size_mean: float = 250.0
    limit_order_rate_mult: float = 2.0
    limit_order_size_mean: float = 300.0
    cancel_rate_mult: float = 1.0
    imbalance_beta0: float = 0.0
    imbalance_beta1: float = 0.8
    imbalance_beta2: float = 25.0
    imbalance_beta3: float = 0.5
    intensity_cap_mult: float = 5.0
    adverse_alpha_phi: float = 0.97
    adverse_alpha_sigma_bps: float = 1.2
    adverse_alpha_to_flow: float = 0.6
    adverse_alpha_to_drift: float = 0.5


@dataclass(frozen=True)
class RewardConfig:
    cost_scale: float = 1.0e-3
    inventory_penalty: float = 1.0e-6
    impact_penalty: float = 5.0e-2
    constraint_penalty: float = 0.05


@dataclass(frozen=True)
class RLConfig:
    training_episodes: int = 3000
    validation_episodes: int = 200
    test_episodes: int = 600
    seeds: tuple[int, ...] = (1210,)
    hidden_size: int = 64
    learning_rate: float = 3.0e-4
    gamma: float = 0.999
    gae_lambda: float = 0.95
    clip_epsilon: float = 0.2
    entropy_coef: float = 0.01
    entropy_final: float = 0.001
    value_coef: float = 0.5
    rollout_steps: int = 2048
    minibatch_size: int = 256
    update_epochs: int = 4
    max_grad_norm: float = 0.5
    eval_every_episodes: int = 250
    early_stop_patience: int = 6
    reward: RewardConfig = field(default_factory=RewardConfig)


@dataclass(frozen=True)
class AblationConfig:
    features: tuple[str, ...] = (
        "imbalance",
        "recent_flow",
        "transient_impact",
        "volume_state",
        "vol_state",
    )
    training_episodes: int = 1500


@dataclass(frozen=True)
class Config:
    """Typed view over the merged YAML profile. ``raw`` keeps the full dict."""

    raw: dict[str, Any]

    profile: str = "default"
    seed: int = 1210
    side: str = "sell"
    initial_inventory: float = 100000.0
    horizon_seconds: float = 1800.0
    n_decision_steps: int = 60
    arrival_price: float = 100.0

    annualized_volatility: float = 0.20
    vol_profile: str = "u_shape"
    vol_u_amplitude: float = 0.5
    stochastic_vol: StochasticVolConfig = field(default_factory=StochasticVolConfig)
    jumps: JumpConfig = field(default_factory=JumpConfig)
    alpha: AlphaConfig = field(default_factory=AlphaConfig)

    average_daily_volume: float = 5_000_000.0
    volume_profile: str = "u_shape"
    volume_u_amplitude: float = 0.5
    volume_mult_sigma: float = 0.30
    spread_bps: float = 2.0
    tick_size: float = 0.01
    fee_bps: float = 0.10
    liquidity: LiquidityConfig = field(default_factory=LiquidityConfig)

    impact: ImpactConfig = field(default_factory=ImpactConfig)

    risk_aversion_lambda: float = 1.0e-6
    max_participation_rate: float = 0.20
    max_child_order_frac: float = 0.10
    terminal_inventory_penalty: float = 10.0
    price_collar_bps: float = 150.0

    lob: LOBConfig = field(default_factory=LOBConfig)

    n_scenarios: int = 2000
    n_test_scenarios: int = 5000
    mc_chunk_size: int = 5000
    lob_eval_episodes: int = 600
    lob_stress_episodes: int = 200
    lob_example_episodes: int = 6

    rl: RLConfig = field(default_factory=RLConfig)
    ablation: AblationConfig = field(default_factory=AblationConfig)

    artifacts_dir: str = "artifacts"
    reports_dir: str = "reports"

    # ---- derived quantities -------------------------------------------------

    @property
    def dt(self) -> float:
        """Decision interval in seconds."""
        return self.horizon_seconds / self.n_decision_steps

    @property
    def sign(self) -> int:
        """+1 for a sell program, -1 for a buy program."""
        return 1 if self.side == "sell" else -1

    @property
    def sigma_abs(self) -> float:
        """Unaffected mid volatility in currency / share / sqrt(second)."""
        return self.annualized_volatility * self.arrival_price / TRADING_YEAR_SECONDS**0.5

    @property
    def sigma_daily(self) -> float:
        """Daily volatility in currency / share."""
        return self.sigma_abs * TRADING_DAY_SECONDS**0.5

    @property
    def market_volume_rate(self) -> float:
        """Average market volume in shares / second."""
        return self.average_daily_volume / TRADING_DAY_SECONDS

    @property
    def expected_interval_volume(self) -> float:
        """Expected market volume over the whole execution horizon (shares)."""
        return self.market_volume_rate * self.horizon_seconds

    @property
    def half_spread(self) -> float:
        """Average half-spread in currency."""
        return 0.5 * self.spread_bps * 1e-4 * self.arrival_price

    @property
    def notional(self) -> float:
        return self.initial_inventory * self.arrival_price

    @property
    def fee_per_share(self) -> float:
        return self.fee_bps * 1e-4 * self.arrival_price

    @property
    def mo_rate_per_side(self) -> float:
        """Exogenous market-order arrival rate per second per side, derived
        from ADV so the book world and the schedule world share one volume
        scale: 2 sides * rate * mean size = flow_scale * ADV rate."""
        return (
            self.lob.flow_scale * self.market_volume_rate / (2.0 * self.lob.market_order_size_mean)
        )

    @property
    def kappa(self) -> float:
        """Almgren–Chriss urgency sqrt(lambda sigma^2 / eta), 1/second."""
        return (self.risk_aversion_lambda * self.sigma_abs**2 / self.impact.temporary_eta) ** 0.5

    # ---- construction ---------------------------------------------------------

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> Config:
        r = raw

        def sub(cls: type, key: str, **renames: str) -> Any:
            data = dict(r.get(key) or {})
            fields = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
            kwargs = {}
            for k, v in data.items():
                k = renames.get(k, k)
                if k in fields:
                    kwargs[k] = tuple(v) if isinstance(v, list) else v
            return cls(**kwargs)

        rl_data = dict(r.get("rl") or {})
        reward = sub(RewardConfig, "reward") if "reward" not in rl_data else None
        if "reward" in rl_data:
            reward_data = {
                k: v
                for k, v in (rl_data.pop("reward") or {}).items()
                if k in RewardConfig.__dataclass_fields__
            }
            reward = RewardConfig(**reward_data)
        rl_kwargs = {
            k: (tuple(v) if isinstance(v, list) else v)
            for k, v in rl_data.items()
            if k in RLConfig.__dataclass_fields__
        }
        rl_cfg = RLConfig(reward=reward or RewardConfig(), **rl_kwargs)

        scalar_fields = {
            f
            for f in Config.__dataclass_fields__
            if f
            not in {
                "raw",
                "stochastic_vol",
                "jumps",
                "alpha",
                "liquidity",
                "impact",
                "lob",
                "rl",
                "ablation",
            }
        }
        scalars = {k: v for k, v in r.items() if k in scalar_fields}
        return Config(
            raw=copy.deepcopy(r),
            stochastic_vol=sub(StochasticVolConfig, "stochastic_vol"),
            jumps=sub(JumpConfig, "jumps"),
            alpha=sub(AlphaConfig, "alpha"),
            liquidity=sub(LiquidityConfig, "liquidity"),
            impact=sub(ImpactConfig, "impact"),
            lob=sub(LOBConfig, "lob"),
            rl=rl_cfg,
            ablation=sub(AblationConfig, "ablation"),
            **scalars,
        )

    def with_overrides(self, patch: dict[str, Any]) -> Config:
        """Return a new Config with ``patch`` deep-merged over the raw dict."""
        return Config.from_dict(deep_merge(self.raw, patch))

    def stress_regimes(self) -> dict[str, Config]:
        """Named stress-regime Configs built from ``stress_regimes`` overrides."""
        regimes = self.raw.get("stress_regimes") or {}
        return {name: self.with_overrides(patch) for name, patch in regimes.items()}

    def misspecification_config(self) -> Config:
        patch = (self.raw.get("misspecification") or {}).get("test_overrides") or {}
        return self.with_overrides(patch)


def load_config(path: str | Path) -> Config:
    """Load a YAML profile (honouring ``extends``) into a :class:`Config`."""
    p = Path(path)
    raw = _load_yaml_with_extends(p)
    cfg = Config.from_dict(raw)
    _validate(cfg)
    return cfg


def _validate(cfg: Config) -> None:
    if cfg.side not in ("sell", "buy"):
        raise ValueError(f"side must be 'sell' or 'buy', got {cfg.side!r}")
    if cfg.initial_inventory <= 0:
        raise ValueError("initial_inventory must be positive")
    if cfg.horizon_seconds <= 0 or cfg.n_decision_steps <= 0:
        raise ValueError("horizon_seconds and n_decision_steps must be positive")
    if cfg.impact.temporary_eta <= 0:
        raise ValueError("temporary_eta must be positive")
    if not 0 < cfg.max_participation_rate <= 1:
        raise ValueError("max_participation_rate must be in (0, 1]")
    if cfg.vol_profile not in ("constant", "u_shape"):
        raise ValueError(f"unknown vol_profile {cfg.vol_profile!r}")
    if cfg.volume_profile not in ("flat", "u_shape"):
        raise ValueError(f"unknown volume_profile {cfg.volume_profile!r}")
    if cfg.impact.propagator not in ("exponential", "powerlaw"):
        raise ValueError(f"unknown propagator {cfg.impact.propagator!r}")
