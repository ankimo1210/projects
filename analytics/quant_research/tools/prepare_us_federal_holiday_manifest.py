"""Write a locked U.S. federal holiday manifest for B9 availability dates.

The B9 Core contract defines a fact as usable on the next U.S. federal business
day after its SEC filing/acceptance date.  This tool makes that calendar input
explicit and hashable rather than silently relying on the installed pandas
calendar at a later rebuild.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar


def _iso_date(value: str, *, name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"{name} must be an ISO date (YYYY-MM-DD)") from error


def prepare_us_federal_holiday_manifest(
    *,
    start: date,
    end: date,
    output: Path,
) -> dict[str, object]:
    """Create a deterministic, bounded holiday manifest."""

    if start > end:
        raise ValueError("start must be on or before end")
    coverage_end = end + timedelta(days=14)
    holidays = USFederalHolidayCalendar().holidays(
        start=pd.Timestamp(start), end=pd.Timestamp(coverage_end)
    )
    holiday_dates = [timestamp.date().isoformat() for timestamp in holidays]
    manifest = {
        "schema_version": "b9-us-federal-holidays-v1",
        "calendar": "pandas.USFederalHolidayCalendar",
        "pandas_version": pd.__version__,
        "start": start.isoformat(),
        "requested_end": end.isoformat(),
        "end": coverage_end.isoformat(),
        "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "holiday_dates": holiday_dates,
    }
    path = output.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
    return manifest


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, type=lambda value: _iso_date(value, name="start"))
    parser.add_argument("--end", required=True, type=lambda value: _iso_date(value, name="end"))
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    manifest = prepare_us_federal_holiday_manifest(
        start=args.start, end=args.end, output=args.output
    )
    print(
        json.dumps(
            {
                "output": str(args.output.expanduser().resolve()),
                "holiday_count": len(manifest["holiday_dates"]),
                "schema_version": manifest["schema_version"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
