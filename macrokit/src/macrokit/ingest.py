"""Ingestion: snapshot first, parse second.

The order matters. `save_snapshot` runs before anything is parsed, so a source
whose parser is unwritten or broken still banks its bytes. For Japanese sources
that is not a nicety -- a day not snapshotted is a vintage that can never be
recovered.

Parsing is skipped entirely when the content hash is unchanged, which is the
common case on a daily schedule.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import duckdb

from .catalog import Indicator
from .snapshot import save_snapshot
from .sources.alfred import AlfredAdapter
from .store import insert_observations

ADAPTERS: dict[str, type] = {"alfred": AlfredAdapter}


def default_catalog_root() -> Path:
    """The catalog shipped with the package (``macrokit/catalog``)."""
    return Path(__file__).resolve().parents[2] / "catalog"


@dataclass(frozen=True)
class IngestReport:
    indicator: str
    changed: bool
    rows_inserted: int
    skipped_reason: str | None = None


def _sniff_suffix(content: bytes) -> str:
    """Guess a snapshot's file extension from its leading byte.

    Strips a UTF-8 BOM before sniffing: ``bytes.lstrip()`` does not strip one,
    so a BOM-prefixed payload (common in Japanese ministry CSVs) would
    otherwise be misclassified as ``json``. Empty content gets a neutral
    ``bin`` suffix rather than being guessed as either format.
    """
    stripped = content.removeprefix(b"\xef\xbb\xbf").lstrip()
    if not stripped:
        return "bin"
    return "json" if stripped[:1] in (b"{", b"[") else "csv"


def ingest_one(
    indicator: Indicator,
    *,
    con: duckdb.DuckDBPyConnection,
    raw_root: Path,
    adapter,
    start: date,
    now: datetime,
) -> IngestReport:
    content, url, status = adapter.fetch_raw(indicator, start)

    suffix = _sniff_suffix(content)
    result = save_snapshot(
        raw_root,
        adapter.source,
        indicator.name,
        content,
        ingested_at=now,
        url=url,
        http_status=status,
        filename=f"payload.{suffix}",
    )

    if not result.changed:
        return IngestReport(indicator.name, False, 0, "content unchanged")

    rows = adapter.parse(indicator, content, ingested_at=now)
    inserted = insert_observations(con, rows)
    return IngestReport(indicator.name, True, inserted)
