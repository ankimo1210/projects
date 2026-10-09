"""ADR two disclosed periods, primary PDF reconciliation, and acquisition evidence."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from global_city_xlsx import xlsx_rows
from japan_noi_valuation import ID, parse_adr_tables

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "_data/market-research/market/raw/noi_expansion_20261001/adr"
OUT = ROOT / "_data/market-research/market/processed/noi_expansion_20261001/adr"


def parse_pdf_income(text: str) -> dict[str, list[int]]:
    section = text.split("Ｃ．個別不動産等の損益状況", 1)[1].split("Ｄ．", 1)[0]
    lines = section.splitlines()
    result = {}
    for index, line in enumerate(lines):
        match = re.match(r"\s*([TSR]-\d{3})\s+(.+)", line)
        if not match:
            continue
        values = re.findall(r"(?<![\w.-])(?:\d[\d,]*|[－-])(?![\w.-])", match[2])
        if len(values) == 10:
            # pdftotext places an expense subtotal in the preceding line in six Jan rows.
            previous = re.findall(r"\d[\d,]*", lines[index - 1]) if index else []
            if len(previous) != 1:
                raise ValueError(f"Missing wrapped expense: {match[1]}")
            values.insert(1, previous[0])
        if len(values) != 11 or match[1] in result:
            raise ValueError(f"Income PDF schema or duplicate: {match[1]}")
        result[match[1]] = [
            0 if values[i] in {"－", "-"} else int(values[i].replace(",", "")) for i in (0, 1, 9)
        ]
    if not result:
        raise ValueError("Empty PDF income")
    return result


def parse_pdf_appraisals(text: str) -> dict[str, int]:
    section = text.split("Ｂ．不動産鑑定評価の概要", 1)[1].split("Ｃ．個別不動産等の損益状況", 1)[0]
    blocks = re.split(r"([TSR]-\d{3})", section)
    result = {}
    for index in range(1, len(blocks), 2):
        key, block = blocks[index : index + 2]
        match = re.search(r"[①②③④⑤]\s+([\d,]+)", block)
        if not match or key in result:
            raise ValueError(f"Appraisal PDF schema or duplicate: {key}")
        result[key] = int(match[1].replace(",", "")) * 1_000_000
    return result


def annual_cohort(prior: list[dict], current: list[dict]) -> tuple[list[dict], list[dict]]:
    old = {p["property_id"]: p for p in prior}
    rows, exclusions = [], []
    for item in current:
        key = item["property_id"]
        previous = old.get(key)
        reason = None
        if previous is None:
            reason = "前期未保有"
        elif not previous["baseline_eligible"] or not item["baseline_eligible"]:
            reason = "端数期間・契約条件"
        elif previous["acquisition_price_yen"] != item["acquisition_price_yen"]:
            reason = "取得額・持分変更"
        if reason:
            exclusions.append({"property_id": key, "reason": reason})
            continue
        row = {
            **item,
            "period_start": previous["period_start"],
            "operating_days": previous["operating_days"] + item["operating_days"],
            "income_basis": "actual_two_full_disclosed_periods",
        }
        for target, source in (
            ("noi_annual_yen", "noi_period_yen"),
            ("revenue_annual_yen", "revenue_period_yen"),
            ("operating_expense_annual_yen", "operating_expense_period_yen"),
            ("capex_annual_yen", "capex_period_yen"),
        ):
            row[target] = previous[source] + item[source]
        if row["operating_days"] != 365:
            raise ValueError("Annual cohort must cover 365 days")
        row.pop("noi_annualized_yen", None)
        row["yield_on_acquisition"] = row["noi_annual_yen"] / row["acquisition_price_yen"]
        row["yield_on_appraisal"] = row["noi_annual_yen"] / row["appraisal_value_yen"]
        rows.append(row)
    return rows, exclusions


def pdf_text(path: Path) -> str:
    return subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def run() -> dict:
    sources = json.loads((RAW / "manifest.json").read_text())
    if isinstance(sources, dict):
        sources = sources["sources"]
    for source in sources:
        path = RAW / source["filename"]
        payload = path.read_bytes()
        size = source.get("size_bytes", source.get("bytes"))
        if len(payload) != size or hashlib.sha256(payload).hexdigest() != source["sha256"]:
            raise ValueError(f"Archive changed: {path.name}")
    periods, qualities = [], []
    # Official financial statement note ※1, property rental income/expenses, thousand yen.
    official = {"202601": (18980758, 8295706, 3716355), "202607": (19547259, 8448397, 3757263)}
    for stamp, start, end, days in (
        ("202601", "2025-08-01", "2026-01-31", 184),
        ("202607", "2026-02-01", "2026-07-31", 181),
    ):
        payload = (RAW / f"adr_{stamp}_property_data.xlsx").read_bytes()
        tables = {
            s: dict(xlsx_rows(payload, s)) for s in ("物件概要", "帳簿価額", "鑑定評価", "収益状況")
        }
        rows, quality = parse_adr_tables(tables, period_days=days)
        text = pdf_text(RAW / f"adr_{stamp}_financial_statement.pdf")
        pdf_income = parse_pdf_income(text)
        pdf_appraisals = parse_pdf_appraisals(text)
        income = tables["収益状況"]
        columns = {key: col for col, key in income[24].items() if ID.fullmatch(key)}
        if set(pdf_income) != set(columns):
            raise ValueError(f"PDF income coverage differs: {stamp}")
        for key, col in columns.items():
            if pdf_income[key] != [int(float(income[r][col])) for r in (26, 28, 36)]:
                raise ValueError(f"PDF/XLSX income differs: {stamp}/{key}")
        detail = [sum(values[i] for values in pdf_income.values()) for i in range(3)]
        reported = official[stamp]
        # Verify the aggregate references really occur in this archived primary PDF.
        if any(f"{value:,}" not in text for value in reported):
            raise ValueError("Official aggregate not found in primary PDF")
        difference = detail[0] - detail[1] + detail[2] - (reported[0] - reported[1] + reported[2])
        conflicts = []
        for row in rows:
            key = row["property_id"]
            value = pdf_appraisals[key]
            if row["appraisal_value_yen"] != value:
                conflicts.append(
                    {"property_id": key, "xlsx_yen": row["appraisal_value_yen"], "pdf_yen": value}
                )
            row.update(
                {
                    "fund": "ADR",
                    "fund_name": "アドバンス・レジデンス投資法人",
                    "period_start": start,
                    "period_end": end,
                    "period_days": days,
                    "currency": "JPY",
                    "asset_type": "賃貸住宅",
                    "appraisal_value_yen": value,
                    "source_url": next(
                        s["url"]
                        for s in sources
                        if s["filename"] == f"adr_{stamp}_property_data.xlsx"
                    ),
                    "appraisal_source_url": next(
                        s["url"]
                        for s in sources
                        if s["filename"] == f"adr_{stamp}_financial_statement.pdf"
                    ),
                    "noi_definition": "rental_revenue_minus_property_expense_excluding_depreciation_before_capex_financing_and_fund_fees",
                }
            )
        quality.update(
            {
                "period_end": end,
                "pdf_income_rows_verified": len(pdf_income),
                "appraisal_conflicts_pdf_preferred": conflicts,
                "official_total_reconciliation": {
                    "all_detail_revenue_expense_depreciation_thousand_yen": detail,
                    "official_revenue_expense_depreciation_thousand_yen": reported,
                    "difference_noi_thousand_yen": difference,
                    "difference_ratio": difference / (reported[0] - reported[1] + reported[2]),
                    "status": "within_rounding"
                    if abs(difference) <= len(columns)
                    else "unallocated_difference_not_explained",
                    "financial_statement_pdf_page": 26 if stamp == "202601" else 25,
                },
                "excel_aggregate_used": False,
                "price_basis_note": "旧NRI承継分の物件概要は2010年2月鑑定額、帳簿表は2010年3月1日承継額。T-019の相違を同じ価格と扱わない。",
            }
        )
        periods.append(rows)
        qualities.append(quality)
    annual, exclusions = annual_cohort(*periods)
    latest = {p["property_id"]: p for p in periods[1]}
    acquisitions = []
    presentation = pdf_text(RAW / "adr_202607_presentation.pdf")
    for key, name, acquired, rate in (
        ("T-195", "レジディア松陰神社前", "2026-05-27", 0.037),
        ("T-196", "レジディアときわ台", "2026-05-28", 0.039),
        ("T-197", "レジディア武蔵小山", "2026-06-30", 0.038),
        ("S-040", "レジディア横濱戸部", "2026-07-01", 0.041),
    ):
        item = latest[key]
        # Slide names wrap across lines. Dates/rates are a transcription of PDF p28;
        # ownership and exact acquisition costs are verified against the archived XLSX.
        if name not in re.sub(r"\s+", "", presentation):
            raise ValueError(f"Acquisition slide name missing: {key}")
        acquisitions.append(
            {
                "fund": "ADR",
                "property_id": key,
                "property_name": name,
                "xlsx_property_name": item["property_name"],
                "market": item["market"],
                "acquisition_date": acquired,
                "acquisition_date_status": "actual_period_end_owned_and_presentation",
                "asset_type": "賃貸住宅",
                "acquisition_price_yen": item["acquisition_price_yen"],
                "noi_forecast_annual_yen": None,
                "yield_on_acquisition": rate,
                "income_basis": "appraisal_forecast_yield_rounded_0.1_percentage_point_not_actual",
                "forecast_definition": "direct_capitalization_appraisal_NOI_before_capex",
                "source_url": next(
                    s["url"] for s in sources if s["filename"] == "adr_202607_presentation.pdf"
                ),
                "source_pdf_page": 28,
            }
        )
    summary = {
        "schema_version": "adr_noi_v1",
        "fund": "ADR",
        "as_of": "2026-10-01",
        "period_properties": periods[0] + periods[1],
        "annual_properties": annual,
        "acquisitions": acquisitions,
        "quality": {"periods": qualities, "annual_exclusions": exclusions},
        "sources": sources,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    summary = run()
    print(
        f"ADR: {len(summary['annual_properties'])} annual properties, {len(summary['acquisitions'])} acquisitions"
    )
