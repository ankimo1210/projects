"""Build Fukuoka City's 1983–2026 public-notice land-price history.

Source: MLIT National Land Numerical Information (国土数値情報) L01 public-notice land
prices, Fukuoka-prefecture GML ZIPs. Run from ``market-research/``::

    ../.venv/bin/python scripts/analysis/fukuoka_land_price_history.py [--download]

The ZIPs live in the git-ignored ``_data/market-research/market/raw/land_price_history_fukuoka``
next to ``manifest.json`` (file, source URL, bytes, SHA-256). ``--download`` fetches only
missing ZIPs and records or verifies each hash; every build verifies all ZIPs against the
manifest first. Outputs go to ``_data/market-research/market/processed``.

Category is the standard-land code group (000 residential, 005 commercial), which agrees
with Fukuoka City's published 2026 counts and rounded averages. Mean price is a
cross-sectional mean, not a same-site appreciation index. The chained index links each
residential site to the raw previous-year code (``previousRepresentedLandCode``) when the
selection status (``selectedLandStatus``) is 1 (continuing) or 2 (renumbered).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import statistics
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT.parent / "_data/market-research"
RAW = DATA_ROOT / "market/raw/land_price_history_fukuoka"
OUT = DATA_ROOT / "market/processed"
MANIFEST = "manifest.json"
CATALOG_URL = "https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-L01-2026.html"
YEARS = range(1983, 2027)
WARDS = {
    "40131": "東区",
    "40132": "博多区",
    "40133": "中央区",
    "40134": "南区",
    "40135": "西区",
    "40136": "城南区",
    "40137": "早良区",
}
CATEGORIES = {"000": "住宅地", "005": "商業地"}
# selectedLandStatus in the saved L01 files (checked against every Fukuoka City row,
# 1984–2026): 1 keeps the previous-year code; 2 points to a different previous-year code
# with the same address text; 4 and 5 carry an empty previous code (000-000).
LINK_STATUSES = frozenset({"1", "2"})
KNOWN_STATUSES = frozenset({"1", "2", "4", "5"})
CODE_TAGS = ("representedLandCode", "rlc")
PREVIOUS_CODE_TAGS = ("previousRepresentedLandCode", "plc", "previousStandardLandCode")
STATUS_PARENT_TAGS = ("attributeChange", "atc")
# Start years follow the current standard site's continuous address/location segment.
SITES = (
    ("大濠1丁目", "40133", "002", 1983),
    ("赤坂2丁目", "40133", "001", 2001),
    ("赤坂3丁目", "40133", "012", 2003),
    ("箱崎1丁目", "40131", "021", 1990),
    ("吉塚2丁目", "40132", "009", 2010),
    ("高宮2丁目", "40134", "001", 2013),
    ("大橋3丁目", "40134", "005", 1990),
    ("別府5丁目", "40136", "002", 2013),
    ("西新2丁目", "40137", "001", 1995),
)


def zip_path(year: int, raw: Path = RAW) -> Path:
    return raw / f"L01-{year % 100:02d}_40_GML.zip"


def source_url(year: int) -> str:
    yy = year % 100
    return f"https://nlftp.mlit.go.jp/ksj/gml/data/L01/L01-{yy:02d}/L01-{yy:02d}_40_GML.zip"


def fetch_zip(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def load_manifest(raw: Path = RAW) -> dict:
    path = raw / MANIFEST
    if not path.is_file():
        return {
            "dataset": "国土数値情報 地価公示（L01）福岡県 GML",
            "catalog_url": CATALOG_URL,
            "files": {},
        }
    return json.loads(path.read_text(encoding="utf-8"))


def _write_manifest(raw: Path, manifest: dict) -> None:
    files = sorted(manifest["files"].items(), key=lambda item: int(item[1]["year"]))
    ordered = {**manifest, "files": dict(files)}
    tmp = raw / f"{MANIFEST}.tmp"
    tmp.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(raw / MANIFEST)


def _check_zip(payload: bytes, year: int) -> None:
    if not payload.startswith(b"PK"):
        raise ValueError(f"Not a ZIP: {year}")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"Bad ZIP member: {year} {bad}")


def _verify_entry(entry: Mapping, payload: bytes, name: str) -> None:
    digest = hashlib.sha256(payload).hexdigest()
    if len(payload) != entry["bytes"] or digest != entry["sha256"]:
        raise ValueError(
            f"SHA-256/size mismatch for {name}: manifest {entry['sha256'][:12]}… "
            f"({entry['bytes']} bytes), file {digest[:12]}… ({len(payload)} bytes)"
        )


def download_missing(
    raw: Path = RAW,
    years: Iterable[int] = YEARS,
    fetch: Callable[[str], bytes] = fetch_zip,
) -> dict:
    """Fetch absent ZIPs; record new hashes and verify known ones in the manifest.

    A file already on disk without a manifest entry is recorded as ``existing_file``
    (its hash was taken from disk, not at download time). A hash mismatch stops the run
    without replacing any file.
    """
    raw.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(raw)
    files = manifest["files"]
    for year in years:
        dest = zip_path(year, raw)
        entry = files.get(dest.name)
        if dest.is_file():
            payload = dest.read_bytes()
            if entry is not None:
                _verify_entry(entry, payload, dest.name)
                continue
            _check_zip(payload, year)
            recorded_from = "existing_file"
        else:
            payload = fetch(source_url(year))
            _check_zip(payload, year)
            if entry is not None:
                _verify_entry(entry, payload, dest.name)
            tmp = dest.with_suffix(".tmp")
            tmp.write_bytes(payload)
            tmp.replace(dest)
            if entry is not None:
                continue
            recorded_from = "download"
        files[dest.name] = {
            "year": year,
            "url": source_url(year),
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "recorded_from": recorded_from,
        }
        _write_manifest(raw, manifest)
    return manifest


def verify_manifest(raw: Path = RAW, years: Iterable[int] = YEARS) -> dict:
    """Fail unless every requested ZIP matches its manifest size and SHA-256."""
    manifest = load_manifest(raw)
    if not manifest["files"]:
        raise FileNotFoundError(
            f"No {MANIFEST} in {raw}; run with --download to record the saved ZIPs"
        )
    for year in years:
        path = zip_path(year, raw)
        entry = manifest["files"].get(path.name)
        if entry is None:
            raise ValueError(f"ZIP missing from manifest: {path.name}")
        _verify_entry(entry, path.read_bytes(), path.name)
    return manifest


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child_values(element: ET.Element) -> dict[str, str]:
    """Map each direct child to its text; nested parts (code digits) are space-separated."""
    return {_local(child.tag): " ".join(" ".join(child.itertext()).split()) for child in element}


def _first(value: Mapping[str, str], tags: Iterable[str]) -> str:
    return next((value[tag] for tag in tags if tag in value), "")


def _selected_land_status(element: ET.Element) -> str:
    for child in element:
        if _local(child.tag) in STATUS_PARENT_TAGS:
            found = [x for x in child.iter() if _local(x.tag) == "selectedLandStatus"]
            if len(found) != 1:
                raise ValueError("Expected one selectedLandStatus per site")
            return "".join(found[0].itertext()).strip()
    return ""


def _previous_code(value: Mapping[str, str], ward: str) -> str:
    parts = _first(value, PREVIOUS_CODE_TAGS).split()
    if not parts:
        return ""
    if len(parts) == 2:
        parts = [ward, *parts]  # Files before 2024 omit the municipality code.
    if len(parts) != 3:
        raise ValueError(f"Unexpected previous standard-land code: {parts}")
    return "" if parts[1:] == ["000", "000"] else "-".join(parts)


def read_year(year: int, raw: Path = RAW) -> list[dict[str, str | int]]:
    path = zip_path(year, raw)
    with zipfile.ZipFile(path) as archive:
        xml_name = next(
            name for name in archive.namelist() if name.endswith(".xml") and "META" not in name
        )
        root = ET.fromstring(archive.read(xml_name))
    rows = []
    for element in root:
        if _local(element.tag) != "LandPrice":
            continue
        value = child_values(element)
        code = _first(value, CODE_TAGS).split()
        if len(code) < 2:
            raise ValueError(f"Missing standard-land code: {year}")
        admin = value.get("administrativeAreaCode", value.get("aac", ""))
        if not admin and len(code) >= 3:
            admin = code[0]
        if admin not in WARDS:
            continue
        price = int(value.get("postedLandPrice", value.get("plp", "0")))
        if price <= 0:
            raise ValueError(f"Invalid price: {year} {admin} {code}")
        address = value.get("location") or value.get("address") or value.get("as1", "")
        rows.append(
            {
                "year": year,
                "ward_code": admin,
                "ward": WARDS[admin],
                "code_group": code[-2],
                "code_number": code[-1],
                "price_yen_m2": price,
                "address": "".join(address.split()),
                "current_use": value.get("currentUse", value.get("pu1", "")),
                "source_zip": path.name,
                "previous_code": _previous_code(value, admin),
                "land_status": _selected_land_status(element),
            }
        )
    return rows


def site_code(row: Mapping) -> str:
    return f"{row['ward_code']}-{row['code_group']}-{row['code_number']}"


def chained_index(
    rows: Iterable[Mapping],
    statuses: frozenset[str] = LINK_STATUSES,
    code_group: str = "000",
) -> dict[str, dict[str, float | int]]:
    """Chain yearly median price relatives of sites linked by their previous-year code.

    A link needs the current row in ``code_group`` with an allowed selection status and a
    previous-year row that is also in ``code_group``. Keys are year strings.
    """
    by_year: dict[int, dict[str, Mapping]] = defaultdict(dict)
    for row in rows:
        year, code = int(row["year"]), site_code(row)
        if code in by_year[year]:
            raise ValueError(f"Duplicate standard-land code: {year} {code}")
        by_year[year][code] = row
    years = sorted(by_year)
    if not years:
        raise ValueError("No land-price rows for the chained index")
    index: dict[str, float] = {str(years[0]): 100.0}
    matches: dict[str, int] = {}
    for previous, current in pairwise(years):
        if current != previous + 1:
            raise ValueError(f"Missing year between {previous} and {current}")
        relatives = []
        for code, row in by_year[current].items():
            if row["code_group"] != code_group:
                continue
            status = str(row["land_status"])
            if status not in KNOWN_STATUSES:
                raise ValueError(f"Unknown selectedLandStatus {status!r}: {current} {code}")
            if status not in statuses:
                continue
            if status == "1" and row["previous_code"] != code:
                raise ValueError(f"Continuing site changed code: {current} {code}")
            prior = by_year[previous].get(str(row["previous_code"]))
            if prior is None:
                raise ValueError(f"Linked site missing: {current} {code} ← {row['previous_code']}")
            if prior["code_group"] != code_group:
                continue  # category changed, e.g. the 2013 reclassification into 000
            relatives.append(int(row["price_yen_m2"]) / int(prior["price_yen_m2"]))
        if not relatives:
            raise ValueError(f"No linked sites: {previous}→{current}")
        index[str(current)] = round(index[str(previous)] * statistics.median(relatives), 8)
        matches[str(current)] = len(relatives)
    return {"index": index, "matches": matches}


def build(raw: Path = RAW, out: Path = OUT) -> None:
    verify_manifest(raw)
    rows = [row for year in YEARS for row in read_year(year, raw)]
    keys = [(r["year"], r["ward_code"], r["code_group"], r["code_number"]) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate standard-land code within ward/year")
    if {r["year"] for r in rows} != set(YEARS):
        raise ValueError("Incomplete year coverage")
    for year in YEARS:
        if {r["ward_code"] for r in rows if r["year"] == year} != set(WARDS):
            raise ValueError(f"Incomplete ward coverage: {year}")
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "fukuoka_land_price_history_1983_2026.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    grouped: dict[tuple[int, str, str], list[int]] = defaultdict(list)
    for row in rows:
        if row["code_group"] not in CATEGORIES:
            continue
        key = (int(row["year"]), str(row["code_group"]), str(row["ward_code"]))
        grouped[key].append(int(row["price_yen_m2"]))
        grouped[(int(row["year"]), str(row["code_group"]), "city")].append(int(row["price_yen_m2"]))
    averages = [
        {
            "year": year,
            "category": CATEGORIES[code],
            "area": "福岡市" if area == "city" else WARDS[area],
            "count": len(values),
            "mean_yen_m2": round(sum(values) / len(values)),
        }
        for (year, code, area), values in sorted(grouped.items())
    ]
    residential = {
        (int(row["year"]), str(row["ward_code"]), str(row["code_number"])): row
        for row in rows
        if row["code_group"] == "000"
    }
    sites = []
    for name, ward, number, first_year in SITES:
        values = []
        for year in range(first_year, 2027):
            row = residential.get((year, ward, number))
            if row is None:
                raise ValueError(f"Curated site missing: {name} {year}")
            values.append({"year": year, "price_yen_m2": row["price_yen_m2"]})
        sites.append(
            {
                "name": name,
                "ward": WARDS[ward],
                "first_year": first_year,
                "code": f"{ward}-{number}",
                "values": values,
            }
        )
    chain = chained_index(rows)
    data = {
        "source": CATALOG_URL,
        "period": [1983, 2026],
        "averages": averages,
        "sites": sites,
        "chained_index": {
            "base": "1983=100",
            "method": (
                "median price relative of residential (000) sites linked to the raw "
                "previous-year code, selectedLandStatus 1 or 2, previous year also 000"
            ),
            **chain,
        },
    }
    json_path = out / "fukuoka_land_price_history_1983_2026_chart.json"
    json_path.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    index, matches = chain["index"], chain["matches"]
    fewest = min(matches, key=lambda year: (matches[year], year))
    print(f"{len(rows)} city land-price rows; {len(averages)} annual averages; {len(sites)} sites")
    print(
        "chained index (1983=100): "
        + ", ".join(f"{year}={index[year]:.1f}" for year in ("1991", "2013", "2026"))
        + f"; fewest links {matches[fewest]} ({fewest})"
    )
    print(csv_path)
    print(json_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--download",
        action="store_true",
        help="Fetch missing official ZIP files and record or verify manifest hashes",
    )
    args = parser.parse_args()
    if args.download:
        download_missing()
    build()
