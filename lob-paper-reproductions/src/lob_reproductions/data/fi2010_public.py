from __future__ import annotations

import shutil
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from lob_reproductions.data.fi2010 import (
    FI2010_CLASS_NAMES,
    FI2010_HORIZONS,
    FI2010Matrix,
    build_windows,
)
from lob_reproductions.provenance.profiles import project_root
from lob_reproductions.provenance.sources import sha256_file

EXPECTED_FILES = {
    "Train_Dst_NoAuction_DecPre_CF_7.txt",
    "Test_Dst_NoAuction_DecPre_CF_7.txt",
    "Test_Dst_NoAuction_DecPre_CF_8.txt",
    "Test_Dst_NoAuction_DecPre_CF_9.txt",
}


def dataset_manifest() -> dict[str, Any]:
    path = project_root() / "manifests" / "datasets" / "fi2010_public_optional.yaml"
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def default_archive_path() -> Path:
    return project_root() / "data" / "raw" / "fi2010_deeplob_ff14d7c.zip"


def fetch_fi2010(*, accept_terms: bool, destination: Path | None = None) -> dict[str, Any]:
    manifest = dataset_manifest()
    if not accept_terms:
        raise PermissionError(
            "explicit --accept-terms is required; review " + manifest["terms_url"]
        )
    path = default_archive_path() if destination is None else destination
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    with urllib.request.urlopen(manifest["author_archive_url"], timeout=120) as response:
        with temporary.open("wb") as output:
            shutil.copyfileobj(response, output)
    actual = sha256_file(temporary)
    expected = manifest["author_archive_sha256"]
    if actual != expected:
        temporary.unlink(missing_ok=True)
        raise ValueError(f"FI-2010 archive hash mismatch: {actual} != {expected}")
    temporary.replace(path)
    return {"path": str(path), "sha256": actual, "terms_url": manifest["terms_url"]}


def load_fi2010_member(path: Path | None = None, *, member: str) -> np.ndarray:
    """Stream one pinned text member into the canonical ``[149, N]`` matrix."""

    archive_path = default_archive_path() if path is None else path
    rows: list[np.ndarray] = []
    with zipfile.ZipFile(archive_path) as archive:
        if member not in set(archive.namelist()):
            raise FileNotFoundError(f"archive member not found: {member}")
        with archive.open(member) as handle:
            for raw_line in handle:
                rows.append(np.fromstring(raw_line.decode("ascii"), sep=" "))
    values = np.vstack(rows)
    if values.shape[0] != 149:
        raise ValueError(f"FI-2010 member {member} must have 149 rows, got {values.shape[0]}")
    return values


def matrix_from_values(values: np.ndarray) -> FI2010Matrix:
    """Wrap one source file under the author-contiguity assumption.

    The public archive does not identify per-stock or per-day boundaries, and
    the pinned author notebooks window each file as one contiguous block, so
    the boundary ids are constant here.
    """

    matrix = np.asarray(values, dtype=np.float64)
    columns = matrix.shape[1]
    return FI2010Matrix(
        values=matrix,
        asset_id=np.zeros(columns, dtype=np.int16),
        day_id=np.zeros(columns, dtype=np.int16),
    )


def audit_fi2010_archive(
    path: Path | None = None, *, sequence_length: int = 100, horizon: int = 100
) -> dict[str, Any]:
    """Structural audit of the fetched real archive: shapes, labels, windowing.

    This inspects real data but trains and evaluates nothing, so it never
    produces paper-metric claims.
    """

    if horizon not in FI2010_HORIZONS:
        raise ValueError(f"unsupported FI-2010 horizon: {horizon}")
    if sequence_length <= 0:
        raise ValueError("sequence_length must be positive")
    manifest = dataset_manifest()
    archive_path = default_archive_path() if path is None else path
    if not archive_path.is_file():
        raise FileNotFoundError(f"FI-2010 archive not found: {archive_path}")
    actual_hash = sha256_file(archive_path)
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
    members_match = names == EXPECTED_FILES
    members: dict[str, Any] = {}
    if members_match:
        for member in sorted(EXPECTED_FILES):
            values = load_fi2010_member(archive_path, member=member)
            matrix = matrix_from_values(values)
            label_distribution = {
                label_horizon: dict(
                    zip(
                        FI2010_CLASS_NAMES,
                        np.bincount(matrix.labels(label_horizon), minlength=3).tolist(),
                        strict=True,
                    )
                )
                for label_horizon in FI2010_HORIZONS
            }
            sample_columns = min(matrix.n_observations, 5 * sequence_length)
            sample = build_windows(
                matrix_from_values(values[:, :sample_columns]),
                sequence_length=sequence_length,
                horizon=horizon,
                all_features=False,
                stride=sequence_length,
            )
            members[member] = {
                "columns": matrix.n_observations,
                "label_distribution": label_distribution,
                "contiguous_window_count": max(0, matrix.n_observations - sequence_length + 1),
                "sample_windows": {
                    "count": int(sample.labels.size),
                    "feature_shape": list(sample.features.shape[1:]),
                    "stride": sequence_length,
                },
            }
    return {
        "path": str(archive_path),
        "sha256": actual_hash,
        "hash_matches": actual_hash == manifest["author_archive_sha256"],
        "members_match": members_match,
        "sequence_length": sequence_length,
        "horizon": horizon,
        "boundary_assumption": "author-contiguity: each source file is one windowing segment",
        "members": members,
        "numerical_benchmark_attempted": False,
        "claim_limit": "dataset structural audit only; no model was trained or evaluated",
        "ok": members_match and actual_hash == manifest["author_archive_sha256"],
    }


def _stream_matrix_shape_and_labels(archive: zipfile.ZipFile, member: str) -> dict[str, Any]:
    row_count = 0
    column_count: int | None = None
    label_values: set[int] = set()
    with archive.open(member) as handle:
        for raw_line in handle:
            values = np.fromstring(raw_line.decode("ascii"), sep=" ")
            if column_count is None:
                column_count = int(values.size)
            elif values.size != column_count:
                raise ValueError(f"ragged FI-2010 matrix row in {member}")
            if row_count >= 144:
                label_values.update(np.unique(values.astype(np.int8)).tolist())
            row_count += 1
    return {
        "rows": row_count,
        "columns": column_count,
        "label_values": sorted(label_values),
        "valid": row_count == 149 and label_values <= {1, 2, 3},
    }


def verify_fi2010_archive(path: Path | None = None, *, deep: bool = True) -> dict[str, Any]:
    manifest = dataset_manifest()
    archive_path = default_archive_path() if path is None else path
    if not archive_path.is_file():
        raise FileNotFoundError(f"FI-2010 archive not found: {archive_path}")
    actual_hash = sha256_file(archive_path)
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        bad_member = archive.testzip()
        shapes = (
            {
                name: _stream_matrix_shape_and_labels(archive, name)
                for name in sorted(EXPECTED_FILES)
            }
            if deep and names == EXPECTED_FILES and bad_member is None
            else {}
        )
    return {
        "path": str(archive_path),
        "sha256": actual_hash,
        "hash_matches": actual_hash == manifest["author_archive_sha256"],
        "members": sorted(names),
        "members_match": names == EXPECTED_FILES,
        "zip_crc_error": bad_member,
        "shapes": shapes,
        "variants": {"normalization": "decimal_precision", "auction": "no_auction"},
        "ok": (
            actual_hash == manifest["author_archive_sha256"]
            and names == EXPECTED_FILES
            and bad_member is None
            and (not deep or all(item["valid"] for item in shapes.values()))
        ),
    }
