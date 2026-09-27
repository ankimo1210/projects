"""Local command-line entry point."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from .alfred import AlfredRequest, ingest_alfred
from .calendars import SessionCalendar
from .contracts import Instrument
from .esri import (
    CALENDAR_KEY,
    EsriGdpRequest,
    ingest_esri_calendar,
    ingest_esri_gdp,
    releases_from_snapshot,
)
from .estat import EstatRequest, ingest_estat
from .fetch import FetchError
from .ingestion import ingest_prices
from .mof import MoFRequest, ingest_mof_jgb
from .prices import PriceView
from .providers import ADJUSTMENTS, PriceRequest
from .sec import SecRequest, ingest_sec_companyfacts
from .services import build_demo_run
from .storage import ResearchStore, Snapshot


def _summary(snapshot: Snapshot) -> dict:
    return {
        "snapshot_id": snapshot.snapshot_id,
        "key": asdict(snapshot.key),
        "observed_at": snapshot.observed_at.isoformat(),
        "raw_hash": snapshot.raw_hash,
        "complete": snapshot.complete,
        "stale": snapshot.stale,
    }


def _view(snapshot: Snapshot, view: PriceView, *, error: str | None = None) -> dict:
    return {
        **_summary(snapshot),
        "bars": [asdict(bar) for bar in view.bars],
        "excluded": [asdict(item) for item in view.exclusions],
        "gaps": [asdict(gap) for gap in view.gaps],
        "excluded_count": len(view.exclusions) + len(view.gaps),
        "error": error,
    }


def _row_view(snapshot: Snapshot, rows: tuple, *, error: str | None = None) -> dict:
    return {**_summary(snapshot), "rows": [asdict(row) for row in rows], "error": error}


def _required(args, *names):
    if any(getattr(args, name) is None for name in names):
        raise ValueError("required provider argument is missing")


def _classes(values: list[str]) -> tuple[tuple[str, str], ...]:
    pairs = []
    for value in values:
        name, divider, code = value.partition("=")
        if not divider or not name or not code:
            raise ValueError("classification must be name=code")
        pairs.append((name, code))
    return tuple(pairs)


def _macro_request(args):
    if args.provider == "alfred":
        _required(args, "series_id", "start", "end", "unit", "frequency", "seasonal_adjustment")
        return AlfredRequest(
            args.series_id,
            args.indicator or args.series_id,
            args.start,
            args.end,
            args.unit,
            args.frequency,
            args.seasonal_adjustment,
            args.realtime_start or date(1776, 7, 4),
            args.realtime_end or date(9999, 12, 31),
        )
    if args.provider == "esri-gdp":
        _required(args, "period_start", "release_kind", "calendar_snapshot_id")
        return EsriGdpRequest(
            args.period_start,
            args.release_kind,
            indicator=args.indicator or "JP_REAL_GDP_QOQ_SAAR",
            column=args.column or "国内総生産(支出側)",
            menu_override=args.menu_url,
        )
    if args.provider == "mof-jgb":
        _required(args, "tenor_years")
        return MoFRequest(args.tenor_years, args.start, args.end)
    if args.provider == "estat":
        _required(args, "stats_data_id", "indicator", "unit", "frequency")
        return EstatRequest(
            args.stats_data_id,
            args.indicator,
            args.unit,
            args.frequency,
            _classes(args.classifications),
        )
    return None


def _fetch_macro(store: ResearchStore, args) -> dict:
    request = _macro_request(args)
    if args.provider == "alfred":
        result = ingest_alfred(store, request, resume=args.resume, allow_stale=args.allow_stale)
        return _row_view(result.snapshot, result.rows, error=result.error)
    key = CALENDAR_KEY if request is None else request.key
    try:
        if args.provider == "esri-calendar":
            snapshot = ingest_esri_calendar(store)
            rows = releases_from_snapshot(store, snapshot, snapshot.observed_at)
        elif args.provider == "esri-gdp":
            calendar = store.get_snapshot(args.calendar_snapshot_id)
            events = releases_from_snapshot(store, calendar, datetime.now(UTC))
            matches = [
                event
                for event in events
                if (event.period_start, event.release_kind)
                == (request.period_start, request.release_kind)
            ]
            if len(matches) != 1:
                raise ValueError("GDP release is not unique in calendar snapshot")
            result = ingest_esri_gdp(store, request, matches[0], resume=args.resume)
            snapshot, rows = result.snapshot, result.rows
        elif args.provider == "mof-jgb":
            result = ingest_mof_jgb(store, request, resume=args.resume)
            snapshot, rows = result.snapshot, result.rows
        else:
            result = ingest_estat(store, request, resume=args.resume)
            snapshot, rows = result.snapshot, result.rows
        return _row_view(snapshot, rows)
    except FetchError as error:
        if not args.allow_stale:
            raise
        snapshot = store.latest_snapshot(
            key, now=datetime.now(UTC), max_age=timedelta(days=1), allow_stale=True
        )
        snapshot = replace(snapshot, stale=True)
        rows = (
            releases_from_snapshot(store, snapshot, datetime.now(UTC))
            if args.provider == "esri-calendar"
            else store.snapshot_macro_view(snapshot, datetime.now(UTC))
        )
        return _row_view(snapshot, rows, error=error.category)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="market-research")
    parser.add_argument(
        "--data-root", type=Path, default=Path.home() / ".local/share/market-research"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="Run the offline synthetic workflow")
    demo.add_argument("--json", action="store_true", help="Print machine-readable summary")
    fetch = sub.add_parser("fetch-prices", help="Explicitly fetch and persist daily prices")
    fetch.add_argument("--provider", choices=sorted(ADJUSTMENTS), required=True)
    for name in ("market", "symbol", "provider-symbol", "currency", "timezone", "adjustment"):
        fetch.add_argument("--" + name, required=True)
    fetch.add_argument("--start", type=date.fromisoformat, required=True)
    fetch.add_argument("--end", type=date.fromisoformat, required=True)
    fetch.add_argument("--calendar", type=Path, help="Verified session schedule JSON")
    fetch.add_argument(
        "--allow-stale", action="store_true", help="Expose cached data after a failed refresh"
    )
    fetch.add_argument(
        "--resume", action="store_true", help="Resume a pending J-Quants page sequence"
    )
    prices = sub.add_parser("prices", help="Read one stored snapshot without network access")
    prices.add_argument("--snapshot-id", required=True)
    prices.add_argument("--as-of", type=datetime.fromisoformat, required=True)
    snapshots = sub.add_parser("snapshots", help="List local snapshot manifests")
    snapshots.add_argument("--limit", type=int, default=50)
    macro_fetch = sub.add_parser("fetch-macro", help="Explicitly fetch macro observations")
    macro_fetch.add_argument(
        "--provider",
        choices=("alfred", "esri-calendar", "esri-gdp", "mof-jgb", "estat"),
        required=True,
    )
    for name in (
        "series-id",
        "indicator",
        "unit",
        "frequency",
        "seasonal-adjustment",
        "stats-data-id",
        "calendar-snapshot-id",
        "release-kind",
        "column",
        "menu-url",
    ):
        macro_fetch.add_argument("--" + name)
    for name in ("start", "end", "realtime-start", "realtime-end", "period-start"):
        macro_fetch.add_argument("--" + name, type=date.fromisoformat)
    macro_fetch.add_argument("--tenor-years", type=float)
    macro_fetch.add_argument("--class", dest="classifications", action="append", default=[])
    macro_fetch.add_argument("--resume", action="store_true")
    macro_fetch.add_argument("--allow-stale", action="store_true")
    macro_read = sub.add_parser("macro", help="Read one completed macro snapshot offline")
    macro_read.add_argument("--snapshot-id", required=True)
    macro_read.add_argument("--as-of", type=datetime.fromisoformat, required=True)
    releases = sub.add_parser("releases", help="Read one ESRI calendar snapshot offline")
    releases.add_argument("--snapshot-id", required=True)
    releases.add_argument("--as-of", type=datetime.fromisoformat, required=True)
    sec_fetch = sub.add_parser("fetch-fundamentals", help="Explicitly fetch SEC companyfacts")
    sec_fetch.add_argument("--cik", type=int, required=True)
    for name in ("taxonomy", "concept", "unit", "form"):
        sec_fetch.add_argument("--" + name, required=True)
    sec_fetch.add_argument("--allow-stale", action="store_true")
    sec_read = sub.add_parser("fundamentals", help="Read one SEC snapshot offline")
    sec_read.add_argument("--snapshot-id", required=True)
    sec_read.add_argument("--as-of", type=datetime.fromisoformat, required=True)
    args = parser.parse_args(argv)
    if args.command == "demo":
        run = build_demo_run()
        summary = {
            "mode": run.mode,
            "run_id": run.run_id,
            "input_hash": run.input_hash,
            "observations": len(run.prices),
            "assets": list(run.prices.columns),
            "last_equity": round(float(run.backtest.equity.iloc[-1]), 8),
        }
        if args.json:
            print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        else:
            print(f"合成デモ {run.run_id}: {len(run.prices)}観測、終値ベースの研究近似")
        return 0
    failure = None
    try:
        with ResearchStore(args.data_root) as store:
            if args.command == "snapshots":
                payload = [_summary(item) for item in store.snapshots(args.limit)]
            elif args.command == "prices":
                snapshot = store.get_snapshot(args.snapshot_id)
                payload = _view(snapshot, store.snapshot_price_view(snapshot, args.as_of))
            elif args.command == "macro":
                snapshot = store.get_snapshot(args.snapshot_id)
                payload = _row_view(snapshot, store.snapshot_macro_view(snapshot, args.as_of))
            elif args.command == "releases":
                snapshot = store.get_snapshot(args.snapshot_id)
                payload = _row_view(snapshot, releases_from_snapshot(store, snapshot, args.as_of))
            elif args.command == "fundamentals":
                snapshot = store.get_snapshot(args.snapshot_id)
                payload = _row_view(snapshot, store.snapshot_fundamental_view(snapshot, args.as_of))
            elif args.command == "fetch-macro":
                payload = _fetch_macro(store, args)
            elif args.command == "fetch-fundamentals":
                request = SecRequest(args.cik, args.taxonomy, args.concept, args.unit, args.form)
                try:
                    result = ingest_sec_companyfacts(store, request)
                    payload = _row_view(result.snapshot, result.rows)
                except FetchError as error:
                    if not args.allow_stale:
                        raise
                    snapshot = store.latest_snapshot(
                        request.key,
                        now=datetime.now(UTC),
                        max_age=timedelta(days=1),
                        allow_stale=True,
                    )
                    snapshot = replace(snapshot, stale=True)
                    payload = _row_view(
                        snapshot,
                        store.snapshot_fundamental_view(snapshot, datetime.now(UTC)),
                        error=error.category,
                    )
            else:
                calendar = (
                    SessionCalendar.from_json(args.calendar.read_text()) if args.calendar else None
                )
                instrument = Instrument(args.market, args.symbol, args.currency, args.timezone)
                request = PriceRequest(
                    instrument, args.provider_symbol, args.start, args.end, args.adjustment
                )
                result = ingest_prices(
                    store,
                    args.provider,
                    request,
                    calendar=calendar,
                    allow_stale=args.allow_stale,
                    resume=args.resume,
                )
                payload = _view(result.snapshot, result.view, error=result.error)
    except FetchError as error:
        failure = {"error": error.category, "status": error.status}
    except (ValueError, OSError) as error:
        # Do not print paths, source bodies, credentials or arbitrary third-party messages.
        failure = {"error": type(error).__name__}
    if failure:
        print(json.dumps(failure, sort_keys=True))
        return 2
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=lambda x: x.isoformat()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
