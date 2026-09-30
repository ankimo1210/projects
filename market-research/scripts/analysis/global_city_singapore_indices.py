"""Archive Singapore government locality price/rent indices for comparison.

The output is a relative price-to-rent *index*, never a property yield.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT.parent / "_data/market-research"
RAW = DATA_ROOT / "market/raw/global_city_pilot/singapore_indices_20260929"
PROCESSED = DATA_ROOT / "market/processed/global_city_pilot/singapore_indices_20260929"
API = "https://data.gov.sg/api/action/datastore_search"
DATASETS = {
    "price": "d_f65e490a8ad430f60a9a3d9df2bff2a0",
    "rent": "d_56b0c7f6538be69f24956634d88d82e8",
}
SEGMENTS = (
    "Core Central Region",
    "Rest of Central Region",
    "Outside Central Region",
)


def _segment(value: object) -> str:
    normalized = " ".join(str(value).split()).casefold()
    for segment in SEGMENTS:
        if normalized == segment.casefold():
            return segment
    raise ValueError(f"Unknown Singapore market segment: {value}")


def _number(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid Singapore index: {value}") from exc
    if not 0 < number < float("inf"):
        raise ValueError(f"Invalid Singapore index: {value}")
    return number


def parse_price(records: list[dict]) -> dict[tuple[str, str], float]:
    """Read URA's long price table, checking period and region keys."""
    result: dict[tuple[str, str], float] = {}
    for row in records:
        quarter = str(row.get("quarter", ""))
        if not re.fullmatch(r"20\d{2}-Q[1-4]", quarter):
            raise ValueError(f"Invalid Singapore price quarter: {quarter}")
        key = (quarter.replace("-", ""), _segment(row.get("market_segment")))
        if key in result:
            raise ValueError(f"Duplicate Singapore price cell: {key}")
        result[key] = _number(row.get("price_index"))
    if not result:
        raise ValueError("No Singapore price index observations")
    return result


def parse_rent(records: list[dict]) -> dict[tuple[str, str], float]:
    """Unpivot SingStat's wide quarterly rent table."""
    result: dict[tuple[str, str], float] = {}
    for row in records:
        segment = _segment(row.get("DataSeries"))
        quarters = 0
        for name, value in row.items():
            match = re.fullmatch(r"(20\d{2})([1-4])Q", name)
            if match is None:
                if name not in {"DataSeries", "_id"}:
                    raise ValueError(f"Unexpected Singapore rent column: {name}")
                continue
            quarter = f"{match.group(1)}Q{match.group(2)}"
            key = (quarter, segment)
            if key in result:
                raise ValueError(f"Duplicate Singapore rent cell: {key}")
            result[key] = _number(value)
            quarters += 1
        if not quarters:
            raise ValueError(f"No Singapore rent periods for {segment}")
    if not result:
        raise ValueError("No Singapore rent index observations")
    return result


def align_indices(
    price: dict[tuple[str, str], float], rent: dict[tuple[str, str], float], *, base: str
) -> list[dict]:
    """Rebase equal quarter/region cells and compute a relative price/rent index."""
    if set(price) != set(rent):
        raise ValueError("Singapore price and rent indices have different coverage")
    rows = []
    for quarter, segment in sorted(price):
        base_key = (base, segment)
        if base_key not in price or base_key not in rent:
            raise ValueError(f"Singapore base quarter missing: {base_key}")
        price_base = 100 * price[quarter, segment] / price[base_key]
        rent_base = 100 * rent[quarter, segment] / rent[base_key]
        rows.append(
            {
                "quarter": quarter,
                "segment": segment,
                "price_index": price[quarter, segment],
                "rent_index": rent[quarter, segment],
                "price_base_100": price_base,
                "rent_base_100": rent_base,
                "relative_price_rent_base_100": 100 * price_base / rent_base,
            }
        )
    return rows


def _records(payload: bytes, dataset_id: str) -> list[dict]:
    body = json.loads(payload)
    if body.get("success") is not True:
        raise ValueError(f"Singapore API did not succeed: {dataset_id}")
    result = body.get("result", {})
    rows = result.get("records")
    if result.get("resource_id") != dataset_id or not isinstance(rows, list):
        raise ValueError(f"Singapore API resource mismatch: {dataset_id}")
    if len(rows) != result.get("total") or len(rows) > result.get("limit", 0):
        raise ValueError(f"Singapore API result is incomplete: {dataset_id}")
    return rows


def run(*, download: bool = False) -> tuple[Path, Path]:
    """Process a fixed 2004Q1–2026Q2 public API snapshot."""
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    manifest_path = RAW / "manifest.json"
    old_manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    )
    if old_manifest is None and not download:
        raise FileNotFoundError("Singapore archive manifest missing; run --download first")
    files: dict[str, dict[str, str | int]] = {}
    series: dict[str, list[dict]] = {}
    for name, dataset_id in DATASETS.items():
        params = {"resource_id": dataset_id, "limit": 1000}
        path = RAW / f"{name}.json"
        if not path.exists():
            if not download:
                raise FileNotFoundError(f"Missing Singapore source: {path}")
            response = requests.get(API, params=params, timeout=30)
            response.raise_for_status()
            if "json" not in response.headers.get("Content-Type", "").lower():
                raise ValueError(f"Singapore {name} did not return JSON")
            payload = response.content
            _records(payload, dataset_id)
            path.write_bytes(payload)
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        if old_manifest is not None and old_manifest["files"][path.name]["sha256"] != digest:
            raise ValueError(f"Archived Singapore source checksum mismatch: {path.name}")
        series[name] = _records(payload, dataset_id)
        files[path.name] = {
            "api_url": requests.Request("GET", API, params=params).prepare().url,
            "catalog_url": f"https://data.gov.sg/datasets/{dataset_id}/view",
            "sha256": digest,
            "bytes": len(payload),
        }
    if old_manifest is None:
        manifest_path.write_text(
            json.dumps(
                {"archived_at_utc": datetime.now(UTC).isoformat(), "files": files},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    elif old_manifest["files"] != files:
        raise ValueError("Singapore source request differs from manifest")
    price, rent = parse_price(series["price"]), parse_rent(series["rent"])
    expected_quarters = [
        f"{year}Q{quarter}" for year in range(2004, 2027) for quarter in range(1, 5)
    ]
    expected_quarters = [quarter for quarter in expected_quarters if quarter <= "2026Q2"]
    expected_keys = {(quarter, segment) for quarter in expected_quarters for segment in SEGMENTS}
    if set(price) != expected_keys or set(rent) != expected_keys:
        raise ValueError("Singapore locality indices have missing/unexpected quarter-region cells")
    rows = align_indices(price, rent, base="2015Q1")
    output = PROCESSED / "locality_price_rent_indices.csv"
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    quality = PROCESSED / "quality.json"
    quality.write_text(
        json.dumps(
            {
                "start": expected_quarters[0],
                "end": expected_quarters[-1],
                "quarter_count": len(expected_quarters),
                "segment_count": len(SEGMENTS),
                "price_raw_rows": len(series["price"]),
                "rent_raw_rows": len(series["rent"]),
                "output_rows": len(rows),
                "base": "2015Q1=100",
                "meaning": "relative index only; no price/rent level, gross yield, or NOI yield",
                "rent_method_note": "SingStat reports hedonic rental index from 2015Q1; earlier methods may differ",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return output, quality


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--download", action="store_true", help="Fetch missing official API records")
    args = cli.parse_args()
    for output in run(download=args.download):
        print(output)
