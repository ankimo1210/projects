"""Reprice a portfolio snapshot at current market closes.

The snapshot in ``data/portfolio.private.json`` records what the account
screens said on the day it was transcribed. This script does not edit it.
It reads that file, replaces the price of every position that carries a
quantity with the latest close at or before ``--as-of``, and writes a new
snapshot next to it.

Positions without a quantity (cash, the DC balance fund, the reconciliation
plug) have no market quote, so they are carried forward unchanged and the
reason is written into ``source_note``. Account totals are recomputed as the
sum of their positions, and any account P&L figure that the repricing
invalidates is dropped rather than carried forward as if it still held.

This is the second script that touches the network (``estimate_factors.py``
is the other one). ``build_dashboard.py`` stays offline and reads only the
files these two write.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

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


def download_closes(symbols: list[str], start: str, end: str) -> dict[str, Any]:
    """Return the last non-null close and its date for each symbol."""
    import warnings

    import pandas as pd
    import yfinance as yf

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
        if series.empty:
            raise RuntimeError(f"no usable close for {symbol}")
        out[symbol] = {
            "close": Decimal(str(series.iloc[-1])).quantize(PRICE_DECIMALS),
            "date": pd.Timestamp(series.index[-1]).date().isoformat(),
        }
    return out


def reprice(snapshot: dict[str, Any], quotes: dict[str, Any], fx: Decimal, as_of: str) -> dict:
    """Return a new snapshot priced at ``quotes``, leaving ``snapshot`` untouched."""
    positions: list[dict[str, Any]] = []
    repriced_accounts: set[str] = set()

    for row in snapshot["positions"]:
        new = dict(row)
        ticker = market_symbol(str(row["symbol"]), str(row["currency"]))
        if ticker is not None and row.get("quantity") is not None:
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
        if account_id in repriced_accounts:
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

    stale = {ticker: quote["date"] for ticker, quote in quotes.items() if quote["date"] != as_of}
    return {
        "snapshot_name": f"{as_of} 再評価スナップショット",
        "base_currency": snapshot.get("base_currency", "JPY"),
        "repricing": {
            "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "as_of": as_of,
            "source": "yfinance (close)",
            "fx_symbol": FX_SYMBOL,
            "fx_rate": float(fx),
            "quotes": {ticker: quote["date"] for ticker, quote in quotes.items()},
            "quotes_older_than_as_of": stale,
            "carried_forward": "現金・DC残高・残高調整は時価が取れないため元スナップショットのまま",
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
    return parser.parse_args()


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

    repriced = reprice(snapshot, quotes, fx, args.as_of)
    target = (
        Path(args.output)
        if args.output
        else source.with_name(f"portfolio-{args.as_of}.private.json")
    )
    target.write_text(json.dumps(repriced, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"repriced snapshot: {target}")
    print(f"  {FX_SYMBOL}: {fx}")
    for ticker, quote in sorted(quotes.items()):
        flag = "" if quote["date"] == args.as_of else "  <- 直近終値が基準日より前"
        print(f"  {ticker}: {quote['close']} ({quote['date']}){flag}")
    for account in repriced["accounts"]:
        print(f"  {account['id']}: {account['total_value_jpy']:,.0f} JPY")


if __name__ == "__main__":
    main()
