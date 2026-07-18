"""Versioned, torch-free JSON + NPZ pricing dataset contract."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

SCHEMA_VERSION = 1
SPLITS = ("train", "validation", "test", "ood")
REQUIRED_LABELS = ("price", "delta", "gamma", "vega", "theta", "rho")


@dataclass(frozen=True)
class PricingDatasetManifest:
    """Versioned dataset manifest: teacher, seed, split fingerprints, checksums."""

    schema_version: int
    artifact_kind: str
    model: str
    teacher_method: str
    parameterization: str
    seed: int
    split_fingerprints: dict[str, str]
    overlap_count: int
    arrays: str
    generator_version: str
    git_sha: str
    arrays_sha256: str
    array_metadata: dict[str, dict[str, Any]]
    metadata: dict[str, Any]
    created_at_utc: str


def _canonical_array(array: np.ndarray) -> np.ndarray:
    value = np.asarray(array)
    if value.dtype.hasobject:
        raise ValueError("object arrays are not allowed in pricing artifacts")
    return np.ascontiguousarray(value)


def _row_digests(array: np.ndarray) -> list[str]:
    value = _canonical_array(array)
    if value.ndim != 2:
        raise ValueError("split input rows must be a two-dimensional array")
    return [hashlib.sha256(row.tobytes(order="C")).hexdigest() for row in value]


def fingerprint_rows(array: np.ndarray) -> str:
    """Fingerprint shape, dtype, and ordered row bytes."""
    value = _canonical_array(array)
    header = json.dumps(
        {"shape": value.shape, "dtype": value.dtype.str}, sort_keys=True, separators=(",", ":")
    ).encode()
    return "sha256:" + hashlib.sha256(header + value.tobytes(order="C")).hexdigest()


def split_overlap_count(split_rows: Mapping[str, np.ndarray]) -> int:
    """Count duplicate input rows across the train/validation/test/ood splits."""
    seen: set[str] = set()
    overlap = 0
    for split in SPLITS:
        if split not in split_rows:
            raise ValueError(f"missing split {split}")
        current = set(_row_digests(split_rows[split]))
        overlap += len(seen.intersection(current))
        seen.update(current)
    return overlap


def assert_disjoint_splits(split_rows: Mapping[str, np.ndarray]) -> None:
    """Reject any exact parameter row reused across logical splits."""
    overlap = split_overlap_count(split_rows)
    if overlap:
        raise ValueError(f"pricing dataset splits overlap in {overlap} row(s)")


def _npz_bytes(arrays: Mapping[str, np.ndarray]) -> bytes:
    """Write deterministic NPZ bytes with fixed member timestamps/order."""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(arrays):
            buffer = io.BytesIO()
            np.lib.format.write_array(buffer, _canonical_array(arrays[name]), allow_pickle=False)
            info = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, buffer.getvalue())
    return output.getvalue()


def _validate_split_arrays(split_arrays: Mapping[str, Mapping[str, np.ndarray]]) -> None:
    for split in SPLITS:
        if split not in split_arrays:
            raise ValueError(f"missing split {split}")
        arrays = split_arrays[split]
        required = {"inputs", *REQUIRED_LABELS, "standard_error", "ci_lower", "ci_upper"}
        missing = required.difference(arrays)
        if missing:
            raise ValueError(f"{split} missing arrays: {sorted(missing)}")
        inputs = np.asarray(arrays["inputs"])
        if inputs.ndim != 2 or inputs.shape[1] != 5:
            raise ValueError(f"{split}.inputs must have shape (n, 5)")
        n_rows = inputs.shape[0]
        for name in required - {"inputs"}:
            value = np.asarray(arrays[name])
            if value.shape != (n_rows,):
                raise ValueError(f"{split}.{name} must have shape ({n_rows},)")
            if not np.issubdtype(value.dtype, np.number):
                raise ValueError(f"{split}.{name} must be numeric")


def save_pricing_dataset(
    split_arrays: Mapping[str, Mapping[str, np.ndarray]],
    *,
    output_dir: Path,
    model: str,
    teacher_method: str,
    parameterization: str,
    seed: int,
    generator_version: str,
    git_sha: str = "unknown",
    metadata: Mapping[str, Any] | None = None,
) -> tuple[Path, Path]:
    """Validate and atomically save a pricing dataset manifest and arrays."""
    _validate_split_arrays(split_arrays)
    rows = {split: np.asarray(split_arrays[split]["inputs"]) for split in SPLITS}
    assert_disjoint_splits(rows)
    flat = {
        f"{split}_{name}": _canonical_array(value)
        for split in SPLITS
        for name, value in split_arrays[split].items()
    }
    payload = _npz_bytes(flat)
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    output_dir.mkdir(parents=True, exist_ok=True)
    arrays_path = output_dir / "pricing_dataset.npz"
    manifest_path = output_dir / "pricing_dataset.json"
    arrays_path.write_bytes(payload)
    manifest = PricingDatasetManifest(
        schema_version=SCHEMA_VERSION,
        artifact_kind="pricing_dataset",
        model=model,
        teacher_method=teacher_method,
        parameterization=parameterization,
        seed=seed,
        split_fingerprints={split: fingerprint_rows(rows[split]) for split in SPLITS},
        overlap_count=0,
        arrays=arrays_path.name,
        generator_version=generator_version,
        git_sha=git_sha,
        arrays_sha256=digest,
        array_metadata={
            name: {"shape": list(value.shape), "dtype": value.dtype.str, "unit": _unit(name)}
            for name, value in sorted(flat.items())
        },
        metadata=dict(metadata or {}),
        created_at_utc=datetime.now(UTC).isoformat(),
    )
    manifest_path.write_text(
        json.dumps(asdict(manifest), indent=2, sort_keys=True), encoding="utf-8"
    )
    return manifest_path, arrays_path


def _unit(name: str) -> str:
    label = name.split("_", 1)[-1]
    return {
        "inputs": "x,tau_years,r,q,sigma",
        "price": "strike_units",
        "delta": "price_per_spot",
        "gamma": "price_per_spot_squared",
        "vega": "price_per_unit_volatility",
        "theta": "price_per_year",
        "rho": "price_per_unit_rate",
        "standard_error": "strike_units",
        "ci_lower": "strike_units",
        "ci_upper": "strike_units",
    }.get(label, "dimensionless")


def load_pricing_dataset(
    manifest_path: Path,
) -> tuple[PricingDatasetManifest, dict[str, np.ndarray]]:
    """Load a dataset without importing torch and verify every contract field."""
    raw = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    required = {item.name for item in fields(PricingDatasetManifest)}
    missing = required.difference(raw)
    if missing:
        raise ValueError(f"manifest missing fields: {sorted(missing)}")
    if raw["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"unsupported pricing schema {raw['schema_version']}")
    if raw["artifact_kind"] != "pricing_dataset":
        raise ValueError("manifest is not a pricing_dataset")
    arrays_name = Path(raw["arrays"])
    if arrays_name.is_absolute() or len(arrays_name.parts) != 1:
        raise ValueError("manifest arrays path must be a local filename")
    arrays_path = Path(manifest_path).parent / arrays_name
    payload = arrays_path.read_bytes()
    actual = "sha256:" + hashlib.sha256(payload).hexdigest()
    if actual != raw["arrays_sha256"]:
        raise ValueError("pricing arrays digest mismatch")
    with np.load(io.BytesIO(payload), allow_pickle=False) as archive:
        arrays = {name: archive[name] for name in archive.files}
    if set(arrays) != set(raw["array_metadata"]):
        raise ValueError("pricing array names do not match manifest")
    for name, value in arrays.items():
        expected = raw["array_metadata"][name]
        if list(value.shape) != expected["shape"] or value.dtype.str != expected["dtype"]:
            raise ValueError(f"pricing array metadata mismatch for {name}")
    split_arrays = {
        split: {
            name: arrays[f"{split}_{name}"]
            for name in ("inputs", *REQUIRED_LABELS, "standard_error", "ci_lower", "ci_upper")
        }
        for split in SPLITS
    }
    _validate_split_arrays(split_arrays)
    rows = {split: split_arrays[split]["inputs"] for split in SPLITS}
    assert_disjoint_splits(rows)
    for split in SPLITS:
        if fingerprint_rows(rows[split]) != raw["split_fingerprints"][split]:
            raise ValueError(f"split fingerprint mismatch for {split}")
    return PricingDatasetManifest(**{name: raw[name] for name in required}), arrays
