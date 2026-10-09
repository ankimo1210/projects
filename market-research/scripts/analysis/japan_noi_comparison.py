"""Offline, three residential J-REITs: actual annual NOI and acquisition forecasts."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from japan_noi_valuation import financing

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "market-research"
DATA = ROOT / "_data/market-research/market/processed/noi_expansion_20261001"
REPORT = PROJECT / "docs/data/validation/japan_noi_comparison_2026-10-01"
FUNDS = {"ADR": "adr", "NAF": "naf", "CFR": "comforia"}


def normalize_annual(row: dict, fund: str) -> dict:
    days = row.get("actual_operating_days", row.get("operating_days"))
    if days != 365:
        raise ValueError(f"Not full actual year: {fund}/{row.get('property_id')}")
    lease = row.get("master_lease", row.get("masterlease"))
    result = {
        **row,
        "fund": fund,
        "property_name": row.get("property_name", row.get("name")),
        "period_start": row.get("actual_period_start", row.get("period_start")),
        "period_end": row.get("actual_period_end", row.get("period_end")),
        "operating_days": days,
        "period_days": days,
        "period_calendar_days": days,
        "master_lease": lease,
        "contract_verified": lease in {"パス・スルー型", "パス・スルー"},
        "income_basis": "actual_two_full_disclosed_periods",
        "capex_annual_yen": row.get("capex_annual_yen"),
    }
    # The canonical annual export has one observation window. Half-year measures
    # remain in each fund's period_properties rather than sharing annual dates.
    for field in (
        "noi_period_yen",
        "revenue_period_yen",
        "operating_expense_period_yen",
        "depreciation_period_yen",
        "opex_ex_dep_period_yen",
        "capex_period_yen",
        "operating_expense_ex_dep",
        "noi_annualized_yen",
        "period",
    ):
        result.pop(field, None)
    for denominator in ("acquisition_price_yen", "appraisal_value_yen"):
        if result[denominator] <= 0:
            raise ValueError("Non-positive denominator")
    return result


def normalize_acquisition(row: dict, fund: str) -> dict:
    result = {
        **row,
        "fund": fund,
        "property_name": row.get("property_name", row.get("name")),
        "noi_forecast_annual_yen": row.get(
            "noi_forecast_annual_yen", row.get("forecast_noi_annual_yen")
        ),
        "yield_on_acquisition": row.get(
            "yield_on_acquisition", row.get("forecast_noi_yield_on_purchase")
        ),
        "income_basis": "acquisition_appraisal_forecast_not_actual",
        "source_income_basis": row.get("income_basis"),
        "acquisition_date": row.get("acquisition_date"),
        "acquisition_date_status": row.get("acquisition_date_status", row.get("acquired_status")),
        "asset_label": "学生住宅" if row.get("asset_type") == "alternative_housing" else "一般住宅",
    }
    # Keep forecast amounts only in explicitly named columns in the acquisition export.
    result.pop("noi_annual_yen", None)
    return result


def aggregate(rows: list[dict], *, by_fund: bool = False) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[(row["market"], row["fund"] if by_fund else "3社参考合算")].append(row)
    result = []
    for (market, fund), properties in sorted(groups.items()):
        sums = {
            key: sum(r[key] for r in properties)
            for key in (
                "noi_annual_yen",
                "acquisition_price_yen",
                "appraisal_value_yen",
                "revenue_annual_yen",
                "operating_expense_annual_yen",
            )
        }
        result.append(
            {
                "market": market,
                "fund": fund,
                "n": len(properties),
                **sums,
                "yield_on_acquisition": sums["noi_annual_yen"] / sums["acquisition_price_yen"],
                "yield_on_appraisal": sums["noi_annual_yen"] / sums["appraisal_value_yen"],
                "expense_ratio": sums["operating_expense_annual_yen"] / sums["revenue_annual_yen"],
                "unknown_contract_n": sum(not r["contract_verified"] for r in properties),
                "periods": sorted(
                    {f"{r.get('period_start')}〜{r.get('period_end')}" for r in properties}
                ),
            }
        )
    return result


def markdown(summary: dict) -> str:
    lines = [
        "# 日本の住宅NOI比較 — 3社・通年実績・直近取得",
        "",
        "調査日: 2026-10-01",
        "",
        "## 結果",
        "",
        "3社の通年住宅531件を接続。福岡14件の実績NOI/期末鑑定額は約4.57%、東京23区410件は約3.71%。"
        "これはREIT保有標本であり、都市平均・現在の売出利回り・成約Cap Rateではない。"
        "3社参考合算は決算時点と契約確認範囲が異なるため、社別表も併記する。",
        "",
        "| 都市 | 件数 | 実績NOI/開示取得価格 | 実績NOI/鑑定額 | 契約種別未確認 |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in summary["markets"]:
        lines.append(
            f"| {row['market']} | {row['n']} | {row['yield_on_acquisition']:.2%} | {row['yield_on_appraisal']:.2%} | {row['unknown_contract_n']} |"
        )
    lines += [
        "",
        "## 期間・選別・定義",
        "",
        "| 社 | 2期の実績期間 | 通年採用数 | 契約・除外 |",
        "|---|---|---:|---|",
    ]
    for row in summary["coverage"]:
        lines.append(
            f"| {row['fund']} | {row['period_start']}〜{row['period_end']} | {row['annual_n']} | {row['selection']} |"
        )
    lines += [
        "",
        "NOIは賃貸事業収入−減価償却を除く物件運営費。経常修繕・公租公課を含み、CAPEX・利息・基金運営報酬・投資家税を含まない。"
        "2期とも全期間運用・同じ取得額/持分の一般住宅を採用。半期を2倍せず、実際の2期NOIを加算。"
        "都市値はNOI合計÷価格合計で、物件利回りの単純平均ではない。取得価格は過去の取得/合併時条件を含む。",
        "",
        "## 社別比較",
        "",
        "| 都市 | 社 | 件数 | NOI/取得額 | NOI/鑑定額 |",
        "|---|---|---:|---:|---:|",
    ]
    for row in summary["fund_markets"]:
        lines.append(
            f"| {row['market']} | {row['fund']} | {row['n']} | {row['yield_on_acquisition']:.2%} | {row['yield_on_appraisal']:.2%} |"
        )
    lines += [
        "",
        "## 融資試算",
        "",
        "金利3%、LTV70%、30年元利均等、取得費7%、年次CAPEX積立0.5%/価格。実績NOIが続き、期末鑑定額で取得する分析用仮定。税引前。",
        "| 都市 | DSCR | CoC | DSCR1.25の価格/鑑定額 |",
        "|---|---:|---:|---:|",
    ]
    for row in summary["financing_default"]:
        lines.append(
            f"| {row['market']} | {row['dscr']:.2f} | {row['cash_on_cash']:.2%} | {row['max_price_ratio_for_dscr_125']:.1%} |"
        )
    lines += [
        "",
        "DSCR=NOI÷年間元利返済。CoC=(NOI−返済−積立)/(頭金+取得費)。逆算価格はDSCR条件のみで成約予測ではない。",
        "",
        "## 直近取得案件",
        "",
        "2025〜2026年の保有確認済み28件（一般住宅27・学生住宅1）。価格は実取得価格、NOIは取得時鑑定の予想で、取得後実績ではない。"
        "ADR4件は開示利回りが0.1ポイント丸めで、正確なNOI金額を逆算しない。小岩は改修後安定賃料による査定。"
        "NAF八王子・大森山王は保有確認済みだが、個別実引渡日未確認。予定日を実日付として表示しない。",
        "",
        "| 社 | 物件 | 取得日（未確認は空欄） | 取得額 百万円 | 予想NOI 百万円/年 | 予想NOI/取得額 | 原典 |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for row in summary["acquisitions"]:
        n = row["noi_forecast_annual_yen"]
        lines.append(
            f"| {row['fund']} | {row['property_name']} | {row['acquisition_date'] or '未確認'} | {row['acquisition_price_yen'] / 1e6:,.1f} | {n / 1e6 if n is not None else '非開示（丸め利回りのみ）'} | {row['yield_on_acquisition']:.2%} | [原典]({row['source_url']}) |"
        )
    lines += [
        "",
        "## 海外の参考値",
        "",
        "NY: CBRE H2 2025 Class A Infill Multifamily stabilized cap rate **4.50〜5.00%**（2026-02-10公表、p9）。"
        "H1 2026は登録フォーム経由の都市表を確認できず空欄。",
        "London: Knight Frank 2026-04-30 Prime BTR NIYはZone1 **3.90〜4.00%**、Zone2 **4.00〜4.15%**、"
        "Zones3–4 **4.15〜4.30%**、Greater London **4.25〜4.50%**。"
        "NIYの費用・取得費込み分母は未照合。日本の実績NOI/鑑定額と同一定義の順位を作らない。",
        "[海外定義・原典・保存状態](../global_noi_references_2026-10-01.json)",
        "",
        "## 品質・残る差",
        "",
        *[f"- {n}" for n in summary["quality_notes"]],
        "",
        "## 次の課題",
        "",
        "- 築年・駅距離・土地権利・住戸構成で条件を揃え、最近の取得案件と実績を接続。",
        "- コンフォリアの物件別マスターリースを確認。沖縄の住宅NOI標本を追加。",
        "- NY・Londonの同一物件NOI/NCF・価格と、実際の新規融資・為替ヘッジ費を確認。",
        "- ADR 1月期の全体対物件明細の費用差、Excel集計セルの範囲を解明。",
        "",
        "## 再実行・保存",
        "",
        "```bash",
        "cd /home/kazumasa/projects",
        "uv run --no-sync python market-research/scripts/analysis/japan_noi_adr.py",
        "uv run --no-sync python market-research/scripts/analysis/japan_noi_naf.py",
        "uv run --no-sync python market-research/scripts/analysis/japan_noi_comforia.py",
        "uv run --no-sync python market-research/scripts/analysis/japan_noi_comparison.py",
        "```",
        "",
        "PDF読取には既存のpdftotextが必要。保存原本から通信なしで再生成。原本はURL・取得日時・サイズ・SHA-256を照合。",
        "原本: `_data/market-research/market/raw/noi_expansion_20261001/`",
        "結果・531件CSV・28取得CSV・集計JSON: `_data/market-research/market/processed/noi_expansion_20261001/`",
        "",
        "## 原典一覧",
        "",
    ]
    for fund, sources in summary["sources"].items():
        for s in sources:
            if s.get("url"):
                lines.append(
                    f"- {fund}: [{s['filename']}]({s['url']}) — SHA-256 `{s.get('sha256', '未保存')}`"
                )
    return "\n".join(lines) + "\n"


def run() -> dict:
    summaries = {
        fund: json.loads((DATA / directory / "summary.json").read_text())
        for fund, directory in FUNDS.items()
    }
    rows = [
        normalize_annual(r, fund) for fund, d in summaries.items() for r in d["annual_properties"]
    ]
    keys = {(r["fund"], r["property_id"]) for r in rows}
    if len(keys) != len(rows):
        raise ValueError("Duplicate fund/property annual records")
    acquisitions = [
        normalize_acquisition(r, fund) for fund, d in summaries.items() for r in d["acquisitions"]
    ]
    markets = aggregate(rows)
    coverage = []
    selection = {
        "ADR": "2期全期間・パススルー確認済み、賃料保証除外",
        "NAF": "2期全期間・一般住宅・パススルー確認済み、宿泊等除外",
        "CFR": "2期全期間・一般住宅、契約種別未確認、持分変更・学生等除外",
    }
    for fund in FUNDS:
        selected = [r for r in rows if r["fund"] == fund]
        windows = {(r["period_start"], r["period_end"]) for r in selected}
        if len(windows) != 1:
            raise ValueError(f"Mixed annual period inside fund: {fund}")
        start, end = windows.pop()
        coverage.append(
            {
                "fund": fund,
                "annual_n": len(selected),
                "period_start": start,
                "period_end": end,
                "selection": selection[fund],
            }
        )
    summary = {
        "as_of": "2026-10-01",
        "coverage": coverage,
        "annual_properties": rows,
        "markets": markets,
        "fund_markets": aggregate(rows, by_fund=True),
        "verified_contract_markets": aggregate([r for r in rows if r["contract_verified"]]),
        "acquisitions": acquisitions,
        "financing_default": [
            {
                "market": m["market"],
                **financing(
                    m["yield_on_appraisal"], rate=0.03, ltv=0.7, years=30, reserve=0.005, costs=0.07
                ),
            }
            for m in markets
        ],
        "global": json.loads(
            (PROJECT / "docs/data/global_noi_references_2026-10-01.json").read_text()
        ),
        "quality": {f: d["quality"] for f, d in summaries.items()},
        "sources": {
            f: [
                {
                    **s,
                    "filename": s.get("filename", s.get("file")),
                    "size_bytes": s.get("size_bytes", s.get("bytes")),
                }
                for s in d["sources"]
            ]
            for f, d in summaries.items()
        },
        "quality_notes": [
            "ADR 7月期：売却済みを含む291件の全収益・費用・償却をPDFとExcelで全数照合。短信総額とのNOI差−141千円は丸め範囲。旧集計セルとの−0.09%を新集計の誤差として引き継がない。Excel集計セルの内訳は未解明のため不使用。",
            "ADR 1月期：売却済みを含む290件の収益・費用・償却はPDFとExcelで完全一致。ただし短信総額との差はNOI＋4,495千円（0.031%）、費用−4,795千円で丸めを超える。共通費等への配賦はせず、原因未確認として物件明細を採用。",
            "ADR R-011の7月鑑定額：Excel12.1億円に対し短信PDF12.3億円。短信を優先。2期の鑑定差と取得価格の異なる基準を記録。",
            "NAFの最新公表期は2026年2月期。8月期決算は10月20日公表予定。3社合算には5か月の時点差がある。非開示ホスピタリティの収入を補完しない。住宅通年118件のNOIは開示されている。",
            "コンフォリアは物件別マスターリース未確認156件を含む。ADR/NAFの確認済み375件集計を別途出し、156件をパススルーと推定しない。非開示ニチイホーム川口1件・底地/学生/高齢者等は一般住宅の基準から除外。",
            "コンフォリア学芸大学イーストの7月Excel収入内訳は合計欄と不一致。短信と一致する収入合計・費用合計・償却・NOIを採用し、収入構成の分析には使わない。",
            "全体のREIT報酬・財務費用は物件NOIの外。物件別CAPEXはADRだけ2期実額を取得、NAF/CFRはnullのまま。試算の積立0.5%は仮定で、実績CAPEXをゼロと扱わない。",
            "海外：Knight Frank PDFは保存・ハッシュ確認。CBRE等6原典はHTTP403のためWebで本文・表を照合、原本未保存を記録。都市表未照合・費用定義不明・融資未取得を空欄として残す。",
        ],
    }
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    for filename, items in (("annual_properties.csv", rows), ("acquisitions.csv", acquisitions)):
        fields = sorted({k for row in items for k in row})
        with (DATA / filename).open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(items)
    REPORT.with_suffix(".md").write_text(markdown(summary))
    template = (Path(__file__).with_suffix(".template.html")).read_text()
    css = (ROOT / "docs/templates/claude-report/tokens.css").read_text()
    embedded = json.dumps(summary, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    REPORT.with_suffix(".html").write_text(
        template.replace("@@TOKENS@@", css).replace("@@DATA@@", embedded)
    )
    print(
        f"{len(rows)} actual annual properties / {len(acquisitions)} acquisition forecasts -> {REPORT}.html"
    )
    return summary


if __name__ == "__main__":
    run()
