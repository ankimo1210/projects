"""Reprice a portfolio snapshot at current market closes.

The snapshot in ``data/portfolio.private.json`` records what the account
screens said on the day it was transcribed. This script does not edit it.
It reads that file, replaces the price of every position that carries a
quantity with the latest close at or before ``--as-of``, and writes a new
snapshot next to it.

The DC plan's fund has no market quote; it is valued like the daily report
does, at its fund company's published price times the units held (the plan's
anchor plus the contributions in its trade history, ``dcplan``), and its account
P&L is the value less the contributions. Cash and the reconciliation plug have
no quote either, so they are carried forward unchanged and the reason is written
into ``source_note`` (so is the DC balance when the price CSV cannot be read). Account totals are recomputed as the
sum of their positions, and any account P&L figure that the repricing
invalidates is dropped rather than carried forward as if it still held.

This is the second script that touches the network (``estimate_factors.py``
is the other one). ``build_dashboard.py`` stays offline and reads only the
files these two write.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from portfolio_analyzer import dcplan
from portfolio_analyzer.mtm import bar_is_final

FX_SYMBOL = "JPY=X"
PRICE_DECIMALS = Decimal("0.0001")
FX_DECIMALS = Decimal("0.000001")
VALUE_DECIMALS = Decimal("0.01")


def market_symbol(symbol: str, currency: str) -> str | None:
    """Return the yfinance ticker for a holding, or None if it has no quote."""
    if symbol in {"CASH_JPY", "RECONCILIATION"}:
        return None
    if currency == "JPY" and symbol.isdigit():
        return f"{symbol}.T"
    if currency == "USD":
        return symbol
    return None


def last_final_close(series: Any, symbol: str, now: datetime) -> dict[str, Any] | None:
    """The last close whose session has ended at ``now``; a bar still trading is skipped."""
    import pandas as pd

    for stamp, value in reversed(list(series.items())):
        bar_date = pd.Timestamp(stamp).date()
        if bar_is_final(symbol, bar_date, now):
            return {
                "close": Decimal(str(value)).quantize(PRICE_DECIMALS),
                "date": bar_date.isoformat(),
            }
    return None


def download_closes(symbols: list[str], start: str, end: str) -> dict[str, Any]:
    """Return the last non-null close and its date for each symbol."""
    import warnings

    import pandas as pd
    import yfinance as yf

    now = datetime.now(UTC)
    out: dict[str, Any] = {}
    for symbol in symbols:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            raw = yf.download(symbol, start=start, end=end, auto_adjust=False, progress=False)
        if raw is None or raw.empty:
            raise RuntimeError(f"empty price response for {symbol}")
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        series = pd.to_numeric(raw["Close"], errors="coerce").dropna()
        quote = last_final_close(series, symbol, now)
        if quote is None:
            raise RuntimeError(f"no usable close for {symbol}")
        out[symbol] = quote
    return out


def fund_quote(
    holding: dict[str, Any],
    trades: list[dcplan.Trade],
    nav: list[tuple[str, Decimal]],
    as_of: str,
) -> dict[str, Any] | None:
    """The DC plan's fund on ``as_of``: units from the plan's anchor plus the contributions
    traded by then (in 10,000 units), at the last published price on or before the day.
    None when there is no price yet or the anchor is later than the day."""
    prices = [(d, p) for d, p in nav if d <= as_of]
    if not prices or holding["anchor"]["as_of"] > as_of:
        return None
    (h,) = dcplan.ledger(holding, [t for t in trades if t.trade_date <= as_of])["holdings"]
    day, price = max(prices)
    return {
        "ticker": holding["ticker"],
        "quantity": h["quantity"],
        "close": price,
        "date": day,
        "cost_basis_jpy": h["cost_basis_jpy"],
    }


def reprice(
    snapshot: dict[str, Any],
    quotes: dict[str, Any],
    fx: Decimal,
    as_of: str,
    funds: dict[tuple[str, str], dict[str, Any]] | None = None,
) -> dict:
    """Return a new snapshot priced at ``quotes``, leaving ``snapshot`` untouched.
    ``funds`` prices unlisted funds by (account id, symbol) with ``fund_quote``'s result."""
    funds = funds or {}
    positions: list[dict[str, Any]] = []
    repriced_accounts: set[str] = set()
    fund_accounts: dict[str, dict[str, Any]] = {}

    for row in snapshot["positions"]:
        new = dict(row)
        ticker = market_symbol(str(row["symbol"]), str(row["currency"]))
        fund = funds.get((str(row["account_id"]), str(row["symbol"])))
        if fund is not None:
            value = (fund["quantity"] * fund["close"]).quantize(VALUE_DECIMALS)
            new["quantity"] = float(fund["quantity"])
            new["price"] = float(fund["close"])
            new["fx_rate"] = 1.0
            new["market_value_jpy"] = float(value)
            new["value_status"] = "estimated"
            new["price_as_of"] = fund["date"]
            new["source_note"] = (
                f"{fund['date']} の基準価額（1万口あたり）× 保有口数（万口）。"
                "口数は DC サイトの残高に掛金履歴を足したもの"
            )
            account = fund_accounts.setdefault(
                str(row["account_id"]), {"value": Decimal(0), "cost": Decimal(0), "date": ""}
            )
            account["value"] += value
            account["cost"] += fund["cost_basis_jpy"]
            account["date"] = max(account["date"], fund["date"])
        elif ticker is not None and row.get("quantity") is not None:
            quote = quotes[ticker]
            rate = fx if row["currency"] == "USD" else Decimal(1)
            quantity = Decimal(str(row["quantity"]))
            value = (quantity * quote["close"] * rate).quantize(VALUE_DECIMALS)
            new["price"] = float(quote["close"])
            new["fx_rate"] = float(rate)
            new["market_value_jpy"] = float(value)
            new["value_status"] = "estimated"
            new["price_as_of"] = quote["date"]
            new["source_note"] = f"{quote['date']} 終値 × 数量" + (
                f"（為替 {FX_SYMBOL} {as_of}）" if row["currency"] == "USD" else ""
            )
            new.pop("fx_rate_status", None)
            repriced_accounts.add(str(row["account_id"]))
        else:
            carried = str(row.get("source_note", ""))
            new["source_note"] = (
                f"{carried}（時価が取れないため据え置き）" if carried else "据え置き"
            )
            if row.get("value_status") == "exact" and row["asset_class"] != "現金":
                new["value_status"] = "estimated"
        positions.append(new)

    totals: dict[str, Decimal] = {}
    for row in positions:
        account_id = str(row["account_id"])
        totals[account_id] = totals.get(account_id, Decimal(0)) + Decimal(
            str(row["market_value_jpy"])
        )

    accounts = []
    for row in snapshot["accounts"]:
        new = dict(row)
        account_id = str(row["id"])
        new["total_value_jpy"] = float(totals[account_id].quantize(VALUE_DECIMALS))
        if account_id in fund_accounts and account_id not in repriced_accounts:
            fund = fund_accounts[account_id]
            new["as_of"] = fund["date"]
            new["unrealized_pnl_jpy"] = float(fund["value"] - fund["cost"])
            new["daily_pnl_jpy"] = None
            new["quality_note"] = (
                f"{fund['date']} の基準価額で再評価。口座損益は評価額 − 拠出金累計"
                f"（{fund['cost']:,.0f} 円）"
            )
        elif account_id in repriced_accounts:
            new["as_of"] = as_of
            new["unrealized_pnl_jpy"] = None
            new["daily_pnl_jpy"] = None
            new["quality_note"] = (
                f"{as_of} 時点の終値で再評価。口座損益は取得原価が未入力のため再計算できず、"
                f"元スナップショット（{row['as_of']}）の値は無効になったので落とした"
            )
        else:
            new["quality_note"] = (
                f"{row['as_of']} の残高を据え置き（{as_of} 時点の基準価額を取得できない）。"
                f"元の注記: {row.get('quality_note', '')}"
            )
        accounts.append(new)

    dates = {ticker: quote["date"] for ticker, quote in quotes.items()}
    dates.update({fund["ticker"]: fund["date"] for fund in funds.values()})
    stale = {ticker: day for ticker, day in dates.items() if day != as_of}
    return {
        "snapshot_name": f"{as_of} 再評価スナップショット",
        "base_currency": snapshot.get("base_currency", "JPY"),
        "repricing": {
            "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "as_of": as_of,
            "source": "yfinance (close)",
            "fx_symbol": FX_SYMBOL,
            "fx_rate": float(fx),
            "quotes": dates,
            "quotes_older_than_as_of": stale,
            "carried_forward": (
                "現金・残高調整は時価が無いため元スナップショットのまま"
                + ("" if funds else "。DC残高も基準価額が取れなかったため据え置き")
            ),
        },
        "accounts": accounts,
        "positions": positions,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--input", default=str(root / "data" / "portfolio.private.json"))
    parser.add_argument(
        "--output", default=None, help="default: data/portfolio-<as-of>.private.json"
    )
    parser.add_argument("--as-of", default=date.today().isoformat())
    parser.add_argument("--lookback-days", type=int, default=30)
    parser.add_argument(
        "--dc-holding",
        default=str(root / "data" / "dc-holding.private.json"),
        help="the DC plan's anchor and its fund's price CSV (skipped when missing)",
    )
    parser.add_argument(
        "--dc-transactions",
        default=str(root / "data" / "dc-transactions.private.tsv"),
        help="the DC plan's trade history as pasted from its site",
    )
    return parser.parse_args()


def load_funds(args: argparse.Namespace) -> dict[tuple[str, str], dict[str, Any]]:
    """The DC fund's quote for ``args.as_of``, or nothing (and a note) when it cannot be had."""
    import urllib.request

    holding_path = Path(args.dc_holding)
    if not holding_path.exists():
        return {}
    holding = json.loads(holding_path.read_text(encoding="utf-8"))
    tx_path = Path(args.dc_transactions)
    trades = dcplan.parse_trades(dcplan.decode(tx_path.read_bytes())) if tx_path.exists() else []
    request = urllib.request.Request(holding["nav_csv_url"], headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            nav = dcplan.parse_nav(dcplan.decode(response.read()))
    except OSError as exc:
        print(f"DC fund price unavailable, balance carried forward: {exc}")
        return {}
    quote = fund_quote(holding, trades, nav, args.as_of)
    if quote is None:
        print(f"no DC fund price on or before {args.as_of}; balance carried forward")
        return {}
    return {(holding["account_id"], holding["symbol"]): quote}


def main() -> None:
    args = parse_args()
    source = Path(args.input)
    snapshot = json.loads(source.read_text(encoding="utf-8"))

    tickers = sorted(
        {
            ticker
            for row in snapshot["positions"]
            if row.get("quantity") is not None
            and (ticker := market_symbol(str(row["symbol"]), str(row["currency"]))) is not None
        }
    )
    as_of = date.fromisoformat(args.as_of)
    start_date = date.fromordinal(as_of.toordinal() - args.lookback_days).isoformat()
    # yfinance treats `end` as exclusive, so ask for the day after `as_of`.
    end_date = date.fromordinal(as_of.toordinal() + 1).isoformat()

    print(f"downloading {len(tickers) + 1} series from yfinance ...")
    quotes = download_closes([*tickers, FX_SYMBOL], start_date, end_date)
    fx = quotes.pop(FX_SYMBOL)["close"].quantize(FX_DECIMALS)

    funds = load_funds(args)
    repriced = reprice(snapshot, quotes, fx, args.as_of, funds=funds)
    target = (
        Path(args.output)
        if args.output
        else source.with_name(f"portfolio-{args.as_of}.private.json")
    )
    target.write_text(json.dumps(repriced, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"repriced snapshot: {target}")
    print(f"  {FX_SYMBOL}: {fx}")
    for ticker, quote in sorted([*quotes.items(), *((f["ticker"], f) for f in funds.values())]):
        flag = "" if quote["date"] == args.as_of else "  <- 直近終値が基準日より前"
        print(f"  {ticker}: {quote['close']} ({quote['date']}){flag}")
    for account in repriced["accounts"]:
        print(f"  {account['id']}: {account['total_value_jpy']:,.0f} JPY")


if __name__ == "__main__":
    main()
