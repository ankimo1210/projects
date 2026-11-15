"""Property screen and cash budget linked to frozen phase 6; CPU only."""

import csv
import json
import math
from datetime import date

from .costs import BASE, ROOT

DATA = BASE / "property-v1"
BUDGET_CAP = 200000000
KEYS = [
    "rent_ex_tax",
    "refundable_deposit",
    "paid_preopening_months",
    "nonref_initial_cash",
    "pit_saving",
    "mep_saving",
    "procurement_saving",
    "extra_direct",
    "extra_cash",
    "opex_delta",
]
GATES = [
    ("use", "貸主の用途/浴槽/営業と必要工事の承諾"),
    ("fit", "面積・柱梁・動線・機械室の収まり"),
    ("support", "浴槽の支持と基礎までの荷重経路"),
    ("pit", "床下型Aの実現又は再設計した代替断面"),
    ("utilities", "区画への電源/給水/排水/熱源の割当"),
    ("outside", "排熱/排気/屋外機/搬入更新経路の権限と収まり"),
    ("egress", "建物全体の避難/消防/アクセス改修の成立"),
    ("permission", "所在地の用途変更/衛生等の適用・必要手続き"),
    ("net_cost", "追加費・再利用・調達減額の工事ID/根拠と非重複"),
]


def basis():
    return json.loads((BASE / "cost-v1/calculations.json").read_text())


def gate_template():
    return [
        {"id": k, "label": label, "status": 0, "evidence": "", "checked_at": ""}
        for k, label in GATES
    ]


def goal_inputs():
    return dict(
        rent_ex_tax=1200000,
        refundable_deposit=7200000,
        paid_preopening_months=5,
        nonref_initial_cash=3480000,
        pit_saving=2000000,
        mep_saving=5000000,
        procurement_saving=5000000,
        extra_direct=0,
        extra_cash=0,
        opex_delta=0,
    )


def candidate_budget(p):
    missing = [k for k in KEYS if p.get(k) is None or p.get(k) == ""]
    if missing:
        return {"total_cash": None, "missing": missing}
    if any(not isinstance(p[k], (int, float)) or not math.isfinite(p[k]) for k in KEYS):
        raise ValueError("All cash inputs must be finite numbers")
    if any(p[k] < 0 for k in KEYS if k != "opex_delta"):
        raise ValueError("Negative budget input")
    d = basis()
    s = d["cases"]["base"]["summary"]
    cfg = d["config"]["profiles"]["base"]
    prices = {r["id"]: r["base_amount"] for r in d["items"]}
    if p["pit_saving"] > sum(prices[k] for k in ["P01", "P02"]):
        raise ValueError("Pit savings exceed base scope")
    if p["mep_saving"] > sum(prices[k] for k in ["E03", "G05", "G08", "V01"]):
        raise ValueError("MEP savings exceed base scope")
    savings = sum(p[k] for k in ["pit_saving", "mep_saving", "procurement_saving"])
    if savings > s["direct"]:
        raise ValueError("Savings exceed direct budget")
    direct = s["direct"] - savings + p["extra_direct"]
    multiplier = (1 + cfg["contractor_rate"]) * (1 + cfg["contingency_rate"]) * 1.1
    construction = direct * multiplier
    nonrent = s["monthly_opex"] - cfg["rent_ex_tax"] * 1.1
    if nonrent + p["opex_delta"] < 0:
        raise ValueError("Non-rent monthly costs cannot be negative")
    monthly = nonrent + p["rent_ex_tax"] * 1.1 + p["opex_delta"]
    preopen = p["rent_ex_tax"] * 1.1 * p["paid_preopening_months"]
    total = sum(
        [
            construction,
            s["soft_cash"],
            preopen,
            p["nonref_initial_cash"],
            p["refundable_deposit"],
            p["extra_cash"],
            monthly * 3,
        ]
    )
    return {
        "total_cash": total,
        "headroom": BUDGET_CAP - total,
        "construction_cash": construction,
        "soft_cash": s["soft_cash"],
        "preopening_rent_cash": preopen,
        "nonref_initial_cash": p["nonref_initial_cash"],
        "deposit_cash": p["refundable_deposit"],
        "other_extra_cash": p["extra_cash"],
        "monthly_cash": monthly,
        "runway_3m_cash": monthly * 3,
        "direct": direct,
        "savings": savings,
        "multiplier": multiplier,
        "missing": [],
    }


def search_total(rent, deposit_months, saving):
    """Search-only closed form: all fees scale with rent, full return deposit.

    Uses phase 6's 5 paid preopening months, key1/broker1/guarantee.7, runway3.
    The candidate build instead accepts actual cash fees and refundable deposit.
    """
    d = basis()
    s = d["cases"]["base"]["summary"]
    p = d["config"]["profiles"]["base"]
    intercept = s["funding_3m"] - p["rent_ex_tax"] * (p["deposit_months"] + 11.7)
    return intercept + rent * (deposit_months + 11.7) - saving * 1.3915


def rent_limit(deposit_months, saving, cap=BUDGET_CAP):
    return (cap - search_total(0, deposit_months, saving)) / (deposit_months + 11.7)


def valid_text(value):
    return isinstance(value, str) and value.strip().lower() not in [
        "",
        "未確認",
        "未取得",
        "未入力",
        "未定",
        "不明",
        "n/a",
        "na",
        "?",
        "-",
    ]


def valid_evidence(g):
    try:
        day = date.fromisoformat(g.get("checked_at", ""))
    except (ValueError, TypeError):
        return False
    return 2000 <= day.year <= 2100 and valid_text(g.get("evidence"))


def assess(p, gates, identity=None, finance_evidence=None, budget_change_plan=None):
    byid = {g["id"]: g for g in gates}
    failed = [k for k, _ in GATES if byid.get(k, {}).get("status") == 3 and valid_evidence(byid[k])]
    result = candidate_budget(p)
    identity = identity or {}
    finance_evidence = finance_evidence or {}
    if not all(valid_text(identity.get(k)) for k in ["name", "location"]):
        return {"status": "資料不足", "unknown": ["物件名/所在地"], "budget": result}
    if failed:
        return {"status": "成立困難", "failed": failed, "budget": result}
    unknown = [
        k
        for k, _ in GATES
        if byid.get(k, {}).get("status") not in [1, 2] or not valid_evidence(byid.get(k, {}))
    ]
    unknown += ["費用根拠:" + k for k in KEYS if not valid_text(finance_evidence.get(k))]
    if unknown or result["total_cash"] is None:
        return {"status": "資料不足", "unknown": unknown, "budget": result}
    if result["headroom"] < 0:
        return {
            "status": "変更で対応" if valid_text(budget_change_plan) else "予算超過・変更案未確認",
            "budget": result,
        }
    if any(g["status"] == 2 for g in gates):
        return {"status": "変更で対応", "budget": result}
    return {
        "status": "成立見込み（予備判定）",
        "budget": result,
        "note": "基本条件の予備照合。契約判断・構造安全・許可取得済みを意味しない。",
    }


def calculate():
    with (ROOT / "plan/basic_design/property_conditions.csv").open(encoding="utf-8-sig") as f:
        conditions = list(csv.DictReader(f))
    sources = json.loads((ROOT / "plan/basic_design/property_sources.json").read_text())
    ids = {s["id"] for s in sources}
    assert len({r["id"] for r in conditions}) == len(conditions)
    for r in conditions:
        assert set(r["source_ids"].split(";")) <= ids
        assert all(r[k] for k in ["target", "hold_or_reject", "documents", "basis_type"])
    d = basis()
    s = d["cases"]["base"]["summary"]
    p = d["config"]["profiles"]["base"]
    rents = [1000000, 1100000, 1200000, 1300000, 1400000, 1500000]
    deposits = [4, 6, 8, 10]
    matrix = [
        {
            "rent_ex_tax": r,
            "deposit_months": n,
            "total_cash": search_total(r, n, 12000000),
            "required_direct_saving": max(0, (search_total(r, n, 0) - BUDGET_CAP) / 1.3915),
        }
        for r in rents
        for n in deposits
    ]
    frontiers = [
        {"deposit_months": n, "saving": saving, "max_rent_ex_tax": rent_limit(n, saving)}
        for n in deposits
        for saving in [7000000, 12000000]
    ]
    empty = {k: None for k in KEYS}
    gates = gate_template()
    return {
        "date": "2026-11-15",
        "currency": "JPY",
        "cap": BUDGET_CAP,
        "scope": "⑦物件条件表のみ。物件未取得、3D/GPU作業は保留。外部への照会送信なし。",
        "conditions": conditions,
        "sources": sources,
        "empty_candidate": {
            "identity": {"name": "", "location": ""},
            "finance": empty,
            "finance_evidence": {k: "" for k in KEYS},
            "budget_change_plan": "",
            "gates": gates,
            "assessment": assess(empty, gates),
        },
        "goal_example": {
            "label": "費用比較用の仮想条件。実物件ではない",
            "inputs": goal_inputs(),
            "budget": candidate_budget(goal_inputs()),
        },
        "matrix": matrix,
        "frontiers": frontiers,
        "frozen_cost": {
            "direct": s["direct"],
            "soft_cash": s["soft_cash"],
            "nonrent_monthly": s["monthly_opex"] - p["rent_ex_tax"] * 1.1,
            "construction_multiplier": 1.3915,
            "tax": 0.1,
            "runway_months": 3,
            "rent_coefficient_without_deposit": 11.7,
            "search_intercept": search_total(0, 0, 0),
            "base_funding": s["funding_3m"],
        },
        "limitations": [
            "現物件なし。数値は探索/比較条件、法定最低やメーカー採用条件ではない",
            "価格未取得を0円にしない。候補の金融欄は全て未入力で配布",
            "主室/サブの能力離隔、アウフ集中/休憩24席等は未解決のまま引継ぎ",
            "余剰面積・建物改修・譲渡/償却・融資費/撤退費は個別の金額/時点を確認",
        ],
    }


def main():
    r = calculate()
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "tables").mkdir(exist_ok=True)
    (DATA / "property.json").write_text(json.dumps(r, ensure_ascii=False, indent=2) + "\n")
    for name, rows in [
        ("conditions", r["conditions"]),
        ("rent_deposit_comparison", r["matrix"]),
        ("rent_limits", r["frontiers"]),
        ("candidate_gates", r["empty_candidate"]["gates"]),
    ]:
        with (DATA / "tables" / f"{name}.csv").open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    print(
        json.dumps(
            {
                "conditions": len(r["conditions"]),
                "gates": len(GATES),
                "blank_candidate_status": r["empty_candidate"]["assessment"]["status"],
                "goal_example_man": r["goal_example"]["budget"]["total_cash"] / 10000,
                "rent_limit_700_saving_6mo_man": rent_limit(6, 7000000) / 10000,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
