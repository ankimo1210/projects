"""Spike: download raw inputs once a day into _data/megatech-tracker/raw/.

Run: .venv/bin/python -I megatech-tracker/fetch.py [--refresh]
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

RAW = Path("/home/kazumasa/projects/_data/megatech-tracker/raw")
# Yahoo serves only today's consensus, so every snapshot is kept here; a
# surprise needs the last one taken before the results came out.
CONSENSUS = RAW.parent / "consensus.jsonl"
NY = ZoneInfo("America/New_York")
# data.sec.gov answers a plain project agent; no personal contact is sent.
SEC_UA = "megatech-tracker/0.1 (personal research)"
COMPANIES = {
    "AAPL": 320193,
    "MSFT": 789019,
    "GOOGL": 1652044,
    "AMZN": 1018724,
    "META": 1326801,
    "NVDA": 1045810,
    "TSLA": 1318605,
    "AVGO": 1730168,
    "MU": 723125,
    "AMD": 2488,
    "ORCL": 1341439,
}
INDEX = "^GSPC"
SPY_URL = (
    "https://www.ssga.com/us/en/intermediary/library-content/products/fund-data/etfs/us/"
    "holdings-daily-us-en-spy.xlsx"
)


def _settled(t: datetime) -> datetime:
    """The last 16:30 New York time at or before `t`: that day's close is final."""
    t = t.astimezone(NY)
    cut = t.replace(hour=16, minute=30, second=0, microsecond=0)
    return cut if t >= cut else cut - timedelta(days=1)


def _fresh(path: Path, refresh: bool) -> bool:
    # A file stays fresh until the next New York close settles. A Japan calendar
    # day would keep a bar fetched mid-session, or a fetch made just before an
    # after-the-close release, until midnight in Tokyo.
    if refresh or not path.exists():
        return False
    fetched = datetime.fromtimestamp(path.stat().st_mtime, NY)
    return _settled(fetched) == _settled(datetime.now(NY))


def _get(url: str, agent: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": agent})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def fetch_sec(refresh: bool) -> None:
    for ticker, cik in COMPANIES.items():
        for kind, url in (
            ("companyfacts", f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"),
            ("submissions", f"https://data.sec.gov/submissions/CIK{cik:010d}.json"),
        ):
            path = RAW / f"{kind}_{ticker}.json"
            if _fresh(path, refresh):
                continue
            path.write_bytes(_get(url, SEC_UA))
            time.sleep(0.25)
        print("sec", ticker)


def _frame_json(df: pd.DataFrame | None) -> list[dict]:
    if df is None or len(df) == 0:
        return []
    out = df.reset_index()
    out.columns = [str(c) for c in out.columns]
    return json.loads(out.to_json(orient="records", date_format="iso"))


def _recorded() -> set[tuple[str, str]]:
    if not CONSENSUS.exists():
        return set()
    rows = (json.loads(line) for line in CONSENSUS.read_text().splitlines() if line.strip())
    return {(r["ticker"], r["taken"]) for r in rows}


def _current_quarter(rows: list[dict]) -> dict | None:
    return next((r for r in rows if r.get("period") == "0q"), None)


def record_consensus(ticker: str, path: Path) -> None:
    """Append the current-quarter consensus in `path`, stamped with when it was fetched."""
    y = json.loads(path.read_text())
    # Files written before the stamp existed fall back to their time on disk,
    # which a copy without -p would reset.
    taken = y.get("fetched") or datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(
        timespec="seconds"
    )
    if (ticker, taken) in _recorded():
        return
    history = y.get("earnings_history") or []
    row = {
        "ticker": ticker,
        "taken": taken,
        "last_reported": history[-1]["quarter"][:10] if history else None,
        "eps": _current_quarter(y.get("earnings_estimate", [])),
        "revenue": _current_quarter(y.get("revenue_estimate", [])),
    }
    with CONSENSUS.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _next_earnings(info: dict) -> dict | None:
    # t.calendar gives the date in the machine's zone (a day late in Japan);
    # the timestamp converted to New York is the date the company announces.
    stamp = info.get("earningsTimestampStart") or info.get("earningsTimestamp")
    if not stamp:
        return None
    return {
        "date": datetime.fromtimestamp(stamp, NY).date().isoformat(),
        "estimate": bool(info.get("isEarningsDateEstimate")),
    }


def fetch_yahoo(refresh: bool) -> None:
    prices = RAW / "prices.csv"
    # A company added to COMPANIES today still needs its column.
    if not _fresh(prices, refresh) or not set(COMPANIES) <= set(
        pd.read_csv(prices, nrows=0).columns
    ):
        df = yf.download(
            [*COMPANIES, INDEX], period="11y", interval="1d", auto_adjust=False, progress=False
        )
        df["Close"].to_csv(prices)
        print("prices", df.shape)
    for ticker in COMPANIES:
        path = RAW / f"yahoo_{ticker}.json"
        if _fresh(path, refresh):
            continue
        if path.exists():
            record_consensus(ticker, path)
        t = yf.Ticker(ticker)
        info = t.info
        payload = {
            "info": {
                k: info.get(k)
                for k in (
                    "longName",
                    "marketCap",
                    "forwardPE",
                    "trailingPE",
                    "forwardEps",
                    "trailingEps",
                    "sharesOutstanding",
                    "currency",
                )
            },
            "next_earnings": _next_earnings(info),
            "earnings_history": _frame_json(t.earnings_history),
            "earnings_estimate": _frame_json(t.earnings_estimate),
            "revenue_estimate": _frame_json(t.revenue_estimate),
            "splits": [[str(d.date()), float(r)] for d, r in t.splits.items()],
            "fetched": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
        record_consensus(ticker, path)
        print("yahoo", ticker)


def fetch_spy(refresh: bool) -> None:
    path = RAW / "spy_holdings.xlsx"
    if not _fresh(path, refresh):
        path.write_bytes(_get(SPY_URL, "Mozilla/5.0"))
        print("spy holdings")


if __name__ == "__main__":
    refresh = "--refresh" in sys.argv
    RAW.mkdir(parents=True, exist_ok=True)
    fetch_sec(refresh)
    fetch_yahoo(refresh)
    fetch_spy(refresh)
