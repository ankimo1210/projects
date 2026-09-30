"""Reproducible pilot for Fukuoka land and overseas housing indices."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import re
import statistics
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import fukuoka_land_price_history as fukuoka_history
import requests
from global_city_xlsx import excel_date, xlsx_rows

SOURCES = {
    "hk_rent_q": "https://www.rvd.gov.hk/datagovhk/1.3Q.csv",
    "hk_price_q": "https://www.rvd.gov.hk/datagovhk/1.4Q.csv",
}
UK_SOURCE = "https://publicdata.landregistry.gov.uk/market-trend-data/house-price-index-data/Indices-2026-07.csv"
UK_RELEASE = "https://www.gov.uk/government/statistical-data-sets/uk-house-price-index-data-downloads-july-2026"
ONS_SOURCE = "https://www.ons.gov.uk/file?uri=%2Feconomy%2Finflationandpriceindices%2Fdatasets%2Fpriceindexofprivaterentsukmonthlypricestatistics%2F16september2026%2Fpriceindexofprivaterentsukmonthlypricestatistics.xlsx"
ONS_CATALOG = "https://www.ons.gov.uk/economy/inflationandpriceindices/datasets/priceindexofprivaterentsukmonthlypricestatistics"
NSW_SOURCE = "https://www.nsw.gov.au/sites/default/files/noindex/2026-09/rentalbond_lodgements_august_2026.xlsx"
NSW_CATALOG = (
    "https://www.nsw.gov.au/housing-and-construction/rental-forms-surveys-and-data/rental-bond-data"
)
UK_GEOGRAPHIES = {
    "E12000007": ("London", "uk_london_region", "ロンドン地域"),
    "E08000003": ("Manchester", "uk_manchester_city", "マンチェスター市"),
}
HK_CATALOG = "https://data.gov.hk/en-data/dataset/hk-rvd-tsinfo_rvd-property-market-statistics"
HK_TERMS = "https://data.gov.hk/en/terms-and-conditions"
WARD_NAMES = {
    "40131": "東区",
    "40132": "博多区",
    "40133": "中央区",
    "40134": "南区",
    "40135": "西区",
    "40136": "城南区",
    "40137": "早良区",
}
FUKUOKA_LINK_FIELDS = {"previous_code", "land_status"}
FUKUOKA_LINK_METHOD = (
    "L01 previousRepresentedLandCode; selectedLandStatus 1 (continuing) or 2 (renumbered); "
    "previous-year site also residential (000)"
)
# Sample or definition changes marked on the chained-index chart.
FUKUOKA_BREAKS = {"1994": "1994–95 地点増", "2013": "2013 区分変更", "2022": "2022 表記変更"}


def fetch_csv(url: str) -> bytes:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    if "csv" not in response.headers.get("content-type", "").lower():
        raise ValueError(f"Unexpected content type for {url}")
    return response.content


def fetch_xlsx(url: str) -> bytes:
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    if "spreadsheetml" not in response.headers.get("content-type", "").lower():
        raise ValueError(f"Unexpected XLSX content type for {url}")
    if not response.content.startswith(b"PK\x03\x04"):
        raise ValueError(f"Invalid XLSX response for {url}")
    return response.content


def _check_csv_payload(payload: bytes) -> None:
    if not payload:
        raise ValueError("Empty CSV response")
    decoded = payload.decode("utf-8-sig")
    head = decoded.lstrip().lower()[:100]
    if head.startswith(("<html", "<!doctype", "<?xml")):
        raise ValueError("HTML/XML response at CSV URL")
    if b"," not in payload[:1024] or b"\n" not in payload[:1024]:
        raise ValueError("No CSV header found")


def _source_shape(payload: bytes, source_id: str) -> tuple[list[str], str, str]:
    reader = csv.reader(io.StringIO(payload.decode("utf-8-sig")))
    first = next(reader)
    if source_id.startswith("hk_") and "Quarter" not in first:
        first = next(reader)
    columns = first
    period_column = (
        "Quarter"
        if source_id.startswith("hk_")
        else ("Date" if source_id == "uk_hpi_index" else "year")
    )
    if period_column not in columns:
        raise ValueError(f"Missing period column in {source_id}")
    period_index = columns.index(period_column)
    start = end = ""
    for fields in reader:
        if not fields:
            continue
        if not start:
            start = fields[period_index]
        end = fields[period_index]
    if not start:
        raise ValueError(f"No data rows in {source_id}")
    return columns, start, end


def _xlsx_source_shape(payload: bytes, source_id: str) -> tuple[list[str], str, str]:
    sheet = "Table 1" if source_id == "uk_pipr" else "August26 Rental Bond Lodgments"
    header = start = end = None
    for row_number, fields in xlsx_rows(payload, sheet):
        if row_number == 3:
            header = [fields.get(chr(column), "") for column in range(ord("A"), ord("H") + 1)]
            required = (
                {
                    "A": "Time period",
                    "B": "Area code",
                    "C": "Area name",
                    "E": "Index",
                    "H": "Rental price",
                }
                if source_id == "uk_pipr"
                else {
                    "A": "Lodgement Date",
                    "B": "Postcode",
                    "C": "Dwelling Type",
                    "D": "Bedrooms",
                    "E": "Weekly Rent",
                }
            )
            if any(fields.get(column) != title for column, title in required.items()):
                raise ValueError(f"XLSX column mismatch in {source_id}")
        if row_number >= 4 and fields.get("A"):
            period = _xlsx_iso_date(fields["A"])[:7]
            start = start or period
            end = period
    if not payload.startswith(b"PK\x03\x04") or header is None or start is None:
        raise ValueError(f"Invalid XLSX source: {source_id}")
    return header, start, end


def collect_sources(
    run_id: str,
    data_root: Path,
    fukuoka_csv: Path,
    fetch: Callable[[str], bytes] = fetch_csv,
    include_uk: bool = False,
    include_ons: bool = False,
    include_nsw: bool = False,
    fetch_spreadsheet: Callable[[str], bytes] = fetch_xlsx,
) -> Path:
    """Create one immutable set of raw inputs; record and report fetch failures."""
    if not re.fullmatch(r"\d{8}T\d{6}Z(?:-[a-z0-9-]+)?", run_id):
        raise ValueError("run_id must be an ISO-like UTC identifier")
    raw = data_root / "market" / "raw" / "global_city_pilot" / run_id
    raw.mkdir(parents=True, exist_ok=False)
    manifest: dict[str, object] = {
        "run_id": run_id,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "code_version": "global_city_pilot/0.1",
        "sources": {},
    }
    sources: dict[str, dict[str, object]] = manifest["sources"]  # type: ignore[assignment]
    inputs = [
        ("jp_fukuoka_land", str(fukuoka_csv), fukuoka_csv.read_bytes),
        *((name, url, lambda url=url: fetch(url)) for name, url in SOURCES.items()),
    ]
    if include_uk:
        inputs.append(("uk_hpi_index", UK_SOURCE, lambda: fetch(UK_SOURCE)))
    if include_ons:
        inputs.append(("uk_pipr", ONS_SOURCE, lambda: fetch_spreadsheet(ONS_SOURCE)))
    if include_nsw:
        inputs.append(("nsw_bonds", NSW_SOURCE, lambda: fetch_spreadsheet(NSW_SOURCE)))
    failures = []
    for source_id, origin, get_payload in inputs:
        try:
            payload = get_payload()
            spreadsheet = source_id in {"uk_pipr", "nsw_bonds"}
            if spreadsheet:
                columns, period_start, period_end = _xlsx_source_shape(payload, source_id)
            else:
                _check_csv_payload(payload)
                columns, period_start, period_end = _source_shape(payload, source_id)
            filename = f"{source_id}.{'xlsx' if spreadsheet else 'csv'}"
            (raw / filename).write_bytes(payload)
            entry = {
                "status": "ok",
                "source": origin,
                "file": filename,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "retrieved_at": datetime.now(UTC).isoformat(),
                "raw_columns": columns,
                "period_start": period_start,
                "period_end": period_end,
                "source_base": "1999=100"
                if source_id.startswith("hk_")
                else ("January 2015=100" if source_id == "uk_hpi_index" else "none"),
                "analysis_base": "2015Q1=100" if source_id != "jp_fukuoka_land" else "none",
                "unit": "JPY/m2 land" if source_id == "jp_fukuoka_land" else "index",
                "catalog_url": UK_RELEASE
                if source_id == "uk_hpi_index"
                else (
                    HK_CATALOG
                    if source_id != "jp_fukuoka_land"
                    else "https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-L01-2026.html"
                ),
                "terms_url": "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
                if source_id == "uk_hpi_index"
                else (
                    HK_TERMS if source_id != "jp_fukuoka_land" else "https://nlftp.mlit.go.jp/ksj/"
                ),
                "release": "2026-07" if source_id == "uk_hpi_index" else "",
            }
            if source_id == "uk_pipr":
                entry.update(
                    source_base="January 2023=100",
                    analysis_base="2015Q1=100",
                    unit="index and GBP/month",
                    catalog_url=ONS_CATALOG,
                    terms_url="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
                    release="2026-09-16",
                )
            elif source_id == "nsw_bonds":
                entry.update(
                    source_base="none",
                    analysis_base="none",
                    unit="AUD/week",
                    catalog_url=NSW_CATALOG,
                    terms_url="https://www.nsw.gov.au/nsw-government/about-website/copyright",
                    release="2026-08",
                )
            sources[source_id] = entry
        except (OSError, requests.RequestException, UnicodeError, ValueError) as exc:
            sources[source_id] = {"status": "failed", "source": origin, "reason": str(exc)}
            failures.append(source_id)
    (raw / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if failures:
        raise ValueError(
            f"Source collection failed: {', '.join(failures)}; see {raw / 'manifest.json'}"
        )
    return raw


def quarter_label(text: str) -> str:
    match = re.fullmatch(r"(01-03|04-06|07-09|10-12)/(\d{4})", text.strip())
    if match is None:
        raise ValueError(f"Invalid quarter: {text}")
    quarter = {"01-03": 1, "04-06": 2, "07-09": 3, "10-12": 4}[match[1]]
    return f"{match[2]}Q{quarter}"


def rebase(points: dict[str, float], base_period: str) -> dict[str, float]:
    if base_period not in points:
        raise ValueError(f"Missing base period: {base_period}")
    if any(value <= 0 for value in points.values()):
        raise ValueError("Nonpositive index")
    base = points[base_period]
    return {period: 100 * value / base for period, value in points.items()}


def relative_price_rent(price_index: float, rent_index: float) -> float:
    if price_index <= 0 or rent_index <= 0:
        raise ValueError("Nonpositive price or rent index")
    return 100 * price_index / rent_index


def parse_hk_csv(payload: bytes, source_id: str) -> list[dict[str, object]]:
    if source_id not in SOURCES:
        raise ValueError(f"Unknown Hong Kong source: {source_id}")
    reader = csv.reader(io.StringIO(payload.decode("utf-8-sig")))
    next(reader)  # RVD title row, followed by column names.
    header = next(reader)
    required = {"Quarter", "All Classes", "All Classes - Remarks"}
    if not required.issubset(header):
        raise ValueError(f"RVD column mismatch: {header}")
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for fields in reader:
        if len(fields) != len(header):
            raise ValueError(f"RVD column count mismatch: {len(fields)} vs {len(header)}")
        row = dict(zip(header, fields, strict=True))
        period = quarter_label(row["Quarter"])
        if period in seen:
            raise ValueError(f"Duplicate quarter: {period}")
        seen.add(period)
        raw_value = row["All Classes"].strip()
        remark = row["All Classes - Remarks"].strip()
        try:
            value = float(raw_value.replace(",", ""))
        except ValueError:
            value = None
            if raw_value not in {"", "-"}:
                remark = f"{remark} non_numeric:{raw_value}".strip()
        if value is not None and value <= 0:
            raise ValueError(f"Nonpositive RVD index: {period}")
        rows.append(
            {
                "source_id": source_id,
                "geo_id": "hong_kong_territory",
                "asset_type": "private_domestic_all_classes",
                "metric": "rent_index" if source_id == "hk_rent_q" else "price_index",
                "period": period,
                "frequency": "quarterly",
                "value": value,
                "unit": "index",
                "remark": remark,
                "raw_value": raw_value,
            }
        )
    if not rows:
        raise ValueError(f"No RVD observations: {source_id}")
    return rows


def parse_fukuoka_csv(payload: bytes) -> list[dict[str, object]]:
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    seen: set[tuple[str, str, str, str]] = set()
    for row in reader:
        if row["code_group"] != "000":
            continue
        year = row["year"]
        ward = row["ward_code"]
        if ward not in WARD_NAMES or not re.fullmatch(r"\d{4}", year):
            raise ValueError(f"Invalid Fukuoka land record: {year} {ward}")
        key = (year, ward, row["code_group"], row["code_number"])
        if key in seen:
            raise ValueError(f"Duplicate land-site record: {key}")
        seen.add(key)
        value = int(row["price_yen_m2"])
        if value <= 0:
            raise ValueError(f"Nonpositive land price: {key}")
        groups[(year, ward)].append(value)
        groups[(year, "city")].append(value)
    if not groups:
        raise ValueError("No Fukuoka residential land records")
    return [
        {
            "source_id": "jp_fukuoka_land",
            "geo_id": "fukuoka_city" if geo == "city" else f"fukuoka_ward_{geo}",
            "geo_label": "福岡市" if geo == "city" else WARD_NAMES[geo],
            "asset_type": "residential_land",
            "metric": "public_notice_mean_yen_m2",
            "period": year,
            "frequency": "annual",
            "value": float(round(sum(values) / len(values))),
            "unit": "JPY/land_m2",
            "remark": "cross_sectional_mean",
            "count": len(values),
        }
        for (year, geo), values in sorted(groups.items())
    ]


def fukuoka_link_rows(
    payload: bytes, l01_dir: Path | None = None
) -> tuple[list[dict[str, str]], dict[str, str]]:
    """Return land rows carrying the L01 previous-year code and selection status.

    Snapshots taken before 2026-09-30 lack those fields. Their rows are then read from the
    saved L01 ZIPs after the ZIP manifest check, and every site-year price must equal the
    snapshot's.
    """
    rows = list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))
    if not rows:
        raise ValueError("No Fukuoka land rows")
    if FUKUOKA_LINK_FIELDS.issubset(rows[0]):
        return rows, {"link_source": "snapshot"}
    if l01_dir is None:
        raise ValueError("Fukuoka snapshot lacks L01 link fields; pass the saved L01 ZIP folder")
    years = sorted({int(row["year"]) for row in rows})
    fukuoka_history.verify_manifest(l01_dir, years)
    zip_rows = [row for year in years for row in fukuoka_history.read_year(year, l01_dir)]

    def key(row: dict) -> tuple[str, ...]:
        fields = ("year", "ward_code", "code_group", "code_number", "price_yen_m2")
        return tuple(str(row[field]) for field in fields)

    if sorted(map(key, rows)) != sorted(map(key, zip_rows)):
        raise ValueError("Fukuoka snapshot and saved L01 ZIPs disagree")
    manifest = (l01_dir / fukuoka_history.MANIFEST).read_bytes()
    return [{k: str(v) for k, v in row.items()} for row in zip_rows], {
        "link_source": "L01 ZIPs checked against manifest.json",
        "l01_manifest_sha256": hashlib.sha256(manifest).hexdigest(),
    }


def fukuoka_matched_site_index(rows: list[dict[str, str]]) -> dict[str, dict[str, float | int]]:
    """Chain yearly median price relatives of residential sites linked by previous-year code."""
    return fukuoka_history.chained_index(rows)


def parse_uk_index(payload: bytes) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Read fixed HMLR geography codes and emit only complete three-month quarters."""
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
    required = {"Date", "Region_Name", "Area_Code", "Index"}
    if reader.fieldnames is None or not required.issubset(reader.fieldnames):
        raise ValueError(f"UK HPI column mismatch: {reader.fieldnames}")
    quarters: dict[tuple[str, str], dict[int, float]] = defaultdict(dict)
    seen: set[tuple[str, str]] = set()
    raw_rows = selected_months = 0
    for row in reader:
        raw_rows += 1
        code = row["Area_Code"]
        if code not in UK_GEOGRAPHIES:
            continue
        expected_name, _, _ = UK_GEOGRAPHIES[code]
        if row["Region_Name"] != expected_name:
            raise ValueError(f"UK HPI geography mismatch for {code}: {row['Region_Name']}")
        date = datetime.strptime(row["Date"], "%Y-%m-%d")
        if date.day != 1:
            raise ValueError(f"Unexpected UK HPI month: {row['Date']}")
        if date.year < 1995:
            continue  # London has a derived historical back series; Manchester begins in 1995.
        key = (code, row["Date"])
        if key in seen:
            raise ValueError(f"Duplicate UK HPI code and month: {key}")
        seen.add(key)
        value = float(row["Index"])
        if value <= 0:
            raise ValueError(f"Nonpositive UK HPI index: {key}")
        selected_months += 1
        quarter = f"{date.year}Q{(date.month - 1) // 3 + 1}"
        quarters[(code, quarter)][date.month] = value
    rows = []
    incomplete = set()
    for (code, period), months in sorted(
        quarters.items(), key=lambda item: (item[0][1], item[0][0])
    ):
        quarter_number = int(period[-1])
        required_months = {3 * quarter_number - 2, 3 * quarter_number - 1, 3 * quarter_number}
        if set(months) != required_months:
            incomplete.add(period)
            continue
        _, geo_id, label = UK_GEOGRAPHIES[code]
        rows.append(
            {
                "source_id": "uk_hpi_index",
                "geo_id": geo_id,
                "geo_label": label,
                "asset_type": "residential_all_types",
                "metric": "price_index",
                "period": period,
                "frequency": "quarterly",
                "value": sum(months.values()) / 3,
                "unit": "index",
                "remark": "",
            }
        )
    if not rows:
        raise ValueError("No complete UK HPI quarters")
    return rows, {
        "raw_rows": raw_rows,
        "selected_months": selected_months,
        "incomplete_quarters": sorted(incomplete),
    }


def _xlsx_iso_date(value: str) -> str:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value
    return excel_date(value)


def parse_ons_pipr(payload: bytes) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Select fixed ONS geographies, preserving monthly rents and complete-quarter indices."""
    header = {
        "A": "Time period",
        "B": "Area code",
        "C": "Area name",
        "E": "Index",
        "H": "Rental price",
    }
    monthly: dict[tuple[str, str], tuple[float, float]] = {}
    quarters: dict[tuple[str, str], dict[int, float]] = defaultdict(dict)
    raw_rows = selected = 0
    for row_number, fields in xlsx_rows(payload, "Table 1"):
        if row_number == 3:
            if any(fields.get(column) != title for column, title in header.items()):
                raise ValueError("ONS PIPR column mismatch")
            continue
        if row_number < 4 or not fields.get("A"):
            continue
        raw_rows += 1
        code = fields.get("B", "")
        if code not in UK_GEOGRAPHIES:
            continue
        expected_name, _, _ = UK_GEOGRAPHIES[code]
        if fields.get("C") != expected_name:
            raise ValueError(f"ONS PIPR geography mismatch for {code}")
        date = datetime.strptime(_xlsx_iso_date(fields["A"]), "%Y-%m-%d")
        if date.day != 1:
            raise ValueError(f"ONS PIPR unexpected month: {date.date()}")
        key = (code, date.strftime("%Y-%m"))
        if key in monthly:
            raise ValueError(f"Duplicate ONS code and month: {key}")
        try:
            index = float(fields["E"])
            rent = float(fields["H"])
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Missing ONS value: {key}") from exc
        if index <= 0 or rent <= 0:
            raise ValueError(f"Nonpositive ONS value: {key}")
        monthly[key] = (index, rent)
        period = f"{date.year}Q{(date.month - 1) // 3 + 1}"
        quarters[(code, period)][date.month] = index
        selected += 1
    if not monthly:
        raise ValueError("No ONS PIPR observations")
    rows: list[dict[str, object]] = []
    for (code, month), (_, rent) in sorted(monthly.items()):
        _, geo_id, label = UK_GEOGRAPHIES[code]
        rows.append(
            {
                "source_id": "uk_pipr",
                "geo_id": geo_id,
                "geo_label": label,
                "asset_type": "private_rented_residential",
                "metric": "monthly_rent_gbp",
                "period": month,
                "frequency": "monthly",
                "value": rent,
                "unit": "GBP/month",
                "remark": "achieved_existing_and_new_tenancies",
            }
        )
    incomplete = set()
    for (code, period), months in sorted(
        quarters.items(), key=lambda item: (item[0][1], item[0][0])
    ):
        quarter = int(period[-1])
        required = {3 * quarter - 2, 3 * quarter - 1, 3 * quarter}
        if set(months) != required:
            incomplete.add(period)
            continue
        _, geo_id, label = UK_GEOGRAPHIES[code]
        rows.append(
            {
                "source_id": "uk_pipr",
                "geo_id": geo_id,
                "geo_label": label,
                "asset_type": "private_rented_residential",
                "metric": "rent_index",
                "period": period,
                "frequency": "quarterly",
                "value": statistics.mean(months.values()),
                "unit": "index",
                "remark": "three_month_mean",
            }
        )
    return rows, {
        "raw_rows": raw_rows,
        "selected_months": selected,
        "incomplete_quarters": sorted(incomplete),
    }


def parse_nsw_bonds(
    payload: bytes, month: str
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Summarise flat/unit 1–2 bedroom lodgements, keeping the postcode boundary explicit."""
    header = {
        "A": "Lodgement Date",
        "B": "Postcode",
        "C": "Dwelling Type",
        "D": "Bedrooms",
        "E": "Weekly Rent",
    }
    groups: dict[str, list[float]] = {"nsw_state": [], "nsw_postcode_2000": []}
    raw_rows = unknown = zero = invalid_dwelling = positive = 0
    for row_number, fields in xlsx_rows(payload, "August26 Rental Bond Lodgments"):
        if row_number == 3:
            if any(fields.get(column) != title for column, title in header.items()):
                raise ValueError("NSW rental bond column mismatch")
            continue
        if row_number < 4 or not fields.get("A"):
            continue
        raw_rows += 1
        date = _xlsx_iso_date(fields["A"])
        if not date.startswith(month + "-"):
            raise ValueError(f"NSW rental bond wrong month: {date}")
        dwelling = fields.get("C", "")
        if dwelling not in {"F", "H", "T", "O", "U"}:
            invalid_dwelling += 1
        rent_text = fields.get("E", "")
        if rent_text in {"U", ""}:
            unknown += 1
            continue
        try:
            rent = float(rent_text)
        except ValueError as exc:
            raise ValueError(f"Unexpected NSW rent: {rent_text}") from exc
        if rent < 0:
            raise ValueError("Negative NSW rent")
        if rent == 0:
            zero += 1
            continue
        positive += 1
        if dwelling == "F" and fields.get("D") in {"1", "2"}:
            groups["nsw_state"].append(rent)
            if fields.get("B") == "2000":
                groups["nsw_postcode_2000"].append(rent)
    if raw_rows == 0 or not groups["nsw_state"] or not groups["nsw_postcode_2000"]:
        raise ValueError("No NSW rental bond segment observations")
    rows = [
        {
            "source_id": "nsw_bonds",
            "geo_id": geo_id,
            "geo_label": "NSW州全体" if geo_id == "nsw_state" else "postcode 2000",
            "asset_type": "flat_unit_1_2_bedroom_new_tenancy",
            "metric": "median_weekly_rent_aud",
            "period": month,
            "frequency": "monthly",
            "value": statistics.median(values),
            "unit": "AUD/week",
            "count": len(values),
            "remark": "positive_rent_only",
        }
        for geo_id, values in groups.items()
    ]
    return rows, {
        "raw_rows": raw_rows,
        "positive_rent": positive,
        "unknown_rent": unknown,
        "zero_rent": zero,
        "invalid_dwelling": invalid_dwelling,
        "segment_count": len(groups["nsw_state"]),
    }


def uk_price_rent_metrics(
    price_series: dict[str, dict[str, float]], rent_rows: list[dict[str, object]]
) -> dict[str, dict[str, object]]:
    """Compare changes in the two UK indices where both quarters exist."""
    result = {}
    for geo_id, prices in price_series.items():
        rents = {
            str(row["period"]): float(row["value"])
            for row in rent_rows
            if row["geo_id"] == geo_id and row["metric"] == "rent_index"
        }
        monthly = {
            str(row["period"]): float(row["value"])
            for row in rent_rows
            if row["geo_id"] == geo_id and row["metric"] == "monthly_rent_gbp"
        }
        price_rebased = rebase(prices, "2015Q1")
        rent_rebased = rebase(rents, "2015Q1")
        common = sorted(price_rebased.keys() & rent_rebased.keys())
        latest_month = max(monthly)
        result[geo_id] = {
            "rent_raw": rents,
            "rent_rebased": rent_rebased,
            "relative_price_rent": {
                period: relative_price_rent(price_rebased[period], rent_rebased[period])
                for period in common
            },
            "latest_monthly_rent": {"period": latest_month, "value": monthly[latest_month]},
        }
    return result


def _verified_payloads(raw: Path) -> tuple[dict[str, object], dict[str, bytes]]:
    manifest = json.loads((raw / "manifest.json").read_text(encoding="utf-8"))
    payloads = {}
    for source_id, entry in manifest["sources"].items():
        if entry["status"] != "ok":
            raise ValueError(f"Source {source_id} was not collected: {entry['reason']}")
        payload = (raw / entry["file"]).read_bytes()
        if hashlib.sha256(payload).hexdigest() != entry["sha256"]:
            raise ValueError(f"SHA-256 mismatch: {source_id}")
        payloads[source_id] = payload
    return manifest, payloads


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_dataset(raw: Path, processed: Path, l01_dir: Path | None = None) -> Path:
    """Verify saved originals and derive observations, coverage and chart data.

    ``l01_dir`` holds the saved Fukuoka L01 ZIPs, needed only when the run's Fukuoka
    snapshot predates the previous-code link fields.
    """
    manifest, payloads = _verified_payloads(raw)
    required = {"jp_fukuoka_land", "hk_rent_q", "hk_price_q"}
    if not required.issubset(payloads):
        raise ValueError(f"Missing required sources: {sorted(required - payloads.keys())}")
    rent = parse_hk_csv(payloads["hk_rent_q"], "hk_rent_q")
    price = parse_hk_csv(payloads["hk_price_q"], "hk_price_q")
    fukuoka = parse_fukuoka_csv(payloads["jp_fukuoka_land"])
    observations = rent + price + fukuoka
    hk_rent = {str(x["period"]): float(x["value"]) for x in rent if x["value"] is not None}
    hk_price = {str(x["period"]): float(x["value"]) for x in price if x["value"] is not None}
    rent_rebased = rebase(hk_rent, "2015Q1")
    price_rebased = rebase(hk_price, "2015Q1")
    relative = {
        period: relative_price_rent(value, rent_rebased[period])
        for period, value in price_rebased.items()
        if period in rent_rebased
    }
    ward_series: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
    for row in fukuoka:
        ward_series[str(row["geo_id"])][str(row["period"])] = {
            "value": row["value"],
            "count": row["count"],
            "label": row["geo_label"],
        }
    coverage: list[dict[str, object]] = []
    for source_id, rows in (("hk_rent_q", rent), ("hk_price_q", price)):
        coverage.append(
            {
                "source_id": source_id,
                "status": "ok",
                "period_start": rows[0]["period"],
                "period_end": rows[-1]["period"],
                "raw_rows": len(rows),
                "valid_observations": sum(x["value"] is not None for x in rows),
                "series_count": 1,
                "unique_properties": "",
                "missing_observations": sum(x["value"] is None for x in rows),
                "reason": "",
            }
        )
    all_land_rows = list(
        csv.DictReader(io.StringIO(payloads["jp_fukuoka_land"].decode("utf-8-sig")))
    )
    residential_rows = sum(x["code_group"] == "000" for x in all_land_rows)
    years = sorted(ward_series["fukuoka_city"])
    coverage.append(
        {
            "source_id": "jp_fukuoka_land",
            "status": "ok",
            "period_start": years[0],
            "period_end": years[-1],
            "raw_rows": len(all_land_rows),
            "valid_observations": residential_rows,
            "series_count": len(ward_series),
            "unique_properties": "",
            "missing_observations": 0,
            "reason": "",
        }
    )
    uk_summary = None
    if "uk_hpi_index" in payloads:
        uk_rows, uk_stats = parse_uk_index(payloads["uk_hpi_index"])
        observations.extend(uk_rows)
        uk_series = {
            geo_id: {
                str(row["period"]): float(row["value"])
                for row in uk_rows
                if row["geo_id"] == geo_id
            }
            for _, geo_id, _ in UK_GEOGRAPHIES.values()
        }
        uk_summary = {
            "asset_type": "residential_all_types",
            "base_period": "2015Q1",
            "series": {
                geo_id: {"raw": series, "rebased": rebase(series, "2015Q1")}
                for geo_id, series in uk_series.items()
            },
            "incomplete_quarters": uk_stats["incomplete_quarters"],
            "geographies": {geo_id: label for _, geo_id, label in UK_GEOGRAPHIES.values()},
            "release": "2026-07",
        }
        periods = sorted({str(x["period"]) for x in uk_rows})
        coverage.append(
            {
                "source_id": "uk_hpi_index",
                "status": "ok",
                "period_start": periods[0],
                "period_end": periods[-1],
                "raw_rows": uk_stats["raw_rows"],
                "valid_observations": uk_stats["selected_months"],
                "series_count": len(UK_GEOGRAPHIES),
                "unique_properties": "",
                "missing_observations": 0,
                "reason": f"Incomplete quarters excluded: {', '.join(uk_stats['incomplete_quarters'])}",
            }
        )
    ons_summary = None
    if "uk_pipr" in payloads:
        ons_rows, ons_stats = parse_ons_pipr(payloads["uk_pipr"])
        observations.extend(ons_rows)
        if uk_summary is not None:
            raw_uk_prices = {
                geo_id: values["raw"] for geo_id, values in uk_summary["series"].items()
            }
            ons_summary = {
                "release": "2026-09-16",
                "series": uk_price_rent_metrics(raw_uk_prices, ons_rows),
                "incomplete_quarters": ons_stats["incomplete_quarters"],
            }
        rent_months = sorted(
            str(row["period"]) for row in ons_rows if row["metric"] == "monthly_rent_gbp"
        )
        coverage.append(
            {
                "source_id": "uk_pipr",
                "status": "ok",
                "period_start": rent_months[0],
                "period_end": rent_months[-1],
                "raw_rows": ons_stats["raw_rows"],
                "valid_observations": ons_stats["selected_months"],
                "series_count": len(UK_GEOGRAPHIES),
                "unique_properties": "",
                "missing_observations": 0,
                "reason": f"Incomplete quarters excluded: {', '.join(ons_stats['incomplete_quarters'])}",
            }
        )
    nsw_summary = None
    if "nsw_bonds" in payloads:
        nsw_rows, nsw_stats = parse_nsw_bonds(payloads["nsw_bonds"], "2026-08")
        observations.extend(nsw_rows)
        nsw_summary = {
            "month": "2026-08",
            "geographies": {
                str(row["geo_id"]): {
                    "label": row["geo_label"],
                    "median_weekly_rent_aud": row["value"],
                    "lodgements": row["count"],
                }
                for row in nsw_rows
            },
            "quality": nsw_stats,
        }
        coverage.append(
            {
                "source_id": "nsw_bonds",
                "status": "ok",
                "period_start": "2026-08",
                "period_end": "2026-08",
                "raw_rows": nsw_stats["raw_rows"],
                "valid_observations": nsw_stats["positive_rent"],
                "series_count": 2,
                "unique_properties": "",
                "missing_observations": nsw_stats["unknown_rent"] + nsw_stats["zero_rent"],
                "reason": "Unknown/zero rent excluded; invalid dwelling code counted separately",
            }
        )
    link_rows, link_source = fukuoka_link_rows(payloads["jp_fukuoka_land"], l01_dir)
    summary = {
        "run_id": manifest["run_id"],
        "retrieved_at": manifest["retrieved_at"],
        "hong_kong": {
            "asset_type": "private_domestic_all_classes",
            "base_period": "2015Q1",
            "rent_index": hk_rent,
            "price_index": hk_price,
            "rent_rebased": rent_rebased,
            "price_rebased": price_rebased,
            "relative_price_rent": relative,
            "missing_periods": {
                "rent": [str(x["period"]) for x in rent if x["value"] is None],
                "price": [str(x["period"]) for x in price if x["value"] is None],
            },
            "provisional_periods": {
                "rent": [str(x["period"]) for x in rent if "P" in str(x["remark"])],
                "price": [str(x["period"]) for x in price if "P" in str(x["remark"])],
            },
        },
        "fukuoka": {
            "asset_type": "residential_land",
            "city": ward_series["fukuoka_city"],
            "wards": {k: v for k, v in ward_series.items() if k != "fukuoka_city"},
            "matched_site": {
                **fukuoka_matched_site_index(link_rows),
                "method": FUKUOKA_LINK_METHOD,
                **link_source,
            },
        },
    }
    if uk_summary is not None:
        summary["united_kingdom"] = uk_summary
    if ons_summary is not None:
        summary["uk_rents"] = ons_summary
    if nsw_summary is not None:
        summary["nsw_bonds"] = nsw_summary
    processed.mkdir(parents=True, exist_ok=True)
    _write_csv(
        processed / "observations.csv",
        [
            "source_id",
            "geo_id",
            "asset_type",
            "metric",
            "period",
            "frequency",
            "value",
            "unit",
            "remark",
            "count",
            "raw_value",
            "geo_label",
        ],
        observations,
    )
    _write_csv(
        processed / "coverage.csv",
        [
            "source_id",
            "status",
            "period_start",
            "period_end",
            "raw_rows",
            "valid_observations",
            "series_count",
            "unique_properties",
            "missing_observations",
            "reason",
        ],
        coverage,
    )
    (processed / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return processed


def _period_number(period: str, frequency: str) -> int:
    if frequency == "annual":
        return int(period)
    if frequency == "quarterly":
        return int(period[:4]) * 4 + int(period[-1]) - 1
    raise ValueError(f"Unsupported frequency: {frequency}")


def line_segments(points: dict[str, float], frequency: str) -> list[list[tuple[str, float]]]:
    """Split at absent periods so a plotted path cannot bridge a data gap."""
    segments: list[list[tuple[str, float]]] = []
    for period, value in sorted(points.items()):
        if (
            not segments
            or _period_number(period, frequency)
            != _period_number(segments[-1][-1][0], frequency) + 1
        ):
            segments.append([])
        segments[-1].append((period, value))
    return segments


def _chart(
    series: dict[str, dict[str, float]],
    frequency: str,
    unit: str,
    colors: list[str],
    markers: dict[str, str] | None = None,
) -> str:
    all_points = [(period, value) for points in series.values() for period, value in points.items()]
    if not all_points:
        return "<p>有効な観測値がありません。</p>"
    xs = [_period_number(period, frequency) for period, _ in all_points]
    values = [value for _, value in all_points]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(values), max(values)
    spread = max(y1 - y0, y1 * 0.1, 1)
    y0 = max(0, y0 - spread * 0.08)
    y1 += spread * 0.08
    left, right, top, bottom = 68, 820, 18, 286

    def xcoord(period: str) -> float:
        return left + (_period_number(period, frequency) - x0) * (right - left) / max(x1 - x0, 1)

    def ycoord(value: float) -> float:
        return bottom - (value - y0) * (bottom - top) / (y1 - y0)

    parts = [
        f'<svg viewBox="0 0 850 326" role="img" aria-label="{html.escape(unit)}の時系列グラフ">'
    ]
    for step in range(5):
        value = y0 + (y1 - y0) * step / 4
        y = ycoord(value)
        parts.append(
            f'<line x1="{left}" x2="{right}" y1="{y:.1f}" y2="{y:.1f}" style="stroke:var(--grid)"/>'
        )
        parts.append(
            f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="11">{value:,.0f}</text>'
        )
    tick_periods = sorted({period for period, _ in all_points})
    for index in sorted({round((len(tick_periods) - 1) * step / 4) for step in range(5)}):
        period = tick_periods[index]
        parts.append(
            f'<text x="{xcoord(period):.1f}" y="310" text-anchor="middle" font-size="11">{html.escape(period)}</text>'
        )
    for period, note in (markers or {}).items():
        if x0 <= _period_number(period, frequency) <= x1:
            x = xcoord(period)
            parts.append(
                f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top}" y2="{bottom}" '
                'style="stroke:var(--ink-3)" stroke-dasharray="3 3"/>'
                f'<text x="{x + 4:.1f}" y="{top + 10}" font-size="10">{html.escape(note)}</text>'
            )
    for (label, points), color in zip(series.items(), colors, strict=True):
        for segment in line_segments(points, frequency):
            coords = " ".join(
                f"{xcoord(period):.1f},{ycoord(value):.1f}" for period, value in segment
            )
            if len(segment) > 1:
                parts.append(
                    f'<polyline points="{coords}" fill="none" style="stroke:var({color})" stroke-width="2.3" stroke-linejoin="round"/>'
                )
            for period, value in segment:
                parts.append(
                    f'<circle cx="{xcoord(period):.1f}" cy="{ycoord(value):.1f}" r="2" '
                    f'style="fill:var({color})"><title>{html.escape(label)} {html.escape(period)}: '
                    f"{value:,.1f} {html.escape(unit)}</title></circle>"
                )
    parts.append("</svg>")
    return "".join(parts)


def _sparkline(points: dict[str, float], label: str) -> str:
    values = list(points.values())
    if not values:
        return "—"
    years = [int(year) for year in points]
    xmin, xmax = min(years), max(years)
    ymin, ymax = min(values), max(values)

    def xcoord(year: str) -> float:
        return 3 + (int(year) - xmin) * 174 / max(xmax - xmin, 1)

    def ycoord(value: float) -> float:
        return 42 - (value - ymin) * 36 / max(ymax - ymin, 1)

    paths = []
    for segment in line_segments(points, "annual"):
        coords = " ".join(f"{xcoord(year):.1f},{ycoord(value):.1f}" for year, value in segment)
        if len(segment) > 1:
            paths.append(
                f'<polyline points="{coords}" fill="none" style="stroke:var(--series-2)" '
                'stroke-width="2.2" stroke-linejoin="round"/>'
            )
    year = max(points)
    paths.append(
        f'<circle cx="{xcoord(year):.1f}" cy="{ycoord(points[year]):.1f}" r="2.7" '
        'style="fill:var(--series-2)"/>'
    )
    return (
        f'<svg class="spark" viewBox="0 0 180 46" role="img" '
        f'aria-label="{html.escape(label)}の{min(years)}年から{max(years)}年の年次推移">'
        f"<title>{html.escape(label)}：{min(years)}–{max(years)}年、最新 {points[year]:,.0f}円/土地㎡</title>"
        + "".join(paths)
        + "</svg>"
    )


def _figure(
    title: str,
    sub: str,
    series: dict[str, dict[str, float]],
    frequency: str,
    unit: str,
    colors: list[str],
    caption: str,
    markers: dict[str, str] | None = None,
) -> str:
    colors = colors[: len(series)]
    legend = "".join(
        f'<span><i style="background:var({color})"></i>{html.escape(label)}</span>'
        for label, color in zip(series, colors, strict=True)
    )
    return (
        f'<figure><p class="figtitle">{html.escape(title)}</p>'
        f'<p class="figsub">{html.escape(sub)}</p><div class="legend">{legend}</div>'
        f'<div class="scroll">{_chart(series, frequency, unit, colors, markers)}</div>'
        f"<figcaption>{html.escape(caption)}</figcaption></figure>"
    )


def _pct_change(points: dict[str, float], end: str, years: int) -> str:
    previous = f"{int(end[:4]) - years}{end[4:]}"
    if end not in points or previous not in points:
        return "—"
    return f"{100 * (points[end] / points[previous] - 1):+.1f}%"


def _source_origin(source_id: str, entry: dict) -> str:
    """Describe a source without the collecting machine's absolute paths."""
    origin = str(entry["source"])
    if source_id == "jp_fukuoka_land":
        return (
            f"国土数値情報 地価公示（L01）福岡県 {entry['period_start']}–{entry['period_end']}年のZIP"
            "（_data/market-research/market/raw/land_price_history_fukuoka/、"
            "SHA-256はmanifest.json）から scripts/analysis/fukuoka_land_price_history.py "
            "で作ったCSVの、run時点の複製"
        )
    return origin if origin.startswith(("http://", "https://")) else Path(origin).name


def render_report(raw: Path, processed: Path, css_path: Path) -> Path:
    """Write an offline HTML report with source-backed, separately typed panels."""
    summary = json.loads((processed / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((raw / "manifest.json").read_text(encoding="utf-8"))
    with (processed / "coverage.csv").open(encoding="utf-8") as stream:
        coverage = list(csv.DictReader(stream))
    hk = summary["hong_kong"]
    latest_hk = max(set(hk["price_rebased"]) & set(hk["rent_rebased"]))
    relative_now = hk["relative_price_rent"][latest_hk]
    city = summary["fukuoka"]["city"]
    latest_year = max(city)
    city_value = city[latest_year]["value"]
    city_count = city[latest_year]["count"]
    matched = summary["fukuoka"]["matched_site"]
    matched_index = matched["index"]
    css = css_path.read_text(encoding="utf-8")
    e = html.escape
    retrieved_at = summary["retrieved_at"][:16].replace("T", " ") + " UTC"
    sections = []
    sections.append(
        '<section><div class="head"><span class="step">01</span><h2>香港｜住宅価格と賃料</h2></div>'
        '<div class="col"><p>民間住宅の全クラス指数（原系列は1999年=100）を2015年第1四半期=100に揃えた。'
        "両系列の差は価格と賃料の<strong>相対変化</strong>であり、同一住戸の価格・賃料ではない。</p></div>"
    )
    sections.append(
        _figure(
            "価格指数と賃料指数",
            "香港全域・民間住宅全クラス／四半期／2015Q1=100",
            {"価格": hk["price_rebased"], "賃料": hk["rent_rebased"]},
            "quarterly",
            "指数",
            ["--series-1", "--series-2"],
            "欠損四半期は線を結ばない。元の指数をそれぞれ同じ期でリベースした。",
        )
    )
    sections.append(
        _figure(
            "価格／賃料の相対指数",
            "100 × 価格の対2015Q1倍率 ÷ 賃料の対2015Q1倍率",
            {"相対指数": hk["relative_price_rent"]},
            "quarterly",
            "相対指数",
            ["--series-1"],
            "100超は基準期より価格の伸びが賃料を上回った意味。利回りではない。",
        )
    )
    change_rows = "".join(
        f'<tr><td>{years}年</td><td class="num">{_pct_change(hk["price_index"], latest_hk, years)}</td>'
        f'<td class="num">{_pct_change(hk["rent_index"], latest_hk, years)}</td></tr>'
        for years in (1, 5, 10)
    )
    sections.append(
        '<div class="tw"><table><caption>同じ四半期との変化率（現地名目）</caption>'
        "<thead><tr><th>期間</th><th>価格</th><th>賃料</th></tr></thead>"
        f"<tbody>{change_rows}</tbody></table></div>"
        '<div class="note"><span class="lab">読取上の注意</span>'
        f"<p>欠損：賃料 {e(', '.join(hk['missing_periods']['rent']) or 'なし')}、"
        f"価格 {e(', '.join(hk['missing_periods']['price']) or 'なし')}。"
        f"暫定 P：賃料 {e(', '.join(hk['provisional_periods']['rent']) or 'なし')}、"
        f"価格 {e(', '.join(hk['provisional_periods']['price']) or 'なし')}。"
        "この指数から表面利回りやNOI利回りは算出できない。</p></div></section>"
    )
    sections.append(
        '<section><div class="head"><span class="step">02</span><h2>福岡｜住宅地の公示価格</h2></div>'
        '<div class="col"><p>価格変化は、国土数値情報の前年地点コードで前年とつないだ住宅地'
        "（継続・番号変更）の変化率中央値を連鎖した指数で示す。"
        "同一地点を全期間固定した指数ではない。価格水準は各年の断面平均として別に示す。</p></div>"
    )
    fewest = min(matched["matches"], key=lambda year: (matched["matches"][year], year))
    sections.append(
        _figure(
            "福岡市の住宅地・継続地点連鎖指数",
            f"{min(matched_index)}年=100／前年地点コードで接続した住宅地（継続・番号変更）の変化率中央値を連鎖",
            {"福岡市": matched_index},
            "annual",
            "指数",
            ["--series-1"],
            f"{latest_year}年は前年から{matched['matches'][latest_year]}地点を接続"
            f"（最少は{fewest}年の{matched['matches'][fewest]}地点）。"
            "点線は標本・定義の変わり目：1994–95年の地点急増、"
            "2013年の用途区分変更（前年が別区分の地点は接続しない）、"
            "2022年の所在表記の地番表示への変更（地点コードで接続）。標本は年ごとに変わる。",
            FUKUOKA_BREAKS,
        )
    )
    city_points = {year: row["value"] for year, row in city.items()}
    sections.append(
        _figure(
            "福岡市の住宅地・断面平均価格",
            "1983–2026年／円・土地㎡／各年の住宅地標準地の断面平均",
            {"福岡市": city_points},
            "annual",
            "円/土地㎡",
            ["--series-1"],
            f"{latest_year}年は{city_count}地点。各年の対象地点数・構成は変わる。",
        )
    )
    ward_data = summary["fukuoka"]["wards"]
    ward_rows = "".join(
        f"<tr><td>{e(points[latest_year]['label'])}</td>"
        f"<td>{_sparkline({year: row['value'] for year, row in points.items()}, points[latest_year]['label'])}</td>"
        f'<td class="num">{points[latest_year]["value"]:,.0f}</td>'
        f'<td class="num">{points[latest_year]["count"]}</td></tr>'
        for points in ward_data.values()
        if latest_year in points
    )
    sections.append(
        f'<div class="tw"><table><caption>7区の年次推移と{latest_year}年の住宅地</caption>'
        "<thead><tr><th>区</th><th>年次推移</th><th>平均 円/土地㎡</th><th>地点数</th></tr></thead>"
        f"<tbody>{ward_rows}</tbody></table></div>"
        "<p>小図は区ごとに縦軸を設定。傾きや高さは区間で直接比較できない。"
        "各年の地点数・構成も異なる。元の全観測値はobservations.csvに保存。</p></section>"
    )
    if "united_kingdom" in summary:
        uk = summary["united_kingdom"]
        uk_series = {
            uk["geographies"][geo_id]: values["rebased"] for geo_id, values in uk["series"].items()
        }
        sections.append(
            '<section><div class="head"><span class="step">03</span><h2>英国｜住宅価格指数</h2></div>'
            '<div class="col"><p>ロンドンは広域の地域（E12000007）、マンチェスターは市自治体'
            "（E08000003）。どちらも全住宅タイプの価格指数で、2015Q1=100に揃えた。"
            "1995年以降の系列に限定し、3か月揃わない四半期を除外した。"
            "直近値は取引登録の遅れに伴い改定され得る。</p></div>"
        )
        sections.append(
            _figure(
                "ロンドン地域とマンチェスター市",
                "UK HPI／四半期平均／現地名目価格指数／2015Q1=100",
                uk_series,
                "quarterly",
                "指数",
                ["--series-1", "--series-2"],
                f"公開版 {uk['release']}。不完全な四半期 {', '.join(uk['incomplete_quarters']) or 'なし'} は表示しない。",
            )
        )
        sections.append(
            '<div class="note"><span class="lab">比較できない部分</span>'
            + (
                "<p>一棟NOIは未収集。価格と家賃の指数から期待利回りは推定しない。"
                if "uk_rents" in summary
                else "<p>英国の家賃・一棟NOIは未収集。価格だけから期待利回りは推定しない。"
            )
            + "ロンドン地域とマンチェスター市の地理範囲も同一ではない。</p></div>"
        )
        if "uk_rents" in summary:
            rents = summary["uk_rents"]
            sections.append(
                "<h3>英国｜家賃と価格の伸び</h3><p>ONSの民間賃貸住宅は既存契約と新規契約を含む。"
                "UK HPIの購入住宅と同一物件の組ではない。2015Q1=100に揃え、"
                "3か月揃った四半期のみ比較する。</p>"
            )
            for geo_id, label in uk["geographies"].items():
                price_points = uk["series"][geo_id]["rebased"]
                rent_points = rents["series"][geo_id]["rent_rebased"]
                common = sorted(price_points.keys() & rent_points.keys())
                sections.append(
                    _figure(
                        f"{label}：価格と家賃",
                        "UK HPI・ONS PIPR／完全四半期／2015Q1=100",
                        {
                            "価格": {p: price_points[p] for p in common},
                            "家賃": {p: rent_points[p] for p in common},
                        },
                        "quarterly",
                        "指数",
                        ["--series-1", "--series-2"],
                        "比較対象は両系列がある四半期のみ。標本・住宅タイプの構成は異なる。",
                    )
                )
            sections.append(
                _figure(
                    "英国：価格／家賃の相対指数",
                    "100 × 価格倍率 ÷ 家賃倍率／2015Q1=100",
                    {
                        uk["geographies"][geo_id]: values["relative_price_rent"]
                        for geo_id, values in rents["series"].items()
                    },
                    "quarterly",
                    "相対指数",
                    ["--series-1", "--series-2"],
                    "100超は基準期より価格が家賃に対して高くなった意味。現物利回りではない。",
                )
            )
            rent_rows = "".join(
                f"<tr><td>{e(uk['geographies'][geo_id])}</td>"
                f"<td>{e(values['latest_monthly_rent']['period'])}</td>"
                f'<td class="num">£{values["latest_monthly_rent"]["value"]:,.0f}/月</td>'
                f'<td class="num">{values["relative_price_rent"][max(values["relative_price_rent"])]:.1f}</td></tr>'
                for geo_id, values in rents["series"].items()
            )
            sections.append(
                '<div class="tw"><table><caption>最新月額家賃と直近完全四半期の相対指数</caption>'
                "<thead><tr><th>地域</th><th>家賃月</th><th>平均月額</th><th>価格/家賃</th></tr></thead>"
                f"<tbody>{rent_rows}</tbody></table></div>"
                "<p>ONSの月額は地域平均で、個別物件の募集家賃やNOIではない。"
                f"家賃の不完全四半期 {e(', '.join(rents['incomplete_quarters']))} は指数比較から除いた。"
                "</p>"
            )
        sections.append("</section>")
    if "nsw_bonds" in summary:
        nsw = summary["nsw_bonds"]
        quality = nsw["quality"]
        nsw_rows = "".join(
            f'<tr><td>{e(value["label"])}</td><td class="num">'
            f"A${value['median_weekly_rent_aud']:,.0f}/週</td>"
            f'<td class="num">{value["lodgements"]:,}</td></tr>'
            for value in nsw["geographies"].values()
        )
        sections.append(
            '<section><div class="head"><span class="step">04</span><h2>NSW｜新規契約の賃料試験集計</h2></div>'
            f"<p>{e(nsw['month'])}の賃貸ボンド登録。フラット/ユニットの1〜2寝室・正の週額家賃のみを集計。"
            "州全体とpostcode 2000は同じ集合ではなく、後者はシドニー都市圏全体を表さない。</p>"
            '<div class="tw"><table><caption>入居開始時の週額家賃中央値</caption>'
            "<thead><tr><th>範囲</th><th>中央値</th><th>登録件数</th></tr></thead>"
            f"<tbody>{nsw_rows}</tbody></table></div>"
            f"<p>原本 {quality['raw_rows']:,}行のうち家賃不明 {quality['unknown_rent']:,}、"
            f"0円 {quality['zero_rent']:,}、住宅種類コード不正 {quality['invalid_dwelling']:,}。"
            "同じ記載の登録は物件IDがないため重複と判定していない。"
            "これは1か月の試験値で、価格指数や利回りには接続しない。</p></section>"
        )
    rows = "".join(
        f"<tr><td>{e(row['source_id'])}</td><td>{e(row['period_start'])}–{e(row['period_end'])}</td>"
        f'<td class="num">{int(row["raw_rows"]):,}</td>'
        f'<td class="num">{int(row["valid_observations"]):,}</td>'
        f'<td class="num">{e(row["missing_observations"])}</td></tr>'
        for row in coverage
    )
    source_links = "".join(
        f'<li><a href="{e(entry["catalog_url"], quote=True)}">{e(source_id)}</a>：'
        f"{e(_source_origin(source_id, entry))}（SHA-256 {e(entry['sha256'][:12])}…）"
        f' <a href="{e(entry["terms_url"], quote=True)}">利用条件</a></li>'
        for source_id, entry in manifest["sources"].items()
    )
    uk_coverage = next((row for row in coverage if row["source_id"] == "uk_hpi_index"), None)
    uk_count_note = (
        f"英国は対象2地域の月次{int(uk_coverage['valid_observations']):,}観測"
        f"（図では完全四半期{sum(len(item['raw']) for item in summary['united_kingdom']['series'].values()):,}点）で、"
        if uk_coverage
        else ""
    )
    sections.append(
        f'<section><div class="head"><span class="step">{"05" if "nsw_bonds" in summary else "04"}</span><h2>収集範囲と限界</h2></div>'
        '<div class="tw"><table><caption>原本の行数と有効な入力観測</caption>'
        "<thead><tr><th>原本</th><th>対象期間</th><th>原本行数</th><th>有効入力</th><th>欠損</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
        "<p>福岡の有効入力は住宅地の地点×年。香港は四半期の指数観測、"
        + uk_count_note
        + "独立した物件件数ではない。"
        + (
            "NSWの有効入力は正の家賃登録行数で、表はその部分集合。"
            if "nsw_bonds" in summary
            else ""
        )
        + "福岡の地価と海外の建物込み住宅指数は別の資産。"
        "地価の絶対額を為替換算して都市間ランキングにはしない。</p>"
        + (
            "<p>未収集：都市別の比較可能な実取得価格・同一物件の賃料と運営費、NOI、Cap Rate、"
            if "uk_rents" in summary
            else "<p>未収集：都市別の実取得価格、実際の賃料と運営費、NOI、Cap Rate、"
        )
        + "金利・為替・CPI調整。現段階では期待利回りを比較できない。</p>"
        f"<h3>原典</h3><ul>{source_links}</ul>"
        '<p class="report-meta">福岡：国土交通省・地価公示。香港：香港特別行政区政府・'
        "差餉物業估價署（RVD）／DATA.GOV.HK。"
        "Contains HM Land Registry data © Crown copyright and database right 2020. "
        "This data is licensed under the Open Government Licence v3.0."
        + (
            " Price Index of Private Rents: Source: Office for National Statistics (ONS). "
            "Contains public sector information licensed under the Open Government Licence v3.0."
            if "uk_pipr" in manifest["sources"]
            else ""
        )
        + (
            " © State of New South Wales. For current information go to www.nsw.gov.au."
            if "nsw_bonds" in summary
            else ""
        )
        + "</p></section>"
    )
    uk_card = (
        '<div><span class="k">英国価格指数</span><span class="v b">2地域</span>'
        '<span class="n">ロンドン地域とマンチェスター市</span></div>'
        if "united_kingdom" in summary
        else ""
    )
    page = (
        '<!doctype html><html lang="ja"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>都市不動産データ先行調査</title><style>"
        + css
        + "\n.report-meta{font-family:var(--mono);font-size:12px;color:var(--ink-3)}"
        ".spark{width:180px;height:46px}"
        "@media(max-width:700px){.strip{grid-template-columns:1fr}figure .scroll svg{width:760px;max-width:none}}"
        '</style></head><body><div class="wrap"><header class="mast">'
        f'<div class="eyebrow"><span>国際不動産比較</span><span>{e(summary["run_id"])}</span>'
        "<b>公開データの先行調査</b></div>"
        '<h1>都市不動産データ<span class="sub">'
        + (
            "福岡の地価と海外の住宅価格・家賃を、定義ごとに読む"
            if "uk_rents" in summary
            else "福岡の住宅地と海外の住宅指数を、定義ごとに読む"
        )
        + "</span></h1>"
        '<p class="lede">長期系列は取得できた。<strong>'
        + (
            "利回りの国際比較には同一物件の家賃・NOIと資産の揃え込みが必要"
            if "uk_rents" in summary
            else "利回りの国際比較には家賃・NOIと資産の揃え込みが必要"
        )
        + "</strong>。"
        "現段階で示すのは現地名目の価格・賃料の動きと、データの被覆である。</p>"
        '<div class="strip">'
        f'<div><span class="k">福岡市 住宅地 {e(latest_year)}</span><span class="v a">{city_value / 10000:,.1f}<small>万円/㎡</small></span>'
        f'<span class="n">{city_count}地点の断面平均</span></div>'
        f'<div><span class="k">香港 相対価格/賃料 {e(latest_hk)}</span><span class="v b">{relative_now:.1f}</span>'
        '<span class="n">2015Q1=100・利回りではない</span></div>'
        f'<div><span class="k">収集原本</span><span class="v">{len(coverage)}本</span>'
        f'<span class="n">取得 {e(retrieved_at)}</span></div>{uk_card}</div></header>'
        + "".join(sections)
        + f"<footer>run {e(summary['run_id'])}／原本と観測値は同じrunディレクトリに保存。"
        "本資料は取得可否と定義を調べるための研究用レポート。</footer></div></body></html>\n"
    )
    report = processed / "report.html"
    report.write_text(page, encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, help="UTC timestamp, e.g. 20260928T120000Z")
    parser.add_argument("--download", action="store_true", help="Create an immutable raw run")
    parser.add_argument(
        "--uk", action="store_true", help="Include UK HPI July 2026 release on new run"
    )
    parser.add_argument("--ons", action="store_true", help="Include ONS PIPR September 2026 XLSX")
    parser.add_argument("--nsw", action="store_true", help="Include NSW August 2026 bond XLSX")
    args = parser.parse_args(argv)
    project = Path(__file__).resolve().parents[2]
    data_root = project.parent / "_data/market-research"
    raw = data_root / "market" / "raw" / "global_city_pilot" / args.run_id
    processed = data_root / "market" / "processed" / "global_city_pilot" / args.run_id
    if args.download:
        fukuoka = data_root / "market" / "processed" / "fukuoka_land_price_history_1983_2026.csv"
        raw = collect_sources(
            args.run_id,
            data_root,
            fukuoka,
            include_uk=args.uk,
            include_ons=args.ons,
            include_nsw=args.nsw,
        )
    if (args.uk or args.ons or args.nsw) and not args.download:
        parser.error("source flags only select inputs when --download creates a new run")
    build_dataset(raw, processed, data_root / "market" / "raw" / "land_price_history_fukuoka")
    template = project.parent / "docs/templates/claude-report/tokens.css"
    print(render_report(raw, processed, template))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
