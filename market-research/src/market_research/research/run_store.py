"""Immutable local artifacts for the existing synthetic DemoRun contract."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from market_research.services import DemoRun

SCHEMA_VERSION = 1
_RUN_ID = re.compile(r"[0-9a-f]{16}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_IDENTITY_FIELDS = (
    "schema_version",
    "source_run_id",
    "input_hash",
    "code_commit",
    "config",
    "seed",
    "splits",
    "costs",
    "quality",
    "failure_reasons",
    "mode",
    "backtest_contract",
    "pit_claim",
)
_SECRET_WORDS = (
    "apikey",
    "accesstoken",
    "refreshtoken",
    "password",
    "secret",
    "credential",
    "authorization",
    "privatekey",
)
_SECRET_REASON = re.compile(
    r"(?i)\b(?:authorization\s*:|bearer\s+\S+|api[_-]?key\s*[:=]|"
    r"password\s*[:=]|secret\s*[:=]|(?:access|refresh)[_-]?token\s*[:=])"
)


@dataclass(frozen=True, slots=True)
class RunArtifact:
    artifact_id: str
    path: Path
    manifest: dict[str, object]
    result: dict[str, object]
    html: str | None


def _encode(value: object) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"unsupported run value: {type(value).__name__}")


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=_encode,
    ).encode("utf-8")


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _no_secret_keys(value: object) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError("run metadata keys must be strings")
            normalized = re.sub(r"[^a-z0-9]", "", key.lower())
            if any(word in normalized for word in _SECRET_WORDS):
                raise ValueError("secret-like metadata key cannot be stored")
            _no_secret_keys(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _no_secret_keys(child)


def _plain_mapping(value: Mapping[str, object], name: str) -> dict[str, object]:
    if not isinstance(value, Mapping) or not value:
        raise ValueError(f"{name} must be a nonempty mapping")
    _no_secret_keys(value)
    try:
        plain = json.loads(_canonical(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain finite JSON values") from exc
    if not isinstance(plain, dict):
        raise ValueError(f"{name} must be a JSON object")
    return plain


def _root_path(root: Path, *, create: bool) -> Path:
    path = Path(root).expanduser().resolve()
    if any(
        (marker := parent / ".git").is_file()
        or marker.is_symlink()
        or (marker.is_dir() and (marker / "HEAD").is_file())
        for parent in (path, *path.parents)
    ):
        raise ValueError("run artifacts must be stored outside a Git checkout")
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def _artifact_path(root: Path, artifact_id: str) -> Path:
    if not isinstance(artifact_id, str) or _SHA256.fullmatch(artifact_id) is None:
        raise ValueError("invalid artifact ID")
    path = root / artifact_id
    if path.is_symlink():
        raise ValueError("run artifact path cannot be a symlink")
    return path


def _read_file(folder: Path, name: str) -> bytes:
    path = folder / name
    if path.is_symlink():
        raise ValueError(f"run artifact file cannot be a symlink: {name}")
    if not path.is_file():
        raise ValueError(f"run artifact file is missing: {name}")
    return path.read_bytes()


def _frame_rows(frame: pd.DataFrame, index: pd.DatetimeIndex, name: str) -> list[list[float]]:
    if not frame.index.equals(index):
        raise ValueError(f"{name} timestamps must match demo prices")
    try:
        return frame.to_numpy(dtype=float).tolist()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc


def _series_values(series: pd.Series, index: pd.DatetimeIndex, name: str) -> list[float]:
    if not series.index.equals(index):
        raise ValueError(f"{name} timestamps must match demo prices")
    try:
        return series.to_numpy(dtype=float).tolist()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc


def _result_payload(run: DemoRun) -> dict[str, object]:
    if not isinstance(run, DemoRun) or run.mode != "synthetic-demo":
        raise ValueError("only a synthetic DemoRun can be stored")
    if (
        not isinstance(run.input_hash, str)
        or _SHA256.fullmatch(run.input_hash) is None
        or not isinstance(run.run_id, str)
        or _RUN_ID.fullmatch(run.run_id) is None
        or run.run_id != run.input_hash[:16]
    ):
        raise ValueError("run_id must be the first 16 digits of input hash")
    index = run.prices.index
    if (
        not isinstance(index, pd.DatetimeIndex)
        or index.tz is None
        or index.empty
        or index.has_duplicates
        or not index.is_monotonic_increasing
    ):
        raise ValueError("demo prices require ordered timezone-aware timestamps")
    columns = [str(column) for column in run.prices.columns]
    if not columns or len(columns) != len(set(columns)):
        raise ValueError("demo prices require unique asset columns")
    if list(run.target_weights.columns) != list(run.prices.columns):
        raise ValueError("target weight assets must match demo prices")
    if list(run.backtest.held_weights.columns) != list(run.prices.columns):
        raise ValueError("held weight assets must match demo prices")
    result = {
        "source_run_id": run.run_id,
        "input_hash": run.input_hash,
        "timestamps": [timestamp.isoformat() for timestamp in index],
        "assets": columns,
        "prices": _frame_rows(run.prices, index, "prices"),
        "target_weights": _frame_rows(run.target_weights, index, "target_weights"),
        "bars": [asdict(bar) for bar in run.bars],
        "macro_observations": [asdict(row) for row in run.macro_observations],
        "backtest": {
            "base_currency": run.backtest.base_currency,
            "held_weights": _frame_rows(run.backtest.held_weights, index, "held_weights"),
            "gross_returns": _series_values(run.backtest.gross_returns, index, "gross_returns"),
            "turnover": _series_values(run.backtest.turnover, index, "turnover"),
            "costs": _series_values(run.backtest.costs, index, "costs"),
            "net_returns": _series_values(run.backtest.net_returns, index, "net_returns"),
            "equity": _series_values(run.backtest.equity, index, "equity"),
        },
    }
    try:
        _canonical(result)
    except (TypeError, ValueError) as exc:
        raise ValueError("DemoRun contains nonfinite or unsupported values") from exc
    return result


def _quality(run: DemoRun) -> dict[str, object]:
    return {
        "bar_count": len(run.bars),
        "states": {
            state: sum(bar.quality == state for bar in run.bars)
            for state in ("ok", "warn", "reject")
        },
        "reasons": sorted({reason for bar in run.bars for reason in bar.quality_reasons}),
    }


def _costs(costs: Mapping[str, object], run: DemoRun) -> dict[str, object]:
    plain = _plain_mapping(costs, "costs")
    try:
        commission = plain["commission_bps"]
        slippage = plain["slippage_bps"]
    except KeyError as exc:
        raise ValueError("costs require commission_bps and slippage_bps") from exc
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
        for value in (commission, slippage)
    ):
        raise ValueError("cost basis points must be finite and nonnegative")
    rate = (commission + slippage) / 10_000
    if any(
        not math.isclose(float(cost), float(turnover) * rate, rel_tol=1e-10, abs_tol=1e-12)
        for cost, turnover in zip(run.backtest.costs, run.backtest.turnover, strict=True)
    ):
        raise ValueError("cost settings do not match saved backtest costs")
    return plain


def _write_file(path: Path, payload: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _same_or_conflict(
    root: Path,
    artifact_id: str,
    manifest: dict[str, object],
    result: dict[str, object],
    html: str | None,
) -> RunArtifact:
    existing = load_demo_run(root, artifact_id)
    if existing.manifest != manifest or existing.result != result or existing.html != html:
        raise ValueError("artifact ID already contains different content")
    return existing


def save_demo_run(
    root: Path,
    run: DemoRun,
    *,
    code_commit: str,
    config: Mapping[str, object],
    seed: int | None,
    splits: Mapping[str, object],
    costs: Mapping[str, object],
    failure_reasons: Sequence[str] = (),
    html: str | None = None,
) -> RunArtifact:
    """Save a DemoRun once under a deterministic identity in a Git-external root.

    This is a synthetic, retrospective artifact, not a PIT performance claim.
    Credentials must never be passed in metadata or failure reasons.
    """
    result = json.loads(_canonical(_result_payload(run)))
    if not isinstance(code_commit, str) or _COMMIT.fullmatch(code_commit) is None:
        raise ValueError("code_commit must be a full Git commit hash")
    if seed is not None and (type(seed) is not int or seed < 0):
        raise ValueError("seed must be a nonnegative integer or None")
    if not isinstance(failure_reasons, (list, tuple)) or any(
        not isinstance(reason, str) or not reason.strip() for reason in failure_reasons
    ):
        raise ValueError("failure_reasons must be a sequence of nonempty strings")
    if any(_SECRET_REASON.search(reason) for reason in failure_reasons):
        raise ValueError("secret-like failure reason cannot be stored")
    if html is not None and not isinstance(html, str):
        raise ValueError("html must be a string or None")
    identity = {
        "schema_version": SCHEMA_VERSION,
        "source_run_id": run.run_id,
        "input_hash": run.input_hash,
        "code_commit": code_commit,
        "config": _plain_mapping(config, "config"),
        "seed": seed,
        "splits": _plain_mapping(splits, "splits"),
        "costs": _costs(costs, run),
        "quality": _quality(run),
        "failure_reasons": list(failure_reasons),
        "mode": "synthetic-demo",
        "backtest_contract": "close_to_close_lag1_research_approximation",
        "pit_claim": False,
    }
    artifact_id = _digest(_canonical(identity))
    result_bytes = _canonical(result)
    html_bytes = html.encode("utf-8") if html is not None else None
    manifest = {
        **identity,
        "artifact_id": artifact_id,
        "result_sha256": _digest(result_bytes),
        "html_sha256": _digest(html_bytes) if html_bytes is not None else None,
    }
    manifest_bytes = _canonical(manifest)
    root_path = _root_path(root, create=True)
    destination = _artifact_path(root_path, artifact_id)
    if destination.exists():
        return _same_or_conflict(root_path, artifact_id, manifest, result, html)
    with tempfile.TemporaryDirectory(prefix=".pending-run-", dir=root_path) as temporary:
        stage = Path(temporary)
        _write_file(stage / "result.json", result_bytes)
        if html_bytes is not None:
            _write_file(stage / "report.html", html_bytes)
        _write_file(stage / "manifest.json", manifest_bytes)
        _write_file(stage / "manifest.sha256", (_digest(manifest_bytes) + "\n").encode())
        try:
            os.rename(stage, destination)
        except OSError:
            if not destination.exists() and not destination.is_symlink():
                raise
            return _same_or_conflict(root_path, artifact_id, manifest, result, html)
    return load_demo_run(root_path, artifact_id, expected=run)


def load_demo_run(
    root: Path,
    artifact_id: str,
    *,
    expected: DemoRun | None = None,
) -> RunArtifact:
    """Read and verify an artifact, optionally matching a freshly rebuilt DemoRun."""
    root_path = _root_path(root, create=False)
    folder = _artifact_path(root_path, artifact_id)
    if not folder.is_dir():
        raise FileNotFoundError(f"run artifact not found: {artifact_id}")
    manifest_bytes = _read_file(folder, "manifest.json")
    manifest_hash = _read_file(folder, "manifest.sha256").decode("ascii").strip()
    if manifest_hash != _digest(manifest_bytes):
        raise ValueError("manifest hash mismatch")
    manifest = json.loads(manifest_bytes)
    if not isinstance(manifest, dict) or manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported run manifest schema")
    if manifest.get("artifact_id") != artifact_id:
        raise ValueError("artifact ID differs from manifest")
    try:
        identity = {name: manifest[name] for name in _IDENTITY_FIELDS}
    except KeyError as exc:
        raise ValueError("run manifest is incomplete") from exc
    if _digest(_canonical(identity)) != artifact_id:
        raise ValueError("artifact ID does not match manifest identity")
    result_bytes = _read_file(folder, "result.json")
    if manifest.get("result_sha256") != _digest(result_bytes):
        raise ValueError("result hash mismatch")
    result = json.loads(result_bytes)
    if (
        not isinstance(result, dict)
        or result.get("source_run_id") != manifest["source_run_id"]
        or result.get("input_hash") != manifest["input_hash"]
    ):
        raise ValueError("result provenance differs from manifest")
    html_hash = manifest.get("html_sha256")
    if html_hash is None:
        if (folder / "report.html").exists() or (folder / "report.html").is_symlink():
            raise ValueError("unmanifested HTML output")
        html = None
    else:
        html_bytes = _read_file(folder, "report.html")
        if html_hash != _digest(html_bytes):
            raise ValueError("HTML hash mismatch")
        html = html_bytes.decode("utf-8")
    if expected is not None:
        expected_payload = _result_payload(expected)
        if _digest(_canonical(expected_payload)) != manifest["result_sha256"]:
            raise ValueError("expected run differs from saved result")
    return RunArtifact(artifact_id, folder, manifest, result, html)
