from pathlib import Path

import pytest
from bond_timing.data.store import indicators, read_latest, store_bytes


def test_store_and_read_back(tmp_path: Path):
    store_bytes(
        tmp_path, "fred", "DTB3", b"a,b\n", url="https://example.invalid/a", filename="DTB3.csv"
    )
    store_bytes(
        tmp_path,
        "fredmd",
        "monthly_2026-01",
        b"x",
        url="https://example.invalid/b",
        filename="x.csv",
    )
    assert read_latest(tmp_path, "fred", "DTB3") == b"a,b\n"
    assert indicators(tmp_path, "fredmd") == ["monthly_2026-01"]
    assert indicators(tmp_path, "etf") == []


def test_read_latest_names_the_missing_snapshot(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="bond-timing snapshot"):
        read_latest(tmp_path, "fred", "DTB3")
