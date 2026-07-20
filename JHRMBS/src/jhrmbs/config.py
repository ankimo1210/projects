from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from jhrmbs.exceptions import ConfigurationError


@dataclass(frozen=True)
class HttpConfig:
    timeout_seconds: float = 60.0
    retries: int = 3
    backoff_seconds: float = 0.5
    max_download_mb: int = 64
    user_agent: str = "jhrmbs/0.1 public-research-client"


@dataclass(frozen=True)
class FeatureConfig:
    publication_lag_months: int = 1
    psj_seasoning_months: int = 60
    rate_feature_mode: str = "jgb_proxy"


@dataclass(frozen=True)
class ModelConfig:
    fixed_psj_terminal_cpr_pct: float = 6.0
    time_test_months: int = 12
    vintage_test_years: int = 2
    l2_penalty: float = 0.0001
    minimum_train_rows: int = 250
    random_seed: int = 20260720


@dataclass(frozen=True)
class CashflowConfig:
    cleanup_threshold: float = 0.10
    cleanup_lag_months: int = 1
    valuation_yield_pct: float = 2.0


@dataclass(frozen=True)
class SourceConfig:
    id: str
    kind: str
    url: str
    allowed_hosts: tuple[str, ...]
    data_definition: str
    coverage: str
    filename: str | None = None
    link_pattern: str | None = None


@dataclass(frozen=True)
class AppConfig:
    data_root: Path
    http: HttpConfig = field(default_factory=HttpConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    models: ModelConfig = field(default_factory=ModelConfig)
    cashflow: CashflowConfig = field(default_factory=CashflowConfig)
    sources: tuple[SourceConfig, ...] = ()
    config_path: Path | None = None


def _default_config_path() -> Path:
    candidates = [
        Path("jhrmbs.yml"),
        Path("config/default.yml"),
        Path("JHRMBS/config/default.yml"),
    ]
    env_path = os.getenv("JHRMBS_CONFIG")
    if env_path:
        candidates.insert(0, Path(env_path))
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise ConfigurationError(
        "設定ファイルが見つかりません。--config JHRMBS/config/default.yml を指定してください。"
    )


def _section(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise ConfigurationError(f"{key} must be a mapping")
    return value


def load_config(path: str | Path | None = None) -> AppConfig:
    config_path = Path(path).expanduser().resolve() if path else _default_config_path()
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigurationError(f"設定ファイルを読めません: {config_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ConfigurationError("configuration root must be a mapping")

    project_root = (
        config_path.parent.parent if config_path.parent.name == "config" else config_path.parent
    )
    root_value = os.getenv("JHRMBS_DATA_ROOT", str(payload.get("data_root", "../_data/jhrmbs")))
    data_root = Path(root_value).expanduser()
    if not data_root.is_absolute():
        data_root = (project_root / data_root).resolve()

    sources_raw = payload.get("sources", [])
    if not isinstance(sources_raw, list):
        raise ConfigurationError("sources must be a list")
    sources: list[SourceConfig] = []
    for raw in sources_raw:
        if not isinstance(raw, dict):
            raise ConfigurationError("each source must be a mapping")
        try:
            sources.append(
                SourceConfig(
                    id=str(raw["id"]),
                    kind=str(raw["kind"]),
                    url=str(raw["url"]),
                    allowed_hosts=tuple(str(host) for host in raw["allowed_hosts"]),
                    data_definition=str(raw["data_definition"]),
                    coverage=str(raw["coverage"]),
                    filename=str(raw["filename"]) if raw.get("filename") else None,
                    link_pattern=str(raw["link_pattern"]) if raw.get("link_pattern") else None,
                )
            )
        except KeyError as exc:
            raise ConfigurationError(f"source is missing {exc.args[0]}") from exc

    features = FeatureConfig(**_section(payload, "features"))
    if features.rate_feature_mode not in {"jgb_proxy", "mortgage_rate"}:
        raise ConfigurationError(
            "features.rate_feature_mode must be 'jgb_proxy' or 'mortgage_rate'"
        )
    if features.publication_lag_months < 0 or features.psj_seasoning_months <= 0:
        raise ConfigurationError("feature lags must be non-negative and seasoning positive")

    return AppConfig(
        data_root=data_root,
        http=HttpConfig(**_section(payload, "http")),
        features=features,
        models=ModelConfig(**_section(payload, "models")),
        cashflow=CashflowConfig(**_section(payload, "cashflow")),
        sources=tuple(sources),
        config_path=config_path,
    )
