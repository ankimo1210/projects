"""Validated configuration objects and YAML profile loading.

The configuration layer is intentionally dependency-light and strict: unknown
keys are rejected so that a misspelled scientific parameter cannot silently
fall back to a default value.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from dataclasses import asdict, dataclass, field, fields
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class FbmConfig:
    """Fractional Brownian-motion simulation and path diagnostics."""

    h_values: tuple[float, ...] = (0.10, 0.50, 0.80)
    n_steps: int = 4096
    n_paths: int = 200
    n_display_paths: int = 6
    horizon: float = 1.0
    n_lags: int = 15
    max_lag_fraction: float = 0.10

    def validate(self) -> None:
        _validate_h_values(self.h_values)
        if self.n_steps < 2 or self.n_paths < 1 or self.n_display_paths < 1:
            raise ValueError("fBM path counts and n_steps must be positive")
        if self.horizon <= 0:
            raise ValueError("fBM horizon must be positive")
        if self.n_lags < 3 or not 0 < self.max_lag_fraction <= 0.5:
            raise ValueError("fBM lag settings are invalid")


@dataclass(frozen=True)
class HurstStudyConfig:
    """Monte Carlo recovery study for Hurst estimators."""

    h_values: tuple[float, ...] = (0.10, 0.50, 0.80)
    sample_sizes: tuple[int, ...] = (512, 2048, 8192)
    n_replications: int = 200
    estimators: tuple[str, ...] = (
        "variogram",
        "madogram",
        "aggregated_variance",
    )
    n_lags: int = 15

    def validate(self) -> None:
        _validate_h_values(self.h_values)
        if not self.sample_sizes or any(n < 32 for n in self.sample_sizes):
            raise ValueError("Hurst sample sizes must all be at least 32")
        if self.n_replications < 1 or self.n_lags < 3:
            raise ValueError("Hurst replications and lag count must be positive")
        allowed = {"variogram", "madogram", "aggregated_variance"}
        unknown = set(self.estimators) - allowed
        if not self.estimators or unknown:
            raise ValueError(f"unknown Hurst estimators: {sorted(unknown)}")


@dataclass(frozen=True)
class OuConfig:
    """Ordinary and fractional OU log-volatility comparison."""

    kappa: float = 5.0
    mean: float = math.log(0.20)
    target_std: float = 0.35
    x0: float = math.log(0.20)
    hurst: float = 0.10
    horizon: float = 4.0
    n_steps: int = 4096
    n_paths: int = 100
    burn_in_steps: int = 1024

    def validate(self) -> None:
        if self.kappa <= 0 or self.target_std <= 0:
            raise ValueError("OU kappa and target_std must be positive")
        _validate_h_values((self.hurst,))
        if self.horizon <= 0 or self.n_steps < 2 or self.n_paths < 1:
            raise ValueError("OU horizon and simulation sizes must be positive")
        if self.burn_in_steps < 0:
            raise ValueError("OU burn_in_steps cannot be negative")


@dataclass(frozen=True)
class BergomiConfig:
    """Rough Bergomi-style pricing-measure simulation parameters."""

    s0: float = 100.0
    r: float = 0.0
    h: float = 0.10
    eta: float = 1.50
    rho: float = -0.70
    xi0: float = 0.04
    maturity_years: float = 1.0
    n_steps: int = 500
    n_paths: int = 30_000
    chunk_size: int = 15_000
    keep_paths: int = 200
    h_grid: tuple[float, ...] = (0.05, 0.10, 0.20, 0.50)
    forward_variance: tuple[tuple[float, float], ...] = ()

    def validate(self) -> None:
        if self.s0 <= 0 or self.eta < 0 or self.xi0 <= 0:
            raise ValueError("Bergomi s0/xi0 must be positive and eta non-negative")
        _validate_h_values((self.h, *self.h_grid))
        if not -1 <= self.rho <= 1:
            raise ValueError("Bergomi rho must lie in [-1, 1]")
        if self.maturity_years <= 0 or self.n_steps < 1:
            raise ValueError("Bergomi maturity and n_steps must be positive")
        if self.n_paths < 1 or self.chunk_size < 1 or self.keep_paths < 0:
            raise ValueError("Bergomi path and chunk counts are invalid")
        if self.forward_variance:
            previous = -math.inf
            for time, variance in self.forward_variance:
                if time < 0 or time > self.maturity_years or time <= previous:
                    raise ValueError("forward-variance times must increase within maturity")
                if variance <= 0:
                    raise ValueError("forward-variance values must be positive")
                previous = time


@dataclass(frozen=True)
class HestonConfig:
    """Full-truncation Euler Heston benchmark parameters."""

    v0: float = 0.04
    kappa: float = 2.0
    theta: float = 0.04
    nu: float = 0.50
    rho: float = -0.70

    def validate(self) -> None:
        if self.v0 < 0 or self.theta < 0:
            raise ValueError("Heston variances cannot be negative")
        if self.kappa <= 0 or self.nu < 0:
            raise ValueError("Heston kappa must be positive and nu non-negative")
        if not -1 <= self.rho <= 1:
            raise ValueError("Heston rho must lie in [-1, 1]")


@dataclass(frozen=True)
class OptionGridConfig:
    """Strike, maturity and local-skew grids."""

    maturities: tuple[float, ...] = (0.02, 0.05, 0.10, 0.25, 0.50, 1.00)
    log_moneyness_span: float = 0.20
    n_strikes: int = 17
    skew_window_coeff: float = 1.50
    skew_window_cap: float = 0.10
    skew_window_floor: float = 0.03
    skew_maturity_steps: int = 256

    def validate(self) -> None:
        if not self.maturities or any(t <= 0 for t in self.maturities):
            raise ValueError("option maturities must be positive")
        if tuple(sorted(set(self.maturities))) != self.maturities:
            raise ValueError("option maturities must be unique and increasing")
        if self.log_moneyness_span <= 0 or self.n_strikes < 5:
            raise ValueError("option strike grid is invalid")
        if self.n_strikes % 2 == 0:
            raise ValueError("option n_strikes must be odd so that ATM is included")
        if self.skew_window_coeff <= 0:
            raise ValueError("skew_window_coeff must be positive")
        if not 0 < self.skew_window_floor <= self.skew_window_cap:
            raise ValueError("skew window floor/cap are invalid")
        if self.skew_maturity_steps < 16:
            raise ValueError("skew_maturity_steps must be at least 16")


@dataclass(frozen=True)
class HawkesConfig:
    """Bivariate buy/sell Hawkes scenarios."""

    horizon: float = 2000.0
    target_rate: float = 10.0
    exponential_beta: float = 1.0
    betas: tuple[float, ...] = (
        0.1,
        0.6309573445,
        3.981071706,
        25.11886432,
        158.4893192,
        1000.0,
    )
    alpha_tail: float = 0.50
    branching_stable: float = 0.60
    branching_critical: float = 0.97
    cross_fraction: float = 0.80
    max_events: int = 100_000
    bin_width: float = 1.0
    intensity_grid_points: int = 2000

    def validate(self) -> None:
        if self.horizon <= 0 or self.target_rate <= 0:
            raise ValueError("Hawkes horizon and target_rate must be positive")
        if self.exponential_beta <= 0:
            raise ValueError("Hawkes exponential_beta must be positive")
        if not self.betas or any(beta <= 0 for beta in self.betas):
            raise ValueError("Hawkes betas must be positive")
        if tuple(sorted(self.betas)) != self.betas:
            raise ValueError("Hawkes betas must be increasing")
        if not 0 < self.alpha_tail < 1:
            raise ValueError("Hawkes alpha_tail must lie in (0, 1)")
        for name, branching in (
            ("stable", self.branching_stable),
            ("critical", self.branching_critical),
        ):
            if not 0 <= branching < 0.995:
                raise ValueError(f"Hawkes {name} branching ratio must be below 0.995")
        if self.branching_stable >= self.branching_critical:
            raise ValueError("stable branching must be below near-critical branching")
        if not 0 <= self.cross_fraction <= 1:
            raise ValueError("Hawkes cross_fraction must lie in [0, 1]")
        if self.max_events < 1 or self.bin_width <= 0 or self.intensity_grid_points < 2:
            raise ValueError("Hawkes simulation sizes are invalid")


@dataclass(frozen=True)
class MicrostructureConfig:
    """Signed-event price and realized-volatility proxy settings."""

    p0: float = 100.0
    tick_eps: float = 0.01
    observation_noise_std: float = 0.0
    rv_window: int = 25
    intensity_window: int = 25
    floor_quantile: float = 0.05

    def validate(self) -> None:
        if self.p0 <= 0 or self.tick_eps <= 0:
            raise ValueError("microstructure price and tick size must be positive")
        if self.observation_noise_std < 0:
            raise ValueError("observation noise cannot be negative")
        if self.rv_window < 2 or self.intensity_window < 2:
            raise ValueError("microstructure rolling windows must be at least 2")
        if not 0 <= self.floor_quantile < 1:
            raise ValueError("floor_quantile must lie in [0, 1)")


@dataclass(frozen=True)
class NoiseStudyConfig:
    """Sampling/noise fragility study for roughness estimators."""

    latent_h: float = 0.10
    n_steps: int = 4096
    horizon: float = 1.0
    n_replications: int = 30
    noise_stds: tuple[float, ...] = (0.0, 0.02, 0.05, 0.10, 0.20)
    strides: tuple[int, ...] = (1, 2, 4, 8)
    estimators: tuple[str, ...] = ("variogram", "madogram", "aggregated_variance")
    aggregate_window: int = 4
    preaverage_window: int = 4

    def validate(self) -> None:
        _validate_h_values((self.latent_h,))
        if self.n_steps < 64 or self.horizon <= 0 or self.n_replications < 1:
            raise ValueError("noise-study simulation sizes are invalid")
        if not self.noise_stds or any(level < 0 for level in self.noise_stds):
            raise ValueError("noise levels must be non-negative")
        if not self.strides or any(stride < 1 for stride in self.strides):
            raise ValueError("sampling strides must be positive")
        allowed = {"variogram", "madogram", "aggregated_variance"}
        unknown = set(self.estimators) - allowed
        if not self.estimators or unknown:
            raise ValueError(f"unknown noise-study estimators: {sorted(unknown)}")
        if self.aggregate_window < 2 or self.preaverage_window < 2:
            raise ValueError("aggregation windows must be at least 2")


@dataclass(frozen=True)
class OutputConfig:
    """Relative output locations."""

    artifacts_dir: str = "artifacts"
    reports_dir: str = "reports"
    notebook_path: str = "notebooks/01_rough_volatility_visual_lab.ipynb"

    def validate(self) -> None:
        if not self.artifacts_dir or not self.reports_dir or not self.notebook_path:
            raise ValueError("output paths cannot be empty")


@dataclass(frozen=True)
class ProjectConfig:
    """Fully resolved configuration for one execution profile."""

    profile: str = "default"
    seed: int = 1210
    fbm: FbmConfig = field(default_factory=FbmConfig)
    hurst: HurstStudyConfig = field(default_factory=HurstStudyConfig)
    ou: OuConfig = field(default_factory=OuConfig)
    bergomi: BergomiConfig = field(default_factory=BergomiConfig)
    heston: HestonConfig = field(default_factory=HestonConfig)
    options: OptionGridConfig = field(default_factory=OptionGridConfig)
    hawkes: HawkesConfig = field(default_factory=HawkesConfig)
    microstructure: MicrostructureConfig = field(default_factory=MicrostructureConfig)
    noise: NoiseStudyConfig = field(default_factory=NoiseStudyConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    def validate(self) -> None:
        if not self.profile:
            raise ValueError("profile cannot be empty")
        if not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError("seed must be a non-negative integer")
        for section in (
            self.fbm,
            self.hurst,
            self.ou,
            self.bergomi,
            self.heston,
            self.options,
            self.hawkes,
            self.microstructure,
            self.noise,
            self.output,
        ):
            section.validate()
        if self.options.maturities[-1] > self.bergomi.maturity_years:
            raise ValueError("option maturity exceeds the Bergomi horizon")
        for maturity in self.options.maturities:
            index = maturity * self.bergomi.n_steps / self.bergomi.maturity_years
            if not math.isclose(index, round(index), rel_tol=0.0, abs_tol=1e-9):
                raise ValueError(f"option maturity {maturity:g} is not aligned to the Bergomi grid")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def fingerprint(self, length: int = 12) -> str:
        if length < 1:
            raise ValueError("fingerprint length must be positive")
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def _validate_h_values(values: tuple[float, ...]) -> None:
    if not values or any(not 0 < value < 1 for value in values):
        raise ValueError("Hurst values must lie strictly between 0 and 1")


def _strict_section[T](cls: type[T], raw: Any, name: str) -> T:
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError(f"configuration section {name!r} must be a mapping")
    allowed = {item.name for item in fields(cls)}
    unknown = set(raw) - allowed
    if unknown:
        raise ValueError(f"unknown keys in {name}: {sorted(unknown)}")
    return cls(**raw)


def _tuple_values(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize YAML sequences into immutable tuple-valued fields."""
    converted = dict(raw)
    tuple_keys = {
        "h_values",
        "sample_sizes",
        "estimators",
        "h_grid",
        "maturities",
        "betas",
        "noise_stds",
        "strides",
    }
    for key in tuple_keys & converted.keys():
        value = converted[key]
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"configuration key {key!r} must be a sequence")
        converted[key] = tuple(value)
    if "forward_variance" in converted:
        value = converted["forward_variance"]
        if not isinstance(value, (list, tuple)):
            raise ValueError("forward_variance must be a sequence of [time, variance]")
        try:
            converted["forward_variance"] = tuple(
                (float(point[0]), float(point[1])) for point in value
            )
        except (IndexError, TypeError, ValueError) as exc:
            raise ValueError("forward_variance entries must be [time, variance]") from exc
    return converted


def _construct(raw: dict[str, Any]) -> ProjectConfig:
    allowed = {item.name for item in fields(ProjectConfig)}
    unknown = set(raw) - allowed
    if unknown:
        raise ValueError(f"unknown top-level configuration keys: {sorted(unknown)}")

    def section[T](cls: type[T], name: str) -> T:
        value = raw.get(name, {})
        if isinstance(value, dict):
            value = _tuple_values(value)
        return _strict_section(cls, value, name)

    config = ProjectConfig(
        profile=str(raw.get("profile", "default")),
        seed=raw.get("seed", 1210),
        fbm=section(FbmConfig, "fbm"),
        hurst=section(HurstStudyConfig, "hurst"),
        ou=section(OuConfig, "ou"),
        bergomi=section(BergomiConfig, "bergomi"),
        heston=section(HestonConfig, "heston"),
        options=section(OptionGridConfig, "options"),
        hawkes=section(HawkesConfig, "hawkes"),
        microstructure=section(MicrostructureConfig, "microstructure"),
        noise=section(NoiseStudyConfig, "noise"),
        output=section(OutputConfig, "output"),
    )
    config.validate()
    return config


def load_config(path: str | Path) -> ProjectConfig:
    """Load a YAML profile and reject misspelled or invalid parameters."""
    config_path = Path(path)
    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise ValueError("configuration root must be a mapping")
    return _construct(raw)


def _plain_data(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _plain_data(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_data(item) for item in value]
    if isinstance(value, list):
        return [_plain_data(item) for item in value]
    return value


def save_config(config: ProjectConfig, path: str | Path) -> Path:
    """Write a complete, resolved, safe-loadable YAML configuration."""
    config.validate()
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        yaml.safe_dump(_plain_data(config.to_dict()), sort_keys=False),
        encoding="utf-8",
    )
    return output


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[2],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    commit = result.stdout.strip()
    return commit if len(commit) == 40 else "unknown"


def provenance_stamp(config: ProjectConfig, sample_size: int) -> dict[str, Any]:
    """Return the common provenance payload embedded in metric artifacts."""
    if sample_size < 0:
        raise ValueError("sample_size cannot be negative")
    from rough_volatility import __version__

    return {
        "seed": config.seed,
        "profile": config.profile,
        "params_fingerprint": config.fingerprint(),
        "sample_size": sample_size,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(),
        "package_version": __version__,
    }
