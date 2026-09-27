"""The portfolio adapter reads only validated, offline market exports."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest
from portfolio_analyzer.market_export import load_market_quotes

AS_OF = datetime(2026, 9, 26, tzinfo=UTC)
NOW = datetime(2026, 9, 27, tzinfo=UTC)


def _rows() -> list[tuple]:
    rows = []
    for symbol, instrument, currency, before, latest in (
        ("AAA", "NYSE:AAA", "USD", 90.0, 100.0),
        ("7203.T", "TSE:7203", "JPY", 2450.0, 2500.0),
        ("JPY=X", "FX:JPY=X", "JPY", 149.0, 150.0),
    ):
        for day, close in ((24, before), (25, latest)):
            rows.append(
                (
                    f"snapshot-{symbol}",
                    instrument,
                    symbol,
                    currency,
                    "raw",
                    "ok",
                    f"2026-09-{day}T21:00:00+00:00",
                    f"2026-09-{day}T21:00:00+00:00",
                    True,
                    f"2026-09-{day}",
                    close,
                    f"2026-09-{day}T00:00:00+00:00",
                    f"2026-09-{day}T20:00:00+00:00",
                    "fixture",
                    "1d",
                    "r1",
                )
            )
    return rows


def _export(tmp_path: Path, rows: list[tuple] | None = None) -> Path:
    rows = _rows() if rows is None else rows
    parquet = tmp_path / "prices.parquet"
    with duckdb.connect() as db:
        db.execute(
            """CREATE TABLE prices (
            snapshot_id VARCHAR, instrument_id VARCHAR, provider_symbol VARCHAR,
            currency VARCHAR, adjustment VARCHAR, quality VARCHAR,
            available_at TIMESTAMPTZ, observed_at TIMESTAMPTZ, is_final BOOLEAN,
            session_date DATE, close DOUBLE, bar_start TIMESTAMPTZ,
            bar_end TIMESTAMPTZ, provider VARCHAR, interval VARCHAR,
            revision_id VARCHAR)"""
        )
        db.executemany(
            "INSERT INTO prices VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows
        )
        db.execute("COPY prices TO ? (FORMAT PARQUET)", [str(parquet)])
    payload = {
        "schema_version": 1,
        "as_of": AS_OF.isoformat(),
        "data_file": "prices.parquet",
        "data_sha256": hashlib.sha256(parquet.read_bytes()).hexdigest(),
        "row_count": len(rows),
        "snapshot_ids": sorted({row[0] for row in rows}),
        "fx_symbol": "JPY=X",
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["export_id"] = hashlib.sha256(encoded).hexdigest()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    return manifest


def _load(path: Path, *, now: datetime = NOW, fx_age: timedelta = timedelta(days=3)):
    return load_market_quotes(
        path,
        now=now,
        max_price_age=timedelta(days=4),
        max_fx_age=fx_age,
    )


def test_loads_previous_and_latest_closes_as_decimal(tmp_path: Path) -> None:
    quotes, fx = _load(_export(tmp_path))

    assert set(quotes) == {"AAA", "7203.T"}
    assert quotes["AAA"].close == Decimal("100")
    assert quotes["AAA"].prev_close == Decimal("90")
    assert quotes["AAA"].date == "2026-09-25"
    assert quotes["7203.T"].close == Decimal("2500")
    assert fx.close == Decimal("150")
    assert fx.prev_close == Decimal("149")


def test_rejects_modified_parquet(tmp_path: Path) -> None:
    manifest = _export(tmp_path)
    with (tmp_path / "prices.parquet").open("ab") as output:
        output.write(b"tampered")

    with pytest.raises(ValueError, match=r"hash|SHA"):
        _load(manifest)


@pytest.mark.parametrize("version", [0, 2, "1"])
def test_rejects_unknown_schema_version(tmp_path: Path, version: object) -> None:
    manifest = _export(tmp_path)
    payload = json.loads(manifest.read_text())
    payload["schema_version"] = version
    manifest.write_text(json.dumps(payload))

    with pytest.raises(ValueError, match=r"version|schema"):
        _load(manifest)


@pytest.mark.parametrize("data_file", ["../secret.parquet", "/tmp/secret.parquet"])
def test_rejects_manifest_path_escape(tmp_path: Path, data_file: str) -> None:
    manifest = _export(tmp_path)
    payload = json.loads(manifest.read_text())
    payload["data_file"] = data_file
    manifest.write_text(json.dumps(payload))

    with pytest.raises(ValueError, match=r"data_file|path"):
        _load(manifest)


def test_rejects_stale_fx_independently_of_price(tmp_path: Path) -> None:
    manifest = _export(tmp_path)
    with pytest.raises(ValueError, match=r"FX|fx"):
        _load(manifest, fx_age=timedelta(hours=1))


def test_rejects_missing_fx(tmp_path: Path) -> None:
    manifest = _export(tmp_path, [row for row in _rows() if row[2] != "JPY=X"])
    with pytest.raises(ValueError, match=r"FX|fx"):
        _load(manifest)


def test_rejects_same_symbol_for_distinct_instruments(tmp_path: Path) -> None:
    rows = _rows()
    conflicting = list(rows[0])
    conflicting[1] = "NASDAQ:AAA"
    rows.append(tuple(conflicting))
    manifest = _export(tmp_path, rows)

    with pytest.raises(ValueError, match=r"symbol|instrument"):
        _load(manifest)


def test_rejects_rows_unavailable_as_of_export(tmp_path: Path) -> None:
    rows = _rows()
    future = list(rows[0])
    future[6] = "2026-09-27T00:00:00+00:00"
    rows[0] = tuple(future)
    manifest = _export(tmp_path, rows)

    with pytest.raises(ValueError, match=r"as_of|future|available"):
        _load(manifest)


def test_rejects_stale_price_even_when_fx_is_fresh_enough(tmp_path: Path) -> None:
    manifest = _export(tmp_path)
    with pytest.raises(ValueError, match="price"):
        load_market_quotes(
            manifest,
            now=datetime(2026, 9, 30, tzinfo=UTC),
            max_price_age=timedelta(days=4),
            max_fx_age=timedelta(days=10),
        )


def test_rejects_other_fx_pair_even_with_valid_manifest_hash(tmp_path: Path) -> None:
    manifest = _export(tmp_path)
    payload = json.loads(manifest.read_text())
    payload["fx_symbol"] = "EUR=X"
    encoded = json.dumps(
        {key: value for key, value in payload.items() if key != "export_id"},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    payload["export_id"] = hashlib.sha256(encoded).hexdigest()
    manifest.write_text(json.dumps(payload))

    with pytest.raises(ValueError, match="JPY=X"):
        _load(manifest)


def test_closed_market_uses_shared_latest_session_for_previous_close(tmp_path: Path) -> None:
    rows = [row for row in _rows() if not (row[2] == "AAA" and row[9] == "2026-09-25")]
    earlier = list(next(row for row in rows if row[2] == "AAA"))
    earlier[9] = "2026-09-23"
    earlier[10] = 80.0
    earlier[6] = "2026-09-23T21:00:00+00:00"
    earlier[7] = "2026-09-23T21:00:00+00:00"
    earlier[11] = "2026-09-23T00:00:00+00:00"
    earlier[12] = "2026-09-23T20:00:00+00:00"
    rows.append(tuple(earlier))
    quotes, _ = _load(_export(tmp_path, rows))

    assert quotes["AAA"].close == Decimal("90")
    assert quotes["AAA"].prev_close == Decimal("90")
    assert quotes["AAA"].date == "2026-09-24"
    assert quotes["AAA"].prev_date == "2026-09-24"
    assert quotes["7203.T"].prev_close == Decimal("2450")


def test_rejects_fx_symbol_on_an_unrelated_instrument_even_with_valid_hash(tmp_path: Path) -> None:
    rows = []
    for row in _rows():
        if row[2] == "JPY=X":
            changed = list(row)
            changed[1] = "XTKS:FAKE"
            rows.append(tuple(changed))
        else:
            rows.append(row)
    with pytest.raises(ValueError, match="FX instrument"):
        _load(_export(tmp_path, rows))
