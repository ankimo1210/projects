"""Paths, provenance metadata, and deterministic artifact writers.

All generated outputs carry a small common provenance record.  The project
is often run while it is still uncommitted, so ``git_commit`` may be ``null``;
that state is recorded explicitly rather than guessed.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from .config import Config

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_SOURCE_FILES = (
    "almgren_chriss.py",
    "config.py",
    "environment.py",
    "evaluation.py",
    "experiments.py",
    "fills.py",
    "impact.py",
    "liquidity.py",
    "order_book.py",
    "price_process.py",
    "random.py",
    "resilience.py",
    "rl_policy.py",
    "rl_training.py",
    "signal_adaptive.py",
    "strategies.py",
    "tca.py",
    "volume.py",
)


def resolve_project_path(path: str | Path) -> Path:
    """Resolve a configured path relative to the project directory."""
    p = Path(path)
    return p if p.is_absolute() else PROJECT_ROOT / p


def artifact_dirs(cfg: Config) -> dict[str, Path]:
    root = resolve_project_path(cfg.artifacts_dir)
    return {
        "root": root,
        "data": root / "data",
        "metrics": root / "metrics",
        "checkpoints": root / "checkpoints",
        "figures": root / "figures",
        "reports": resolve_project_path(cfg.reports_dir),
    }


def ensure_artifact_dirs(cfg: Config) -> dict[str, Path]:
    paths = artifact_dirs(cfg)
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def git_commit() -> str | None:
    """Return HEAD when available; an uncommitted project still records HEAD."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    value = proc.stdout.strip()
    return value or None


def generated_at() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def config_fingerprint(cfg: Config) -> str:
    """Stable SHA-256 of the complete merged experiment configuration."""
    payload = json.dumps(
        json_safe(cfg.raw),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@lru_cache(maxsize=1)
def model_fingerprint() -> str:
    """Hash model/training source so stale outputs survive neither dirty nor new commits."""
    digest = hashlib.sha256()
    source_root = Path(__file__).resolve().parent
    for name in MODEL_SOURCE_FILES:
        digest.update(name.encode("utf-8"))
        digest.update((source_root / name).read_bytes())
    return digest.hexdigest()


def provenance(
    cfg: Config,
    *,
    strategy_id: str | None = None,
    model_parameters: dict[str, Any] | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "seed": cfg.seed,
        "profile": cfg.profile,
        "config_fingerprint": config_fingerprint(cfg),
        "model_fingerprint": model_fingerprint(),
        "generated_at": timestamp or generated_at(),
        "git_commit": git_commit(),
        "model_parameters": model_parameters or {},
    }
    if strategy_id is not None:
        out["strategy_id"] = strategy_id
    return out


def with_provenance_columns(
    frame: pd.DataFrame,
    cfg: Config,
    *,
    strategy_id: str | None = None,
    model_parameters: dict[str, Any] | None = None,
    timestamp: str | None = None,
) -> pd.DataFrame:
    """Return a copy with locale-independent provenance columns."""
    meta = provenance(cfg, strategy_id=strategy_id, timestamp=timestamp)
    out = frame.copy()
    for key in (
        "seed",
        "profile",
        "config_fingerprint",
        "model_fingerprint",
        "generated_at",
        "git_commit",
    ):
        out[key] = meta[key]
    params = model_parameters or {
        "side": cfg.side,
        "initial_inventory": cfg.initial_inventory,
        "horizon_seconds": cfg.horizon_seconds,
        "n_decision_steps": cfg.n_decision_steps,
        "annualized_volatility": cfg.annualized_volatility,
        "temporary_eta": cfg.impact.temporary_eta,
        "permanent_gamma": cfg.impact.permanent_gamma,
        "transient_eta": cfg.impact.transient_eta,
        "resilience_rho": cfg.impact.resilience_rho,
        "lob_sub_steps": cfg.lob.sub_steps_per_decision,
        "rl_hidden_size": cfg.rl.hidden_size,
    }
    out["model_parameters_json"] = json.dumps(
        json_safe(params), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    if strategy_id is not None and "strategy_id" not in out:
        out["strategy_id"] = strategy_id
    return out


def write_frame(
    frame: pd.DataFrame,
    path: Path,
    cfg: Config,
    *,
    strategy_id: str | None = None,
    model_parameters: dict[str, Any] | None = None,
    timestamp: str | None = None,
    parquet: bool = False,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = with_provenance_columns(
        frame,
        cfg,
        strategy_id=strategy_id,
        model_parameters=model_parameters,
        timestamp=timestamp,
    )
    if parquet:
        out.to_parquet(path, index=False)
    else:
        out.to_csv(path, index=False)
    return path


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            json_safe(payload),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_safe(value: Any) -> Any:
    """Convert NumPy/pandas scalars and non-finite values for strict JSON."""
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if hasattr(value, "item"):
        try:
            return json_safe(value.item())
        except (TypeError, ValueError):
            pass
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, Path):
        return str(value)
    return value
