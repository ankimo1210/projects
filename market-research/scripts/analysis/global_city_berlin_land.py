"""Archive and summarize Berlin's official Bodenrichtwert WFS zones.

Only ordinary ``W - Wohngebiet`` reference zones are compared. Cross-year
zone medians describe the published zone set, not matched-parcel returns.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
from collections import defaultdict
from datetime import UTC, date, datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT.parent / "_data/market-research"
RAW = DATA_ROOT / "market/raw/global_city_pilot/berlin_history_20260928"
PROCESSED = DATA_ROOT / "market/processed/global_city_pilot/berlin_history_20260928"
YEARS = (2006, 2016, 2026)
FIELDS = "bezirk,brw,nutzung,stichtag,gfz,brwid,anwert,verfahrensart,beitragszustand"


def source(year: int) -> tuple[str, dict[str, str | int]]:
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


def parse_zones(payload: dict, year: int) -> tuple[list[dict], dict[str, int]]:
    """Validate a complete WFS response, retaining ordinary residential zones."""
    if payload.get("type") != "FeatureCollection":
        raise ValueError("Berlin response is not a FeatureCollection")
    features = payload.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError("Berlin response has no features")
    count = len(features)
    if count != payload.get("numberMatched") or count != payload.get("numberReturned"):
        raise ValueError("Berlin WFS response is incomplete")
    ids: set[str] = set()
    rows: list[dict] = []
    excluded_special = 0
    residential_total = 0
    for feature in features:
        p = feature.get("properties") or {}
        zone_id = str(p.get("brwid") or "")
        if not zone_id:
            raise ValueError("Berlin zone without brwid")
        if zone_id in ids:
            raise ValueError(f"Berlin duplicate zone ID: {zone_id}")
        ids.add(zone_id)
        source_date = p.get("stichtag")
        try:
            timestamp = datetime.fromisoformat(source_date)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Unexpected Berlin valuation date: {source_date}") from exc
        if timestamp.date() != date(year, 1, 1) or any(
            (timestamp.hour, timestamp.minute, timestamp.second, timestamp.microsecond)
        ):
            raise ValueError(f"Unexpected Berlin valuation date: {source_date}")
        if p.get("nutzung") != "W - Wohngebiet":
            continue
        residential_total += 1
        if p.get("anwert") is not None or p.get("verfahrensart") is not None:
            excluded_special += 1
            continue
        value = p.get("brw")
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"Invalid Berlin residential reference value: {value}")
        borough = p.get("bezirk")
        if not isinstance(borough, str) or not borough:
            raise ValueError("Berlin residential zone without borough")
        rows.append(
            {
                "year": year,
                "borough": borough,
                "zone_id": zone_id,
                "brw_eur_m2": value,
                "gfz": p.get("gfz"),
            }
        )
    if not rows:
        raise ValueError("No ordinary Berlin residential zones")
    return rows, {
        "total_zones": count,
        "residential_zones": residential_total,
        "residential_regular": len(rows),
        "excluded_special_residential": excluded_special,
        "excluded_other_use": count - residential_total,
    }


def summarize_zones(rows: list[dict]) -> dict[tuple[int, str], dict[str, int | float]]:
    """Compute unweighted medians over zones, by borough and full city."""
    buckets: dict[tuple[int, str], list[float]] = defaultdict(list)
    for row in rows:
        year = int(row["year"])
        value = float(row["brw_eur_m2"])
        buckets[(year, "Berlin")].append(value)
        buckets[(year, str(row["borough"]))].append(value)
    return {
        key: {"zones": len(values), "median_eur_m2": statistics.median(values)}
        for key, values in sorted(buckets.items())
    }


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def run(*, download: bool = False) -> tuple[Path, Path, Path]:
    """Use fixed archived source years; ``--download`` fills missing raw files."""
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    manifest_path = RAW / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    all_rows: list[dict] = []
    quality: dict[str, dict[str, int]] = {}
    source_files: dict[str, dict[str, str | int]] = {}
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
            data = response.content
            parsed = json.loads(data)
            parse_zones(parsed, year)  # Reject partial or invalid responses before archiving.
            path.write_bytes(data)
        data = path.read_bytes()
        digest = _sha(data)
        old = manifest.get("files", {}).get(path.name, {})
        if old and old.get("sha256") != digest:
            raise ValueError(f"Archived Berlin source changed: {path.name}")
        zones, year_quality = parse_zones(json.loads(data), year)
        all_rows.extend(zones)
        quality[str(year)] = year_quality
        source_files[path.name] = {
            "url": requests.Request("GET", url, params=params).prepare().url,
            "sha256": digest,
            "bytes": len(data),
        }
    if not manifest_path.exists():
        manifest_path.write_text(
            json.dumps(
                {"archived_at_utc": datetime.now(UTC).isoformat(), "files": source_files},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    all_rows.sort(key=lambda row: (row["year"], row["borough"], row["zone_id"]))
    zones_path = PROCESSED / "residential_zones.csv"
    _write_csv(zones_path, ["year", "borough", "zone_id", "brw_eur_m2", "gfz"], all_rows)
    summary = summarize_zones(all_rows)
    summary_path = PROCESSED / "zone_medians.csv"
    _write_csv(
        summary_path,
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
                "years": quality,
                "metric": "Bodenrichtwert; ordinary residential zone, EUR/m2 land",
                "aggregation": "unweighted median across published zones; not area weighted or same-parcel appreciation",
                "source": "Berlin GDI WFS official Bodenrichtwerte",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return zones_path, summary_path, quality_path


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--download", action="store_true", help="Fetch missing official source files")
    args = cli.parse_args()
    for output in run(download=args.download):
        print(output)
