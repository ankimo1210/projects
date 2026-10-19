import os
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd
import pytest
from sector_leadlag.data import jpx, yf
from sector_leadlag.data.snapshot import snapshot_all
from sector_leadlag.data.store import FetchError, indicators, read_latest


def _fake_download(failing: set[str]):
    def download(ticker: str, *, fetched_at: datetime) -> bytes:
        if ticker in failing:
            raise FetchError(f"no history for {ticker}")
        return f"date,close\n2026-10-16,{len(ticker)}\n".encode()

    return download


def test_snapshot_stores_the_listing_every_etf_and_the_topix500_stocks(
    tmp_path: Path, listing_bytes
):
    content = listing_bytes([("7203", 6, "TOPIX Core30"), ("1301", 1, "TOPIX Small 1")])
    lines = snapshot_all(
        tmp_path,
        fetch_listing=lambda url: content,
        download=_fake_download({"9999.T"}),
        sleep=lambda _: None,
        now=datetime(2026, 10, 19, 10, 0, tzinfo=UTC),
    )
    stored = indicators(tmp_path, "yf")
    assert set(stored) == {*yf.US_SECTORS, *jpx.ETF_TICKERS, "7203.T"}
    assert jpx.parse_listing(read_latest(tmp_path, "jpx", "data_j")).as_of == date(2026, 9, 30)
    assert lines[0].startswith("jpx/data_j: stored")


def test_a_failing_stock_is_listed_and_a_failing_etf_stops_the_snapshot(
    tmp_path: Path, listing_bytes
):
    content = listing_bytes([("7203", 6, "TOPIX Core30"), ("6758", 9, "TOPIX Core30")])
    lines = snapshot_all(
        tmp_path,
        fetch_listing=lambda url: content,
        download=_fake_download({"6758.T"}),
        sleep=lambda _: None,
    )
    assert "yf/6758.T: failed" in lines
    with pytest.raises(FetchError, match=r"1617\.T"):
        snapshot_all(
            tmp_path / "other",
            fetch_listing=lambda url: content,
            download=_fake_download({"1617.T"}),
            sleep=lambda _: None,
        )


@pytest.mark.skipif(os.environ.get("SECTOR_LEADLAG_NETWORK") != "1", reason="network test")
def test_the_real_listing_and_one_history_download():
    from sector_leadlag.data.store import fetch

    listing = jpx.parse_listing(fetch(jpx.URL))
    assert len(jpx.topix500(listing)) > 450
    frame = yf.parse_csv(yf.download("1617.T"))
    assert frame.index[0] < pd.Timestamp("2009-01-01") and (frame["volume"] >= 0).all()
