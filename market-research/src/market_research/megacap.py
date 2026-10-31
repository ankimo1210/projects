"""Explicit acquisition of a small, display-only Mag7 snapshot.

This is a present-day monitoring view, not a PIT dataset or a trading signal.
No function used to read a saved snapshot performs network access.
"""

from __future__ import annotations

import copy
import json
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from itertools import pairwise
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

COMPANIES = {
    "AAPL": ("Apple", "デバイス・サービス", "https://investor.apple.com/"),
    "MSFT": ("Microsoft", "クラウド・ソフトウェア", "https://www.microsoft.com/en-us/Investor/"),
    "GOOGL": ("Alphabet", "検索・クラウド", "https://abc.xyz/investor/"),
    "AMZN": ("Amazon", "コマース・クラウド", "https://ir.aboutamazon.com/"),
    "META": ("Meta", "広告・ソーシャル", "https://investor.atmeta.com/"),
    "NVDA": ("NVIDIA", "半導体・AI", "https://investor.nvidia.com/"),
    "TSLA": ("Tesla", "EV・エネルギー", "https://ir.tesla.com/"),
}

INCOME_FIELDS = {
    "revenue": ("Total Revenue",),
    "net_income": ("Net Income Common Stockholders", "Net Income"),
    "operating_income": ("Operating Income", "Total Operating Income As Reported"),
    "eps": ("Diluted EPS",),
}
BALANCE_FIELDS = {
    "cash": ("Cash Cash Equivalents And Short Term Investments",),
    "debt": ("Total Debt",),
    "equity": ("Stockholders Equity", "Common Stock Equity"),
    "assets": ("Total Assets",),
}
CASHFLOW_FIELDS = {
    "operating_cf": ("Operating Cash Flow",),
    "capex": ("Capital Expenditure",),
}


def _number(value):
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _ratio(numerator, denominator):
    numerator, denominator = _number(numerator), _number(denominator)
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return _number(numerator / denominator)


def _quarters(frame, fields):
    if frame is None or frame.empty:
        return []
    rows = []
    for column in sorted(frame.columns, reverse=True):
        row = {"end": pd.Timestamp(column).date().isoformat()}
        for field, alternatives in fields.items():
            row[field] = next(
                (
                    value
                    for label in alternatives
                    if label in frame.index
                    and (value := _number(frame.at[label, column])) is not None
                ),
                None,
            )
        if any(row[field] is not None for field in fields):
            rows.append(row)
    return rows[:8]


def _ttm(rows, field):
    window = rows[:4]
    if len(window) != 4 or any(row.get(field) is None for row in window):
        return None
    ends = [date.fromisoformat(row["end"]) for row in window]
    if any(not 60 <= (a - b).days <= 120 for a, b in pairwise(ends)):
        return None
    return _number(sum(row[field] for row in window))


def _iso_timestamp(value):
    value = _number(value)
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(value, UTC).isoformat()
    except (ValueError, OverflowError, OSError):
        return None


def build_company(*, symbol, info, history, income, balance, cashflow, calendar, fetched_at):
    """Normalize provider values; missing measurements stay None, never zero."""
    name, business, ir_url = COMPANIES[symbol]
    income_rows = _quarters(income, INCOME_FIELDS)
    balance_rows = _quarters(balance, BALANCE_FIELDS)
    cf_rows = _quarters(cashflow, CASHFLOW_FIELDS)
    for row in cf_rows:
        if row["capex"] is not None:
            row["capex"] = abs(row["capex"])
        row["fcf"] = (
            row["operating_cf"] - row["capex"]
            if row["operating_cf"] is not None and row["capex"] is not None
            else None
        )

    price = _number(info.get("regularMarketPrice"))
    if price is not None and price <= 0:
        price = None
    previous = _number(info.get("regularMarketPreviousClose"))
    eps, forward_eps, bps, cap = (
        _number(info.get(key)) for key in ("trailingEps", "forwardEps", "bookValue", "marketCap")
    )
    currency, financial_currency = info.get("currency"), info.get("financialCurrency")
    same_currency = bool(currency and financial_currency and currency == financial_currency)
    revenue, net_income, operating_income = (
        _ttm(income_rows, key) for key in ("revenue", "net_income", "operating_income")
    )
    operating_cf, capex, fcf = (_ttm(cf_rows, key) for key in ("operating_cf", "capex", "fcf"))
    bs = balance_rows[0] if balance_rows else dict.fromkeys(BALANCE_FIELDS)
    growth = None
    if income_rows:
        latest_end = date.fromisoformat(income_rows[0]["end"])
        prior = next(
            (
                row
                for row in income_rows[1:]
                if 350 <= (latest_end - date.fromisoformat(row["end"])).days <= 380
            ),
            None,
        )
        if (
            prior
            and (growth_ratio := _ratio(income_rows[0]["revenue"], prior["revenue"])) is not None
        ):
            growth = growth_ratio - 1

    metrics = {
        "market_cap": cap,
        "pe_ttm": _ratio(price, eps) if same_currency else None,
        "pe_forward": _ratio(price, forward_eps) if same_currency else None,
        "pb": _ratio(price, bps) if same_currency else None,
        "ps": _ratio(cap, revenue) if same_currency else None,
        "ev_ebitda": (
            _number(info.get("enterpriseToEbitda"))
            if same_currency and (_number(info.get("ebitda")) or 0) > 0
            else None
        ),
        "eps_ttm": eps,
        "eps_forward": forward_eps,
        "book_value_per_share": bps,
        "roe": _number(info.get("returnOnEquity")),
        "revenue_ttm": revenue,
        "net_income_ttm": net_income,
        "operating_income_ttm": operating_income,
        "net_margin": _ratio(net_income, revenue),
        "operating_margin": _ratio(operating_income, revenue),
        "operating_cf_ttm": operating_cf,
        "capex_ttm": capex,
        "fcf_ttm": fcf,
        "fcf_yield": _ratio(fcf, cap) if same_currency else None,
        "cash": bs["cash"],
        "debt": bs["debt"],
        "net_cash": (
            bs["cash"] - bs["debt"] if bs["cash"] is not None and bs["debt"] is not None else None
        ),
        "equity": bs["equity"],
        "equity_ratio": _ratio(bs["equity"], bs["assets"]),
        "debt_equity": _ratio(bs["debt"], bs["equity"]),
        "revenue_growth_yoy": growth,
    }
    prices = []
    if history is not None and not history.empty and "Close" in history:
        for index, row in history.sort_index().iterrows():
            close = _number(row["Close"])
            if close is not None and close > 0:
                prices.append({"date": pd.Timestamp(index).date().isoformat(), "close": close})
    today_ny = fetched_at.astimezone(ZoneInfo("America/New_York")).date()
    earnings_dates = []
    for value in calendar.get("Earnings Date", []):
        try:
            event_date = pd.Timestamp(value).date()
        except (TypeError, ValueError):
            continue
        if event_date >= today_ny:
            earnings_dates.append(event_date.isoformat())
    quality_errors = []
    if price is None or _iso_timestamp(info.get("regularMarketTime")) is None:
        quality_errors.append("株価または価格時点を取得できません")
    if not prices:
        quality_errors.append("株価履歴を取得できません")
    if revenue is None or net_income is None:
        quality_errors.append("損益TTMを算出できません（必要な4四半期に欠損）")
    if fcf is None:
        quality_errors.append("CF TTMを算出できません（必要な4四半期に欠損）")
    if any(bs[key] is None for key in BALANCE_FIELDS):
        quality_errors.append("貸借対照表の主要項目に欠損があります")
    if not same_currency:
        quality_errors.append("株価と財務の通貨が不明または異なるため一部倍率を算出できません")
    return {
        "symbol": symbol,
        "name": name,
        "business": business,
        "currency": currency,
        "financial_currency": financial_currency,
        "fetched_at": fetched_at.isoformat(),
        "fetch_status": "partial" if quality_errors else "ok",
        "errors": quality_errors,
        "quote": {
            "price": price,
            "previous_close": previous,
            "change_pct": (
                price / previous - 1 if price is not None and previous and previous > 0 else None
            ),
            "as_of": _iso_timestamp(info.get("regularMarketTime")),
            "exchange": "NASDAQ",
        },
        "metrics": metrics,
        "income_period_end": income_rows[0]["end"] if income_rows else None,
        "balance_period_end": balance_rows[0]["end"] if balance_rows else None,
        "cashflow_period_end": cf_rows[0]["end"] if cf_rows else None,
        "income_quarters": income_rows,
        "balance_quarters": balance_rows,
        "cashflow_quarters": cf_rows,
        "prices": prices,
        "earnings": {
            "dates": sorted(set(earnings_dates)),
            "eps_estimate": _number(calendar.get("Earnings Average")),
            "revenue_estimate": _number(calendar.get("Revenue Average")),
            "status": "provider_schedule_unconfirmed",
        },
        "sources": {
            "quote": f"https://finance.yahoo.com/quote/{symbol}/",
            "statistics": f"https://finance.yahoo.com/quote/{symbol}/key-statistics/",
            "income": f"https://finance.yahoo.com/quote/{symbol}/financials/",
            "balance": f"https://finance.yahoo.com/quote/{symbol}/balance-sheet/",
            "cashflow": f"https://finance.yahoo.com/quote/{symbol}/cash-flow/",
            "ir": ir_url,
        },
    }


def _fetch_company(symbol):
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    errors = []

    def obtain(label, operation, fallback):
        try:
            value = operation()
            if (
                value is None
                or (hasattr(value, "empty") and value.empty)
                or (isinstance(value, dict) and not value)
            ):
                errors.append(label)
                return fallback
            return value
        except Exception:
            # Provider exceptions may contain URLs or user-agent details.
            errors.append(label)
            return fallback

    info = obtain("基本情報", ticker.get_info, {})
    history = obtain(
        "株価履歴",
        lambda: ticker.history(
            period="1y",
            interval="1d",
            auto_adjust=False,
            back_adjust=False,
            actions=False,
            repair=False,
            raise_errors=True,
            timeout=15,
        ),
        pd.DataFrame(),
    )
    income = obtain("損益計算書", lambda: ticker.quarterly_income_stmt, pd.DataFrame())
    balance = obtain("貸借対照表", lambda: ticker.quarterly_balance_sheet, pd.DataFrame())
    cashflow = obtain("キャッシュフロー", lambda: ticker.quarterly_cashflow, pd.DataFrame())
    calendar = obtain("決算予定", lambda: ticker.calendar, {})
    company = build_company(
        symbol=symbol,
        info=info,
        history=history,
        income=income,
        balance=balance,
        cashflow=cashflow,
        calendar=calendar,
        fetched_at=datetime.now(UTC),
    )
    # yfinance can return a truthy info dictionary containing only a null
    # trailingPegRatio even when every endpoint failed. Keep the prior snapshot
    # unless normalization actually yielded an observable financial value.
    if (
        company["quote"]["price"] is None
        and not company["prices"]
        and not company["income_quarters"]
        and not company["balance_quarters"]
        and not company["cashflow_quarters"]
        and not any(value is not None for value in company["metrics"].values())
    ):
        raise RuntimeError("all_provider_sections_unavailable")
    company["errors"].extend(f"{label}を取得できませんでした" for label in errors)
    if company["errors"]:
        company["fetch_status"] = "partial"
    return company


def collect_snapshot(previous=None):
    """Fetch seven issuers; keep old observations honestly labeled on failure."""
    old = {row["symbol"]: row for row in (previous or {}).get("companies", [])}

    def one(symbol):
        try:
            return _fetch_company(symbol)
        except Exception:
            if symbol in old:
                company = copy.deepcopy(old[symbol])
                company["fetch_status"] = "stale"
                company["errors"] = ["更新に失敗しました。以前の取得データを表示しています"]
                return company
            company = build_company(
                symbol=symbol,
                info={},
                history=pd.DataFrame(),
                income=pd.DataFrame(),
                balance=pd.DataFrame(),
                cashflow=pd.DataFrame(),
                calendar={},
                fetched_at=datetime.now(UTC),
            )
            company["fetched_at"] = None
            company["fetch_status"] = "unavailable"
            company["errors"] = ["データを取得できませんでした"]
            return company

    with ThreadPoolExecutor(max_workers=3) as pool:
        companies = list(pool.map(one, COMPANIES))
    return {
        "schema_version": 1,
        "attempted_at": datetime.now(UTC).isoformat(),
        "provider": "Yahoo Finance via yfinance",
        "companies": companies,
    }


def load_snapshot(path):
    path = Path(path)
    if not path.exists():
        return {"schema_version": 1, "attempted_at": None, "companies": []}
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    if snapshot.get("schema_version") != 1 or not isinstance(snapshot.get("companies"), list):
        raise ValueError("unsupported tracker snapshot")
    return snapshot


def save_snapshot(snapshot, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(snapshot, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    temporary = path.with_suffix(".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)
