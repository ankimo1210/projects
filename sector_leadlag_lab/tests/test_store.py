from pathlib import Path

import pytest
from sector_leadlag.data.store import indicators, manifest_records, read_latest, store_bytes


def test_store_and_read_back(tmp_path: Path):
    store_bytes(tmp_path, "yf", "XLK", b"a,b\n", url="yfinance:XLK", filename="XLK.csv")
    store_bytes(tmp_path, "yf", "1617.T", b"c\n", url="yfinance:1617.T", filename="1617.T.csv")
    store_bytes(tmp_path, "jpx", "data_j", b"x", url="https://example.invalid", filename="d.xlsx")
    assert read_latest(tmp_path, "yf", "XLK") == b"a,b\n"
    assert indicators(tmp_path, "yf") == ["1617.T", "XLK"]
    assert indicators(tmp_path, "etf") == []
    records = manifest_records(tmp_path)
    assert list(records) == ["jpx/data_j", "yf/1617.T", "yf/XLK"]
    assert len(records["yf/XLK"]["sha256"]) == 64


def test_read_latest_names_the_missing_snapshot(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="sector-leadlag snapshot"):
        read_latest(tmp_path, "yf", "XLK")
