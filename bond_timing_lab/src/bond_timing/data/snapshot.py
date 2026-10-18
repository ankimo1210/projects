"""Fetch every raw input into the bond-timing store (design §4.5).

GSW is not fetched here: it is read from the macrokit store (`macrokit us-term`).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
from macrokit.snapshot import latest_payload

from . import etf, fred, fredmd, liuwu
from .store import MACROKIT_RAW, RAW_ROOT, FetchError, fetch, store_bytes


def snapshot_all(
    root: Path = RAW_ROOT, macrokit_root: Path = MACROKIT_RAW, *, today: pd.Period | None = None
) -> list[str]:
    lines: list[str] = []

    def keep(source: str, indicator: str, content: bytes, url: str, filename: str) -> None:
        result = store_bytes(root, source, indicator, content, url=url, filename=filename)
        state = "stored" if result.changed else "unchanged"
        lines.append(
            f"{source}/{indicator}: {state}, {result.size:,} bytes, sha256 {result.sha256[:12]}"
        )

    for series in fred.SERIES:
        url = fred.URL.format(series=series)
        keep("fred", series, fetch(url), url, f"{series}.csv")
    for indicator, url in fredmd.HISTORICAL.items():
        content = fetch(url)
        if content[:2] != b"PK":
            raise FetchError(f"{url} did not return a zip archive")
        keep("fredmd", indicator, content, url, f"{indicator}.zip")
    month = fredmd.FIRST_MONTHLY
    last = today if today is not None else pd.Period(date.today(), freq="M")
    while month <= last:
        for url in fredmd.monthly_urls(month):
            try:
                content = fetch(url)
            except FetchError:
                continue
            if content.lstrip()[:7].lower() == b"sasdate":
                keep("fredmd", f"monthly_{month}", content, url, f"{month}-md.csv")
                break
        else:
            lines.append(f"fredmd/monthly_{month}: not published")
        month += 1
    for url in liuwu.URLS:
        try:
            content = fetch(url)
        except FetchError:
            continue
        if content[:2] == b"PK":
            keep("liuwu", "monthly", content, url, "liuwu_monthly.xlsx")
            break
    else:
        raise FetchError("the Liu-Wu monthly workbook could not be downloaded")
    for ticker in etf.TICKERS:
        keep("etf", ticker, etf.download_csv(ticker), f"yfinance:{ticker}", f"{ticker}.csv")
    if latest_payload(macrokit_root, "us_term", "gsw") is None:
        raise FileNotFoundError(f"no GSW snapshot under {macrokit_root}; run `macrokit us-term`")
    lines.append(f"us_term/gsw: read from {macrokit_root}")
    return lines
