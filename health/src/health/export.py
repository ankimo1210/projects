"""Export the typed tables to files. Everything written is private health data."""

from __future__ import annotations

import os
from pathlib import Path

from health.privacy import ensure_private_dir

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
    ensure_private_dir(out_dir)
    written: list[Path] = []
    for table in EXPORT_TABLES:
        path = out_dir / f"{table}.{fmt}"
        # DuckDB's COPY ... TO takes a string literal, not a bind parameter, so
        # the path has to be embedded in the SQL text itself. A single quote is
        # a legal path character, so it must be escaped (SQL-standard: double
        # it) or it would close the literal early -- breaking the statement at
        # best, injecting SQL at worst.
        escaped_path = str(path).replace("'", "''")
        store.con.execute(f"COPY {table} TO '{escaped_path}' (FORMAT {_FORMATS[fmt]})")
        os.chmod(path, 0o600)
        written.append(path)
    return written
