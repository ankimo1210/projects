import io
import zipfile

import pandas as pd
from bond_timing.data import snapshot
from bond_timing.data.store import FetchError, indicators, store_bytes


def archive(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as handle:
        for name, content in members.items():
            handle.writestr(name, content)
    return buffer.getvalue()


def test_snapshot_stores_every_source_and_lists_unpublished_months(tmp_path, monkeypatch):
    vintages = archive({"1999-08.csv": b"sasdate,A\nTransform:,1\n1/1/1999,1\n"})

    def fake_fetch(url: str) -> bytes:
        if url.endswith(".zip"):
            return vintages
        if url.endswith("monthly/2026-01-md.csv"):
            return b"sasdate,A\nTransform:,1\n12/1/2025,1\n"
        if "fredgraph" in url:
            return b"observation_date,X\n2020-01-02,1\n"
        if url.startswith("https://docs.google.com"):
            return b"PK not really a workbook"
        raise FetchError(f"GET {url} returned 404")

    monkeypatch.setattr(snapshot, "fetch", fake_fetch)
    monkeypatch.setattr(snapshot.etf, "download_csv", lambda ticker: b"date,close\n2020-01-02,1\n")
    gsw_root = tmp_path / "macrokit"
    store_bytes(
        gsw_root, "us_term", "gsw", b"Date,", url="https://example.invalid", filename="g.csv"
    )
    raw = tmp_path / "raw"
    lines = snapshot.snapshot_all(raw, gsw_root, today=pd.Period("2026-02", "M"))
    assert indicators(raw, "fredmd") == ["hist_1999_2014", "hist_2015_2025", "monthly_2026-01"]
    assert indicators(raw, "fred") == ["DTB3", "TB3MS"]
    assert indicators(raw, "etf") == ["BIL", "IEF", "TLT"]
    assert indicators(raw, "liuwu") == ["monthly"]
    assert "fredmd/monthly_2026-02: not published" in lines
