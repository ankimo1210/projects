from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pandas as pd

from jhrmbs.util import atomic_write_json, sha256_file, utc_now


def write_table(
    frame: pd.DataFrame, path: Path, *, csv_companion: bool = True
) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=path.suffix, dir=path.parent
    )
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)
    try:
        frame.to_parquet(temporary_path, index=False)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)
    csv_path: Path | None = None
    if csv_companion:
        csv_path = path.with_suffix(".csv")
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{csv_path.name}.", suffix=".csv", dir=csv_path.parent
        )
        os.close(file_descriptor)
        temporary_path = Path(temporary_name)
        try:
            frame.to_csv(temporary_path, index=False, encoding="utf-8")
            os.replace(temporary_path, csv_path)
        finally:
            temporary_path.unlink(missing_ok=True)
    metadata = {
        "path": str(path),
        "sha256": sha256_file(path),
        "rows": len(frame),
        "columns": [str(column) for column in frame.columns],
        "generated_at": utc_now().isoformat(),
        "csv_companion": str(csv_path) if csv_path else None,
    }
    atomic_write_json(path.with_suffix(".metadata.json"), metadata)
    return metadata


def read_table(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"artifact not found: {path}")
    return pd.read_parquet(path)
