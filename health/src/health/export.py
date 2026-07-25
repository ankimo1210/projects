"""Export the typed tables to files. Everything written is private health data."""

from __future__ import annotations

import os
from pathlib import Path

EXPORT_TABLES: tuple[str, ...] = ("daily_series", "sleep_sessions", "intraday", "sync_state")
_FORMATS = {"parquet": "PARQUET", "csv": "CSV"}


def export_tables(store, out_dir: Path, fmt: str = "parquet") -> list[Path]:
    """Write one file per table into `out_dir`, owner-only.

    `fmt` is checked against a fixed map rather than interpolated: it lands
    inside a COPY statement, and the table names are the only other dynamic
    part (they come from this module's own tuple, never from a caller).
    """
    if fmt not in _FORMATS:
        raise ValueError(f"unsupported export format: {fmt!r} (parquet or csv)")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(out_dir, 0o700)
    written: list[Path] = []
    for table in EXPORT_TABLES:
        path = out_dir / f"{table}.{fmt}"
        store.con.execute(f"COPY {table} TO '{path}' (FORMAT {_FORMATS[fmt]})")
        os.chmod(path, 0o600)
        written.append(path)
    return written
