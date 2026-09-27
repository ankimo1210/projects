"""Write immutable, offline price and FX exports for the portfolio adapter."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import duckdb
import pandas as pd

from market_research.research.dataset import PriceDataset

_DATA_FILE = "prices.parquet"
_MANIFEST_FILE = "manifest.json"
_COLUMNS = (
    "snapshot_id",
    "instrument_id",
    "provider_symbol",
    "currency",
    "adjustment",
    "quality",
    "available_at",
    "observed_at",
    "is_final",
    "session_date",
    "close",
    "bar_start",
    "bar_end",
    "provider",
    "interval",
    "revision_id",
)


def _canonical_json(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _validated_rows(
    datasets: Sequence[PriceDataset], fx_symbol: str
) -> tuple[datetime, list[dict], list[str]]:
    if not datasets:
        raise ValueError("at least one saved price dataset is required")
    as_of = datasets[0].as_of
    if (
        not isinstance(as_of, datetime)
        or as_of.utcoffset() is None
        or as_of.utcoffset() != timedelta(0)
    ):
        raise ValueError("as_of must be timezone-aware UTC")
    as_of = as_of.astimezone(UTC)
    rows: list[dict] = []
    snapshot_ids: list[str] = []
    symbols: dict[str, tuple[tuple[str, str, str, str], str]] = {}
    keys: set[tuple] = set()
    daily_keys: set[tuple[str, date]] = set()
    for dataset in datasets:
        if not isinstance(dataset.as_of, datetime) or dataset.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware UTC")
        if dataset.as_of.utcoffset() != timedelta(0) or dataset.as_of != as_of:
            raise ValueError("all datasets must have the same UTC as_of")
        if dataset.mode != "retrospective":
            raise ValueError("retrospective dataset mode is required")
        if dataset.adjustment != "raw":
            raise ValueError("raw dataset adjustment is required")
        if len(dataset.snapshot_ids) != 1 or not isinstance(dataset.snapshot_ids[0], str):
            raise ValueError("one saved snapshot ID per dataset is required")
        snapshot_id = dataset.snapshot_ids[0]
        if not snapshot_id.strip() or snapshot_id in snapshot_ids:
            raise ValueError("duplicate or empty snapshot ID")
        snapshot_ids.append(snapshot_id)
        if not dataset.bars:
            raise ValueError("saved price dataset has no eligible bars")
        dataset_identity: tuple[str, str, str, str] | None = None
        dataset_symbol: str | None = None
        for bar in dataset.bars:
            if not bar.is_final:
                raise ValueError("only final price bars may be exported")
            if bar.quality != "ok":
                raise ValueError("only quality=ok price bars may be exported")
            if bar.available_at > as_of:
                raise ValueError("bar available_at is after as_of")
            if bar.observed_at > as_of:
                raise ValueError("bar observed_at is after as_of")
            if bar.adjustment != "raw" or bar.adjustment != dataset.adjustment:
                raise ValueError("raw bar adjustment is required")
            if bar.instrument.currency != dataset.currency:
                raise ValueError("bar currency differs from dataset currency")
            if bar.interval != "1d":
                raise ValueError("daily price bars are required")
            symbol = bar.provider_symbol
            if not isinstance(symbol, str) or not symbol.strip() or symbol != symbol.strip():
                raise ValueError("provider_symbol is required without surrounding whitespace")
            if dataset_symbol is not None and dataset_symbol != symbol:
                raise ValueError("provider_symbol changes within one snapshot series")
            dataset_symbol = symbol
            identity = (
                bar.instrument.instrument_id,
                bar.instrument.currency,
                bar.provider,
                bar.interval,
            )
            if dataset_identity is not None and dataset_identity != identity:
                raise ValueError("one instrument/provider series per dataset is required")
            dataset_identity = identity
            previous = symbols.setdefault(symbol, (identity, snapshot_id))
            if previous != (identity, snapshot_id):
                raise ValueError("provider_symbol belongs to multiple snapshot series")
            if bar.key in keys:
                raise ValueError("duplicate price bar across datasets")
            keys.add(bar.key)
            daily_key = (symbol, bar.session_date)
            if daily_key in daily_keys:
                raise ValueError("duplicate daily price bar")
            daily_keys.add(daily_key)
            rows.append(
                dict(
                    snapshot_id=snapshot_id,
                    instrument_id=bar.instrument.instrument_id,
                    provider_symbol=symbol,
                    currency=bar.instrument.currency,
                    adjustment=bar.adjustment,
                    quality=bar.quality,
                    available_at=bar.available_at,
                    observed_at=bar.observed_at,
                    is_final=bar.is_final,
                    session_date=bar.session_date,
                    close=float(bar.close),
                    bar_start=bar.bar_start,
                    bar_end=bar.bar_end,
                    provider=bar.provider,
                    interval=bar.interval,
                    revision_id=bar.revision_id,
                )
            )
    if fx_symbol not in symbols:
        raise ValueError(f"FX provider_symbol {fx_symbol!r} is missing")
    if symbols[fx_symbol][0][1] != "JPY":
        raise ValueError("FX quote currency must be JPY")
    if symbols[fx_symbol][0][0] != "FX:JPY=X":
        raise ValueError("FX instrument must be FX:JPY=X")
    rows.sort(
        key=lambda row: (
            row["provider_symbol"],
            row["bar_end"],
            row["instrument_id"],
            row["revision_id"],
        )
    )
    return as_of, rows, sorted(snapshot_ids)


def _same_export(path: Path, manifest_bytes: bytes, data_sha256: str) -> bool:
    if path.is_symlink() or not path.is_dir():
        return False
    if {entry.name for entry in path.iterdir()} != {_MANIFEST_FILE, _DATA_FILE}:
        return False
    manifest = path / _MANIFEST_FILE
    data = path / _DATA_FILE
    if manifest.is_symlink() or data.is_symlink() or not manifest.is_file() or not data.is_file():
        return False
    return manifest.read_bytes() == manifest_bytes and _sha256(data) == data_sha256


def write_portfolio_export(
    datasets: Sequence[PriceDataset], destination: Path, *, fx_symbol: str = "JPY=X"
) -> Path:
    """Export explicitly loaded saved price datasets without any account inputs.

    Each dataset must contain one complete snapshot loaded through
    ``load_price_dataset`` so each row has an unambiguous snapshot ID.
    Freshness relative to report time is checked by the consuming adapter.
    """
    if fx_symbol != "JPY=X":
        raise ValueError("fx_symbol must be JPY=X for a JPY per USD quote")
    as_of, rows, snapshot_ids = _validated_rows(datasets, fx_symbol)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".pending-", dir=destination) as temporary:
        pending = Path(temporary)
        data_path = pending / _DATA_FILE
        frame = pd.DataFrame.from_records(rows, columns=_COLUMNS)
        with duckdb.connect() as con:
            con.execute("SET TimeZone='UTC'")
            con.register("export_prices", frame)
            con.execute(
                "COPY (SELECT * FROM export_prices ORDER BY provider_symbol, bar_end, "
                "instrument_id, revision_id) TO ? (FORMAT PARQUET)",
                [str(data_path)],
            )
        data_sha256 = _sha256(data_path)
        payload = {
            "schema_version": 1,
            "as_of": as_of.isoformat(),
            "data_file": _DATA_FILE,
            "data_sha256": data_sha256,
            "row_count": len(rows),
            "snapshot_ids": snapshot_ids,
            "fx_symbol": fx_symbol,
        }
        export_id = hashlib.sha256(_canonical_json(payload)).hexdigest()
        manifest_bytes = _canonical_json({**payload, "export_id": export_id}) + b"\n"
        (pending / _MANIFEST_FILE).write_bytes(manifest_bytes)
        final = destination / export_id
        if final.exists() or final.is_symlink():
            if not _same_export(final, manifest_bytes, data_sha256):
                raise ValueError("existing export differs from immutable content")
        else:
            try:
                os.rename(pending, final)
            except FileExistsError:
                if not _same_export(final, manifest_bytes, data_sha256):
                    raise ValueError("existing export differs from immutable content") from None
        return final / _MANIFEST_FILE
