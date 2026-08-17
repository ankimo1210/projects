"""Derive each indicator's implementation state from reality, never from YAML.

A hand-written `status:` field in the catalog rots the moment someone implements
an adapter and forgets to update it. So status is computed:

  declared  -- present in the catalog
  fetching  -- the manifest records at least one fetch
  parsed    -- the observations table holds rows for it
  validated -- listed in data/validated.json, written by the validation run

`fetching` is the load-bearing rung. Reaching it means snapshots are accruing,
which for Japanese sources is the only way their vintages will ever exist.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

from .catalog import Indicator
from .snapshot import manifest_path

STATUS_ORDER: tuple[str, ...] = ("declared", "fetching", "parsed", "validated")


def load_validated(data_root: Path) -> set[str]:
    marker = data_root / "validated.json"
    if not marker.exists():
        return set()
    return set(json.loads(marker.read_text(encoding="utf-8")).get("indicators", []))


def _has_snapshot(data_root: Path, indicator: str) -> bool:
    manifest = manifest_path(data_root)
    if not manifest.exists():
        return False
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            # The manifest is append-only and appends are not atomic, so an
            # interrupted process can leave one truncated final line. Skipping
            # it is safe: only the last line can be partial. snapshot.last_sha
            # does the same for the same reason.
            continue
        if record.get("indicator") == indicator:
            return True
    return False


def compute_status(
    indicator: Indicator,
    *,
    con: duckdb.DuckDBPyConnection,
    raw_root: Path,
    validated: set[str],
) -> str:
    if indicator.name in validated:
        return "validated"
    rows = con.execute(
        "SELECT count(*) FROM observations WHERE indicator = ?", [indicator.name]
    ).fetchone()[0]
    if rows:
        return "parsed"
    if _has_snapshot(raw_root, indicator.name):
        return "fetching"
    return "declared"
