"""Rebuild the fixed continuing-site table for Fukuoka City residential land, 2013–2026.

Input is only the saved 2026 L01 ZIP, verified against the ZIP manifest. Each 2026
residential standard site (code group 000 in the 7 wards) carries its surveyed price
history (``surveyedPriceOfS58`` … ``R08``) and its yearly selection status (first digit of
``attributeChangeOf…``). A site enters the fixed set for ``start`` when it has a price in
every year from ``start`` to 2026 and status 1 (continuing) or 2 (renumbered) in every
later year. Figures are medians of per-site price relatives, not ratios of median levels.

Run from ``market-research/``::

    ../.venv/bin/python scripts/analysis/fukuoka_continuing_sites.py [--check]

``--check`` compares the result with the published table and figures in
``docs/data/validation/fukuoka_land_price_history_1983_2026.md`` and exits non-zero on
any difference.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterable, Mapping
from pathlib import Path

from fukuoka_land_price_history import (
    LINK_STATUSES,
    OUT,
    RAW,
    ROOT,
    WARDS,
    child_values,
    verify_manifest,
    zip_path,
)

YEAR = 2026
PUBLISHED = ROOT / "docs/data/validation/fukuoka_land_price_history_1983_2026.md"
STEM = "fukuoka_continuing_sites_2013_2026"


def era_code(year: int) -> str:
    """Return the L01 era suffix: S58=1983 … S63=1988, H01=1989 … H30=2018, R01=2019 …."""
    if 1926 <= year <= 1988:
        return f"S{year - 1925:02d}"
    if year <= 2018:
        return f"H{year - 1988:02d}"
    return f"R{year - 2018:02d}"


def read_sites(raw: Path = RAW, year: int = YEAR) -> list[dict]:
    verify_manifest(raw, [year])
    with zipfile.ZipFile(zip_path(year, raw)) as archive:
        name = next(n for n in archive.namelist() if n.endswith(".xml") and "META" not in n)
        root = ET.fromstring(archive.read(name))
    sites = []
    for element in root:
        if element.tag.rsplit("}", 1)[-1] != "LandPrice":
            continue
        value = child_values(element)
        ward, group, number = value["representedLandCode"].split()
        if ward not in WARDS or group != "000":
            continue
        prices = {y: int(value[f"surveyedPriceOf{era_code(y)}"]) for y in range(1983, year + 1)}
        if prices[year] != int(value["postedLandPrice"]):
            raise ValueError(f"History and posted price differ: {ward}-{number}")
        sites.append(
            {
                "ward_code": ward,
                "ward": WARDS[ward],
                "code_number": number,
                "location": "".join(value["location"].split()),
                "distance_from_station_m": int(value["distanceFromStation"]),
                "floor_area_ratio_pct": int(value["floorAreaRatio"]),
                "prices": prices,
                "statuses": {
                    y: value[f"attributeChangeOf{era_code(y)}"][:1] for y in range(1984, year + 1)
                },
            }
        )
    return sites


def fixed_sites(sites: Iterable[Mapping], start: int, end: int = YEAR) -> list[Mapping]:
    return [
        site
        for site in sites
        if all(site["prices"][y] > 0 for y in range(start, end + 1))
        and all(site["statuses"][y] in LINK_STATUSES for y in range(start + 1, end + 1))
    ]


def median_change_pct(sites: Iterable[Mapping], start: int, end: int = YEAR) -> float:
    return 100 * statistics.median(s["prices"][end] / s["prices"][start] - 1 for s in sites)


def pct(value: float) -> str:
    return f"{value:+.1f}%"


def _areas(sites: list[Mapping]) -> list[tuple[str, list[Mapping]]]:
    wards = [(label, [s for s in sites if s["ward_code"] == code]) for code, label in WARDS.items()]
    return [*wards, ("福岡市", sites)]


def summarize(sites: list[dict]) -> dict:
    fixed_2013 = fixed_sites(sites, 2013)
    fixed_2000 = fixed_sites(sites, 2000)
    near = [s for s in fixed_2013 if s["distance_from_station_m"] <= 1000]
    far = [s for s in fixed_2013 if s["distance_from_station_m"] > 2000]
    dense = [s for s in fixed_2013 if s["floor_area_ratio_pct"] >= 200]
    sparse = [s for s in fixed_2013 if s["floor_area_ratio_pct"] <= 100]
    return {
        "source_zip": zip_path(YEAR).name,
        "residential_sites_2026": len(sites),
        "fixed_2013": {
            "sites": len(fixed_2013),
            "areas": [
                {
                    "area": label,
                    "sites": len(group),
                    "change_2013_2026_pct": median_change_pct(group, 2013),
                    "change_2020_2026_pct": median_change_pct(group, 2020),
                    "change_2025_2026_pct": median_change_pct(group, 2025),
                }
                for label, group in _areas(fixed_2013)
            ],
        },
        "fixed_2000": {
            "sites": len(fixed_2000),
            "areas": [
                {
                    "area": label,
                    "sites": len(group),
                    "change_2000_2026_pct": median_change_pct(group, 2000),
                }
                for label, group in _areas(fixed_2000)
            ],
        },
        "station_distance_2013_2026": {
            "le_1000m": {"sites": len(near), "change_pct": median_change_pct(near, 2013)},
            "gt_2000m": {"sites": len(far), "change_pct": median_change_pct(far, 2013)},
        },
        "floor_area_ratio_2013_2026": {
            "ge_200pct": {"sites": len(dense), "change_pct": median_change_pct(dense, 2013)},
            "le_100pct": {"sites": len(sparse), "change_pct": median_change_pct(sparse, 2013)},
        },
        "below_2013": sum(s["prices"][YEAR] < s["prices"][2013] for s in fixed_2013),
        "site_rows": [
            {
                "ward": s["ward"],
                "code": f"{s['ward_code']}-000-{s['code_number']}",
                "location": s["location"],
                "distance_from_station_m": s["distance_from_station_m"],
                "floor_area_ratio_pct": s["floor_area_ratio_pct"],
                **{f"price_{y}": s["prices"][y] for y in (2000, 2013, 2020, 2025, 2026)},
                "change_2013_2026_pct": round(median_change_pct([s], 2013), 4),
            }
            for s in sorted(fixed_2013, key=lambda s: (s["ward_code"], s["code_number"]))
        ],
    }


def table_rows(summary: Mapping) -> list[tuple[str, int, str, str]]:
    """Ward rows by 2013→2026 change (descending), then the city row."""
    areas = summary["fixed_2013"]["areas"]
    wards = sorted(areas[:-1], key=lambda a: -a["change_2013_2026_pct"])
    return [
        (a["area"], a["sites"], pct(a["change_2013_2026_pct"]), pct(a["change_2020_2026_pct"]))
        for a in [*wards, areas[-1]]
    ]


def published_fragments(summary: Mapping) -> tuple[list[str], dict[str, str]]:
    """Fragments the published note must contain, plus 2025→2026 changes by area."""
    recent = {a["area"]: pct(a["change_2025_2026_pct"]) for a in summary["fixed_2013"]["areas"]}
    fixed_2000 = {a["area"]: pct(a["change_2000_2026_pct"]) for a in summary["fixed_2000"]["areas"]}
    near = summary["station_distance_2013_2026"]["le_1000m"]
    far = summary["station_distance_2013_2026"]["gt_2000m"]
    dense = summary["floor_area_ratio_2013_2026"]["ge_200pct"]
    sparse = summary["floor_area_ratio_2013_2026"]["le_100pct"]
    return [
        f"{summary['residential_sites_2026']}地点のうち",
        f"**{summary['fixed_2000']['sites']}地点**では市全体{fixed_2000['福岡市']}",
        *(f"{ward}{fixed_2000[ward]}" for ward in WARDS.values()),
        f"駅距離1,000m以内は{near['sites']}地点・上昇率中央値{pct(near['change_pct'])}",
        f"2,000m超は{far['sites']}地点・{pct(far['change_pct'])}",
        f"指定容積率200%以上は{dense['sites']}地点・{pct(dense['change_pct'])}",
        f"100%以下は{sparse['sites']}地点・{pct(sparse['change_pct'])}",
        f"2013年を下回る地点は{summary['fixed_2013']['sites']}地点中{summary['below_2013']}地点",
    ], recent


def check_published(summary: Mapping, path: Path = PUBLISHED) -> list[str]:
    text = path.read_text(encoding="utf-8")
    published = {}
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 5 and cells[2].isdigit() and cells[3].endswith("%"):
            published[cells[1]] = (cells[1], int(cells[2]), cells[3], cells[4])
    problems = []
    expected = {row[0]: row for row in table_rows(summary)}
    if published != expected:
        problems.append(f"table differs: published {published} vs computed {expected}")
    fragments, recent = published_fragments(summary)
    problems += [f"missing fragment: {fragment}" for fragment in fragments if fragment not in text]
    sentence = next((s for s in text.split("。") if "2025→2026年を同じ" in s), "")
    for ward, value in re.findall(r"([\u4e00-\u9fff]{1,3}区)([+-]\d+\.\d%)", sentence):
        if recent.get(ward) != value:
            problems.append(f"2025→2026 {ward}: published {value}, computed {recent.get(ward)}")
    return problems


def write_outputs(summary: Mapping, out: Path = OUT) -> tuple[Path, Path]:
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / f"{STEM}.json"
    body = {key: value for key, value in summary.items() if key != "site_rows"}
    json_path.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    csv_path = out / f"{STEM}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary["site_rows"][0]))
        writer.writeheader()
        writer.writerows(summary["site_rows"])
    return json_path, csv_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compare with the published note")
    args = parser.parse_args(argv)
    summary = summarize(read_sites())
    print("| 区 | 継続地点数 | 2013→2026年 | 2020→2026年 |")
    print("|---|---:|---:|---:|")
    for area, count, change_2013, change_2020 in table_rows(summary):
        print(f"| {area} | {count} | {change_2013} | {change_2020} |")
    for path in write_outputs(summary):
        print(path)
    if args.check:
        problems = check_published(summary)
        for problem in problems:
            print(problem)
        print("published note: " + ("MISMATCH" if problems else "matches"))
        return 1 if problems else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
