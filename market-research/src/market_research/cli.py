"""Local command-line entry point."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

from .calendars import SessionCalendar
from .contracts import Instrument
from .fetch import FetchError
from .ingestion import ingest_prices
from .prices import PriceView
from .providers import ADJUSTMENTS, PriceRequest
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
        "excluded_count": len(view.exclusions),
        "error": error,
    }


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
