"""Reproduce a Japan residential NOI pilot from archived REIT disclosure.

Raw amounts have three different units: overview/book values are yen,
income is thousand yen, and appraisals are million yen. The HTML compares
holding economics at disclosed cost and at appraisal, never asking prices.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path

import requests
from global_city_xlsx import excel_date, xlsx_rows

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT.parent
RAW = REPO / "_data/market-research/market/raw/noi_valuation_20260930"
PROCESSED = REPO / "_data/market-research/market/processed/noi_valuation_20260930"
DOCS = ROOT / "docs/data/validation"
REFERENCE = ROOT / "docs/data/japan_noi_references_2026-09-30.json"
PERIOD_DAYS = 181
ID = re.compile(r"[TSR]-\d{3}\Z")


def number(value: object, *, minimum: float | None = None) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Missing or invalid amount: {value!r}") from exc
    if not math.isfinite(result) or (minimum is not None and result < minimum):
        raise ValueError(f"Invalid amount: {value!r}")
    return result


def keyed(rows: dict[int, dict[str, str]], column: str) -> dict[str, tuple[int, dict]]:
    result = {}
    for position, row in rows.items():
        key = row.get(column, "")
        if not ID.fullmatch(key):
            continue
        if key in result:
            raise ValueError(f"Duplicate property identifier: {key}")
        result[key] = (position, row)
    return result


def market_for(property_id: str, address: str) -> str:
    if property_id.startswith("T-"):
        return "東京23区"
    for city in ("福岡", "大阪", "名古屋", "札幌", "仙台", "京都", "横浜", "神戸", "広島"):
        if city + "市" in address:
            return city
    return "その他首都圏・都市"


def parse_adr_tables(
    tables: dict[str, dict[int, dict[str, str]]], *, period_days: int = PERIOD_DAYS
) -> tuple[list[dict], dict]:
    """Join sparse cached cells with explicit unit and cohort checks."""
    overview = keyed(tables["物件概要"], "B")
    book = keyed(tables["帳簿価額"], "C")
    appraisal = keyed(tables["鑑定評価"], "B")
    income = tables["収益状況"]
    if "千円" not in income[5].get("B", "") or income[38].get("B") != "NOI":
        raise ValueError("Income schema or unit changed")
    if "取得価格" not in tables["物件概要"][5].get("I", ""):
        raise ValueError("Overview acquisition price schema changed")
    if "資本的支出" not in tables["帳簿価額"][5].get("X", ""):
        raise ValueError("Book capex schema changed")
    if "評価額" not in tables["鑑定評価"][7].get("M", ""):
        raise ValueError("Appraisal schema changed")
    income_columns = {}
    for column, value in income[24].items():
        if not ID.fullmatch(value):
            continue
        if value in income_columns:
            raise ValueError(f"Duplicate income property identifier: {value}")
        income_columns[value] = column
    if not overview or not (set(book) == set(appraisal) == set(income_columns)):
        raise ValueError("Cross-sheet property coverage differs")
    if not set(overview) <= set(appraisal):
        raise ValueError("Owned property coverage differs")
    sold = sorted(set(appraisal) - set(overview))
    if any(book[key][1].get("B") != "売却" for key in sold):
        raise ValueError("Unexplained property missing from overview coverage")
    rows = []
    name_differences = []
    price_differences = []
    for key, (overview_row, item) in overview.items():
        book_row, b = book[key]
        appraisal_row, a = appraisal[key]
        column = income_columns[key]
        name = item["C"]
        names = {
            "overview": name,
            "book": b["E"],
            "appraisal": a["C"],
            "income": income[25][column],
        }
        if len(set(names.values())) > 1:
            name_differences.append({"property_id": key, "names": names})
        days = number(income[23].get(column), minimum=1)
        if days > period_days or not days.is_integer():
            raise ValueError(f"Invalid operating days: {key}")
        revenue = number(income[26].get(column), minimum=0) * 1000
        expense = number(income[28].get(column), minimum=0) * 1000
        depreciation = number(income[36].get(column), minimum=0) * 1000
        noi = number(income[38].get(column)) * 1000
        if abs(noi - (revenue - expense + depreciation)) > 2000:
            raise ValueError(f"NOI reconciliation failed: {key}")
        if expense < depreciation:
            raise ValueError(f"Operating expenses below zero: {key}")
        cost = number(item.get("I"), minimum=10_000_000)
        book_cost = number(b.get("H"), minimum=10_000_000)
        if cost != book_cost:
            price_differences.append(
                {
                    "property_id": key,
                    "overview_yen": cost,
                    "book_yen": book_cost,
                    "difference_yen": cost - book_cost,
                }
            )
        value = number(a.get("M"), minimum=1) * 1_000_000
        noi_annualized = noi * 365 / days
        lease = item["F"]
        if lease not in {"パス・スルー型", "賃料保証型"}:
            raise ValueError(f"Unknown master lease: {key}")
        reasons = []
        if days != period_days:
            reasons.append("端数期間")
        if lease != "パス・スルー型":
            reasons.append("賃料保証型")
        if b.get("B") == "新規取得":
            reasons.append("当期新規取得")
        rows.append(
            {
                "property_id": key,
                "property_name": name,
                "address": item["D"],
                "market": market_for(key, item["D"]),
                "built_date": excel_date(item["E"]),
                "master_lease": lease,
                "units": number(item["G"], minimum=1),
                "lettable_area_sqm": number(item["H"], minimum=1),
                "operating_days": int(days),
                "revenue_period_yen": revenue,
                "operating_expense_period_yen": expense - depreciation,
                "depreciation_period_yen": depreciation,
                "noi_period_yen": noi,
                "noi_annualized_yen": noi_annualized,
                "acquisition_price_yen": cost,
                "appraisal_value_yen": value,
                "book_acquisition_price_yen": book_cost,
                "appraisal_date": excel_date(a["L"]),
                "appraiser_direct_cap": number(a["O"], minimum=0),
                "capex_period_yen": number(b.get("X"), minimum=0),
                "yield_on_acquisition": noi_annualized / cost,
                "yield_on_appraisal": noi_annualized / value,
                "baseline_eligible": not reasons,
                "exclusion_reasons": ",".join(reasons),
                "source_overview_row": overview_row,
                "source_book_row": book_row,
                "source_appraisal_row": appraisal_row,
                "source_income_column": column,
            }
        )
    reconciliation = {}
    for field, total_row in (("revenue", 7), ("noi", 19)):
        if "F" not in income.get(total_row, {}):
            continue
        property_row = 26 if field == "revenue" else 38
        detail = sum(number(income[property_row][col]) for col in income_columns.values())
        owned_detail = sum(number(income[property_row][income_columns[key]]) for key in overview)
        reported = number(income[total_row]["F"])
        difference = owned_detail - reported
        reconciliation[field] = {
            "reported_thousand_yen": reported,
            "all_detail_thousand_yen": detail,
            "owned_detail_thousand_yen": owned_detail,
            "owned_minus_reported_thousand_yen": difference,
            "owned_minus_reported_ratio": difference / reported,
            "status": "within_rounding" if abs(difference) <= len(overview) else "unreconciled",
        }
    return rows, {
        "income_properties": len(income_columns),
        "owned": len(rows),
        "sold_excluded": sold,
        "name_differences": name_differences,
        "price_differences": price_differences,
        "partial_period": sum(r["operating_days"] != period_days for r in rows),
        "guaranteed_lease": sum(r["master_lease"] == "賃料保証型" for r in rows),
        "baseline": sum(r["baseline_eligible"] for r in rows),
        "exclusion_counts_overlap": True,
        "markets_owned": dict(Counter(r["market"] for r in rows)),
        "portfolio_reconciliation": reconciliation,
    }


def aggregate_markets(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        if row["baseline_eligible"]:
            groups[row["market"]].append(row)
    result = []
    for market, properties in groups.items():
        totals = {
            key: sum(p[key] for p in properties)
            for key in (
                "noi_annualized_yen",
                "acquisition_price_yen",
                "appraisal_value_yen",
                "revenue_period_yen",
                "operating_expense_period_yen",
                "capex_period_yen",
            )
        }
        result.append(
            {
                "market": market,
                "n": len(properties),
                **totals,
                "yield_on_acquisition": totals["noi_annualized_yen"]
                / totals["acquisition_price_yen"],
                "yield_on_appraisal": totals["noi_annualized_yen"] / totals["appraisal_value_yen"],
                "opex_ratio": totals["operating_expense_period_yen"] / totals["revenue_period_yen"],
                "small_sample": len(properties) < 5,
            }
        )
    return sorted(
        result, key=lambda r: (r["market"] != "東京23区", r["market"] != "福岡", r["market"])
    )


def financing(
    yield_rate: float, *, rate: float, ltv: float, years: int, reserve: float, costs: float
) -> dict:
    """Monthly level-payment debt; cash yield includes acquisition costs."""
    if not all(math.isfinite(v) for v in (yield_rate, rate, ltv, years, reserve, costs)):
        raise ValueError("Non-finite financing assumption")
    if rate < 0 or not 0 < ltv < 1 or years <= 0 or reserve < 0 or costs < 0:
        raise ValueError("Invalid financing assumption")
    monthly = rate / 12
    service = (
        ltv / years
        if rate == 0
        else 12 * ltv * monthly / (-math.expm1(-12 * years * math.log1p(monthly)))
    )
    cash = yield_rate - service - reserve
    return {
        "debt_service_per_price": service,
        "dscr": yield_rate / service,
        "cash_after_reserve_per_price": cash,
        "cash_on_cash": cash / (1 - ltv + costs),
        "required_yield_for_dscr_125": 1.25 * service,
        "max_price_ratio_for_dscr_125": yield_rate / (1.25 * service),
    }


def price_change(entry_cap: float, *, growth: float, cap_increase: float, years: int) -> dict:
    if entry_cap <= 0 or entry_cap + cap_increase <= 0 or growth <= -1 or years <= 0:
        raise ValueError("Invalid exit scenario")
    return {
        "price_change": (1 + growth) ** years * entry_cap / (entry_cap + cap_increase) - 1,
        "required_noi_growth": ((entry_cap + cap_increase) / entry_cap) ** (1 / years) - 1,
    }


def archive_sources(references: dict, *, download: bool) -> list[dict]:
    """Read verified originals; fetch only missing inputs when explicitly requested."""
    manifest_path = RAW / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
    entries = {r["filename"]: r for r in manifest}
    for source in references["sources"]:
        name = source.get("filename")
        if not name:
            continue
        path = RAW / name
        if not path.exists() and download:
            response = requests.get(source["url"], timeout=45)
            response.raise_for_status()
            payload = response.content
            digest = hashlib.sha256(payload).hexdigest()
            if name in entries and digest != entries[name]["sha256"]:
                raise ValueError(f"Source changed since archived run: {name}")
            RAW.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            if name not in entries:
                entries[name] = {
                    "filename": name,
                    "url": source["url"],
                    "bytes": len(payload),
                    "sha256": digest,
                    "retrieved_at": datetime.now(UTC).isoformat(),
                }
                manifest_path.write_text(json.dumps(list(entries.values()), indent=2) + "\n")
        if not path.exists() or name not in entries:
            raise ValueError(f"Missing archived original or manifest: {name}; use --download")
        data = path.read_bytes()
        if (
            hashlib.sha256(data).hexdigest() != entries[name]["sha256"]
            or len(data) != entries[name]["bytes"]
        ):
            raise ValueError(f"Source hash or size mismatch: {name}")
    return list(entries.values())


def markdown(summary: dict) -> str:
    market = {r["market"]: r for r in summary["markets"]}
    tokyo, fukuoka = market["東京23区"], market["福岡"]
    lines = [
        "# 福岡と東京のNOI比較：現在の価格では取得条件の選別が必要",
        "",
        "調査日: 2026-09-30。実収支: 2026-02-01〜2026-07-31（181日）。鑑定額: 2026-07-31。",
        "",
        f"福岡{fukuoka['n']}物件の年率換算NOI利回りは開示取得価格に対し{fukuoka['yield_on_acquisition']:.2%}、"
        f"鑑定額に対し{fukuoka['yield_on_appraisal']:.2%}。東京23区{tokyo['n']}物件は"
        f"{tokyo['yield_on_acquisition']:.2%}と{tokyo['yield_on_appraisal']:.2%}。"
        "福岡には東京より収益の厚みがある。ただし、現在の鑑定額では昔の取得条件ほど余裕がない。",
        "",
        "## 実収支の比較",
        "",
        "単一住宅J-REITの期末保有物件のうち、181日運用・パススルー型・当期新規取得を除く物件。"
        "NOIの合計を価格の合計で割る。個別利回りの単純平均ではない。",
        "",
        "| 都市 | n | 開示取得価格に対するNOI | 鑑定額に対するNOI | 運営費/実収入 |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in summary["markets"]:
        lines.append(
            f"| {row['market']} | {row['n']} | {row['yield_on_acquisition']:.2%} | {row['yield_on_appraisal']:.2%} | {row['opex_ratio']:.1%} |"
        )
    lines += [
        "",
        "5物件未満の都市は少数例。沖縄はこの標本に含まれず、利回り0%とは扱わない。"
        "賃料保証型24件は費用・リスクの負担が異なるので基準集計から除外。",
        "",
        "## 融資条件を入れるとどうなるか",
        "",
        "鑑定額で買う仮定。LTV70%、30年元利均等、取得費7%、年次CAPEX積立0.5%/物件価格。"
        "銀行提示条件ではない。税・売却・物件別大規模工事を含まない。",
        "",
        "| 都市 | 仮定金利 | NOI DSCR | 積立・返済後の税引前CoC | DSCR1.25を満たす価格/鑑定額 |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in summary["financing_scenarios"]:
        if row["market"] in {"東京23区", "福岡", "大阪"}:
            lines.append(
                f"| {row['market']} | {row['loan_rate']:.1%} | {row['dscr']:.2f} | {row['cash_on_cash']:.2%} | {row['max_price_ratio_for_dscr_125']:.1%} |"
            )
    lines += [
        "",
        "DSCRはNOI/元利返済。CAPEX積立はDSCRには引かず、CoCから引く。"
        "価格比が100%超でも割安の認定ではない。DSCR条件だけから逆算した価格で、成約予測でもない。",
        "",
        "## 家賃上昇をどう評価するか",
        "",
        "価格比=(1+NOI成長率)^保有年数×取得時NOI利回り/出口NOI利回り。"
        "還元利回りが0.5ポイント上がる場合、5年後の価格を維持するために必要な年次NOI成長は、"
        f"東京23区{price_change(tokyo['yield_on_appraisal'], growth=0, cap_increase=0.005, years=5)['required_noi_growth']:.2%}、"
        f"福岡{price_change(fukuoka['yield_on_appraisal'], growth=0, cap_increase=0.005, years=5)['required_noi_growth']:.2%}。"
        "賃料成長とNOI成長は違う。費用上昇・空室・工事負担を差し引いて考える。"
        "ここで計算した価格変化は保有中の収入を含む総収益・IRRではない。",
        "",
        "英国のCBRE保有住宅指数では2026年3月までの6か月に、市場賃料の評価額（market rental value）が1.7%上昇した一方、"
        "資産価値は2.2%下落し、income return2.2%と合わせたtotal returnは0.0%。"
        "家賃が上がっても資産価格が上がるとは限らない実例。半年のincome returnを年間Cap Rateに置き換えない。",
        "",
        "## 判断と残るデータ",
        "",
        "- 東京のこの保有標本は、現在の収入と鑑定額で見ると融資後CFの余裕が小さい。",
        "- 福岡は相対的に余裕があるが、金利・修繕・取得費を入れると一律に割安とは判断できない。",
        "- この標本では福岡の経常運営費率が約24%。以前の25%仮定に近いが、保証型・築年・一時的工事の差があり、物件ごとの費用明細を置き換える根拠にはしない。",
        "- 次は複数住宅J-REITの標本と直近取得案件を増やし、築年・駅距離・住戸仕様を揃える。ロンドン・マンチェスター・香港・沖縄の同条件NOI比較は未取得。",
        "",
        "## 定義・限界・出典",
        "",
        "NOIは実収入から減価償却を除いた運営費を引いたもの。経常修繕は含み、資本的支出・利息・税効果・取得費は含まない。"
        "半期NOI×365/181は年率換算で、直近12か月の実績や安定化NOIではない。"
        "住宅中心の物件でも店舗・駐車場等の収入を含む。鑑定額は売出価格・成約価格ではない。"
        "鑑定人の直接還元利回りは将来の想定収支等から決まり、ここで計算した実績NOI/鑑定額と一致するとは限らない。",
        "",
        "政策金利は9月18日決定で1.25%。物件融資金利とは区別し、4月の投資家調査・7月の実収支を9月時点の実測値として扱わない。",
        "",
    ]
    for source in summary["references"]["sources"]:
        lines.append(
            f"- [{source['title']}]({source['url']})：時点 {source['as_of']}。{source.get('limitation', '')}"
        )
    quality = summary["quality"]
    lines += [
        "",
        "## 品質の確認",
        "",
        f"期末保有{quality['owned']}件、基準集計{quality['baseline']}件。"
        f"賃料保証{quality['guaranteed_lease']}件、端数期間{quality['partial_period']}件を除外（理由は重複あり）。"
        f"売却済み{len(quality['sold_excluded'])}件も除外。物件ごとのNOIの足し引きは千円単位の丸め範囲で一致。",
        "",
        "原典の集計表と期末保有明細の合計には、次の未解明の差がある。"
        "丸め誤差として扱わず、都市利回りは接続した物件明細だけで計算した。"
        "集計表の値を都市に配賦・補正していない。",
        "",
        "| 項目 | 原典集計（千円） | 期末保有明細（千円） | 明細−集計（千円） | 差/集計 |",
        "|---|---:|---:|---:|---:|",
    ]
    for field, label in (("revenue", "収入"), ("noi", "NOI")):
        r = quality["portfolio_reconciliation"][field]
        lines.append(
            f"| {label} | {r['reported_thousand_yen']:,.0f} | {r['owned_detail_thousand_yen']:,.0f} | "
            f"{r['owned_minus_reported_thousand_yen']:,.0f} | {r['owned_minus_reported_ratio']:.3%} |"
        )
    lines += [
        "",
        "取得価格は物件概要の開示値を採用。帳簿価額シートにも取得価格があり、以下の2件は一致しない。"
        "両方の値を全物件CSVに保存した。原因は未確認。鑑定額を分母とする利回りには影響しない。",
        "",
        "| ID | 物件概要（円） | 帳簿価額シート（円） | 差（円） |",
        "|---|---:|---:|---:|",
    ]
    for r in quality["price_differences"]:
        lines.append(
            f"| {r['property_id']} | {r['overview_yen']:,.0f} | {r['book_yen']:,.0f} | {r['difference_yen']:,.0f} |"
        )
    lines += [
        "",
        f"名称差は{len(quality['name_differences'])}件。表記揺れ・改称を含み、名称だけで落とさずIDで接続。"
        "元の各名称と未解明の集計差は加工JSONとHTMLの検証欄に記録した。",
        "",
        "再計算: リポジトリルートで `uv run --no-sync python market-research/scripts/analysis/japan_noi_valuation.py`。"
        "原本・SHA-256・全物件CSV・集計JSONは `_data/market-research/market/{raw,processed}/noi_valuation_20260930/`。",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Fetch missing original files only")
    args = parser.parse_args()
    references = json.loads(REFERENCE.read_text())
    period_days = (
        date.fromisoformat(references["period_end"])
        - date.fromisoformat(references["period_start"])
    ).days + 1
    if period_days != PERIOD_DAYS:
        raise ValueError("Unexpected period length")
    manifest = archive_sources(references, download=args.download)
    payload = (RAW / "adr_202607_property_data.xlsx").read_bytes()
    tables = {
        sheet: dict(xlsx_rows(payload, sheet))
        for sheet in ("物件概要", "帳簿価額", "鑑定評価", "収益状況")
    }
    properties, quality = parse_adr_tables(tables)
    if {p["appraisal_date"] for p in properties} != {references["period_end"]}:
        raise ValueError("Unexpected appraisal date")
    markets = aggregate_markets(properties)
    scenarios = []
    for market in markets:
        for rate in (0.02, 0.03, 0.04, 0.05):
            scenarios.append(
                {
                    "market": market["market"],
                    "loan_rate": rate,
                    **financing(
                        market["yield_on_appraisal"],
                        rate=rate,
                        ltv=0.7,
                        years=30,
                        reserve=0.005,
                        costs=0.07,
                    ),
                }
            )
    summary = {
        "references": references,
        "sources_manifest": manifest,
        "quality": quality,
        "markets": markets,
        "financing_scenarios": scenarios,
        "fukuoka_properties": [p for p in properties if p["market"] == "福岡"],
    }
    PROCESSED.mkdir(parents=True, exist_ok=True)
    with (PROCESSED / "properties.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(properties[0]))
        writer.writeheader()
        writer.writerows(properties)
    (PROCESSED / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    DOCS.mkdir(parents=True, exist_ok=True)
    name = "japan_noi_valuation_2026-09-30"
    (DOCS / (name + ".md")).write_text(markdown(summary))
    template = Path(__file__).with_suffix(".template.html").read_text()
    tokens = (REPO / "docs/templates/claude-report/tokens.css").read_text()
    safe_data = json.dumps(summary, ensure_ascii=False).replace("<", "\\u003c")
    html = template.replace("@@TOKENS@@", tokens).replace("@@DATA@@", safe_data)
    (DOCS / (name + ".html")).write_text(html)
    print(
        json.dumps({"quality": quality, "report": str(DOCS / (name + ".html"))}, ensure_ascii=False)
    )


if __name__ == "__main__":
    main()
