"""Traceable concept-stage cash budget, JPY throughout; CPU only.

Run from scripts with: python -B -m basic_design.costs
No market quote is inferred from an allowance. Accepted architecture-v1 is read only.
"""

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = Path("/home/kazumasa/projects/_data/sauna-design")
DATA = BASE / "cost-v1"
CASES = ("low", "base", "high")


def quantities():
    b = json.loads((BASE / "architecture-v1/calculations/basis.json").read_text())
    pools = b["pools"]
    wet = 44 + 15.75 + 18.85 - sum(p["surface_m2"] for p in pools)
    floor = sum(math.prod(s["room_inner"]) for s in b["sauna_dimensions"].values())
    skin = sum(
        2 * sum(s["room_inner"]) * s["ceiling"] + math.prod(s["room_inner"])
        for s in b["sauna_dimensions"].values()
    )
    lining = sum(p["surface_m2"] + 2 * sum(p["rect"][2:]) * p["depth"] for p in pools)
    # 10 tiles/case, 0.87 m2/case from 24,260/27,900 nominal catalogue coverage.
    tile_cases = math.ceil(wet * 1.1 / 0.87)
    return {
        "gross": 280,
        "wet_floor": wet,
        "wet_tile_order": tile_cases * 0.87,
        "wet_tile_cases": tile_cases,
        "sauna_floor": floor,
        "sauna_skin": skin,
        "pool_lining_net": lining,
        "pool_lining_order": lining * 1.15,
        "pool_perimeter": sum(2 * sum(p["rect"][2:]) for p in pools),
    }


def validate_items(rows):
    seen, scopes = set(), set()
    for r in rows:
        if r["id"] in seen or r["scope_key"] in scopes:
            raise ValueError("Duplicate item or work scope: " + r["id"])
        seen.add(r["id"])
        scopes.add(r["scope_key"])
        for k in ["quantity", "low", "base", "high"]:
            if not isinstance(r[k], (int, float)) or not math.isfinite(r[k]) or r[k] <= 0:
                raise ValueError("Missing/non-positive quantity or price: " + r["id"] + "/" + k)
        if not r["low"] <= r["base"] <= r["high"]:
            raise ValueError("Unordered price range: " + r["id"])
        if not all(r[k] for k in ["scope_key", "quantity_basis", "source_ids"]):
            raise ValueError("Untraceable cost: " + r["id"])


def load_items(q=None):
    q = q or quantities()
    rows = []
    with (ROOT / "plan/basic_design/cost_items.csv").open(encoding="utf-8-sig") as f:
        for raw in csv.DictReader(f):
            r = dict(raw)
            r["quantity"] = q[r["quantity_key"]] if r["quantity_key"] else float(r["quantity"])
            for k in CASES:
                r[k] = float(r.pop(k + "_man")) * 10000
                r[k + "_amount"] = r["quantity"] * r[k]
            r["tax_rate"] = 0 if r["stage"] == "startup_labor" else 0.1
            rows.append(r)
    validate_items(rows)
    return rows


def funding(
    direct,
    contractor_rate,
    contingency_rate,
    soft_cash,
    property_nonref,
    deposit,
    monthly,
    runway=3,
    tax=0.1,
):
    overhead = direct * contractor_rate
    contingency = (direct + overhead) * contingency_rate
    ex_tax = direct + overhead + contingency
    construction_cash = ex_tax * (1 + tax)
    nonref = construction_cash + soft_cash + property_nonref
    opening_cash = nonref + deposit
    return {
        "direct": direct,
        "contractor_overhead": overhead,
        "contingency": contingency,
        "construction_ex_tax": ex_tax,
        "construction_tax": ex_tax * tax,
        "construction_cash": construction_cash,
        "soft_cash": soft_cash,
        "property_nonref": property_nonref,
        "refundable_deposit": deposit,
        "opening_nonrefundable": nonref,
        "opening_cash": opening_cash,
        "monthly_opex": monthly,
        "reserve_3m": monthly * 3,
        "reserve_6m": monthly * 6,
        "funding_3m": opening_cash + monthly * 3,
        "funding_6m": opening_cash + monthly * 6,
        "funding_selected": opening_cash + monthly * runway,
    }


def tokyo_water_month(m3):
    """23 wards general business, assumed 50mm, one-month bill, 0..1000m3.

    Budget estimate before invoice integer rounding. A bathing subsidy is not assumed.
    """
    if not 0 <= m3 <= 1000:
        raise ValueError("This comparison tariff covers 0..1000m3 only")
    water = 20720 + m3 * 372
    sewer = 560
    left = max(0, m3 - 8)
    for width, rate in [
        (12, 110),
        (10, 140),
        (20, 170),
        (50, 200),
        (100, 230),
        (300, 270),
        (500, 310),
    ]:
        take = min(left, width)
        sewer += take * rate
        left -= take
    return (water + sewer) * 1.1


def operation(p, common, case):
    guests = p["visitors_day"] * p["operating_days"]
    # Previous daily inventory: showers .024m3/guest + make-up .020m3/guest,
    # daily full gross fill 10.2384 + 1m3 backwash; toilets/cleaning/laundry added.
    water_m3 = (11.2384 + 0.044 * p["visitors_day"] + common["water_other_m3_day"]) * p[
        "operating_days"
    ]
    rows = [
        {
            "item": "賃料・共益費枠",
            "quantity": p["rent_ex_tax"],
            "unit": "税抜円/月",
            "rate": 1.1,
            "cash": p["rent_ex_tax"] * 1.1,
            "basis": "A00;C12 賃料は物件未取得の仮定",
        },
        {
            "item": "現場給与・雇用側負担込み",
            "quantity": p["staff_per_shift"] * p["coverage_hours"] * p["operating_days"],
            "unit": "有給労働時間/月",
            "rate": p["loaded_hourly_pay"],
            "cash": p["staff_per_shift"]
            * p["coverage_hours"]
            * p["operating_days"]
            * p["loaded_hourly_pay"],
            "basis": "A00 常駐相当人数×清掃等込み18h。休暇/採用と負担込み単価を仮定",
        },
        {
            "item": "店長・管理人件費",
            "quantity": 1,
            "unit": "人分/月",
            "rate": p["management_month"],
            "cash": p["management_month"],
            "basis": "A00 現場勤務分に含まない管理枠。実シフト未作成",
        },
        {
            "item": "電気基本料金",
            "quantity": p["power_contract_kw"],
            "unit": "kW",
            "rate": common["electric_basic_incl_tax"],
            "cash": p["power_contract_kw"] * common["electric_basic_incl_tax"],
            "basis": "C08 高圧ベーシック税込例。力率/契約方式未定",
        },
        {
            "item": "電気従量・調整等込み仮定",
            "quantity": p["power_kwh"],
            "unit": "kWh/月",
            "rate": p["power_variable_incl_tax"],
            "cash": p["power_kwh"] * p["power_variable_incl_tax"],
            "basis": "A00;C08 25/28/34円は現行公表17.47に賦課/燃料/市場等を含めた感度仮定",
        },
        {
            "item": "ガス給湯・炭酸昇温",
            "quantity": p["gas_m3"],
            "unit": "m³/月",
            "rate": p["gas_unit_incl_tax"],
            "cash": p["gas_m3"] * p["gas_unit_incl_tax"],
            "basis": "A00 公表契約単価でない。損失/追い炊き/冬季を含む請求感度用の使用量と単価",
        },
        {
            "item": "一般用上下水道50mm",
            "quantity": water_m3,
            "unit": "m³/月",
            "rate": None,
            "cash": tokyo_water_month(water_m3),
            "basis": "C09;C10 日量の循環流量ではなく新規給水。便所/清掃等3m³日を追加",
        },
        {
            "item": "リネン・消耗品・洗濯",
            "quantity": guests,
            "unit": "来客/月",
            "rate": p["laundry_per_guest_incl_tax"],
            "cash": guests * p["laundry_per_guest_incl_tax"],
            "basis": "A00 タオル/館内着/アメニティ込み仮定。契約見積なし",
        },
        {
            "item": "保守・水質・薬剤・廃棄・通信等",
            "quantity": 1,
            "unit": "月",
            "rate": common["misc_month_" + case],
            "cash": common["misc_month_" + case],
            "basis": "A00 定期保守/検査/消耗/機器更新の小額積立を含む仮定",
        },
        {
            "item": "定期イベント追加費",
            "quantity": {"low": 4, "base": 8, "high": 12}[case],
            "unit": "開催/月",
            "rate": {"low": 30000, "base": 40000, "high": 60000}[case],
            "cash": {"low": 120000, "base": 320000, "high": 720000}[case],
            "basis": "A00 外部出演/応援要員の開催単価枠。自社対応時は実シフトへ置換し重ねない",
        },
    ]
    return {
        "rows": rows,
        "monthly": sum(r["cash"] for r in rows),
        "water_m3_month": water_m3,
        "note": "売上を差し引かない3/6か月分の資金バッファ。売上予測でも必要運転資金の会計評価でもない。借入元利返済/事業利益への税/決済歩率は除外。",
    }


def calculate():
    cfg = json.loads((ROOT / "plan/basic_design/cost_assumptions.json").read_text())
    sources = json.loads((ROOT / "plan/basic_design/cost_sources.json").read_text())
    q = quantities()
    rows = load_items(q)
    out = {}
    ids = {s["id"] for s in sources["sources"]}
    for r in rows:
        if not set(r["source_ids"].split(";")) <= ids:
            raise ValueError("Unknown source " + r["id"])
    for case in CASES:
        p = cfg["profiles"][case]
        op = operation(p, cfg["common"], case)
        direct = sum(r[case + "_amount"] for r in rows if r["stage"] == "direct")
        soft = sum(
            r[case + "_amount"] * (1 + r["tax_rate"]) for r in rows if r["stage"] != "direct"
        )
        rent = p["rent_ex_tax"]
        prop = {
            "工事期間の賃料": rent * p["construction_months"] * 1.1,
            "礼金": rent * p["key_money_months"] * 1.1,
            "仲介手数料": rent * p["broker_months"] * 1.1,
            "保証会社初回": rent * p["guarantee_months"],
        }
        # Guarantee-company fee is modeled as an insurance-type non-taxable payment;
        # actual contract taxation and renewal fee require confirmation.
        summary = funding(
            direct,
            p["contractor_rate"],
            p["contingency_rate"],
            soft,
            sum(prop.values()),
            rent * p["deposit_months"],
            op["monthly"],
        )
        summary["budget_gaps_3m"] = {
            str(b): b - summary["funding_3m"] for b in [100000000, 150000000, 200000000]
        }
        out[case] = {
            "summary": summary,
            "operation": op,
            "property_breakdown": prop,
            "categories": {
                cat: sum(r[case + "_amount"] for r in rows if r["category"] == cat)
                for cat in dict.fromkeys(r["category"] for r in rows)
            },
        }
    target = cfg["target_to_200m"]
    p = {**cfg["profiles"]["base"], **{k: target[k] for k in ["rent_ex_tax", "deposit_months"]}}
    op = operation(p, cfg["common"], "base")
    rent = p["rent_ex_tax"]
    prop = rent * (
        (p["construction_months"] + p["key_money_months"] + p["broker_months"]) * 1.1
        + p["guarantee_months"]
    )
    adjusted = funding(
        out["base"]["summary"]["direct"] - sum(target["direct_savings"].values()),
        p["contractor_rate"],
        p["contingency_rate"],
        out["base"]["summary"]["soft_cash"],
        prop,
        rent * p["deposit_months"],
        op["monthly"],
    )
    return {
        "date": cfg["date"],
        "currency": "JPY",
        "quantities": q,
        "items": rows,
        "config": cfg,
        "sources": sources["sources"],
        "cases": out,
        "price_status": "全工事の成約見積なし。公開定価は一部の比較資料。主要な工種は作成者の予算仮定。",
        "target_to_200m": {"summary": adjusted, "changes": target},
        "scope": "賃貸、現280㎡計画、3サ室/2冷槽/炭酸泉。浴槽床下と既存インフラが成立する条件付き。土地建物購入は未算入で価格未定。",
    }


def main():
    result = calculate()
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "tables").mkdir(exist_ok=True)
    (DATA / "calculations.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    for name, rows in [
        ("cost_detail", result["items"]),
        ("quantity_basis", [{"key": k, "value": v} for k, v in result["quantities"].items()]),
        (
            "summary",
            [
                {
                    "case": c,
                    **{
                        k: v
                        for k, v in result["cases"][c]["summary"].items()
                        if not isinstance(v, dict)
                    },
                }
                for c in CASES
            ],
        ),
    ]:
        with (DATA / "tables" / f"{name}.csv").open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    print(
        json.dumps(
            {
                "item_count": len(result["items"]),
                "base_summary_man": {
                    k: round(v / 10000, 1)
                    for k, v in result["cases"]["base"]["summary"].items()
                    if isinstance(v, (int, float))
                },
                "funding_3m_man": {
                    c: round(result["cases"][c]["summary"]["funding_3m"] / 10000, 1) for c in CASES
                },
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
