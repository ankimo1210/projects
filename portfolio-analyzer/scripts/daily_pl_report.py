#!/usr/bin/env python3
"""Daily mark-to-market P&L report.

Reads the position snapshot and the IBKR ledger, fetches the last two closes of
every quoted holding plus USD/JPY from yfinance, and writes a self-contained
HTML summary (``dist/pl-daily/pl-<as-of>.html`` and ``latest.html``) together
with one line of history per day (``data/mtm-history.private.jsonl``).

    uv run --no-sync python portfolio-analyzer/scripts/daily_pl_report.py \
        --copy-to /mnt/c/Users/<you>/Documents/pl-daily

Nothing here edits the snapshot or the ledger. This is the third script that
touches the network (``reprice_snapshot.py`` and ``estimate_factors.py`` are
the others).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import warnings
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from portfolio_analyzer import mtm  # noqa: E402

TOKENS_CSS = PROJECT_ROOT.parent / "docs" / "templates" / "claude-report" / "tokens.css"
TZ = ZoneInfo("Asia/Tokyo")


def quotes_from_closes(closes) -> dict[str, mtm.Quote]:
    """Last two non-null closes per column of a date-indexed DataFrame."""
    import pandas as pd

    out: dict[str, mtm.Quote] = {}
    for column in closes.columns:
        series = pd.to_numeric(closes[column], errors="coerce").dropna()
        if series.empty:
            continue
        last = series.iloc[-1]
        prev = series.iloc[-2] if len(series) >= 2 else None
        out[str(column)] = mtm.Quote(
            close=Decimal(str(last)),
            prev_close=None if prev is None else Decimal(str(prev)),
            date=pd.Timestamp(series.index[-1]).date().isoformat(),
            prev_date=None if prev is None else pd.Timestamp(series.index[-2]).date().isoformat(),
        )
    return out


def download_quotes(tickers: list[str], start: str, end: str) -> dict[str, mtm.Quote]:
    import pandas as pd
    import yfinance as yf

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        raw = yf.download(
            tickers, start=start, end=end, auto_adjust=False, progress=False, group_by="column"
        )
    if raw is None or raw.empty:
        raise RuntimeError("empty price response from yfinance")
    closes = (
        raw["Close"]
        if isinstance(raw.columns, pd.MultiIndex)
        else raw[["Close"]].rename(columns={"Close": tickers[0]})
    )
    quotes = quotes_from_closes(closes)
    missing = [t for t in tickers if t not in quotes]
    if missing:
        raise RuntimeError(f"no usable close for {missing}")
    return quotes


def report_as_of(quotes: dict[str, mtm.Quote]) -> str:
    return max(q.date for q in quotes.values())


def stale_quotes(quotes: dict[str, mtm.Quote], as_of: str) -> dict[str, str]:
    return {t: q.date for t, q in quotes.items() if q.date != as_of}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--snapshot", default=str(PROJECT_ROOT / "data" / "portfolio.private.json"))
    parser.add_argument("--ledger", default=str(PROJECT_ROOT / "data" / "ibkr-ledger.private.json"))
    parser.add_argument(
        "--history", default=str(PROJECT_ROOT / "data" / "mtm-history.private.jsonl")
    )
    parser.add_argument("--out-dir", default=str(PROJECT_ROOT / "dist" / "pl-daily"))
    parser.add_argument(
        "--copy-to", default=None, help="also copy the two HTML files here (e.g. a Windows folder)"
    )
    parser.add_argument("--lookback-days", type=int, default=14)
    parser.add_argument(
        "--keep", type=int, default=400, help="how many dated reports to keep in --out-dir"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    ledger_path = Path(args.ledger)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else None

    tickers = sorted(
        {
            ticker
            for row in snapshot["positions"]
            if row.get("quantity") is not None
            and (ticker := mtm.market_symbol(str(row["symbol"]), str(row["currency"]))) is not None
        }
    )
    today = datetime.now(TZ).date()
    start = (today - timedelta(days=args.lookback_days)).isoformat()
    end = (today + timedelta(days=1)).isoformat()  # yfinance end is exclusive
    print(f"downloading {len(tickers) + 1} series from yfinance ({start} .. {today}) ...")
    quotes = download_quotes([*tickers, mtm.FX_SYMBOL], start, end)
    fx = quotes.pop(mtm.FX_SYMBOL)
    as_of = report_as_of(quotes)
    generated_at = datetime.now(TZ).replace(microsecond=0).isoformat()

    rows = mtm.mark_positions(snapshot, quotes, fx, ledger)
    summary = mtm.summarize(snapshot, rows)
    meta = {
        "as_of": as_of,
        "generated_at": generated_at,
        "fx": fx,
        "stale": stale_quotes(quotes, as_of),
    }

    history_path = Path(args.history)
    records = mtm.upsert_history(history_path, mtm.history_record(summary, rows, meta))
    prev = mtm.previous_record(records, as_of)
    if prev and prev.get("total_jpy") is not None:
        meta["since_last"] = {
            "as_of": prev["as_of"],
            "total": prev["total_jpy"],
            "diff": float(summary.total_jpy) - float(prev["total_jpy"]),
        }

    tokens_css = TOKENS_CSS.read_text(encoding="utf-8") if TOKENS_CSS.exists() else ""
    html = mtm.render_html(summary, rows, records, meta, tokens_css)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dated = out_dir / f"pl-{as_of}.html"
    latest = out_dir / "latest.html"
    dated.write_text(html, encoding="utf-8")
    latest.write_text(html, encoding="utf-8")
    for old in sorted(out_dir.glob("pl-*.html"))[: -args.keep]:
        old.unlink()
    if args.copy_to:
        target = Path(args.copy_to)
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dated, target / dated.name)
        shutil.copy2(latest, target / latest.name)

    print(f"as of {as_of}  USD/JPY {fx.close} ({fx.date})")
    for t, q in sorted(quotes.items()):
        flag = "" if q.date == as_of else "  <- older than as-of"
        print(f"  {t:8s} {float(q.close):>12,.2f} ({q.date}){flag}")
    print(
        f"total {float(summary.total_jpy):,.0f} JPY  day P&L {float(summary.day_pnl_jpy or 0):+,.0f} JPY  unrealized(known) {float(summary.unrealized_known_jpy or 0):+,.0f} JPY"
    )
    print(
        f"report: {dated}\nlatest: {latest}"
        + (f"\ncopied to: {args.copy_to}" if args.copy_to else "")
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # the scheduled job must leave a readable line in the log
        print(f"daily_pl_report failed: {exc!r}", file=sys.stderr)
        sys.exit(1)
