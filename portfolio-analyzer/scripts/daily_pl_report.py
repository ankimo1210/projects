#!/usr/bin/env python3
"""Daily mark-to-market dashboard.

Reads the position snapshot, the IBKR ledger and transaction history, fetches two
years of closes for every quoted holding plus USD/JPY from yfinance, and writes a
self-contained HTML dashboard (``dist/pl-daily/pl-<as-of>.html`` and
``latest.html``): headline P&L, allocation and attribution, every position with
its 1-year sparkline, then the account NAV / P&L path reconstructed from the
transaction history and a price + P&L pair per symbol. One line of history per
day goes to ``data/mtm-history.private.jsonl``.

    uv run --no-sync python portfolio-analyzer/scripts/daily_pl_report.py \
        --copy-to /mnt/c/Users/<you>/Documents/pl-daily

Nothing here edits the snapshot, the ledger or the transaction history. This is
the third script that touches the network (``reprice_snapshot.py`` and
``estimate_factors.py`` are the others).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import warnings
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from portfolio_analyzer import chartshot, dashboard, ibkr, mailer, mtm  # noqa: E402
from portfolio_analyzer import timeseries as ts  # noqa: E402

TOKENS_CSS = PROJECT_ROOT.parent / "docs" / "templates" / "claude-report" / "tokens.css"
TZ = ZoneInfo("Asia/Tokyo")
ZERO = Decimal(0)


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


def download_closes(tickers: list[str], start: str, end: str):
    """Date-indexed DataFrame of raw closes, one column per ticker (missing ones dropped)."""
    import pandas as pd
    import yfinance as yf

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        raw = yf.download(
            tickers, start=start, end=end, auto_adjust=False, progress=False, group_by="column"
        )
    if raw is None or raw.empty:
        raise RuntimeError("empty price response from yfinance")
    if isinstance(raw.columns, pd.MultiIndex):
        closes = raw["Close"]
    else:
        closes = raw[["Close"]].rename(columns={"Close": tickers[0]})
    closes = closes.dropna(axis=1, how="all")
    closes.index = pd.to_datetime(closes.index).tz_localize(None).normalize()
    return closes.sort_index()


def report_as_of(quotes: dict[str, mtm.Quote]) -> str:
    return max(q.date for q in quotes.values())


def stale_quotes(quotes: dict[str, mtm.Quote], as_of: str) -> dict[str, str]:
    return {t: q.date for t, q in quotes.items() if q.date != as_of}


def _f(value: Decimal | float | None) -> float | None:
    if value is None:
        return None
    out = float(value)
    return None if out != out else out  # NaN -> null, never let it into the JSON payload


def _pct(value: Decimal | float | None) -> float | None:
    return None if value is None else float(value) * 100


def _downsample(values: list[float], n: int = 80) -> list[float]:
    if len(values) <= n:
        return values
    step = (len(values) - 1) / (n - 1)
    return [values[round(i * step)] for i in range(n)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--snapshot", default=str(PROJECT_ROOT / "data" / "portfolio.private.json"))
    parser.add_argument("--ledger", default=str(PROJECT_ROOT / "data" / "ibkr-ledger.private.json"))
    parser.add_argument(
        "--transactions", default=str(PROJECT_ROOT / "data" / "ibkr-transactions.private.csv")
    )
    parser.add_argument(
        "--history", default=str(PROJECT_ROOT / "data" / "mtm-history.private.jsonl")
    )
    parser.add_argument("--out-dir", default=str(PROJECT_ROOT / "dist" / "pl-daily"))
    parser.add_argument(
        "--copy-to", default=None, help="also copy the two HTML files here (e.g. a Windows folder)"
    )
    parser.add_argument(
        "--window-days", type=int, default=365, help="length of the time-series window"
    )
    parser.add_argument(
        "--history-days", type=int, default=760, help="how far back to fetch closes"
    )
    parser.add_argument("--keep", type=int, default=400, help="dated reports to keep in --out-dir")
    parser.add_argument(
        "--png", action="store_true", help="also render the chart section to pl-<as-of>.png"
    )
    parser.add_argument(
        "--email",
        action="append",
        default=None,
        metavar="ADDRESS",
        help="send the summary there (repeatable). Needs PL_SMTP_USER and PL_SMTP_PASS in the "
        "environment; host and port default to smtp.gmail.com:465 (PL_SMTP_HOST / PL_SMTP_PORT).",
    )
    parser.add_argument(
        "--no-image",
        action="store_true",
        help="send the mail without the rendered chart image; the body then falls back to "
        "figures drawn with table cells, which no mail client can strip",
    )
    return parser.parse_args()


def build_payload(args: argparse.Namespace) -> tuple[dict, dict, str]:
    """Fetch, compute and assemble the dashboard payload. Returns (payload, history record, as_of)."""
    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    ledger_path, tx_path = Path(args.ledger), Path(args.transactions)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else None
    transactions = (
        ibkr.parse_transactions(tx_path.read_text(encoding="utf-8-sig")) if tx_path.exists() else []
    )
    ledger_account = str((ledger or {}).get("account_id", "global_broker"))
    account_names = {str(a["id"]): str(a.get("name", a["id"])) for a in snapshot["accounts"]}

    open_tickers = {
        ticker: (str(row["symbol"]), str(row["account_id"]))
        for row in snapshot["positions"]
        if row.get("quantity") is not None
        and (ticker := mtm.market_symbol(str(row["symbol"]), str(row["currency"]))) is not None
    }
    ledger_symbols = sorted(
        {r.symbol for r in transactions if r.transaction_type in ibkr.TRADE_TYPES and r.symbol}
    )
    tickers = sorted(set(open_tickers) | set(ledger_symbols))

    today = datetime.now(TZ).date()
    start = (today - timedelta(days=args.history_days)).isoformat()
    end = (today + timedelta(days=1)).isoformat()  # yfinance end is exclusive
    print(f"downloading {len(tickers) + 1} series from yfinance ({start} .. {today}) ...")
    closes = download_closes([*tickers, mtm.FX_SYMBOL], start, end)
    quotes = quotes_from_closes(
        closes[[t for t in open_tickers if t in closes.columns] + [mtm.FX_SYMBOL]]
    )
    fx_quote = quotes.pop(mtm.FX_SYMBOL)
    missing = [t for t in open_tickers if t not in quotes]
    if missing:
        raise RuntimeError(f"no usable close for {missing}")
    as_of = report_as_of(quotes)
    generated_at = datetime.now(TZ).replace(microsecond=0).isoformat()

    # ---- today's marks (all accounts) ----
    rows = mtm.mark_positions(snapshot, quotes, fx_quote, ledger)
    summary = mtm.summarize(snapshot, rows)
    meta = {
        "as_of": as_of,
        "generated_at": generated_at,
        "fx": fx_quote,
        "stale": stale_quotes(quotes, as_of),
    }
    record = mtm.history_record(summary, rows, meta)

    # ---- daily paths on the union calendar, forward-filled ----
    filled = closes.ffill()
    # FX has no bar on some JP trading days at the very start of the window: back-fill it so the
    # replay never multiplies by NaN (a NaN in the payload would break JSON.parse in the page).
    filled[mtm.FX_SYMBOL] = filled[mtm.FX_SYMBOL].bfill()
    dates = [d.date().isoformat() for d in filled.index]
    fx_path = [Decimal(str(v)) for v in filled[mtm.FX_SYMBOL].tolist()]
    price_path = {
        t: [
            None if v != v else Decimal(str(v)) for v in filled[t].tolist()
        ]  # NaN before listing/first bar
        for t in tickers
        if t in filled.columns
    }
    paths = ts.replay(transactions, dates)
    ledger_prices = {
        s: [v if v is not None else ZERO for v in price_path[s]]
        for s in paths.positions
        if s in price_path
    }
    values = ts.value_paths(paths, ledger_prices, fx_path)
    wi = ts.window_start_index(dates, as_of, args.window_days)
    n = len(dates)

    def window(series):
        return [_f(v) for v in series[wi:]]

    # ---- headline ----
    nav_ibkr = values.nav[-1]
    pnl_window = values.pnl_total[-1] - values.pnl_total[wi]
    cash = ibkr.summarize_cash(transactions) if transactions else None
    xirr = None
    if cash and cash.deposit_flows:
        flows = [(d, -a) for d, a in cash.deposit_flows] + [(as_of, nav_ibkr)]
        xirr = ibkr.money_weighted_return(flows)
    peak, dd_jpy, dd_pct = None, ZERO, None
    for i in range(wi, n):
        v = values.pnl_total[i]
        if peak is None or v > peak[0]:
            peak = (v, values.nav[i])
        if peak[1] and v - peak[0] < dd_jpy:
            dd_jpy, dd_pct = v - peak[0], (v - peak[0]) / peak[1]
    day_pnl = summary.day_pnl_jpy
    day_base = summary.quoted_value_jpy - (day_pnl or ZERO)
    headline = {
        "nav_total": _f(summary.total_jpy),
        "quoted_value": _f(summary.quoted_value_jpy),
        "quoted_share": _f(summary.quoted_value_jpy / summary.total_jpy)
        if summary.total_jpy
        else 0.0,
        "day_pnl": _f(day_pnl),
        "day_pnl_pct": _pct(day_pnl / day_base) if day_pnl is not None and day_base else None,
        "unrealized_known": _f(summary.unrealized_known_jpy),
        "pnl_window": _f(pnl_window),
        "pnl_incept": _f(values.pnl_total[-1]),
        "realized_cum": _f(paths.realized_cum[-1]),
        "dividends_net": _f(paths.dividends_cum[-1]),
        "xirr": _f(xirr),
        "max_dd_window": _f(dd_pct),
        "max_dd_window_jpy": _f(dd_jpy),
    }

    # ---- general data ----
    accounts = [
        {
            "id": a.id,
            "name": a.name,
            "total": _f(a.total_jpy),
            "day_pnl": _f(a.day_pnl_jpy),
            "unrealized": _f(a.unrealized_known_jpy),
        }
        for a in summary.accounts.values()
    ]
    by_class: dict[str, Decimal] = {}
    for r in rows:
        by_class[r.asset_class] = by_class.get(r.asset_class, ZERO) + r.market_value_jpy
    allocation = [
        {"label": k, "value": _f(v), "pct": _pct(v / summary.total_jpy)}
        for k, v in sorted(by_class.items(), key=lambda kv: -kv[1])
    ]
    positions, tape, symbols = [], [], {}
    total = summary.total_jpy or Decimal(1)
    for r in sorted((r for r in rows if r.quoted), key=lambda r: -r.market_value_jpy):
        series = [v for v in price_path[r.ticker] if v is not None]
        win_prices = [v for v in price_path[r.ticker][wi:]]
        key = f"{r.symbol}@{r.account_id}"
        positions.append(
            {
                "key": key,
                "sym": r.symbol,
                "acct": account_names.get(r.account_id, r.account_id),
                "name": r.name,
                "cls": r.asset_class,
                "cur": r.currency,
                "qty": _f(r.quantity),
                "last": _f(r.price),
                "chg1d": _pct(r.day_change_pct),
                "chg1w": _pct(ts.window_return(series, 5)),
                "chg1m": _pct(ts.window_return(series, 21)),
                "chg1y": _pct(ts.window_return(series, n - 1 - wi)),
                "spark": _downsample([_f(v) for v in win_prices if v is not None]),
                "value": _f(r.market_value_jpy),
                "weight": _pct(r.market_value_jpy / total),
                "day_pnl": _f(r.day_pnl_jpy),
                "avg_cost": _f(r.average_cost),
                "unreal": _f(r.unrealized_jpy),
                "unreal_pct": _pct(r.unrealized_pct),
            }
        )
        if r.account_id == ledger_account and r.ticker in values.unrealized:
            pnl_series = values.unrealized[r.ticker]
            label, mode = "含み損益（取得原価比）", "pnl"
            trades = [
                {"i": dates.index(d) - wi, "qty": _f(q), "price": _f(p)}
                for d, q, p in paths.trades.get(r.ticker, [])
                if d in dates and dates.index(d) >= wi
            ]
        else:
            base = next((v for v in price_path[r.ticker][wi:] if v is not None), None)
            rate = fx_path if r.currency == "USD" else None
            pnl_series = [
                (r.quantity * (v - base) * (rate[i] if rate else Decimal(1)))
                if (v is not None and base is not None)
                else None
                for i, v in enumerate(price_path[r.ticker])
            ]
            label, mode = "評価額の変化（期間初日比・原価なし）", "value"
            trades = []
        symbols[key] = {
            "mode": mode,
            "label": label,
            "cur": r.currency,
            "price": window(price_path[r.ticker]),
            "pnl": window(pnl_series),
            "trades": trades,
            "avg_cost": _f(r.average_cost),
        }
        tape.append(
            {
                "sym": r.symbol,
                "cur": r.currency,
                "last": _f(r.price),
                "chg_pct": _pct(r.day_change_pct),
            }
        )
    seen = set()
    tape = [t for t in tape if not (t["sym"] in seen or seen.add(t["sym"]))]

    def bucket(series, i0: int, i1: int) -> float:
        return float(series[i1] - series[i0])

    unreal_total = [
        sum((values.unrealized[s][i] for s in values.unrealized), ZERO) for i in range(n)
    ]
    attribution = {}
    for name_, i0 in (("window", wi), ("incept", 0)):
        attribution[name_] = {
            "unrealized": bucket(unreal_total, i0, n - 1)
            if name_ == "window"
            else float(unreal_total[-1]),
            "realized": bucket(paths.realized_cum, i0, n - 1)
            if name_ == "window"
            else float(paths.realized_cum[-1]),
            "dividends": bucket(paths.dividends_cum, i0, n - 1)
            if name_ == "window"
            else float(paths.dividends_cum[-1]),
            "fees": bucket(paths.fees_cum, i0, n - 1)
            if name_ == "window"
            else float(paths.fees_cum[-1]),
            "fx_translation": bucket(paths.fx_translation_cum, i0, n - 1)
            if name_ == "window"
            else float(paths.fx_translation_cum[-1]),
            "forex": bucket(paths.forex_cum, i0, n - 1)
            if name_ == "window"
            else float(paths.forex_cum[-1]),
            "total": bucket(values.pnl_total, i0, n - 1)
            if name_ == "window"
            else float(values.pnl_total[-1]),
        }
    holdings_now = ibkr.derive_holdings(transactions) if transactions else {}
    closed = [
        {
            "sym": s,
            "first": paths.first_trade.get(s, ""),
            "last": paths.last_trade.get(s, ""),
            "trades": len(paths.trades.get(s, [])),
            "realized": _f(h.realized_pnl_jpy),
        }
        for s, h in sorted(holdings_now.items())
        if h.is_closed
    ]
    daily = [None] + [_f(values.pnl_total[i] - values.pnl_total[i - 1]) for i in range(wi + 1, n)]

    notes = []
    if meta["stale"]:
        notes.append(
            "基準日より前の終値: "
            + "、".join(f"{k}（{v}）" for k, v in sorted(meta["stale"].items()))
        )
    carried = [r for r in rows if not r.quoted]
    if carried:
        notes.append(
            "時価が取れず据え置き: "
            + "、".join(r.symbol for r in carried)
            + f"（合計 {int(sum((r.market_value_jpy for r in carried), ZERO)):,} 円）"
        )
    no_cost = [r for r in rows if r.quoted and r.unrealized_jpy is None]
    if no_cost:
        notes.append(
            "取得原価が無い保有（含み損益なし、カードの損益は期間初日比の評価額変化）: "
            + "、".join(
                f"{account_names.get(r.account_id, r.account_id)} {r.symbol}" for r in no_cost
            )
        )
    notes.append(
        "日次損益は各銘柄の直近 2 終値の差（価格と為替の両方）。海外証券口座の NAV・損益は取引履歴を日次で再生した値で、"
        f"取引履歴は {paths.dates[0] if transactions else '—'} 以降、履歴 CSV の最終日以降の取引は反映されない"
    )
    notes.append(
        "株価と為替は yfinance の終値。休場日は直前の終値で埋める。DC 残高・現金・調整額はスナップショットの値"
    )

    payload = {
        "as_of": as_of,
        "generated_at": generated_at,
        "fx": {
            "last": _f(fx_quote.close),
            "chg_pct": _pct(fx_quote.close / fx_quote.prev_close - 1)
            if fx_quote.prev_close
            else None,
            "date": fx_quote.date,
        },
        "window": {"start": dates[wi], "end": as_of, "days": args.window_days},
        "headline": headline,
        "accounts": accounts,
        "allocation": allocation,
        "tape": tape,
        "positions": positions,
        "series": {
            "dates": dates[wi:],
            "nav": window(values.nav),
            "pnl": window(values.pnl_total),
            "deposits": window(paths.deposits_cum),
            "daily_pnl": daily,
            "symbols": symbols,
        },
        "attribution": attribution,
        "closed": closed,
        "notes": notes,
    }
    return payload, record, as_of


def main() -> int:
    args = parse_args()
    payload, record, as_of = build_payload(args)
    records = mtm.upsert_history(Path(args.history), record)
    tokens_css = TOKENS_CSS.read_text(encoding="utf-8") if TOKENS_CSS.exists() else ""
    html = dashboard.render(payload, tokens_css)

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

    png_path = None
    if args.png or (args.email and not args.no_image):
        png_path = out_dir / f"pl-{as_of}.png"
        rendered = chartshot.render(latest, png_path)
        if rendered is None:
            png_path = None
            print("no headless browser found; skipping the chart image")
        else:
            print(f"chart image: {png_path} ({png_path.stat().st_size / 1024:.0f} KB)")

    if args.email:
        user = os.environ.get("PL_SMTP_USER")
        password = os.environ.get("PL_SMTP_PASS")
        if not user or not password:
            raise RuntimeError("PL_SMTP_USER / PL_SMTP_PASS are not set; cannot send the email")
        png = png_path.read_bytes() if png_path and not args.no_image else None
        msg = mailer.build_message(
            payload, to=args.email, sender=os.environ.get("PL_SMTP_FROM", user), png=png
        )
        mailer.send(
            msg,
            host=os.environ.get("PL_SMTP_HOST", "smtp.gmail.com"),
            port=int(os.environ.get("PL_SMTP_PORT", "465")),
            user=user,
            password=password,
        )
        print(f"emailed: {', '.join(args.email)}")

    h = payload["headline"]
    print(f"as of {as_of}  USD/JPY {payload['fx']['last']:.2f}  history rows {len(records)}")
    for p in payload["positions"]:
        print(
            f"  {p['sym']:6s} {p['acct'][:6]:6s} {p['last']:>12,.2f} {p['chg1d']:+6.2f}%  value {p['value']:>14,.0f}"
        )
    print(
        f"total {h['nav_total']:,.0f} JPY  day {h['day_pnl'] or 0:+,.0f}  window {h['pnl_window'] or 0:+,.0f}  "
        f"inception {h['pnl_incept'] or 0:+,.0f}  unrealized(known) {h['unrealized_known'] or 0:+,.0f}"
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
