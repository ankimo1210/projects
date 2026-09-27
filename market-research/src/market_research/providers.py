"""Explicit daily-price acquisition; original source series never fall back silently."""

from __future__ import annotations

import io
import json
import os
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, time, timedelta

import pandas as pd

from .calendars import SessionCalendar, daily_timings
from .contracts import Instrument, PriceBar, _utc
from .fetch import FetchError, HttpClient
from .prices import normalize_yfinance

ADJUSTMENTS = {
    "yfinance": {"raw", "unknown"},
    "stooq": {"unknown"},
    "jquants": {"raw", "split"},
    "binance": {"raw"},
}


@dataclass(frozen=True, slots=True)
class PriceRequest:
    instrument: Instrument
    provider_symbol: str
    start: date
    end: date
    adjustment: str = "raw"

    def __post_init__(self):
        if (
            not self.provider_symbol.strip()
            or type(self.start) is not date
            or type(self.end) is not date
            or self.start > self.end
        ):
            raise ValueError("symbol and ordered date range are required")


@dataclass(frozen=True, slots=True)
class PriceBatch:
    raw: bytes
    bars: tuple[PriceBar, ...]
    observed_at: datetime
    calendar_hash: str
    complete: bool = True


def _history(symbol, start, end):
    import yfinance as yf

    result = None
    try:
        result = yf.Ticker(symbol).history(
            start=start.isoformat(),
            end=end.isoformat(),
            interval="1d",
            auto_adjust=False,
            back_adjust=False,
            actions=False,
            repair=False,
            raise_errors=True,
            timeout=10,
        )
    except Exception:
        pass
    if result is None:
        raise FetchError("yfinance_unavailable")
    return result


def _envelope(pages, cursor):
    return json.dumps({"pages": pages, "next_cursor": cursor}, sort_keys=True).encode()


def _jquants(request, client, resume_raw):
    token = os.environ.get("JQUANTS_API_KEY")
    if not token:
        raise FetchError("missing_credentials")
    if request.instrument.market != "XTKS" or request.instrument.currency != "JPY":
        raise FetchError("instrument")
    pages, cursor = [], None
    if resume_raw:
        saved = json.loads(resume_raw)
        pages, cursor = saved["pages"], saved["next_cursor"]
        if not cursor:
            raise FetchError("resume_cursor")
    seen = {cursor} if cursor else set()
    for _ in range(50):
        params = {
            "code": request.provider_symbol,
            "from": request.start.isoformat(),
            "to": request.end.isoformat(),
        }
        if cursor:
            params["pagination_key"] = cursor
        failure = None
        try:
            raw = client.get(
                "https://api.jquants.com/v2/equities/bars/daily",
                params=params,
                headers={"x-api-key": token},
            )
        except FetchError as error:
            failure = (error.category, error.status)
        if failure:
            raise FetchError(
                failure[0],
                status=failure[1],
                partial_raw=_envelope(pages, cursor) if pages else None,
                cursor=cursor,
            )
        payload = json.loads(raw)
        if not isinstance(payload.get("data"), list):
            raise FetchError("schema")
        next_cursor = payload.get("pagination_key")
        if next_cursor and (not isinstance(next_cursor, str) or next_cursor in seen):
            raise FetchError("pagination", partial_raw=_envelope(pages, cursor), cursor=cursor)
        pages.append(raw.decode("utf-8"))
        if not next_cursor:
            rows = [row for page in pages for row in json.loads(page)["data"]]
            code = request.provider_symbol.upper()
            expected = code + "0" if len(code) == 4 else code
            if any(str(row["Code"]).upper() != expected for row in rows):
                raise FetchError("provider_symbol")
            selected = {"O": "Open", "H": "High", "L": "Low", "C": "Close", "Vo": "Volume"}
            if request.adjustment == "split":
                selected = {"Adj" + key: value for key, value in selected.items()}
            frame = pd.DataFrame(rows)
            if frame.empty:
                raise FetchError("empty")
            frame = frame.set_index("Date").rename(columns=selected)
            # Keep only the selected adjustment basis; raw and adjusted OHLC never mix.
            return frame[[column for column in selected.values() if column in frame]], _envelope(
                pages, None
            )
        seen.add(next_cursor)
        cursor = next_cursor
    raise FetchError("pagination", partial_raw=_envelope(pages, cursor), cursor=cursor)


def _binance(request, client):
    if request.instrument.market != "CRYPTO" or not request.provider_symbol.upper().endswith(
        request.instrument.currency
    ):
        raise FetchError("instrument")
    start = int(datetime.combine(request.start, time(), UTC).timestamp() * 1000)
    end = int(datetime.combine(request.end + timedelta(days=1), time(), UTC).timestamp() * 1000) - 1
    rows, pages = [], []
    for _ in range(50):
        raw = client.get(
            "https://api.binance.com/api/v3/klines",
            params={
                "symbol": request.provider_symbol,
                "interval": "1d",
                "startTime": start,
                "endTime": end,
                "limit": 1000,
            },
        )
        page = json.loads(raw)
        if not isinstance(page, list):
            raise FetchError("schema")
        pages.append(raw.decode("utf-8"))
        if any(
            not isinstance(row, list)
            or len(row) < 7
            or int(row[0]) < start
            or int(row[6]) + 1 != int(row[0]) + 86400000
            for row in page
        ):
            raise FetchError("schema")
        rows.extend(page)
        if len(page) < 1000 or int(page[-1][6]) >= end:
            break
        start = int(page[-1][6]) + 1
    else:
        raise FetchError("pagination")
    frame = pd.DataFrame(
        [
            {
                "Date": pd.to_datetime(row[0], unit="ms", utc=True),
                "Open": row[1],
                "High": row[2],
                "Low": row[3],
                "Close": row[4],
                "Volume": row[5],
            }
            for row in rows
        ]
    )
    if frame.empty:
        raise FetchError("empty")
    return frame.set_index("Date"), _envelope(pages, None)


def fetch_prices(
    provider: str,
    request: PriceRequest,
    *,
    calendar: SessionCalendar | None = None,
    client: HttpClient | None = None,
    now=lambda: datetime.now(UTC),
    history=None,
    resume_raw: bytes | None = None,
) -> PriceBatch:
    if provider not in ADJUSTMENTS or request.adjustment not in ADJUSTMENTS[provider]:
        raise FetchError("adjustment")
    client = client or HttpClient()
    failed = False
    try:
        if provider == "yfinance":
            frame = (history or _history)(
                request.provider_symbol, request.start, request.end + timedelta(days=1)
            )
            raw = json.dumps(
                frame.astype(object).where(pd.notna(frame), None).to_dict(orient="split"),
                default=lambda value: value.isoformat(),
                allow_nan=False,
            ).encode()
        elif provider == "stooq":
            raw = client.get(
                "https://stooq.com/q/d/l/",
                params={
                    "s": request.provider_symbol,
                    "d1": request.start.strftime("%Y%m%d"),
                    "d2": request.end.strftime("%Y%m%d"),
                    "i": "d",
                },
                headers={"User-Agent": "market-research/0.1"},
            )
            if raw.lstrip().lower().startswith((b"<!doctype html", b"<html")):
                raise FetchError("provider_challenge")
            frame = pd.read_csv(io.BytesIO(raw)).set_index("Date")
        elif provider == "jquants":
            frame, raw = _jquants(request, client, resume_raw)
        else:
            frame, raw = _binance(request, client)
        observed = _utc(now(), "observed_at")
        frame = frame.copy()
        frame.index = pd.DatetimeIndex(frame.index)
        if frame.index.tz is None:
            frame.index = frame.index.tz_localize(request.instrument.timezone)
        if any(
            not request.start <= label.tz_convert(request.instrument.timezone).date() <= request.end
            for label in frame.index
        ):
            raise FetchError("coverage")
        timings = daily_timings(frame.index, request.instrument, observed, calendar=calendar)
        rows = normalize_yfinance(
            frame,
            request.instrument,
            observed,
            expected_provider_symbol=request.provider_symbol,
            bar_timing=timings,
        )
        if provider == "yfinance":
            bars = tuple(row for row in rows if row.adjustment == request.adjustment)
        else:
            bars = tuple(
                replace(
                    row,
                    provider=provider,
                    adjustment=request.adjustment,
                    revision_id=f"{provider}:{observed.isoformat()}",
                )
                for row in rows
                if row.adjustment == "raw"
            )
        if not bars:
            raise FetchError("empty")
        unit = (
            "base_asset"
            if request.instrument.market == "CRYPTO"
            else "source_units"
            if request.instrument.market == "FX"
            else "shares"
        )
        bars = tuple(
            replace(
                row,
                volume_unit=unit,
                quality="warn" if request.instrument.market == "FX" else row.quality,
                quality_reasons=("live_quote",)
                if request.instrument.market == "FX"
                else row.quality_reasons,
            )
            for row in bars
        )
        return PriceBatch(raw, bars, observed, calendar.digest if calendar else "crypto-utc-v1")
    except (ValueError, TypeError, KeyError, IndexError, AttributeError):
        failed = True
    if failed:
        raise FetchError("schema_or_calendar")
    raise AssertionError("unreachable provider state")
