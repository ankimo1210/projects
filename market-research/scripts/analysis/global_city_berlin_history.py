"""Archive Berlin's 2002–2026 official residential land reference values.

Yearly medians summarize each published zone set. They are not a matched-site
land price index; zone boundaries and development intensity can change.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import median

import requests
from global_city_berlin_land import FIELDS, parse_zones, summarize_zones

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT.parent / "_data/market-research"
RAW = DATA_ROOT / "market/raw/global_city_pilot/berlin_history_20260929"
PROCESSED = DATA_ROOT / "market/processed/global_city_pilot/berlin_history_20260929"
YEARS = tuple(range(2002, 2027))


def matched_zone_change(rows: list[dict], start: int, end: int) -> dict[str, float | int]:
    """Compare identical zone IDs and declared building intensity across two dates."""
    by_year: dict[int, dict[tuple[str, str, str], float]] = {start: {}, end: {}}
    for row in rows:
        year = int(row["year"])
        if year not in by_year:
            continue
        key = (str(row["borough"]), str(row["zone_id"]), str(row["gfz"]))
        if key in by_year[year]:
            raise ValueError(f"Duplicate Berlin matched zone: {year} {key}")
        by_year[year][key] = float(row["brw_eur_m2"])
    common = by_year[start].keys() & by_year[end].keys()
    if not common:
        raise ValueError(f"No Berlin zones matched: {start}→{end}")
    changes = [by_year[end][key] / by_year[start][key] - 1 for key in common]
    return {"zones": len(common), "median_change_pct": round(100 * median(changes), 1)}


def source(year: int) -> tuple[str, dict[str, str | int]]:
    """Return Berlin's official WFS endpoint and attribute-only request."""
    if year not in YEARS:
        raise ValueError(f"Unconfigured Berlin year: {year}")
    typename = f"brw{year}:brw_{year}_vector" if year != 2026 else "brw2026:brw2026_vector"
    return f"https://gdi.berlin.de/services/wfs/brw{year}", {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": typename,
        "count": 10000,
        "propertyName": FIELDS,
        "outputFormat": "application/json",
    }


def _write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def run(*, download: bool = False) -> tuple[Path, Path, Path]:
    """Validate all 25 source years, then write a reproducible annual panel."""
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    manifest_path = RAW / "manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    )
    if manifest is None and not download:
        raise FileNotFoundError("Berlin annual archive manifest missing; run --download first")
    all_rows: list[dict] = []
    qualities: dict[str, dict[str, int]] = {}
    files: dict[str, dict[str, str | int]] = {}
    for year in YEARS:
        url, params = source(year)
        path = RAW / f"berlin_{year}.json"
        if not path.exists():
            if not download:
                raise FileNotFoundError(f"Missing archived Berlin source: {path}")
            response = requests.get(url, params=params, timeout=90)
            response.raise_for_status()
            if "json" not in response.headers.get("Content-Type", "").lower():
                raise ValueError(f"Berlin {year} did not return JSON")
            payload = response.content
            parse_zones(json.loads(payload), year)  # Validate before saving.
            path.write_bytes(payload)
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        if manifest is not None and manifest["files"][path.name]["sha256"] != digest:
            raise ValueError(f"Archived Berlin source checksum mismatch: {path.name}")
        zones, year_quality = parse_zones(json.loads(payload), year)
        if len({zone["borough"] for zone in zones}) != 12:
            raise ValueError(f"Berlin {year} does not cover all 12 boroughs")
        all_rows.extend(zones)
        qualities[str(year)] = year_quality
        files[path.name] = {
            "url": requests.Request("GET", url, params=params).prepare().url,
            "sha256": digest,
            "bytes": len(payload),
        }
    if manifest is None:
        manifest_path.write_text(
            json.dumps(
                {"archived_at_utc": datetime.now(UTC).isoformat(), "files": files},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    elif manifest["files"] != files:
        raise ValueError("Berlin source request or archive differs from manifest")
    all_rows.sort(key=lambda row: (row["year"], row["borough"], row["zone_id"]))
    zones_path = PROCESSED / "residential_zones.csv"
    _write_csv(zones_path, ["year", "borough", "zone_id", "brw_eur_m2", "gfz"], all_rows)
    summary = summarize_zones(all_rows)
    matched_2022_2026 = matched_zone_change(all_rows, 2022, 2026)
    if len(summary) != len(YEARS) * 13:
        raise ValueError("Berlin annual panel has missing borough-year cells")
    annual_path = PROCESSED / "zone_medians_annual.csv"
    _write_csv(
        annual_path,
        ["year", "borough", "zones", "median_eur_m2"],
        [
            {"year": year, "borough": borough, **values}
            for (year, borough), values in summary.items()
        ],
    )
    quality_path = PROCESSED / "quality.json"
    quality_path.write_text(
        json.dumps(
            {
                "period_start": YEARS[0],
                "period_end": YEARS[-1],
                "years": qualities,
                "metric": "Bodenrichtwert; ordinary residential zone, nominal EUR/m2 land",
                "aggregation": "unweighted median across each year's published zones; not area weighted or same-parcel appreciation",
                "matched_2022_2026": matched_2022_2026,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return zones_path, annual_path, quality_path


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--download", action="store_true", help="Fetch missing official WFS years")
    args = cli.parse_args()
    for output in run(download=args.download):
        print(output)
