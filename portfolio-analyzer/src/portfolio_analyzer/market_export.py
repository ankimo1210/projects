"""Read a versioned market-only export without importing market-research."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb

from portfolio_analyzer.mtm import Quote

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
_MANIFEST_KEYS = frozenset(
    {
        "schema_version",
        "export_id",
        "as_of",
        "data_file",
        "data_sha256",
        "row_count",
        "snapshot_ids",
        "fx_symbol",
    }
)


def _utc(value: Any, label: str) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{label} must be a timezone-aware timestamp") from exc
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{label} must be a timezone-aware timestamp")
    return value.astimezone(UTC)


def _digest(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(letter in "0123456789abcdef" for letter in value)
    )


def _manifest(path: Path) -> tuple[dict[str, Any], Path, datetime]:
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid market export manifest") from exc
    if not isinstance(metadata, dict) or set(metadata) != _MANIFEST_KEYS:
        raise ValueError("invalid market export manifest schema")
    if type(metadata["schema_version"]) is not int or metadata["schema_version"] != 1:
        raise ValueError("unsupported market export schema version")
    if metadata["data_file"] != "prices.parquet":
        raise ValueError("invalid data_file path")
    if not _digest(metadata["data_sha256"]) or not _digest(metadata["export_id"]):
        raise ValueError("invalid market export hash")
    if type(metadata["row_count"]) is not int or metadata["row_count"] < 1:
        raise ValueError("invalid market export row count")
    ids = metadata["snapshot_ids"]
    if not isinstance(ids, list) or not ids or any(not isinstance(i, str) or not i for i in ids):
        raise ValueError("invalid snapshot_ids")
    if ids != sorted(set(ids)):
        raise ValueError("snapshot_ids must be sorted and unique")
    if metadata["fx_symbol"] != "JPY=X":
        raise ValueError("portfolio FX symbol must be JPY=X")
    encoded = json.dumps(
        {key: value for key, value in metadata.items() if key != "export_id"},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    if hashlib.sha256(encoded).hexdigest() != metadata["export_id"]:
        raise ValueError("market export manifest hash mismatch")
    as_of = _utc(metadata["as_of"], "as_of")
    if as_of.isoformat() != metadata["as_of"]:
        raise ValueError("as_of must be UTC ISO 8601")
    data_path = path.parent / "prices.parquet"
    if data_path.is_symlink() or not data_path.is_file():
        raise ValueError("invalid data_file path")
    if data_path.resolve().parent != path.parent.resolve():
        raise ValueError("data_file path escapes manifest directory")
    if hashlib.sha256(data_path.read_bytes()).hexdigest() != metadata["data_sha256"]:
        raise ValueError("market export data SHA-256 mismatch")
    return metadata, data_path, as_of


def _close(value: Any) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError("invalid market close")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError("invalid market close")
    return Decimal(str(value))


def load_market_quotes(
    manifest_path: Path,
    *,
    now: datetime,
    max_price_age: timedelta,
    max_fx_age: timedelta,
) -> tuple[dict[str, Quote], Quote]:
    """Return market quotes and USD/JPY FX from a verified offline export.

    Price and FX staleness are checked independently against each latest bar end.
    The existing daily report fetch path is unaffected.
    """
    when = _utc(now, "now")
    if (
        not isinstance(max_price_age, timedelta)
        or not isinstance(max_fx_age, timedelta)
        or max_price_age <= timedelta(0)
        or max_fx_age <= timedelta(0)
    ):
        raise ValueError("maximum quote ages must be positive timedeltas")
    metadata, data_path, as_of = _manifest(Path(manifest_path))
    if as_of > when:
        raise ValueError("market export as_of is after now")
    with duckdb.connect() as db:
        result = db.execute("SELECT * FROM read_parquet(?)", [str(data_path)])
        names = tuple(column[0] for column in result.description)
        if names != _COLUMNS:
            raise ValueError("market export Parquet schema mismatch")
        records = result.fetchall()
    if len(records) != metadata["row_count"]:
        raise ValueError("market export row count mismatch")

    by_symbol: dict[str, list[tuple[date, datetime, Decimal]]] = defaultdict(list)
    identities: dict[str, tuple[str, str, str]] = {}
    observed_ids: set[str] = set()
    for record in records:
        row = dict(zip(_COLUMNS, record, strict=True))
        symbol = row["provider_symbol"]
        identity = row["instrument_id"]
        currency = row["currency"]
        provider = row["provider"]
        if any(not isinstance(x, str) or not x for x in (symbol, identity, currency, provider)):
            raise ValueError("invalid market symbol or instrument")
        if currency not in {"JPY", "USD"}:
            raise ValueError("unsupported market quote currency")
        if row["adjustment"] != "raw" or row["quality"] != "ok" or row["is_final"] is not True:
            raise ValueError("market export requires final raw quality-ok bars")
        if row["snapshot_id"] not in metadata["snapshot_ids"]:
            raise ValueError("unknown market snapshot ID")
        observed_ids.add(row["snapshot_id"])
        start = _utc(row["bar_start"], "bar_start")
        end = _utc(row["bar_end"], "bar_end")
        available = _utc(row["available_at"], "available_at")
        observed = _utc(row["observed_at"], "observed_at")
        if not start < end <= available <= as_of or not end <= observed <= as_of:
            raise ValueError("market bar is unavailable as_of export")
        session = row["session_date"]
        if type(session) is not date or not isinstance(row["interval"], str):
            raise ValueError("invalid market session or interval")
        if row["interval"] != "1d":
            raise ValueError("portfolio quotes require daily bars")
        prior_identity = identities.setdefault(symbol, (identity, currency, provider))
        if prior_identity != (identity, currency, provider):
            raise ValueError("provider symbol conflicts across instruments or currencies")
        by_symbol[symbol].append((session, end, _close(row["close"])))
    if observed_ids != set(metadata["snapshot_ids"]):
        raise ValueError("market snapshot IDs do not match exported rows")

    # Mirror daily_pl_report.quotes_from_closes: the latest saved market
    # session is shared across symbols. A closed market carries its last close
    # into that session, so its daily P&L is zero rather than counted twice.
    latest_global_session = max(session for bars in by_symbol.values() for session, _, _ in bars)
    quotes: dict[str, Quote] = {}
    fx_symbol = metadata["fx_symbol"]
    fx: Quote | None = None
    for symbol, bars in by_symbol.items():
        bars.sort(key=lambda item: (item[0], item[1]))
        if len({session for session, _, _ in bars}) != len(bars):
            raise ValueError("duplicate market session for provider symbol")
        latest_session, latest_end, latest_close = bars[-1]
        if latest_end > when:
            raise ValueError("market quote bar is after now")
        limit = max_fx_age if symbol == fx_symbol else max_price_age
        if when - latest_end > limit:
            label = "FX" if symbol == fx_symbol else "price"
            raise ValueError(f"{label} quote is stale")
        previous = (
            bars[-1]
            if latest_session < latest_global_session
            else bars[-2]
            if len(bars) > 1
            else None
        )
        quote = Quote(
            close=latest_close,
            prev_close=previous[2] if previous else None,
            date=latest_session.isoformat(),
            prev_date=previous[0].isoformat() if previous else None,
        )
        if symbol == fx_symbol:
            if identities[symbol][1] != "JPY":
                raise ValueError("FX quote must be in JPY per USD")
            if identities[symbol][0] != "FX:JPY=X":
                raise ValueError("FX instrument must be FX:JPY=X")
            fx = quote
        else:
            quotes[symbol] = quote
    if fx is None:
        raise ValueError("FX quote is missing")
    return quotes, fx
