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

NEW_YORK = ZoneInfo("America/New_York")
TOKYO = ZoneInfo("Asia/Tokyo")

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
# A quarter counts toward TTM only when all of these are present. Yahoo often lists a
# new quarter with Diluted EPS alone for weeks after the release.
INCOME_TTM_FIELDS = ("revenue", "net_income", "operating_income")
BALANCE_FIELDS = {
    "cash": ("Cash Cash Equivalents And Short Term Investments",),
    # Yahoo's Total Debt includes capital (finance) lease obligations.
    "debt": ("Total Debt",),
    "equity": ("Stockholders Equity", "Common Stock Equity"),
    "assets": ("Total Assets",),
    "leases": ("Capital Lease Obligations",),
}
BALANCE_REQUIRED = ("cash", "debt", "equity", "assets")
CASHFLOW_FIELDS = {
    "operating_cf": ("Operating Cash Flow",),
    "capex": ("Capital Expenditure",),
}
CASHFLOW_TTM_FIELDS = ("operating_cf", "capex")
# Provider quote/statistics values kept in the snapshot so that a later failed quote
# request can reuse them with their original acquisition time.
INFO_FIELDS = (
    "currency",
    "financialCurrency",
    "regularMarketPrice",
    "regularMarketPreviousClose",
    "regularMarketTime",
    "trailingEps",
    "forwardEps",
    "bookValue",
    "marketCap",
    "enterpriseToEbitda",
    "ebitda",
    "returnOnEquity",
    "mostRecentQuarter",
    "nextFiscalYearEnd",
    "earningsTimestamp",
    "earningsTimestampStart",
    "earningsTimestampEnd",
    "isEarningsDateEstimate",
)
BASIS_LABELS = {
    "eps": "EPS",
    "provider": "BPS等",
    "income_ttm": "損益TTM",
    "cashflow_ttm": "CF TTM",
    "balance": "BS",
}
SAME_QUARTER_DAYS = 20  # Apple/NVIDIA fiscal quarters end on a weekday near month-end.
SHARE_GAP_LIMIT = 0.05
STALE_MESSAGE = "更新に失敗しました。以前の取得データを表示しています"
FALLBACK_SECTIONS = {
    "基本情報": ("info", "provider_info"),
    "株価履歴": ("history", "prices"),
    "損益計算書": ("income", "income_quarters"),
    "貸借対照表": ("balance", "balance_quarters"),
    "キャッシュフロー": ("cashflow", "cashflow_quarters"),
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
    if isinstance(frame, list):  # rows saved by a previous snapshot (section fallback)
        rows = [{"end": row["end"], **{f: _number(row.get(f)) for f in fields}} for row in frame]
        return [row for row in rows if any(row[f] is not None for f in fields)][:8]
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


def _complete(row, fields):
    return all(row.get(field) is not None for field in fields)


def _consecutive(window):
    ends = [date.fromisoformat(row["end"]) for row in window]
    return all(60 <= (a - b).days <= 120 for a, b in pairwise(ends))


def _windows(rows, fields):
    """Four consecutive quarters with every field present, newest first."""
    for start in range(len(rows) - 3):
        window = rows[start : start + 4]
        if all(_complete(row, fields) for row in window) and _consecutive(window):
            yield window


def _ttm(window, field):
    return _number(sum(row[field] for row in window)) if window else None


def _moment(value):
    value = _number(value)
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(value, UTC)
    except (ValueError, OverflowError, OSError):
        return None


def _iso_timestamp(value):
    moment = _moment(value)
    return moment.isoformat() if moment else None


def _iso_date(value):
    moment = _moment(value)
    return moment.date().isoformat() if moment else None


def _snap(day, ends):
    """Map a provider quarter date (e.g. Apple's last Saturday) onto the statement end."""
    if day is None:
        return None
    target = date.fromisoformat(day)
    near = [e for e in ends if abs((date.fromisoformat(e) - target).days) <= SAME_QUARTER_DAYS]
    return min(near, key=lambda e: abs((date.fromisoformat(e) - target).days)) if near else day


def _eps_check(rows, eps, provider_quarter):
    """Basis quarter of the provider's TTM EPS, proven by four reported quarterly EPS.

    Returns (basis, verified, latest) where latest is (end, sum) of the newest EPS window.
    """
    sums = [(w[0]["end"], sum(row["eps"] for row in w)) for w in _windows(rows, ("eps",))]
    matches = [
        end
        for end, total in sums
        if eps is not None and abs(total - eps) <= max(0.015 * abs(eps), 0.02)
    ]
    if not matches:
        return provider_quarter, False, sums[0] if sums else None
    return (provider_quarter if provider_quarter in matches else matches[0]), True, sums[0]


def _forward_eps(info, estimates):
    """Which consensus fiscal year Yahoo's forwardEps refers to (fiscal years differ).

    forwardEps can lag the year-by-year consensus by a few percent after a release, so the
    nearest year is accepted when it is within 10% and clearly nearer than the other.
    """
    values = {}
    if estimates is not None and not estimates.empty and "avg" in estimates.columns:
        for period in ("0y", "+1y"):
            if period in estimates.index:
                values[period] = _number(estimates.at[period, "avg"])
    result = {"fiscal_year_end": None, "period": None, "gap": None, "estimates": values}
    forward, fiscal_end = _number(info.get("forwardEps")), _iso_date(info.get("nextFiscalYearEnd"))
    if forward is None or fiscal_end is None:
        return result
    gaps = sorted(
        (abs(forward / average - 1), period)
        for period, average in values.items()
        if average is not None and average > 0
    )
    if not gaps:
        return result
    (best, period), others = gaps[0], gaps[1:]
    if best <= 0.01 or (best <= 0.10 and (not others or others[0][0] >= 3 * best)):
        offset = 0 if period == "0y" else 1
        result.update(
            fiscal_year_end=f"{int(fiscal_end[:4]) + offset}-{fiscal_end[5:7]}",
            period=period,
            gap=forward / values[period] - 1,
        )
    return result


# Yahoo stores after-close releases at 20:00:00 UTC all year (seen for all seven on
# 2026-10-31): 16:00 EDT but 15:00 EST, so the session is read from the UTC value.
AFTER_CLOSE_UTC = (20, 0)


def _session(moment, local):
    if (moment.hour, moment.minute) == AFTER_CLOSE_UTC:
        return "after_close"
    minutes = local.hour * 60 + local.minute
    if minutes < 9 * 60 + 30:
        return "before_open"
    return "after_close" if minutes >= 16 * 60 else "during_market"


def _event(moment, estimate, end=None):
    event = dict.fromkeys(
        ("timestamp", "date_et", "time_et", "session", "window_end", "end_date_et")
    )
    event["is_estimate"] = estimate
    if moment is None:
        return event
    # An estimate stored at 00:00 UTC encodes a calendar date, not an instant; an
    # on-the-hour value is a session placeholder, not the release clock time.
    date_only = estimate is not False and (moment.hour, moment.minute) == (0, 0)
    placeholder = date_only or (moment.minute, moment.second) == (0, 0)
    local = moment.astimezone(NEW_YORK)
    event.update(
        timestamp=moment.isoformat(),
        date_et=(moment if date_only else local).date().isoformat(),
        time_et=None if placeholder else local.strftime("%H:%M"),
        session=_session(moment, local) if estimate is False and not date_only else None,
    )
    if end is not None and end > moment:
        end_day = end if date_only else end.astimezone(NEW_YORK)
        event.update(window_end=end.isoformat(), end_date_et=end_day.date().isoformat())
    return event


def _earnings(info, calendar):
    """Provider earnings events in New York time.

    yfinance's ``calendar`` converts timestamps with the machine's local zone, so on a JST
    machine every after-close release comes back one day late. Only the quote timestamps
    are used for the schedule; calendar supplies the consensus estimates. Start/End hold
    the next event; earningsTimestamp can still point at the last release.
    """
    stamp = _moment(info.get("earningsTimestamp"))
    start = _moment(info.get("earningsTimestampStart"))
    end = _moment(info.get("earningsTimestampEnd"))
    estimate = info.get("isEarningsDateEstimate")
    estimate = estimate if isinstance(estimate, bool) else None
    previous = _event(stamp, False) if stamp and start and stamp < start else None
    return {
        **_event(start or stamp, estimate, end),
        "previous": previous,
        "eps_estimate": _number(calendar.get("Earnings Average")),
        "revenue_estimate": _number(calendar.get("Revenue Average")),
        "source": "Yahoo Finance earningsTimestamp (America/New_York)",
    }


def _provider_info(info):
    kept = {}
    for key in INFO_FIELDS:
        value = info.get(key)
        if isinstance(value, bool) or (isinstance(value, str) and value):
            kept[key] = value
        elif (number := _number(value)) is not None:
            kept[key] = number
    return kept


def _jst(iso):
    return datetime.fromisoformat(iso).astimezone(TOKYO).strftime("%Y-%m-%d %H:%M JST")


def build_company(
    *, symbol, info, history, income, balance, cashflow, calendar, fetched_at, estimates=None
):
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
    # TTM = the latest four consecutive *complete* quarters; newer partial rows are skipped
    # and reported, so a quarter with only EPS no longer blanks every income metric.
    income_window = next(_windows(income_rows, INCOME_TTM_FIELDS), None)
    cf_window = next(_windows(cf_rows, CASHFLOW_TTM_FIELDS), None)
    revenue, net_income, operating_income = (_ttm(income_window, key) for key in INCOME_TTM_FIELDS)
    operating_cf, capex, fcf = (_ttm(cf_window, key) for key in ("operating_cf", "capex", "fcf"))
    income_complete = [row for row in income_rows if _complete(row, INCOME_TTM_FIELDS)]
    cf_complete = [row for row in cf_rows if _complete(row, CASHFLOW_TTM_FIELDS)]
    income_end = (income_window or income_complete or [{"end": None}])[0]["end"]
    cf_end = (cf_window or cf_complete or [{"end": None}])[0]["end"]
    bs = next(
        (row for row in balance_rows if _complete(row, BALANCE_REQUIRED)),
        balance_rows[0] if balance_rows else {"end": None, **dict.fromkeys(BALANCE_FIELDS)},
    )
    partial = {
        key: [row["end"] for row in rows if end is not None and row["end"] > end]
        for key, rows, end in (
            ("income", income_rows, income_end),
            ("cashflow", cf_rows, cf_end),
            ("balance", balance_rows, bs["end"]),
        )
    }
    growth = None
    if income_complete:
        latest_end = date.fromisoformat(income_complete[0]["end"])
        prior = next(
            (
                row
                for row in income_rows
                if 350 <= (latest_end - date.fromisoformat(row["end"])).days <= 380
            ),
            None,
        )
        if (
            prior
            and (growth_ratio := _ratio(income_complete[0]["revenue"], prior["revenue"]))
            is not None
        ):
            growth = growth_ratio - 1
    statement_ends = {row["end"] for row in income_rows + balance_rows + cf_rows}
    provider_quarter = _snap(_iso_date(info.get("mostRecentQuarter")), statement_ends)
    eps_basis, eps_verified, eps_latest = _eps_check(income_rows, eps, provider_quarter)
    basis = {
        "eps": eps_basis,
        "provider": provider_quarter,
        "income_ttm": income_window[0]["end"] if income_window else None,
        "cashflow_ttm": cf_window[0]["end"] if cf_window else None,
        "balance": bs["end"],
    }
    metric_basis = {
        **dict.fromkeys(("pe_ttm", "eps_ttm"), basis["eps"]),
        **dict.fromkeys(("pb", "book_value_per_share", "ev_ebitda", "roe"), provider_quarter),
        **dict.fromkeys(
            (
                "ps",
                "revenue_ttm",
                "net_income_ttm",
                "operating_income_ttm",
                "net_margin",
                "operating_margin",
            ),
            basis["income_ttm"],
        ),
        **dict.fromkeys(
            ("operating_cf_ttm", "capex_ttm", "fcf_ttm", "fcf_yield"), basis["cashflow_ttm"]
        ),
        **dict.fromkeys(
            (
                "cash",
                "debt",
                "lease_obligations",
                "net_cash",
                "equity",
                "equity_ratio",
                "debt_equity",
            ),
            bs["end"],
        ),
    }
    flags = {
        "net_income_exceeds_operating": (
            net_income is not None
            and operating_income is not None
            and net_income > operating_income
        ),
        "eps_verified": eps_verified,
        # Provider TTM EPS disagrees with the sum of the reported quarterly diluted EPS.
        "eps_mismatch": eps is not None and not eps_verified and eps_latest is not None,
        "share_count_gap": None,
    }
    # Shares implied by EPS are only meaningful when the EPS basis is proven to be the
    # same four quarters as net income TTM.
    if (
        eps_verified
        and basis["eps"] == basis["income_ttm"]
        and (eps or 0) > 0
        and (net_income or 0) > 0
        and price is not None
        and cap is not None
    ):
        flags["share_count_gap"] = _number((cap / price) / (net_income / eps) - 1)
    notes = []
    groups = {}
    for key, label in BASIS_LABELS.items():
        if basis[key]:
            groups.setdefault(basis[key], []).append(label)
    if len(groups) > 1:
        notes.append(
            "指標の基準期末が異なります: "
            + " / ".join(
                f"{'・'.join(labels)} {day}" for day, labels in sorted(groups.items())[::-1]
            )
        )
    if flags["eps_mismatch"]:
        notes.append(
            f"提供元のTTM EPS {eps:.2f} が四半期EPSの合計"
            f"（{eps_latest[0]}期まで {eps_latest[1]:.2f}）と一致しません"
        )
    if flags["net_income_exceeds_operating"]:
        notes.append(
            "純利益TTMが営業利益TTMを上回ります。投資評価益など営業外損益がPER (TTM)を押し下げています"
        )
    if flags["share_count_gap"] is not None and abs(flags["share_count_gap"]) > SHARE_GAP_LIMIT:
        notes.append(
            f"時価総額の株数がEPSの株数と{flags['share_count_gap']:+.1%}異なります"
            "（PSR・FCF利回りとPERで株数の基準が違う）"
        )

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
        "lease_obligations": bs.get("leases"),
        "net_cash": (
            bs["cash"] - bs["debt"] if bs["cash"] is not None and bs["debt"] is not None else None
        ),
        "equity": bs["equity"],
        "equity_ratio": _ratio(bs["equity"], bs["assets"]),
        "debt_equity": _ratio(bs["debt"], bs["equity"]),
        "revenue_growth_yoy": growth,
    }
    prices = []
    if isinstance(history, list):  # saved rows from a previous snapshot
        prices = [
            {"date": row["date"], "close": close}
            for row in history
            if (close := _number(row.get("close"))) is not None and close > 0
        ]
    elif history is not None and not history.empty and "Close" in history:
        for index, row in history.sort_index().iterrows():
            close = _number(row["Close"])
            if close is not None and close > 0:
                prices.append({"date": pd.Timestamp(index).date().isoformat(), "close": close})
    quality_errors = []
    if price is None or _iso_timestamp(info.get("regularMarketTime")) is None:
        quality_errors.append("株価または価格時点を取得できません")
    if not prices:
        quality_errors.append("株価履歴を取得できません")
    if revenue is None or net_income is None:
        quality_errors.append("損益TTMを算出できません（連続する完全な4四半期がありません）")
    elif partial["income"]:
        quality_errors.append(
            f"損益: {'・'.join(partial['income'])}期は提供元で一部項目のみのため、"
            f"TTMは{income_end}期までの4四半期"
        )
    if fcf is None:
        quality_errors.append("CF TTMを算出できません（連続する完全な4四半期がありません）")
    elif partial["cashflow"]:
        quality_errors.append(
            f"CF: {'・'.join(partial['cashflow'])}期は提供元で一部項目のみのため、"
            f"TTMは{cf_end}期までの4四半期"
        )
    if any(bs[key] is None for key in BALANCE_REQUIRED):
        quality_errors.append("貸借対照表の主要項目に欠損があります")
    elif partial["balance"]:
        quality_errors.append(
            f"貸借対照表: {'・'.join(partial['balance'])}期は提供元で一部項目のみのため、"
            f"{bs['end']}期末の値を表示"
        )
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
        # Period ends of the values shown (TTM window end / balance sheet used).
        "income_period_end": income_end,
        "balance_period_end": bs["end"],
        "cashflow_period_end": cf_end,
        "partial_quarters": partial,
        "basis": basis,
        "metric_basis": metric_basis,
        "forward_eps": _forward_eps(info, estimates),
        "flags": flags,
        "notes": notes,
        "section_fetched_at": {},
        "provider_info": _provider_info(info),
        "income_quarters": income_rows,
        "balance_quarters": balance_rows,
        "cashflow_quarters": cf_rows,
        "prices": prices,
        "earnings": _earnings(info, calendar),
        "sources": {
            "quote": f"https://finance.yahoo.com/quote/{symbol}/",
            "statistics": f"https://finance.yahoo.com/quote/{symbol}/key-statistics/",
            "income": f"https://finance.yahoo.com/quote/{symbol}/financials/",
            "balance": f"https://finance.yahoo.com/quote/{symbol}/balance-sheet/",
            "cashflow": f"https://finance.yahoo.com/quote/{symbol}/cash-flow/",
            "ir": ir_url,
        },
    }


def _fetch_company(symbol, previous=None):
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
    sources = {
        "info": info,
        "history": history,
        "income": obtain("損益計算書", lambda: ticker.quarterly_income_stmt, pd.DataFrame()),
        "balance": obtain("貸借対照表", lambda: ticker.quarterly_balance_sheet, pd.DataFrame()),
        "cashflow": obtain("キャッシュフロー", lambda: ticker.quarterly_cashflow, pd.DataFrame()),
        "calendar": obtain("決算予定", lambda: ticker.calendar, {}),
    }
    try:  # Optional: only labels which fiscal year forwardEps refers to.
        estimates = ticker.earnings_estimate
    except Exception:
        estimates = None
    fetched_at = datetime.now(UTC)
    company = build_company(symbol=symbol, **sources, estimates=estimates, fetched_at=fetched_at)
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
    # A section that failed alone (e.g. a rate-limited quote request) reuses the previous
    # snapshot's values for that section, labeled with their original acquisition time.
    missing = {
        "基本情報": company["quote"]["price"] is None,
        "株価履歴": not company["prices"],
        "損益計算書": not company["income_quarters"],
        "貸借対照表": not company["balance_quarters"],
        "キャッシュフロー": not company["cashflow_quarters"],
    }
    reused = {}
    for label, (source, field) in FALLBACK_SECTIONS.items():
        if missing[label] and previous and previous.get("fetched_at") and previous.get(field):
            sources[source] = previous[field]
            reused[label] = (previous.get("section_fetched_at") or {}).get(
                label, previous["fetched_at"]
            )
    if reused:
        company = build_company(
            symbol=symbol, **sources, estimates=estimates, fetched_at=fetched_at
        )
    company["section_fetched_at"] = reused
    for label in dict.fromkeys([*errors, *reused]):
        company["errors"].append(
            f"{label}を取得できませんでした。{_jst(reused[label])}取得の前回値を表示しています"
            if label in reused
            else f"{label}を取得できませんでした"
        )
    if company["errors"]:
        company["fetch_status"] = "partial"
    return company


def collect_snapshot(previous=None):
    """Fetch seven issuers; keep old observations honestly labeled on failure."""
    old = {row["symbol"]: row for row in (previous or {}).get("companies", [])}

    def one(symbol):
        try:
            return _fetch_company(symbol, old.get(symbol))
        except Exception:
            if symbol in old:
                company = copy.deepcopy(old[symbol])
                company["fetch_status"] = "stale"
                kept = [m for m in company.get("errors", []) if m != STALE_MESSAGE]
                company["errors"] = [STALE_MESSAGE, *kept]
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
