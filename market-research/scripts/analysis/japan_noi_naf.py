"""Reproduce NAF residential NOI from archived official 39th/40th disclosures.

The 40th data book contains historical individual income, including sold and
not-yet-acquired properties. Only its period-end owned properties enter the
canonical output. The annual cohort sums two actual consecutive full periods.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
import unicodedata
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT.parent / "_data/market-research/market"
RAW = DATA / "raw/noi_expansion_20261001/naf"
PROCESSED = DATA / "processed/noi_expansion_20261001/naf"
FUND = "NAF"
FUND_NAME = "三井不動産アコモデーションファンド投資法人"
PERIODS = {39: ("2025-03-01", "2025-08-31", 184), 40: ("2025-09-01", "2026-02-28", 181)}
XLSX_URL = "https://www.naf-r.jp/file/top_file-c8f40a16923a789813c8da33981c782cd4ddab4e.xlsx"
NON_NUMERIC = {"", "-", "－", "―", "非開示"}


def amount(value: object, *, required: bool = False) -> int | None:
    if value is None or str(value).strip() in NON_NUMERIC:
        if required:
            raise ValueError(f"Missing amount: {value!r}")
        return None
    try:
        result = float(str(value).replace(",", ""))
    except ValueError as exc:
        raise ValueError(f"Invalid amount: {value!r}") from exc
    if not math.isfinite(result) or result < 0 or not result.is_integer():
        raise ValueError(f"Invalid amount: {value!r}")
    return int(result)


def excel_date(value: str) -> str:
    return (date(1899, 12, 30) + timedelta(days=amount(value, required=True))).isoformat()


def market_for(address: str, area: str) -> str:
    if area == "東京23区":
        return "東京23区"
    for city in ("福岡", "大阪", "名古屋", "札幌", "仙台", "京都", "横浜", "神戸", "広島"):
        if city + "市" in address:
            return city
    return "その他首都圏・都市"


def parse_master_leases(text: str) -> dict[str, str]:
    # A nonnumeric property name after the period distinguishes decimal areas.
    headings = list(re.finditer(r"(?m)^[ \t\f]*([０-９0-9]+)[．.][ \t]*([^\d\s][^\n]*)", text))
    result = {}
    for i, header in enumerate(headings):
        stop = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        section = text[header.end() : stop]
        if re.search(r"マスターリース種別[^\n]*パス・スルー", section):
            key = unicodedata.normalize("NFKC", header.group(1))
            if key in result:
                raise ValueError(f"Duplicate master lease property: {key}")
            result[key] = "パス・スルー"
    return result


def _period_columns(rows: dict[int, dict], row: int) -> dict[int, str]:
    result = {}
    for col, value in rows[row].items():
        if value in {"39", "40"}:
            period = int(value)
            if period in result:
                raise ValueError("Duplicate period column")
            result[period] = col
    if set(result) != set(PERIODS):
        raise ValueError("Latest two disclosed periods missing")
    return result


def parse_naf_tables(
    tables: dict[str, dict[int, dict]], leases: dict[int, dict]
) -> tuple[list[dict], dict]:
    base = tables["基礎データ"]
    individual = tables["物件収支（個別）"]
    appraisal = tables["鑑定評価"]
    totals = tables["物件収支（集計）"]
    if "千円" not in base[2].get("O", "") or "千円" not in individual[3].get("G", ""):
        raise ValueError("NAF amount units changed")
    if "2026年2月28日" not in tables["ご利用上の注意"][4].get("C", ""):
        raise ValueError("Latest owned date changed")
    owned = {}
    for pos, row in base.items():
        key = row.get("B", "")
        if key.isdigit():
            if key in owned:
                raise ValueError(f"Duplicate property identifier: {key}")
            owned[key] = (pos, row)
    income = {}
    for pos, row in individual.items():
        key = row.get("D", "")
        if key.isdigit() and row.get("E") and individual.get(pos + 1, {}).get("E") == "期別":
            if key in income:
                raise ValueError(f"Duplicate income property: {key}")
            income[key] = pos
    if not owned or not set(owned) <= set(income):
        raise ValueError("Owned income coverage differs")
    appraisal_columns = _period_columns(appraisal, 2)
    appraisals = {}
    for pos, row in appraisal.items():
        name = row.get("B", "")
        if pos > 5 and name and "合計" not in name:
            if name in appraisals:
                raise ValueError(f"Duplicate appraisal name: {name}")
            appraisals[name] = (pos, row)
    for col in appraisal_columns.values():
        if appraisal[5].get(col) != "百万円" or appraisal[4].get(col) != "鑑定評価額":
            raise ValueError("NAF appraisal schema or unit changed")
    rows = []
    for key, (base_pos, item) in owned.items():
        pos = income[key]
        if individual[pos]["E"] != item["C"]:
            raise ValueError(f"Income name differs: {key}")
        if item["C"] not in appraisals:
            raise ValueError(f"Missing appraisal: {key}")
        appraisal_pos, app = appraisals[item["C"]]
        columns = _period_columns(individual, pos + 1)
        for period, col in columns.items():
            start, end, full_days = PERIODS[period]
            if excel_date(individual[pos + 2][col]) != end:
                raise ValueError("Individual income period changed")
            days = amount(individual[pos + 3].get(col))
            if days is not None and not 1 <= days <= full_days:
                raise ValueError(f"Invalid operating days: {key}")
            revenue = amount(individual[pos + 6].get(col))
            expense = amount(individual[pos + 17].get(col))
            depreciation = amount(individual[pos + 16].get(col))
            noi = amount(individual[pos + 19].get(col))
            if all(v is not None for v in (revenue, expense, depreciation, noi)):
                if abs(revenue - expense + depreciation - noi) > 2:
                    raise ValueError(f"NOI reconciliation failed: {key}/{period}")
                if expense < depreciation:
                    raise ValueError(f"Negative expenses excluding depreciation: {key}")
            value = amount(app.get(appraisal_columns[period]))
            if period == 40 and value is None:
                raise ValueError(f"Missing latest appraisal: {key}")
            raw_values = {
                "revenue_period_yen": revenue,
                "opex_ex_dep_period_yen": None
                if expense is None or depreciation is None
                else expense - depreciation,
                "depreciation_period_yen": depreciation,
                "noi_period_yen": noi,
            }
            row = {
                "fund": FUND,
                "fund_name": FUND_NAME,
                "property_id": key,
                "property_name": item["C"],
                "address": item["G"],
                "address_precision": "municipality",
                "market": market_for(item["G"], item["F"]),
                "currency": "JPY",
                "asset_type": item["D"],
                "property_type": item["E"],
                "period": period,
                "period_start": start,
                "period_end": end,
                "period_days": full_days,
                "operating_days": days,
                **{k: None if v is None else v * 1000 for k, v in raw_values.items()},
                "operating_expense_period_yen": None
                if raw_values["opex_ex_dep_period_yen"] is None
                else raw_values["opex_ex_dep_period_yen"] * 1000,
                "acquisition_date": excel_date(item["I"]),
                "additional_acquisition_date": excel_date(item["K"]) if item.get("K") else None,
                "acquisition_price_yen": amount(item["O"], required=True) * 1000,
                "acquisition_price_as_of": "2026-02-28",
                "appraisal_value_yen": value * 1_000_000 if value is not None else None,
                "appraisal_date": end if value is not None else None,
                "capex_period_yen": None,
                "capex_status": "complete_property_amount_not_disclosed",
                "master_lease": leases.get(period, {}).get(key),
                "latest_period_owned": True,
                "latest_owned_as_of": "2026-02-28",
                "missing_fields": [k for k, v in raw_values.items() if v is None],
                "source_url": XLSX_URL,
                "source_base_row": base_pos,
                "source_income_row": pos,
                "source_income_column": col,
                "source_appraisal_row": appraisal_pos,
                "noi_definition": "rental_revenue_minus_property_expense_excluding_depreciation_before_capex_financing_and_fund_fees",
            }
            if days is None:
                row["missing_fields"].append("operating_days")
            rows.append(row)
    reconciliation = {}
    total_columns = _period_columns(totals, 4)
    for period, col in total_columns.items():
        if (
            excel_date(totals[5][col]) != PERIODS[period][1]
            or amount(totals[6][col]) != PERIODS[period][2]
        ):
            raise ValueError("Portfolio total period changed")
        detail_col = _period_columns(individual, next(iter(income.values())) + 1)[period]
        reconciliation[str(period)] = {}
        for field, offset, total_row in (("revenue", 6, 9), ("noi", 19, 22)):
            values = {
                key: amount(individual[pos + offset].get(detail_col)) for key, pos in income.items()
            }
            missing = [
                key
                for key, pos in income.items()
                if individual[pos + offset].get(detail_col) == "非開示"
            ]
            visible = sum(v for v in values.values() if v is not None) * 1000
            reported = amount(totals[total_row][col], required=True) * 1000
            difference = visible - reported
            status = (
                "non_disclosed_residual"
                if missing
                else "within_rounding"
                if abs(difference) <= len(values) * 1000
                else "unreconciled"
            )
            reconciliation[str(period)][field] = {
                "reported_yen": reported,
                "all_visible_detail_yen": visible,
                "latest_owned_visible_yen": sum(
                    v for key, v in values.items() if key in owned and v is not None
                )
                * 1000,
                "difference_yen": difference,
                "status": status,
                "non_disclosed_ids": missing,
            }
    sold = sorted(
        key
        for key, pos in income.items()
        if key not in owned
        and any(
            amount(individual[pos + 19].get(_period_columns(individual, pos + 1)[p])) is not None
            for p in PERIODS
        )
    )
    return rows, {
        "owned_as_of": "2026-02-28",
        "owned": len(owned),
        "owned_asset_types": dict(Counter(item["D"] for _, item in owned.values())),
        "income_history_properties": len(income),
        "sold_or_not_latest_owned_with_income": sold,
        "portfolio_reconciliation": reconciliation,
        "missing_capex": "Only portfolio total and selected major works are reported; per-property capex is null.",
        "periods": [
            {"period": p, "start": s, "end": e, "days": d} for p, (s, e, d) in PERIODS.items()
        ],
    }


def annual_cohort(rows: list[dict]) -> tuple[list[dict], dict]:
    groups = defaultdict(dict)
    for row in rows:
        key = (row["fund"], row["property_id"])
        if row["period"] in groups[key]:
            raise ValueError(f"Duplicate property period: {key}")
        groups[key][row["period"]] = row
    annual, excluded = [], []
    for (_, key), periods in groups.items():
        reasons = []
        if set(periods) != set(PERIODS):
            reasons.append("missing_period")
        observations = [periods[p] for p in sorted(periods)]
        latest = observations[-1]
        if any(r["asset_type"] != "賃貸住宅" for r in observations):
            reasons.append("not_standard_residential")
        if len({r["asset_type"] for r in observations}) > 1:
            reasons.append("asset_type_changed")
        if any(r["operating_days"] is None for r in observations):
            reasons.append("missing_operating_days")
        if any(
            r["operating_days"] is not None and r["operating_days"] != r["period_days"]
            for r in observations
        ):
            reasons.append("partial_period")
        if len({r["master_lease"] for r in observations if r["master_lease"] is not None}) > 1:
            reasons.append("lease_type_changed")
        if any(r["master_lease"] != "パス・スルー" for r in observations):
            reasons.append("not_verified_pass_through")
        if any(
            r["noi_period_yen"] is None
            or r["revenue_period_yen"] is None
            or r["opex_ex_dep_period_yen"] is None
            for r in observations
        ):
            reasons.append("missing_income")
        if not latest["latest_period_owned"]:
            reasons.append("not_latest_owned")
        if reasons:
            excluded.append(
                {
                    "fund": latest["fund"],
                    "property_id": key,
                    "property_name": latest["property_name"],
                    "reasons": reasons,
                }
            )
            continue
        if date.fromisoformat(observations[0]["period_end"]) + timedelta(
            days=1
        ) != date.fromisoformat(latest["period_start"]):
            raise ValueError("Annual periods are not consecutive")
        row = dict(latest)
        row.update(
            {
                "period_start": observations[0]["period_start"],
                "period_end": latest["period_end"],
                "actual_period_start": observations[0]["period_start"],
                "actual_period_end": latest["period_end"],
                "periods": sorted(periods),
                "operating_days": sum(r["operating_days"] for r in observations),
                "noi_annual_yen": sum(r["noi_period_yen"] for r in observations),
                "revenue_annual_yen": sum(r["revenue_period_yen"] for r in observations),
                "operating_expense_annual_yen": sum(
                    r["opex_ex_dep_period_yen"] for r in observations
                ),
                "capex_annual_yen": None,
                "baseline_eligible": True,
                "annualization": "sum_two_actual_full_periods",
            }
        )
        row["yield_on_acquisition"] = row["noi_annual_yen"] / row["acquisition_price_yen"]
        row["yield_on_appraisal"] = row["noi_annual_yen"] / row["appraisal_value_yen"]
        annual.append(row)
    return annual, {
        "included": len(annual),
        "excluded": excluded,
        "exclusion_counts": dict(Counter(reason for row in excluded for reason in row["reasons"])),
        "exclusion_counts_overlap": True,
    }


def appraisal_nois(text: str) -> list[int]:
    normalized = unicodedata.normalize("NFKC", text)
    return [
        int(v.replace(",", "")) * 1000
        for v in re.findall(r"運営純収益\[[^\]]+\]\s+([\d,]+)", normalized)
    ]


JAPANESE_DATE = r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日"


def appraisal_forecasts(text: str) -> list[dict]:
    normalized = unicodedata.normalize("NFKC", text)
    dates = list(re.finditer("価格時点\\s+" + JAPANESE_DATE, normalized))
    result = []
    for match in re.finditer(r"運営純収益\[[^\]]+\]\s+([\d,]+)", normalized):
        preceding = [d for d in dates if d.start() < match.start()]
        if not preceding:
            raise ValueError("Forecast NOI has no matching appraisal date")
        d = preceding[-1]
        result.append(
            {
                "noi_forecast_annual_yen": int(match.group(1).replace(",", "")) * 1000,
                "appraisal_date": date(*(int(v) for v in d.groups())).isoformat(),
            }
        )
    return result


def completion_date(text: str, property_name: str) -> str | None:
    normalized = unicodedata.normalize("NFKC", text)
    if property_name not in normalized or "完了しました" not in normalized:
        return None
    match = re.search(JAPANESE_DATE, normalized)
    if match is None:
        raise ValueError("Completed acquisition has no release date")
    return date(*(int(v) for v in match.groups())).isoformat()


def portfolio_capex(text: str) -> int | None:
    match = re.search(r"当期の資本的支出は([\d,]+)百万円", unicodedata.normalize("NFKC", text))
    return int(match.group(1).replace(",", "")) * 1_000_000 if match else None


def pdf_text(raw: Path, processed: Path, filename: str) -> str:
    destination = processed / (Path(filename).stem + ".txt")
    subprocess.run(["pdftotext", "-layout", str(raw / filename), str(destination)], check=True)
    return destination.read_text()


def _acquisition_price(text: str, name: str) -> int:
    for line in text.splitlines():
        if name in line:
            nums = re.findall(r"\b\d{1,3}(?:,\d{3})+\b", line)
            if len(nums) >= 2:
                return int(nums[-2].replace(",", "")) * 1000
    match = re.search(r"(?:取得予定価格|取得価格)[^\n]*?([\d,]+)\s*千円", text)
    if match is None:
        raise ValueError(f"Acquisition price not found: {name}")
    return int(match.group(1).replace(",", "")) * 1000


ACQUISITIONS = [
    (
        "145",
        "パークキューブ亀有",
        "ir_news-c90ed823da1c4e4b129a73b240a4850fd7cc3ade.pdf",
        0,
        "2025-02-03",
    ),
    (
        "147",
        "パークキューブ小岩",
        "ir_news-f2a21c85fb8699f9c0e178e9d3efa28aa5cc6e54.pdf",
        0,
        "2025-03-28",
    ),
    (
        "148",
        "パークキューブ錦糸町",
        "ir_news-9f25308d90c3abbff4420c2f7837825ba3f58c8a.pdf",
        0,
        "2025-12-18",
    ),
    (
        "149",
        "パークキューブ上野桜木",
        "ir_news-9f25308d90c3abbff4420c2f7837825ba3f58c8a.pdf",
        1,
        "2025-12-18",
    ),
    (
        "151",
        "パークアクシス押上レジデンス",
        "ir_news-d8fed797cf4a2bc605edbc3e6c0e1a438a2b0926.pdf",
        0,
        "2026-04-09",
    ),
    (
        "152",
        "パークアクシス西馬込",
        "ir_news-d8fed797cf4a2bc605edbc3e6c0e1a438a2b0926.pdf",
        1,
        "2026-04-09",
    ),
    (
        "153",
        "パークキューブ八王子",
        "ir_news-ba07ff7f545da4409122fe9ea3a870c65081dfe8.pdf",
        0,
        "2026-06-05",
    ),
    (
        "154",
        "パークキューブ大森山王",
        "ir_news-d7d6caa38093b789b62bb88514538114e4dc65af.pdf",
        0,
        "2026-09-01",
    ),
]


def acquisitions(raw: Path, processed: Path, period_rows: list[dict]) -> list[dict]:
    portfolio = (raw / "portfolio.html").read_text()
    latest = {r["property_id"]: r for r in period_rows if r["period"] == 40}
    result = []
    completion = pdf_text(raw, processed, "ir_news-516f05b57f0314399f46a0fc0568b5eff80109c3.pdf")
    for key, name, filename, index, scheduled_date in ACQUISITIONS:
        text = pdf_text(raw, processed, filename)
        forecast = appraisal_forecasts(text)[index]
        noi = forecast["noi_forecast_annual_yen"]
        cost = _acquisition_price(text, name)
        # Both latest book and current official portfolio establish completed ownership.
        if key in latest:
            actual_date = latest[key]["acquisition_date"]
            actual_status = "actual_in_period_end_data_book"
            ownership_url = XLSX_URL
            if latest[key]["acquisition_price_yen"] != cost:
                raise ValueError(f"Acquisition cost mismatch: {key}")
            address = latest[key]["address"]
            market = latest[key]["market"]
        else:
            html_row = next(
                (r for r in re.findall(r"<tr\b[^>]*>.*?</tr>", portfolio, re.S) if name in r), None
            )
            if html_row is None:
                raise ValueError(f"Acquisition is not confirmed in owned portfolio: {key}")
            cells = [
                re.sub(r"<[^>]*>", "", c).strip()
                for c in re.findall(r"<td\b[^>]*>(.*?)</td>", html_row, re.S)
            ]
            if int(cells[0]) != int(key) or int(cells[3].replace(",", "")) * 1_000_000 != cost:
                raise ValueError(f"Current portfolio acquisition price differs: {key}")
            address = cells[2]
            market = (
                "東京23区" if "大田区" in address or "墨田区" in address else "その他首都圏・都市"
            )
            ownership_url = "https://www.naf-r.jp/portfolio/5-1.html"
            actual_date = completion_date(completion, name) if key in {"151", "152"} else None
            actual_status = (
                "completion_release"
                if actual_date
                else "current_owned_portfolio_date_not_individually_confirmed"
            )
        address_matches = re.findall(r"所在地\s+住居表示\s+([^\n]+)", text)
        if index < len(address_matches):
            address = address_matches[index].strip()
        result.append(
            {
                "fund": FUND,
                "fund_name": FUND_NAME,
                "property_id": key,
                "property_name": name,
                "address": address,
                "market": market,
                "currency": "JPY",
                "asset_type": "賃貸住宅",
                "acquisition_date": actual_date,
                "acquisition_date_status": actual_status,
                "scheduled_acquisition_date": scheduled_date,
                "acquired_by_as_of": "2026-10-01",
                "acquisition_price_yen": cost,
                "noi_forecast_annual_yen": noi,
                "noi_annual_yen": noi,
                "yield_on_acquisition": noi / cost,
                "income_basis": "acquisition_appraisal_forecast_not_actual",
                "forecast_definition": "appraiser_operating_net_income_before_capex_and_depreciation",
                "forecast_appraisal_date": forecast["appraisal_date"],
                "forecast_notes": "renovation_after_stabilization_assumption"
                if key == "147"
                else "appraiser_stabilized_assumptions",
                "source_url": "https://www.naf-r.jp/file/" + filename,
                "ownership_source_url": ownership_url,
                "completion_source_url": "https://www.naf-r.jp/file/ir_news-516f05b57f0314399f46a0fc0568b5eff80109c3.pdf"
                if key in {"151", "152"}
                else None,
                "source_forecast_table_index": index,
                "capex_annual_yen": None,
            }
        )
    return result


def aggregate_markets(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[row["market"]].append(row)
    result = []
    for market, items in sorted(groups.items()):
        totals = {
            key: sum(r[key] for r in items)
            for key in (
                "noi_annual_yen",
                "revenue_annual_yen",
                "operating_expense_annual_yen",
                "acquisition_price_yen",
                "appraisal_value_yen",
            )
        }
        result.append(
            {
                "fund": FUND,
                "market": market,
                "n": len(items),
                **totals,
                "yield_on_acquisition": totals["noi_annual_yen"] / totals["acquisition_price_yen"],
                "yield_on_appraisal": totals["noi_annual_yen"] / totals["appraisal_value_yen"],
            }
        )
    return result


def build_summary(raw: Path = RAW, processed: Path = PROCESSED) -> dict:
    from global_city_xlsx import xlsx_rows

    processed.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((raw / "manifest.json").read_text())
    for entry in manifest:
        content = (raw / entry["filename"]).read_bytes()
        if (
            len(content) != entry["size_bytes"]
            or hashlib.sha256(content).hexdigest() != entry["sha256"]
        ):
            raise ValueError(f"Archived source hash mismatch: {entry['filename']}")
    payload = (raw / "data40.xlsx").read_bytes()
    tables = {
        name: dict(xlsx_rows(payload, name))
        for name in (
            "ご利用上の注意",
            "基礎データ",
            "物件収支（集計）",
            "物件収支（個別）",
            "鑑定評価",
        )
    }
    securities = {period: pdf_text(raw, processed, f"securities{period}.pdf") for period in PERIODS}
    leases = {period: parse_master_leases(text) for period, text in securities.items()}
    periods, quality = parse_naf_tables(tables, leases)
    annual, cohort = annual_cohort(periods)
    quality["annual_cohort"] = cohort
    quality["master_lease_verified"] = {str(p): len(rows) for p, rows in leases.items()}
    quality["portfolio_capex_period_yen"] = {
        str(period): portfolio_capex(text) for period, text in securities.items()
    }
    quality["unavailable_latest_period"] = {
        "period": "2026-08",
        "scheduled_release": "2026-10-20",
        "source_url": "https://www.naf-r.jp/ir/7-3.html",
    }
    quality["limitations"] = [
        "Observation window is 2025-03-01 to 2026-02-28, not current rents.",
        "Latest disclosed owned cohort is fixed at 2026-02-28; later trades are separate forecast observations.",
        "Per-property capex is not completely disclosed; it is not replaced with zero.",
        "Property book address is municipality precision; acquisition announcements carry street addresses.",
        "Acquisition forecasts use appraisal operating NOI before capex and are not observed income.",
        "Hachioji and Omori Sanno completion is confirmed by owned portfolio; individual actual transfer dates remain null.",
    ]
    result = {
        "schema_version": "naf_noi_v1",
        "fund": FUND,
        "fund_name": FUND_NAME,
        "as_of": "2026-10-01",
        "period_properties": periods,
        "annual_properties": annual,
        "markets": aggregate_markets(annual),
        "acquisitions": acquisitions(raw, processed, periods),
        "quality": quality,
        "sources": manifest,
    }
    (processed / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for filename, rows in (
        ("period_properties.csv", periods),
        ("annual_properties.csv", annual),
        ("acquisitions.csv", result["acquisitions"]),
    ):
        with (processed / filename).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=RAW)
    parser.add_argument("--processed", type=Path, default=PROCESSED)
    args = parser.parse_args()
    result = build_summary(args.raw, args.processed)
    print(
        json.dumps(
            {
                "fund": FUND,
                "owned": result["quality"]["owned"],
                "annual_cohort": len(result["annual_properties"]),
                "acquisitions": len(result["acquisitions"]),
                "markets": result["markets"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
