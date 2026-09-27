"""The explicit portfolio export CLI reads saved snapshots offline."""

from __future__ import annotations

import json
import socket
import urllib.request
from datetime import UTC, datetime, timedelta

from market_research.cli import main
from market_research.contracts import Instrument, PriceBar
from market_research.storage import CacheKey, ResearchStore

AS_OF = datetime(2026, 9, 26, tzinfo=UTC)


def _snapshot(store: ResearchStore, instrument: Instrument, symbol: str) -> str:
    bars = tuple(
        PriceBar(
            instrument=instrument,
            provider="fixture",
            provider_symbol=symbol,
            interval="1d",
            bar_start=AS_OF - timedelta(days=offset, hours=8),
            bar_end=AS_OF - timedelta(days=offset, hours=1),
            available_at=AS_OF - timedelta(days=offset),
            observed_at=AS_OF,
            close=100.0 + offset,
            adjustment="raw",
            revision_id="initial",
        )
        for offset in (2, 1)
    )
    key = CacheKey("fixture", "prices", instrument.instrument_id, "1d", instrument.currency, "raw")
    return store.save(key, b"fixture", observed_at=AS_OF, prices=bars).snapshot_id


def test_export_cli_reuses_saved_snapshot_without_network_or_account_data(
    tmp_path, monkeypatch, capsys
):
    def blocked(*_args, **_kwargs):
        raise AssertionError("unexpected network access")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(urllib.request, "urlopen", blocked)
    with ResearchStore(tmp_path / "data") as store:
        stock = _snapshot(store, Instrument("XNYS", "AAA", "USD", "America/New_York"), "AAA")
        fx = _snapshot(store, Instrument("FX", "JPY=X", "JPY", "UTC"), "JPY=X")
    command = [
        "--data-root",
        str(tmp_path / "data"),
        "export-portfolio",
        "--snapshot-id",
        stock,
        "--fx-snapshot-id",
        fx,
        "--as-of",
        AS_OF.isoformat(),
    ]

    assert main(command) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["export_id"]
    manifest_path = tmp_path / "data" / "exports" / first["export_id"] / "manifest.json"
    assert first["manifest"] == str(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["snapshot_ids"] == sorted((stock, fx))
    assert manifest["row_count"] == 4
    assert "account_id" not in manifest and "holdings" not in manifest

    assert main(command) == 0
    second = json.loads(capsys.readouterr().out)
    assert second == first
