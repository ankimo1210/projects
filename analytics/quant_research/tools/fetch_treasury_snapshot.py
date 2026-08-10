"""Build the frozen 2015--2025 Treasury snapshot from official XML feeds."""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
PROJECT = TOOLS.parent
sys.path.insert(0, str(PROJECT / "src"))

from quant_textbook.treasury_data import (  # noqa: E402
    DEFAULT_TENORS,
    TREASURY_METHOD_BREAK,
    TREASURY_XML_URL,
    audit_treasury_data,
    fetch_treasury_year,
)

START_YEAR = 2015
END_YEAR = 2025
RETRIEVAL_USER_AGENT = "quant-research-textbook/0.1 (educational data audit)"
RESOURCE_DIR = PROJECT / "src" / "quant_textbook" / "resources"
SNAPSHOT_PATH = RESOURCE_DIR / "treasury_yields_2015_2025.json"
MANIFEST_PATH = RESOURCE_DIR / "treasury_yields_2015_2025.manifest.json"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fetch and validate without overwriting the bundled snapshot",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    years = list(range(START_YEAR, END_YEAR + 1))
    with ThreadPoolExecutor(max_workers=4) as executor:
        fetched = list(
            executor.map(
                lambda year: fetch_treasury_year(year, user_agent=RETRIEVAL_USER_AGENT),
                years,
            )
        )

    source_hashes: dict[str, str] = {}
    frames = []
    for year, (raw_xml, frame) in zip(years, fetched, strict=True):
        source_hashes[str(year)] = sha256(raw_xml).hexdigest()
        frames.append(frame)

    import pandas as pd

    combined = pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)
    quality = audit_treasury_data(combined)
    if not quality.accepted:
        raise SystemExit(f"Treasury snapshot failed quality audit: {quality}")

    snapshot = {
        "columns": ["date", *DEFAULT_TENORS],
        "data": [
            [row.date.strftime("%Y-%m-%d"), row._1, row._2, row._3, row._4, row._5]
            for row in combined.itertuples(index=False, name="TreasuryRow")
        ],
    }
    snapshot_bytes = (
        json.dumps(snapshot, separators=(",", ":"), ensure_ascii=True) + "\n"
    ).encode()
    snapshot_hash = sha256(snapshot_bytes).hexdigest()
    manifest = {
        "source_name": "U.S. Treasury Daily Par Yield Curve Rates",
        "source_page": (
            "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
            "TextView?page=1&type=daily_treasury_yield_curve"
        ),
        "source_feed_template": TREASURY_XML_URL,
        "source_terms_pages": [
            "https://home.treasury.gov/subfooter/site-policies-and-notices",
            "https://www.usa.gov/government-copyright",
        ],
        "terms_reviewed_at": "2026-08-10",
        "redistribution_decision": (
            "bundle the factual numeric snapshot with source attribution and hashes; "
            "exclude agency logos and page text; re-check restrictions before external publication"
        ),
        "retrieval_user_agent": RETRIEVAL_USER_AGENT,
        "retrieved_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "start_date": quality.start_date.strftime("%Y-%m-%d"),
        "end_date": quality.end_date.strftime("%Y-%m-%d"),
        "row_count": quality.row_count,
        "tenors": list(DEFAULT_TENORS),
        "value_unit": "percent per annum",
        "quote_convention": "par yield, bond-equivalent, semiannual coupon basis",
        "observation_contract": (
            "constant-maturity par yields derived from indicative bid-side quotations; "
            "not transactions, executable quotes, or zero-coupon rates"
        ),
        "availability_contract": (
            "usually available by 18:00 America/New_York on each trading day; "
            "system delays are possible, so same-day trading claims are prohibited"
        ),
        "methodology_break_date": TREASURY_METHOD_BREAK.strftime("%Y-%m-%d"),
        "source_sha256_by_year": source_hashes,
        "snapshot_sha256": snapshot_hash,
    }
    manifest_text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"

    if args.check:
        if SNAPSHOT_PATH.exists() and SNAPSHOT_PATH.read_bytes() != snapshot_bytes:
            raise SystemExit("live Treasury data differ from the bundled snapshot")
        print(f"validated {quality.row_count} rows from {START_YEAR} through {END_YEAR}")
        return 0

    RESOURCE_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_bytes(snapshot_bytes)
    MANIFEST_PATH.write_text(manifest_text, encoding="utf-8")
    print(f"wrote {SNAPSHOT_PATH} ({quality.row_count} rows)")
    print(f"wrote {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
