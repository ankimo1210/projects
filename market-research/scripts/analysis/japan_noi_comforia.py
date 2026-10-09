"""Extract Comforia's two disclosed periods and acquisition appraisal NOI.

Run from the uv workspace root. XLSX monetary units are thousand yen except
the appraisal sheet's million yen. Annual income is a sum of two actual full
periods; acquisition appraisal NOI is kept as a separate forecast measure.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import subprocess
import unicodedata
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path

import requests
from global_city_xlsx import excel_date, xlsx_rows

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT.parent / "_data/market-research/market"
RAW = DATA / "raw/noi_expansion_20261001/comforia"
PROCESSED = DATA / "processed/noi_expansion_20261001/comforia"
FUND = "コンフォリア・レジデンシャル投資法人"
BASE = "https://www.comforia-reit.co.jp"
SOURCES = {
    "data_202607.xlsx": BASE
    + "/file/ir_library_term-78e0992559b5166a4a3257545018ddf14e0335e7.xlsx",
    "data_202601.xlsx": BASE
    + "/file/ir_library_term-e3dac8fd1409b016e471b31b7c7272de243698f0.xlsx",
    "results_202607.pdf": BASE
    + "/file/ir_library_term-29dd5bbda569fa454b9aa407f07415bdad7cccb7.pdf",
    "results_202601.pdf": BASE
    + "/file/ir_library_term-babbf2027baec698725eb4fa70628952c4702792.pdf",
    "acq_20250128.pdf": BASE + "/file/news-75944f1a43771946e17fc602babd1c0b05828541.pdf",
    "acq_20250317.pdf": BASE + "/file/news-4e806adceb48ceb4833b951cc8296b1ef1bd8286.pdf",
    "acq_20250916.pdf": BASE + "/file/news-ebd6a6200dcd6ceea16a8a4868c517cb7f3d68b4.pdf",
    "acq_20260317.pdf": BASE + "/file/news-9aa59cf045fc98764e487ff247b64ac92f741381.pdf",
    "acq_20260525.pdf": BASE + "/file/news-035a23e79eb3cf95cf72dd056ca4b55b2828dc11.pdf",
    "acq_20260713.pdf": BASE + "/file/news-607b93bc24ecb1422f5a1f49aec3295ac9b84521.pdf",
    "price_20260713.pdf": BASE + "/file/news-72fecf983be704197c2c6336494f5eb02893dc14.pdf",
    "portfolio_20261001.html": BASE + "/ja/portfolio/index.html",
    "library.html": BASE + "/ja/ir/library.html",
    "press_list_2026.html": BASE + "/ja/ir/press-2026.html",
    "press_list_2025.html": BASE + "/ja/ir/press-2025.html",
}
# Dates come from the acquisition notices' numbered acquisition schedules.
ACQUISITION_DATES = {
    "acq_20250128.pdf": {"コンフォリア糀谷": "2025-03-31"},
    "acq_20250317.pdf": {
        "コンフォリア芝浦Ⅱ": "2025-03-28",
        "コンフォリア東大井Ⅰ": "2025-04-11",
        "コンフォリア東大井Ⅱ": "2025-04-11",
        "キャンパスヴィレッジ大阪近大前": "2025-04-11",
        "コンフォリア戸越公園": "2025-09-30",
    },
    "acq_20250916.pdf": {"コンフォリア大森山王": "2025-09-26"},
    "acq_20260317.pdf": {
        "コンフォリア学芸大学イースト": "2026-03-27",
        "コンフォリア西新井": "2026-08-07",
        "コンフォリア板橋区役所前": "2026-08-07",
    },
    "acq_20260525.pdf": {"コンフォリア経堂": "2026-08-03"},
    "acq_20260713.pdf": {
        "コンフォリア志茂": "2026-08-03",
        "コンフォリア武蔵浦和": "2026-08-03",
        "コンフォリア五反野": "2026-08-05",
        "コンフォリア西高島平": "2026-08-05",
        "コンフォリア綾瀬": "2026-08-06",
    },
}


def normalize(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value))


def amount(value: str, *, missing: bool = False) -> int | None:
    cleaned = normalize(value).replace(",", "").replace("△", "-")
    if cleaned in {"", "(注)", "(注9)"}:
        if missing:
            return None
        raise ValueError(f"Missing amount: {value!r}")
    if cleaned == "-":
        return None if missing else 0
    result = float(cleaned)
    if not math.isfinite(result) or not result.is_integer():
        raise ValueError(f"Invalid amount: {value!r}")
    return int(result)


def market_for(address: str) -> str:
    if re.search(r"東京都[^市]+区", address):
        return "東京23区"
    for city in (
        "福岡",
        "大阪",
        "名古屋",
        "札幌",
        "仙台",
        "京都",
        "横浜",
        "神戸",
        "広島",
        "さいたま",
    ):
        if city + "市" in address:
            return city
    return "その他首都圏・都市" if address else "不明"


def keyed(rows: dict[int, dict], column: str) -> dict[str, tuple[int, dict]]:
    result = {}
    for position, row in rows.items():
        key = row.get(column, "")
        if not key.isdigit():
            continue
        if key in result:
            raise ValueError(f"Duplicate property identifier: {key}")
        result[key] = (position, row)
    return result


def parse_tables(tables: dict, start: str, end: str) -> tuple[list[dict], dict]:
    overview = keyed(tables["物件概要"], "B")
    appraisal = keyed(tables["鑑定情報"], "B")
    income = tables["収支状況"]
    if "千円" not in tables["物件概要"][2].get("M", ""):
        raise ValueError("Acquisition price unit changed")
    if "百万円" not in tables["鑑定情報"][5].get("K", ""):
        raise ValueError("Appraisal unit changed")
    if "千円" not in income[28].get("E", "") or normalize(income[24].get("B", "")) != "(A)‐(C)+(B)":
        raise ValueError("Income unit or NOI schema changed")
    columns = {}
    for column, key in income[2].items():
        if not key.isdigit():
            continue
        if key in columns:
            raise ValueError(f"Duplicate income property identifier: {key}")
        columns[key] = column
    if not overview or set(overview) != set(appraisal) or not set(overview) <= set(columns):
        raise ValueError("Cross-sheet property coverage differs")
    full_days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
    quality = {
        "period_start": start,
        "period_end": end,
        "owned": len(overview),
        "income_properties": len(columns),
        "sold_income_ids": sorted(set(columns) - set(overview)),
        "noi_withheld": [],
        "revenue_component_differences": [],
        "name_differences": [],
    }
    result = []
    for key, column in columns.items():
        item = overview[key][1] if key in overview else {}
        pid = f"CFR-{int(key):03d}"
        name = item.get("C", income[3][column].replace("\n", ""))
        days = amount(income[4][column])
        if days < 0 or days > full_days or (key in overview and days == 0):
            raise ValueError(f"Invalid operating days: {pid}")
        revenue, expense, depreciation, noi = [
            amount(income[n].get(column, ""), missing=n != 18) for n in (8, 20, 18, 24)
        ]
        if noi is None:
            quality["noi_withheld"].append(pid)
        elif (
            None in (revenue, expense, depreciation)
            or abs(noi - (revenue - expense + depreciation)) > 2
        ):
            raise ValueError(f"NOI reconciliation failed: {pid}")
        if expense is not None and depreciation is not None and expense < depreciation:
            raise ValueError(f"Negative operating expenses: {pid}")
        components = [amount(income[n].get(column, ""), missing=True) for n in (5, 6)]
        if revenue is not None and None not in components and abs(sum(components) - revenue) > 2:
            quality["revenue_component_differences"].append(
                {
                    "property_id": pid,
                    "name": name,
                    "components_yen": [v * 1000 for v in components],
                    "reported_revenue_yen": revenue * 1000,
                }
            )
        value = None
        if key in appraisal:
            a = appraisal[key][1]
            value = amount(a["K"]) * 1_000_000
            if value != amount(item["O"]) * 1000:
                raise ValueError(f"Appraisal cross-sheet mismatch: {pid}")
            if normalize(name) != normalize(income[3][column]) or normalize(name) != normalize(
                a["C"]
            ):
                quality["name_differences"].append(pid)
        address = item.get("E", "")
        result.append(
            {
                "fund": FUND,
                "property_id": pid,
                "source_property_id": key,
                "name": name,
                "address": address,
                "market": market_for(address),
                "currency": "JPY",
                "asset_type": "rental_apartment"
                if name.startswith("コンフォリア")
                else "alternative_housing",
                "owned_at_period_end": key in overview,
                "period_start": start,
                "period_end": end,
                "operating_days": days,
                "period_calendar_days": full_days,
                "revenue_period_yen": None if revenue is None else revenue * 1000,
                "operating_expense_ex_dep": None
                if expense is None or depreciation is None
                else (expense - depreciation) * 1000,
                "noi_period_yen": None if noi is None else noi * 1000,
                "acquisition_price_yen": amount(item["M"]) * 1000 if item else None,
                "acquisition_date": excel_date(item["F"]) if item else None,
                "appraisal_value_yen": value,
                "appraisal_date": end if value else None,
                "capex_period_yen": None,
                "capex_status": "物件別総額はデータブックに未掲載",
                "masterlease": None,
                "masterlease_status": "物件別種別はデータブックに未掲載",
                "source_overview_row": overview[key][0] if item else None,
                "source_income_column": column,
            }
        )
    quality["disclosed_noi_sum_yen"] = sum(r["noi_period_yen"] or 0 for r in result)
    quality["disclosed_revenue_sum_yen"] = sum(r["revenue_period_yen"] or 0 for r in result)
    return result, quality


def annual_cohort(prior: list[dict], latest: list[dict]) -> tuple[list[dict], dict]:
    def unique(rows):
        index = {r["property_id"]: r for r in rows}
        if len(index) != len(rows):
            raise ValueError("Duplicate period property identifier")
        return index

    before = unique(prior)
    unique(latest)
    result, excluded = [], []
    for current in latest:
        if not current["owned_at_period_end"]:
            continue
        previous = before.get(current["property_id"])
        reason = None
        if current["asset_type"] != "rental_apartment":
            reason = "alternative_housing"
        elif previous is None:
            reason = "missing_prior"
        elif (
            previous["operating_days"] != previous["period_calendar_days"]
            or current["operating_days"] != current["period_calendar_days"]
        ):
            reason = "partial_period"
        elif previous["acquisition_price_yen"] != current["acquisition_price_yen"]:
            reason = "cost_or_share_changed"
        elif previous["noi_period_yen"] is None or current["noi_period_yen"] is None:
            reason = "noi_withheld"
        elif (
            date.fromisoformat(current["period_start"]).toordinal()
            != date.fromisoformat(previous["period_end"]).toordinal() + 1
        ):
            raise ValueError("Non-contiguous periods")
        if reason:
            excluded.append(
                {"property_id": current["property_id"], "name": current["name"], "reason": reason}
            )
            continue
        annual = dict(current)
        annual.update(
            {
                "actual_period_start": previous["period_start"],
                "actual_period_end": current["period_end"],
                "actual_operating_days": previous["operating_days"] + current["operating_days"],
                "noi_annual_yen": previous["noi_period_yen"] + current["noi_period_yen"],
                "revenue_annual_yen": previous["revenue_period_yen"]
                + current["revenue_period_yen"],
                "operating_expense_annual_yen": previous["operating_expense_ex_dep"]
                + current["operating_expense_ex_dep"],
                "income_basis": "two_disclosed_full_periods_actual",
            }
        )
        annual["yield_on_acquisition"] = annual["noi_annual_yen"] / annual["acquisition_price_yen"]
        annual["yield_on_appraisal"] = annual["noi_annual_yen"] / annual["appraisal_value_yen"]
        result.append(annual)
    return result, {
        "included": len(result),
        "exclusions": excluded,
        "exclusion_counts": dict(Counter(r["reason"] for r in excluded)),
    }


def parse_acquisitions(
    text: str, source: str, dates: dict[str, str], *, prices: dict | None = None
) -> list[dict]:
    """Match appraisal NOI blocks to the notice's purchase table by name."""
    normalized_dates = {normalize(k): v for k, v in dates.items()}
    # The first total terminates the purchase table before any disposal table.
    purchase_table = re.split(r"合\s*計", text, maxsplit=1)[0]
    purchase_prices = {}
    lines = purchase_table.splitlines()
    for i, line in enumerate(lines):
        match = re.search(r"^\s*\d+\s+不動産(?:信託受益権)?\s+([^\s（(]+)", line)
        if not match:
            continue
        name = normalize(match[1])
        price = re.search(r"([\d,]{5,})\s*$", line)
        if price is None and i:
            price = re.fullmatch(r"\s*([\d,]{5,})\s*", lines[i - 1])
        if price:
            purchase_prices[name] = amount(price[1]) * 1000
    purchase_prices.update({normalize(k): v for k, v in (prices or {}).items()})
    matches = list(re.finditer(r"物件名\s+([^\n]+)", text))
    result = []
    for i, match in enumerate(matches):
        name = normalize(match[1])
        if name not in normalized_dates:
            continue
        block = text[match.end() : matches[i + 1].start() if i + 1 < len(matches) else len(text)]
        noi = re.search(
            r"③\s*運営純収益[^\n]*?\)\s*([\d,]+)|③\s*運営純収益[^\n]*?）\s*([\d,]+)", block
        )
        appraisal = re.search(r"鑑定評価額\s+([\d,]+)", block)
        valuation_date = re.search(r"価格時点\s+(\d{4})\s*年\s*(\d+)\s*月\s*(\d+)\s*日", block)
        if (
            name not in purchase_prices
            or noi is None
            or appraisal is None
            or valuation_date is None
        ):
            raise ValueError(f"Incomplete acquisition appraisal: {name}")
        price = purchase_prices[name]
        forecast = amount(noi[1] or noi[2]) * 1000
        result.append(
            {
                "fund": FUND,
                "name": name,
                "currency": "JPY",
                "acquisition_date": normalized_dates[name],
                "acquisition_price_yen": price,
                "forecast_noi_annual_yen": forecast,
                "forecast_noi_yield_on_purchase": forecast / price,
                "appraisal_value_yen": amount(appraisal[1]) * 1000,
                "appraisal_date": date(*map(int, valuation_date.groups())).isoformat(),
                "asset_type": "rental_apartment"
                if name.startswith("コンフォリア")
                else "alternative_housing",
                "income_basis": "appraisal_forecast_noi",
                "source_file": source,
                "source_url": SOURCES.get(source),
                "source_pdf_page": text[: match.start()].count("\f") + 1,
                "purchase_price_basis": "売買契約価格・取得諸費用を除く",
            }
        )
    if {r["name"] for r in result} != set(normalized_dates):
        raise ValueError("Acquisition appraisal coverage differs")
    return result


def archive_sources(*, download: bool) -> list[dict]:
    RAW.mkdir(parents=True, exist_ok=True)
    manifest_path = RAW / "manifest.json"
    entries = (
        {r.get("filename", r.get("file")): r for r in json.loads(manifest_path.read_text())}
        if manifest_path.exists()
        else {}
    )
    for filename, url in SOURCES.items():
        path = RAW / filename
        if not path.exists() and download:
            response = requests.get(url, timeout=90)
            response.raise_for_status()
            payload = response.content
            path.write_bytes(payload)
            entries[filename] = {
                "file": filename,
                "url": url,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "retrieved_at": datetime.now(UTC).isoformat(),
            }
            manifest_path.write_text(
                json.dumps(list(entries.values()), ensure_ascii=False, indent=2)
            )
        if not path.exists() or filename not in entries:
            raise ValueError(f"Missing archived source (use --download): {filename}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != entries[filename]["sha256"]:
            raise ValueError(f"Archived source hash mismatch: {filename}")
        if filename.endswith(".pdf"):
            target = path.with_suffix(".txt")
            if not target.exists():
                subprocess.run(["pdftotext", "-layout", str(path), str(target)], check=True)
            text_name = target.name
            payload = target.read_bytes()
            if (
                text_name in entries
                and hashlib.sha256(payload).hexdigest() != entries[text_name]["sha256"]
            ):
                raise ValueError(f"Derived text hash mismatch: {text_name}")
            if text_name not in entries:
                entries[text_name] = {
                    "file": text_name,
                    "url": url,
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "retrieved_at": entries[filename]["retrieved_at"],
                    "derived_from": filename,
                    "derivation": "pdftotext -layout",
                }
    manifest = list(entries.values())
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest


def portfolio_rows(source: str) -> dict[str, dict]:
    result = {}
    for block in re.findall(r'<tr[^>]*class="portfolio-type\s[^>]*>(.*?)</tr>', source, re.S):

        def field(css, row=block):
            m = re.search(r'class="' + css + r'[^\"]*"[^>]*>(.*?)</(?:th|td)>', row, re.S)
            return html.unescape(re.sub(r"<[^>]+>", "", m[1])).strip() if m else ""

        name = normalize(field("portfolio-type__name"))
        if name in result:
            raise ValueError(f"Duplicate current portfolio name: {name}")
        result[name] = {
            "property_id": f"CFR-{int(field('portfolio-type__id-number')):03d}",
            "address": field("portfolio-type__add"),
            "acquisition_price_yen": amount(field("portfolio-type__type")) * 1000,
        }
    if not result:
        raise ValueError("Current portfolio schema changed")
    return result


def financial_totals(text: str) -> list[dict]:
    """Read the latest financial note's prior/current rental totals, in yen."""
    totals = {}
    for key, label in [
        ("revenue_yen", "不動産賃貸事業収益合計"),
        ("expense_including_depreciation_yen", "不動産賃貸事業費用合計"),
        ("depreciation_yen", "（減価償却費）"),
    ]:
        match = re.search(re.escape(label) + r"\s+([\d,]+)\s+([\d,]+)", text)
        if match is None:
            raise ValueError(f"Financial totals missing: {label}")
        totals[key] = [amount(v) * 1000 for v in match.groups()]
    result = [{key: values[i] for key, values in totals.items()} for i in range(2)]
    for row in result:
        row["noi_yen"] = (
            row["revenue_yen"] - row["expense_including_depreciation_yen"] + row["depreciation_yen"]
        )
    return result


def completed_acquisition_dates(text: str) -> dict[str, str]:
    section = text.split("本投資法人は以下の物件を取得しました。", 1)[1].split("物件の譲渡", 1)[0]
    result = {}
    for line in section.splitlines():
        normalized = unicodedata.normalize("NFKC", line)
        match = re.match(
            r"(コンフォリア\S+?)\s+(?:信託不動産|不動産).*?(\d{4})年(\d+)月(\d+)日", normalized
        )
        if not match:
            continue
        name = re.sub(r"[（(]注\d+[）)]", "", match[1])
        if name in result:
            raise ValueError(f"Duplicate completed acquisition: {name}")
        result[name] = date(*map(int, match.groups()[1:])).isoformat()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--download", action="store_true", help="Download only missing official source files"
    )
    args = parser.parse_args()
    manifest = archive_sources(download=args.download)
    periods, qualities = [], []
    for filename, start, end in [
        ("data_202601.xlsx", "2025-08-01", "2026-01-31"),
        ("data_202607.xlsx", "2026-02-01", "2026-07-31"),
    ]:
        payload = (RAW / filename).read_bytes()
        tables = {
            name: dict(xlsx_rows(payload, name)) for name in ("物件概要", "鑑定情報", "収支状況")
        }
        rows, quality = parse_tables(tables, start, end)
        for row in rows:
            row.update(source_file=filename, source_url=SOURCES[filename])
        periods.append(rows)
        qualities.append(quality)
    annual, annual_quality = annual_cohort(*periods)
    fund_totals = financial_totals((RAW / "results_202607.txt").read_text())
    for quality, total in zip(qualities, fund_totals, strict=True):
        quality["published_rental_totals"] = total
        quality["unallocated_noi_residual_yen"] = (
            total["noi_yen"] - quality["disclosed_noi_sum_yen"]
        )
        quality["unallocated_revenue_residual_yen"] = (
            total["revenue_yen"] - quality["disclosed_revenue_sum_yen"]
        )
        quality["reconciliation_basis"] = (
            "全基金財務総計と全収支明細（売却含む）を比較。残差にはNOI非開示物件と千円未満切捨てが含まれ、非開示NOIを推計補完しない。"
        )
    portfolio = portfolio_rows((RAW / "portfolio_20261001.html").read_text())
    completion_dates = completed_acquisition_dates((RAW / "results_202607.txt").read_text())
    latest_owned = {normalize(r["name"]): r for r in periods[1] if r["owned_at_period_end"]}
    acquisitions = []
    final_price_text = (RAW / "price_20260713.txt").read_text()
    price_updates = {}
    for name in ("コンフォリア西新井", "コンフォリア板橋区役所前"):
        match = re.search(re.escape(name) + r"\s+([\d,]+)\s+([\d,]+)", final_price_text)
        if not match:
            raise ValueError(f"Missing finalized acquisition price: {name}")
        price_updates[name] = amount(match[2]) * 1000
    for filename, dates in ACQUISITION_DATES.items():
        prices = price_updates if filename == "acq_20260317.pdf" else None
        acquisitions.extend(
            parse_acquisitions(
                (RAW / filename).with_suffix(".txt").read_text(), filename, dates, prices=prices
            )
        )
    for row in acquisitions:
        holding = portfolio.get(row["name"])
        if holding is None or holding["acquisition_price_yen"] != row["acquisition_price_yen"]:
            raise ValueError(f"Current portfolio acquisition confirmation failed: {row['name']}")
        row.update(holding)
        row.update(
            market=market_for(row["address"]),
            acquired_status="現在保有一覧で取得価格・保有を確認",
            ownership_confirmation_url=SOURCES["portfolio_20261001.html"],
            ownership_confirmation_as_of="2026-08-07",
        )
        if row["name"] in price_updates:
            row["final_price_source_url"] = SOURCES["price_20260713.pdf"]
        latest_record = latest_owned.get(normalize(row["name"]))
        if latest_record:
            actual_date = latest_record["acquisition_date"]
            date_source = SOURCES["data_202607.xlsx"]
            date_status = "actual_in_period_end_data_book"
        else:
            actual_date = completion_dates.get(row["name"])
            date_source = SOURCES["results_202607.pdf"]
            date_status = "completion_disclosed_in_financial_statement"
        if not actual_date or actual_date != row["acquisition_date"]:
            raise ValueError(f"Actual acquisition date confirmation failed: {row['name']}")
        row.update(
            acquisition_date_status=date_status,
            actual_date_source_url=date_source,
            actual_date_source_pdf_page=6 if not latest_record else None,
        )
    summary = {
        "fund": FUND,
        "as_of": "2026-10-01",
        "period_properties": periods[0] + periods[1],
        "annual_properties": annual,
        "acquisitions": acquisitions,
        "quality": {
            "periods": qualities,
            "annual": annual_quality,
            "annual_selection": "latest owned general rental apartments; both full periods; unchanged cost/share; disclosed NOI",
            "masterlease_basis": "物件別種別未確認。短信のテナント表注2は東急住宅リースをパス・スルー型と明記するが、全物件への自動結合は未実施。",
            "component_difference_pdf_check": "CFR-191 latest XLSX賃貸収入内訳41,786千円に対し短信p79は21,804千円。報告小計22,447千円とNOI15,550千円は両資料一致。",
            "limits": [
                "NOIは減価償却前・資本的支出前。物件別capex総額は未取得。",
                "期中売却物件は収支表に保持するが年間標本から除外。",
                "取得利回りの分子は鑑定の将来想定NOIで、取得後の実績NOIとは異なる。",
            ],
        },
        "sources": manifest,
    }
    PROCESSED.mkdir(parents=True, exist_ok=True)
    path = PROCESSED / "summary.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    total_noi = sum(r["noi_annual_yen"] for r in annual)
    cost = sum(r["acquisition_price_yen"] for r in annual)
    appraisal = sum(r["appraisal_value_yen"] for r in annual)
    print(
        json.dumps(
            {
                "output": str(path),
                "period_records": len(summary["period_properties"]),
                "annual_properties": len(annual),
                "acquisitions": len(acquisitions),
                "annual_noi_yen": total_noi,
                "yield_on_cost": total_noi / cost,
                "yield_on_appraisal": total_noi / appraisal,
                "annual_exclusions": annual_quality["exclusion_counts"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
