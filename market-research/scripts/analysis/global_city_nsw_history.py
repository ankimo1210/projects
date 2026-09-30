"""NSW new-tenancy rent history with an auditable Greater Sydney postcode proxy.

The ABS 2021 Mesh Block allocations link Postal Areas (POA) to Greater
Capital City Statistical Areas (GCCSA). An NSW postcode is assigned to the
Greater Sydney proxy when more than half its residential mesh blocks are
in GCCSA 1GSYD. POAs approximate Australia Post postcodes; the resulting
boundary is a proxy, not an exact official postcode-defined metro area.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

import requests
from global_city_xlsx import excel_date, xlsx_rows

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT.parent / "_data/market-research"
RAW = DATA_ROOT / "market/raw/global_city_pilot/nsw_history_20260928"
PROCESSED = DATA_ROOT / "market/processed/global_city_pilot/nsw_history_20260928"
CATALOG = (
    "https://www.nsw.gov.au/housing-and-construction/rental-forms-surveys-and-data/rental-bond-data"
)
ABS_ALLOCATION = "https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs/edition-3-july-2021-june-2026/access-and-downloads/allocation-files/"
ABS_URLS = {
    "abs_mb_2021.xlsx": ABS_ALLOCATION + "MB_2021_AUST.xlsx",
    "abs_poa_2021.xlsx": ABS_ALLOCATION + "POA_2021_AUST.xlsx",
}
MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
HEADER = {
    "A": "Lodgement Date",
    "B": "Postcode",
    "C": "Dwelling Type",
    "D": "Bedrooms",
    "E": "Weekly Rent",
}
GEO_ORDER = ("nsw_state", "greater_sydney_proxy", "nsw_postcode_2000")
BEDROOM_ORDER = ("1", "2", "1-2")
EXPECTED_FILES = {
    *(f"nsw_{year}.xlsx" for year in range(2021, 2026)),
    *(f"nsw_2026-{month:02d}.xlsx" for month in range(1, 9)),
}


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.href: str | None = None
        self.parts: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.parts = []

    def handle_data(self, data: str) -> None:
        if self.href is not None:
            self.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.href is not None:
            self.links.append(("".join(self.parts).strip(), self.href))
            self.href = None


def catalog_sources(html: str, base_url: str) -> dict[str, str]:
    """Map official lodgement links to stable local filenames."""
    parser = _Links()
    parser.feed(html)
    result: dict[str, str] = {}
    months = {
        name: index
        for index, name in enumerate(
            (
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ),
            1,
        )
    }
    for label, href in parser.links:
        annual = re.search(r"lodgement data\s*-\s*year\s+(20\d{2})", label, re.I)
        monthly = re.search(r"lodgement data\s*-\s*([A-Za-z]+)\s+(20\d{2})", label, re.I)
        if annual:
            name = f"nsw_{annual.group(1)}.xlsx"
        elif monthly and monthly.group(1).title() in months:
            name = f"nsw_{monthly.group(2)}-{months[monthly.group(1).title()]:02d}.xlsx"
        else:
            continue
        url = urljoin(base_url, href)
        if name in result and result[name] != url:
            raise ValueError(f"Conflicting NSW catalog link: {name}")
        result[name] = url
    return result


def first_sheet_name(payload: bytes) -> str:
    """Read a workbook's first worksheet name without assuming annual naming."""
    try:
        with ZipFile(io.BytesIO(payload)) as archive:
            workbook = ET.fromstring(archive.read("xl/workbook.xml"))
            sheets = workbook.find(MAIN + "sheets")
            if sheets is None or len(sheets) == 0:
                raise ValueError("XLSX has no worksheets")
            return sheets[0].get("name", "")
    except (BadZipFile, KeyError, ET.ParseError) as exc:
        raise ValueError("Invalid XLSX workbook") from exc


def derive_metro_postcodes(
    mb_payload: bytes, poa_payload: bytes
) -> tuple[dict[str, dict[str, object]], dict[str, int]]:
    """Join ABS 2021 residential mesh blocks to POAs and majority GCCSA."""
    meshblocks: dict[str, str] = {}
    for row_number, fields in xlsx_rows(mb_payload, "MB_2021_AUST"):
        if row_number == 1:
            expected = {
                "A": "MB_CODE_2021",
                "B": "MB_CATEGORY_2021",
                "L": "GCCSA_CODE_2021",
                "N": "STATE_CODE_2021",
            }
            if any(fields.get(column) != label for column, label in expected.items()):
                raise ValueError("ABS Mesh Block allocation column mismatch")
            continue
        if fields.get("N") != "1" or fields.get("B") != "Residential":
            continue
        code = fields.get("A", "")
        if code in meshblocks:
            raise ValueError(f"Duplicate ABS Mesh Block: {code}")
        meshblocks[code] = fields.get("L", "")
    if not meshblocks:
        raise ValueError("No NSW residential Mesh Blocks")
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    seen: set[str] = set()
    unmatched_nsw = 0
    for row_number, fields in xlsx_rows(poa_payload, "POA_2021_AUST"):
        if row_number == 1:
            if fields.get("A") != "MB_CODE_2021" or fields.get("B") != "POA_CODE_2021":
                raise ValueError("ABS Postal Area allocation column mismatch")
            continue
        mb = fields.get("A", "")
        if mb not in meshblocks:
            continue
        if mb in seen:
            raise ValueError(f"Duplicate POA assignment: {mb}")
        seen.add(mb)
        poa = fields.get("B", "")
        if not re.fullmatch(r"\d{4}", poa):
            unmatched_nsw += 1
            continue
        counts[poa][meshblocks[mb]] += 1
    result: dict[str, dict[str, object]] = {}
    for postcode, by_gccsa in counts.items():
        total = sum(by_gccsa.values())
        metro = by_gccsa["1GSYD"]
        result[postcode] = {
            "metro_residential_mb": metro,
            "total_residential_mb": total,
            "metro_share": metro / total,
            "is_metro": 2 * metro > total,
            "is_mixed": 0 < metro < total,
        }
    if "2000" not in result or not result["2000"]["is_metro"]:
        raise ValueError("ABS Sydney CBD postcode missing from metro")
    quality = {
        "nsw_residential_meshblocks": len(meshblocks),
        "assigned_residential_meshblocks": len(seen),
        "unassigned_residential_meshblocks": len(meshblocks) - len(seen),
        "invalid_postcode_meshblocks": unmatched_nsw,
        "nsw_postcodes": len(result),
        "metro_postcodes": sum(bool(entry["is_metro"]) for entry in result.values()),
        "mixed_postcodes": sum(bool(entry["is_mixed"]) for entry in result.values()),
    }
    return result, quality


def _date(text: str) -> str:
    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        return excel_date(text)
    try:
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError as exc:
        raise ValueError(f"Invalid lodgement date: {text}") from exc


def parse_bond_workbook(
    payload: bytes, expected_period: str, postcode_map: dict[str, dict[str, object]]
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Return monthly medians by 1/2 bedrooms and geography, with quality counts."""
    if not re.fullmatch(r"20\d{2}(?:-(?:0[1-9]|1[0-2]))?", expected_period):
        raise ValueError(f"Invalid expected period: {expected_period}")
    groups: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    raw_rows = positive = unknown = zero = invalid_dwelling = unclassified_postcode = 0
    eligible_state = eligible_metro = 0
    sheet = first_sheet_name(payload)
    header_seen = False
    for row_number, fields in xlsx_rows(payload, sheet):
        if row_number == 3:
            if any(fields.get(column) != title for column, title in HEADER.items()):
                raise ValueError(f"NSW rental bond column mismatch: {sheet}")
            header_seen = True
            continue
        if row_number < 4 or not fields.get("A"):
            continue
        raw_rows += 1
        period = _date(fields["A"])[:7]
        if not (
            period == expected_period
            if len(expected_period) == 7
            else period.startswith(expected_period + "-")
        ):
            raise ValueError(f"NSW rental bond wrong source period: {period} vs {expected_period}")
        dwelling = fields.get("C", "")
        if dwelling not in {"F", "H", "T", "O", "U"}:
            invalid_dwelling += 1
        rent_text = fields.get("E", "")
        if rent_text in {"", "U"}:
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
        if dwelling != "F" or fields.get("D") not in {"1", "2"}:
            continue
        bedrooms = fields["D"]
        postcode = fields.get("B", "")
        eligible_state += 1
        groups[period, bedrooms, "nsw_state"].append(rent)
        groups[period, "1-2", "nsw_state"].append(rent)
        if postcode not in postcode_map:
            unclassified_postcode += 1
        elif postcode_map[postcode]["is_metro"]:
            eligible_metro += 1
            groups[period, bedrooms, "greater_sydney_proxy"].append(rent)
            groups[period, "1-2", "greater_sydney_proxy"].append(rent)
        if postcode == "2000":
            groups[period, bedrooms, "nsw_postcode_2000"].append(rent)
            groups[period, "1-2", "nsw_postcode_2000"].append(rent)
    if not header_seen or not raw_rows or not eligible_state:
        raise ValueError(f"No NSW rental bond segment observations: {expected_period}")
    rows = [
        {
            "source_id": "nsw_bonds",
            "period": period,
            "geo_id": geo_id,
            "bedrooms": bedrooms,
            "asset_type": "flat_unit_new_tenancy",
            "metric": "median_weekly_rent_aud",
            "value": statistics.median(values),
            "unit": "AUD/week",
            "count": len(values),
        }
        for (period, bedrooms, geo_id), values in sorted(
            groups.items(),
            key=lambda item: (
                item[0][0],
                BEDROOM_ORDER.index(item[0][1]),
                GEO_ORDER.index(item[0][2]),
            ),
        )
    ]
    return rows, {
        "raw_rows": raw_rows,
        "positive_rent": positive,
        "unknown_rent": unknown,
        "zero_rent": zero,
        "invalid_dwelling": invalid_dwelling,
        "unclassified_postcode_eligible": unclassified_postcode,
        "eligible_state": eligible_state,
        "eligible_metro": eligible_metro,
        "months": sorted({row["period"] for row in rows}),
        "sheet": sheet,
    }


def _fetch_xlsx(url: str) -> bytes:
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    payload = response.content
    if not payload.startswith(b"PK\x03\x04"):
        raise ValueError(f"Non-XLSX response from {url}")
    return payload


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _svg_chart(rows: list[dict[str, object]], bedrooms: str) -> str:
    """Draw two token-coloured monthly rent series with per-point tooltips."""
    selected = [
        row
        for row in rows
        if row["bedrooms"] == bedrooms and row["geo_id"] in {"nsw_state", "greater_sydney_proxy"}
    ]
    periods = sorted({str(row["period"]) for row in selected})
    values = [float(row["value"]) for row in selected]
    if len(periods) < 2 or not values:
        raise ValueError(f"Insufficient monthly series for {bedrooms} bedrooms")
    first = int(periods[0][:4]) * 12 + int(periods[0][5:7])
    last = int(periods[-1][:4]) * 12 + int(periods[-1][5:7])
    ceiling = max(100, ((int(max(values) * 1.08) + 99) // 100) * 100)
    left, right, top, bottom = 62, 826, 28, 268

    def xy(period: str, value: float) -> tuple[float, float]:
        position = int(period[:4]) * 12 + int(period[5:7])
        return (
            left + (position - first) * (right - left) / (last - first),
            bottom - value * (bottom - top) / ceiling,
        )

    parts = [
        '<svg viewBox="0 0 850 310" role="img" '
        f'aria-label="{bedrooms}寝室のNSW州とGreater Sydneyの新規賃貸週額家賃中央値">'
    ]
    for fraction in (0, 0.25, 0.5, 0.75, 1):
        value = ceiling * fraction
        y = bottom - fraction * (bottom - top)
        parts.append(
            f'<line x1="{left}" x2="{right}" y1="{y:.1f}" y2="{y:.1f}" '
            'style="stroke:var(--grid)"/>'
            f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" '
            f'font-size="11">{value:,.0f}</text>'
        )
    for period in [p for p in periods if p.endswith("-01")] + [periods[-1]]:
        x, _ = xy(period, 0)
        parts.append(
            f'<text x="{x:.1f}" y="294" text-anchor="middle" font-size="11">'
            f"{html.escape(period)}</text>"
        )
    for geo_id, label, color in (
        ("greater_sydney_proxy", "Greater Sydney近似", "--series-1"),
        ("nsw_state", "NSW州全体", "--series-2"),
    ):
        points = sorted(
            (str(row["period"]), float(row["value"]), int(row["count"]))
            for row in selected
            if row["geo_id"] == geo_id
        )
        coords = " ".join(
            f"{xy(period, value)[0]:.1f},{xy(period, value)[1]:.1f}" for period, value, _ in points
        )
        parts.append(
            f'<polyline points="{coords}" fill="none" '
            f'style="stroke:var({color})" stroke-width="2.7" '
            'stroke-linejoin="round" stroke-linecap="round"/>'
        )
        for period, value, count in points:
            x, y = xy(period, value)
            parts.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" '
                f'style="fill:var({color})"><title>{label} {period}: '
                f"AUD {value:,.1f}/週, n={count:,}</title></circle>"
            )
    parts.append("</svg>")
    return "".join(parts)


def render_html(rows: list[dict[str, object]], quality: dict[str, object], tokens_css: str) -> str:
    """Build a self-contained report; price and income yields stay separate."""
    lookup = {(str(row["period"]), str(row["bedrooms"]), str(row["geo_id"])): row for row in rows}

    def cell(period: str, bedrooms: str, geo: str) -> tuple[float, int] | None:
        row = lookup.get((period, bedrooms, geo))
        if row is None:
            return None
        return float(row["value"]), int(row["count"])

    def growth(bedrooms: str, geo: str) -> str:
        start = cell("2021-08", bedrooms, geo)
        end = cell("2026-08", bedrooms, geo)
        if start is None or end is None or start[0] <= 0:
            return "—"
        return f"{100 * (end[0] / start[0] - 1):+.1f}%"

    comparison = []
    for bedrooms in ("1", "2", "1-2"):
        for geo, label in (
            ("greater_sydney_proxy", "Greater Sydney近似"),
            ("nsw_state", "NSW州全体"),
            ("nsw_postcode_2000", "postcode 2000"),
        ):
            start, end = cell("2021-08", bedrooms, geo), cell("2026-08", bedrooms, geo)
            if start is None or end is None:
                continue
            comparison.append(
                f"<tr><td>{html.escape(label)}</td><td>{bedrooms}寝室</td>"
                f'<td class="num">{start[0]:,.0f}</td>'
                f'<td class="num">{end[0]:,.0f}</td>'
                f'<td class="num">{growth(bedrooms, geo)}</td>'
                f'<td class="num">{end[1]:,}</td></tr>'
            )
    mapping = quality["mapping"]
    file_quality = quality.get("file_quality", {})
    total_raw = sum(int(item["raw_rows"]) for item in file_quality.values())
    unknown = sum(int(item["unknown_rent"]) for item in file_quality.values())
    unknown_pct = 100 * unknown / total_raw if total_raw else 0
    charts = "".join(
        '<figure><p class="figtitle">'
        f"{bedrooms}寝室の新規賃貸家賃</p>"
        '<p class="figsub">週額中央値（AUD）。同じ寝室数のフラット／ユニットのみ。</p>'
        '<div class="legend"><span><i style="background:var(--series-1)"></i>'
        'Greater Sydney近似</span><span><i style="background:var(--series-2)"></i>'
        "NSW州全体</span></div>"
        f'<div class="scroll">{_svg_chart(rows, bedrooms)}</div>'
        "<figcaption>点にカーソルを合わせると、その月の中央値と登録件数を表示。"
        "同一住戸の家賃改定率ではない。</figcaption></figure>"
        for bedrooms in ("1", "2")
    )
    return (
        '<!doctype html><html lang="ja"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>シドニー賃貸契約の家賃履歴</title><style>"
        + tokens_css
        + "@media(max-width:700px){figure .scroll svg{width:820px;max-width:none}}"
        '</style></head><body><div class="wrap">'
        '<header class="mast"><div class="eyebrow"><span>国際不動産比較</span>'
        "<span>2021-01 – 2026-08</span><b>NSW Rental Bonds</b></div>"
        "<h1>シドニーの新規賃貸家賃"
        '<span class="sub">郵便番号から都市圏を近似し、1寝室・2寝室を分ける</span></h1>'
        '<p class="lede">2021年8月から2026年8月の同月比較では、'
        "<strong>Greater Sydney近似の1寝室は"
        + growth("1", "greater_sydney_proxy")
        + "、2寝室は"
        + growth("2", "greater_sydney_proxy")
        + "</strong>。新規入居時の週額家賃中央値であり、既存契約家賃ではない。</p>"
        '<div class="strip"><div><span class="k">2026年8月・1寝室</span>'
        '<span class="v a">AUD '
        + f"{cell('2026-08', '1', 'greater_sydney_proxy')[0]:,.0f}"
        + '</span><span class="n">Greater Sydney近似・週額中央値</span></div>'
        '<div><span class="k">2026年8月・2寝室</span>'
        '<span class="v b">AUD '
        + f"{cell('2026-08', '2', 'greater_sydney_proxy')[0]:,.0f}"
        + '</span><span class="n">Greater Sydney近似・週額中央値</span></div>'
        '<div><span class="k">月次カバレッジ</span><span class="v">'
        + str(quality["month_count"])
        + '</span><span class="n">2021年1月～2026年8月</span></div></div></header>'
        '<section><div class="head"><span class="step">01</span><h2>家賃の推移</h2></div>'
        '<div class="col"><p>NSW Fair Tradingに届け出られた新規賃貸借の保証金データ。'
        "住宅種類F（フラット／ユニット）、寝室数1または2、週額家賃が正の登録を使用。</p></div>"
        + charts
        + '</section><section><div class="head"><span class="step">02</span>'
        '<h2>同月で比較</h2></div><div class="tw"><table>'
        "<caption>2021年8月と2026年8月・週額家賃中央値（AUD）</caption>"
        "<thead><tr><th>地域</th><th>住戸</th><th>2021-08</th><th>2026-08</th>"
        "<th>変化</th><th>最新n</th></tr></thead><tbody>"
        + "".join(comparison)
        + '</tbody></table></div><div class="note"><span class="lab">構成差</span>'
        "<p>「1–2寝室」合算は参考値。1寝室と2寝室の登録比率が変わるため、"
        "価格変化の判断には寝室別の列を使う。</p></div></section>"
        '<section><div class="head"><span class="step">03</span><h2>地理とデータ品質</h2></div>'
        '<div class="col"><p>ABSの2021年Mesh Block割当で、郵便区域（POA）の居住用'
        "メッシュブロックの過半がGreater Sydney GCCSA（1GSYD）に入る"
        "郵便番号を採用。"
        + str(mapping["metro_postcodes"])
        + "件を含み、"
        + str(mapping["mixed_postcodes"])
        + "件は都市圏境界をまたぐ。POAは実際の郵便番号を近似するため、"
        "この系列はGreater Sydneyの<strong>近似値</strong>。postcode 2000は"
        "中心部の一部で、都市圏全体ではない。</p>"
        f"<p>原本{total_raw:,}登録のうち週額家賃不明は{unknown:,}件"
        f"（{unknown_pct:.2f}%）。不明と0円は中央値から除外した。"
        "毎月の件数はCSVに記録している。</p></div>"
        '<div class="note"><span class="lab">投資利回り</span>'
        "<p>取得価格、運営費、空室、NOI、Cap Rateはこの原本にない。"
        "募集賃料・既存契約賃料とも定義が違うため、この図だけから"
        "一棟物件の利回りや投資IRRは計算しない。</p></div>"
        "<h3>原典</h3><ul>"
        f'<li><a href="{CATALOG}">NSW Fair Trading: Rental bond data</a></li>'
        f'<li><a href="{ABS_ALLOCATION}">ABS ASGS 2021 allocation files</a></li>'
        "</ul></section><footer>© State of New South Wales. "
        "For current information go to www.nsw.gov.au. "
        "ABS ASGS Edition 3 (2021). 作成 2026-09-28。"
        "原本・SHA-256・境界表・月次CSVは検証ノートを参照。</footer>"
        "</div></body></html>"
    )


def run(*, download: bool = False) -> tuple[Path, Path, Path]:
    """Process an archived fixed 2021-01 to 2026-08 source set."""
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    source_urls = dict(ABS_URLS)
    manifest_path = RAW / "manifest.json"
    if download:
        response = requests.get(CATALOG, timeout=30)
        response.raise_for_status()
        catalog = catalog_sources(response.text, CATALOG)
        missing = EXPECTED_FILES - catalog.keys()
        if missing:
            raise ValueError(f"Missing official NSW links: {sorted(missing)}")
        source_urls.update({name: catalog[name] for name in sorted(EXPECTED_FILES)})
        for name, url in source_urls.items():
            path = RAW / name
            if not path.exists():
                path.write_bytes(_fetch_xlsx(url))
        manifest = {
            "catalog": CATALOG,
            "boundary": "ABS ASGS Edition 3 (2021), GCCSA 1GSYD; majority of residential Mesh Blocks by POA",
            "collected_at_utc": datetime.now(UTC).isoformat(),
            "sources": {
                name: {
                    "url": url,
                    "bytes": (RAW / name).stat().st_size,
                    "sha256": hashlib.sha256((RAW / name).read_bytes()).hexdigest(),
                }
                for name, url in sorted(source_urls.items())
            },
        }
        if manifest_path.exists():
            saved = json.loads(manifest_path.read_text(encoding="utf-8"))
            if saved["sources"] != manifest["sources"]:
                raise ValueError("Existing archive differs from catalog; use a new run directory")
        else:
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
            )
    if not manifest_path.is_file():
        raise FileNotFoundError("Archive manifest missing; run --download first")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name in ABS_URLS.keys() | EXPECTED_FILES:
        path = RAW / name
        expected = manifest["sources"][name]["sha256"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Archived source checksum mismatch: {name}")
    mapping, boundary_quality = derive_metro_postcodes(
        (RAW / "abs_mb_2021.xlsx").read_bytes(),
        (RAW / "abs_poa_2021.xlsx").read_bytes(),
    )
    mapping_rows = [{"postcode": postcode, **meta} for postcode, meta in sorted(mapping.items())]
    _write_csv(PROCESSED / "postcode_membership.csv", mapping_rows)
    all_rows: list[dict[str, object]] = []
    file_quality: dict[str, dict[str, object]] = {}
    for name in sorted(EXPECTED_FILES):
        period = name.removeprefix("nsw_").removesuffix(".xlsx")
        rows, quality = parse_bond_workbook((RAW / name).read_bytes(), period, mapping)
        file_quality[name] = quality
        all_rows.extend(rows)
    expected_months = {
        f"{year}-{month:02d}" for year in range(2021, 2026) for month in range(1, 13)
    } | {f"2026-{month:02d}" for month in range(1, 9)}
    observed_months = {str(row["period"]) for row in all_rows}
    if observed_months != expected_months:
        raise ValueError(
            f"Missing/unexpected NSW months: {sorted(expected_months ^ observed_months)}"
        )
    keys = [(row["period"], row["bedrooms"], row["geo_id"]) for row in all_rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate monthly segment after joining source files")
    all_rows.sort(
        key=lambda row: (
            row["period"],
            BEDROOM_ORDER.index(row["bedrooms"]),
            GEO_ORDER.index(row["geo_id"]),
        )
    )
    output = PROCESSED / "monthly_rents.csv"
    _write_csv(output, all_rows)
    quality_path = PROCESSED / "quality.json"
    quality_path.write_text(
        json.dumps(
            {
                "period_start": "2021-01",
                "period_end": "2026-08",
                "month_count": len(observed_months),
                "mapping": boundary_quality,
                "file_quality": file_quality,
                "source_note": (
                    "NSW bond lodgements are new tenancy weekly rents; ABS POA majority "
                    "residential Mesh Block assignment is a Greater Sydney proxy."
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    tokens_path = ROOT.parent / "docs/templates/claude-report/tokens.css"
    html_path = ROOT / "docs/data/validation/global_city_nsw_history_2026-09-28.html"
    html_path.write_text(
        render_html(
            all_rows,
            json.loads(quality_path.read_text(encoding="utf-8")),
            tokens_path.read_text(encoding="utf-8"),
        ),
        encoding="utf-8",
    )
    return output, quality_path, html_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Archive official XLSX sources")
    args = parser.parse_args()
    csv_path, quality_path, html_path = run(download=args.download)
    print(f"Rows: {csv_path}")
    print(f"Quality: {quality_path}")
    print(f"Report: {html_path}")
