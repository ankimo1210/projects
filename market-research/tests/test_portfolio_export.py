"""Offline contract tests for the one-way portfolio quote export."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import duckdb
import pytest
from market_research.contracts import Instrument, PriceBar
from market_research.research.dataset import PriceDataset, load_price_dataset
from market_research.storage import CacheKey, ResearchStore

AS_OF = datetime(2026, 9, 25, 23, tzinfo=UTC)


def _bars(instrument: Instrument, symbol: str, closes: tuple[float, float]) -> tuple[PriceBar, ...]:
    return tuple(
        PriceBar(
            instrument=instrument,
            provider="yfinance",
            provider_symbol=symbol,
            interval="1d",
            bar_start=AS_OF - timedelta(days=offset, hours=8),
            bar_end=AS_OF - timedelta(days=offset, hours=1),
            available_at=AS_OF - timedelta(hours=1),
            observed_at=AS_OF,
            close=close,
            adjustment="raw",
            revision_id="initial",
        )
        for offset, close in ((2, closes[0]), (1, closes[1]))
    )


def _dataset(
    store: ResearchStore, instrument: Instrument, symbol: str, closes: tuple[float, float]
) -> PriceDataset:
    key = CacheKey("yfinance", "prices", instrument.instrument_id, "1d", instrument.currency, "raw")
    snapshot = store.save(
        key,
        f"saved {instrument.instrument_id}".encode(),
        observed_at=AS_OF,
        prices=_bars(instrument, symbol, closes),
    )
    return load_price_dataset(
        store,
        (snapshot.snapshot_id,),
        as_of=AS_OF,
        currency=instrument.currency,
        adjustment="raw",
    )


def _saved_datasets(root) -> tuple[PriceDataset, ...]:
    with ResearchStore(root) as store:
        return (
            _dataset(store, Instrument("XNYS", "XLE", "USD", "America/New_York"), "XLE", (63, 64)),
            _dataset(
                store, Instrument("XTKS", "1329", "JPY", "Asia/Tokyo"), "1329.T", (6900, 7000)
            ),
            _dataset(store, Instrument("FX", "JPY=X", "JPY", "UTC"), "JPY=X", (159, 160)),
        )


def test_saved_prices_write_versioned_parquet_and_manifest(tmp_path):
    from market_research.portfolio_export import write_portfolio_export

    datasets = _saved_datasets(tmp_path / "store")
    manifest_path = write_portfolio_export(datasets, tmp_path / "exports")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    data_path = manifest_path.parent / "prices.parquet"

    assert manifest_path.name == "manifest.json"
    assert manifest_path.parent.name == manifest["export_id"]
    assert set(manifest) == {
        "schema_version",
        "export_id",
        "as_of",
        "data_file",
        "data_sha256",
        "row_count",
        "snapshot_ids",
        "fx_symbol",
    }
    assert manifest["schema_version"] == 1
    assert manifest["as_of"] == AS_OF.isoformat()
    assert manifest["data_file"] == "prices.parquet"
    assert manifest["fx_symbol"] == "JPY=X"
    assert manifest["row_count"] == 6
    assert manifest["snapshot_ids"] == sorted(dataset.snapshot_ids[0] for dataset in datasets)
    assert manifest["data_sha256"] == hashlib.sha256(data_path.read_bytes()).hexdigest()
    assert len(manifest["export_id"]) == 64
    assert not any(
        key in manifest for key in ("account_id", "positions", "holdings", "quantity", "pnl")
    )

    with duckdb.connect() as con:
        rows = con.execute(
            "SELECT provider_symbol, currency, close, snapshot_id, quality, is_final "
            "FROM read_parquet(?) ORDER BY provider_symbol, close",
            [str(data_path)],
        ).fetchall()
    assert rows == [
        ("1329.T", "JPY", 6900.0, datasets[1].snapshot_ids[0], "ok", True),
        ("1329.T", "JPY", 7000.0, datasets[1].snapshot_ids[0], "ok", True),
        ("JPY=X", "JPY", 159.0, datasets[2].snapshot_ids[0], "ok", True),
        ("JPY=X", "JPY", 160.0, datasets[2].snapshot_ids[0], "ok", True),
        ("XLE", "USD", 63.0, datasets[0].snapshot_ids[0], "ok", True),
        ("XLE", "USD", 64.0, datasets[0].snapshot_ids[0], "ok", True),
    ]


def test_same_saved_input_reuses_immutable_export_and_rejects_mutation(tmp_path):
    from market_research.portfolio_export import write_portfolio_export

    datasets = _saved_datasets(tmp_path / "store")
    destination = tmp_path / "exports"
    first = write_portfolio_export(datasets, destination)
    assert write_portfolio_export(tuple(reversed(datasets)), destination) == first
    (first.parent / "prices.parquet").write_bytes(b"modified")
    with pytest.raises(ValueError, match="existing export"):
        write_portfolio_export(datasets, destination)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda bar: replace(bar, is_final=False), "final"),
        (lambda bar: replace(bar, observed_at=AS_OF + timedelta(seconds=1)), "observed_at"),
        (lambda bar: replace(bar, available_at=AS_OF + timedelta(seconds=1)), "available_at"),
        (lambda bar: replace(bar, quality="reject"), "quality"),
        (lambda bar: replace(bar, quality="warn"), "quality"),
        (lambda bar: replace(bar, adjustment="split"), "adjustment"),
    ],
)
def test_rejects_unusable_bar(tmp_path, change, message):
    from market_research.portfolio_export import write_portfolio_export

    datasets = _saved_datasets(tmp_path / "store")
    bad = replace(datasets[0], bars=(change(datasets[0].bars[0]), datasets[0].bars[1]))
    with pytest.raises(ValueError, match=message):
        write_portfolio_export((bad, *datasets[1:]), tmp_path / "exports")


def test_rejects_mixed_as_of_and_ambiguous_symbol(tmp_path):
    from market_research.portfolio_export import write_portfolio_export

    datasets = _saved_datasets(tmp_path / "store")
    with pytest.raises(ValueError, match="as_of"):
        write_portfolio_export(
            (replace(datasets[0], as_of=AS_OF - timedelta(minutes=1)), *datasets[1:]),
            tmp_path / "exports",
        )
    duplicate_symbol = replace(
        datasets[1],
        bars=tuple(replace(bar, provider_symbol="XLE") for bar in datasets[1].bars),
    )
    with pytest.raises(ValueError, match="provider_symbol"):
        write_portfolio_export((datasets[0], duplicate_symbol, datasets[2]), tmp_path / "exports")


def test_rejects_two_snapshots_for_the_same_provider_symbol(tmp_path):
    from market_research.portfolio_export import write_portfolio_export

    datasets = _saved_datasets(tmp_path / "store")
    second_xle = replace(
        datasets[0],
        snapshot_ids=("another-complete-snapshot",),
        bars=(replace(datasets[0].bars[0], revision_id="newer"),),
    )
    with pytest.raises(ValueError, match="provider_symbol"):
        write_portfolio_export((*datasets, second_xle), tmp_path / "exports")


def test_rejects_two_revisions_of_one_daily_bar(tmp_path):
    from market_research.portfolio_export import write_portfolio_export

    datasets = _saved_datasets(tmp_path / "store")
    original = datasets[0].bars[0]
    duplicate_day = replace(
        datasets[0], bars=(original, replace(original, revision_id="later"), datasets[0].bars[1])
    )
    with pytest.raises(ValueError, match="duplicate daily"):
        write_portfolio_export((duplicate_day, *datasets[1:]), tmp_path / "exports")


def test_rejects_multi_snapshot_dataset_without_row_provenance(tmp_path):
    from market_research.portfolio_export import write_portfolio_export

    datasets = _saved_datasets(tmp_path / "store")
    unknown_origin = replace(datasets[0], snapshot_ids=("first", "second"))
    with pytest.raises(ValueError, match="one saved snapshot"):
        write_portfolio_export((unknown_origin, *datasets[1:]), tmp_path / "exports")


def test_rejects_provider_symbol_change_within_one_instrument(tmp_path):
    from market_research.portfolio_export import write_portfolio_export

    datasets = _saved_datasets(tmp_path / "store")
    changed_symbol = replace(
        datasets[0],
        bars=(datasets[0].bars[0], replace(datasets[0].bars[1], provider_symbol="XLE.OLD")),
    )
    with pytest.raises(ValueError, match="provider_symbol"):
        write_portfolio_export((changed_symbol, *datasets[1:]), tmp_path / "exports")


def test_close_column_is_double_even_for_integer_looking_prices(tmp_path):
    from market_research.portfolio_export import write_portfolio_export

    datasets = _saved_datasets(tmp_path / "store")
    path = write_portfolio_export(datasets, tmp_path / "exports")
    with duckdb.connect() as con:
        schema = dict(
            (name, kind)
            for name, kind, *_ in con.execute(
                "DESCRIBE SELECT * FROM read_parquet(?)",
                [str(path.parent / "prices.parquet")],
            ).fetchall()
        )
    assert schema["close"] == "DOUBLE"
