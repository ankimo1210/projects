"""Public-listing comparison; reference cash cases never imply verified feasibility."""

import json

from .costs import BASE, ROOT
from .property import basis

DATA = BASE / "candidate-search-v1"
SOURCE = ROOT / "plan/basic_design/candidate_search_20261115.json"


def reference(candidate, assumptions, saving=0):
    frozen = basis()
    base = frozen["cases"]["base"]["summary"]
    cfg = frozen["config"]["profiles"]["base"]
    tax = assumptions["tax"]
    multiplier = (1 + cfg["contractor_rate"]) * (1 + cfg["contingency_rate"]) * (1 + tax)
    nonrent = base["monthly_opex"] - cfg["rent_ex_tax"] * 1.1
    if saving < 0 or saving > base["direct"]:
        raise ValueError("Saving must be a nonnegative net direct construction saving")
    rent = candidate["rent_ex_yen"]
    common = candidate["common_ex_for_reference_yen"]
    total_monthly_rent = (rent + common) * (1 + tax)
    deposit = rent * candidate["deposit_months"]
    key = rent * (1 + tax) * candidate["key_months_for_reference"]
    broker = rent * (1 + tax) * assumptions["broker_months_base_rent_gross"]
    guarantee = total_monthly_rent * assumptions["guarantee_months_total_gross"]
    preopen = total_monthly_rent * assumptions["preopening_paid_months"]
    construction = (base["direct"] - saving) * multiplier
    monthly = nonrent + total_monthly_rent
    reserve = monthly * assumptions["runway_months"]
    total = (
        construction + base["soft_cash"] + preopen + deposit + key + broker + guarantee + reserve
    )
    # Unknown additional costs are expressly outside the numeric reference, not real zeros.
    return dict(
        reference_total_yen=total,
        headroom_yen=assumptions["budget_yen"] - total,
        construction_yen=construction,
        soft_yen=base["soft_cash"],
        deposit_paid_yen=deposit,
        key_reference_yen=key,
        broker_reference_yen=broker,
        guarantee_reference_yen=guarantee,
        preopen_rent_yen=preopen,
        monthly_rent_gross_yen=total_monthly_rent,
        monthly_opex_reference_yen=monthly,
        reserve_yen=reserve,
        saving_direct_yen=saving,
        multiplier=multiplier,
        unpriced_extras_yen=None,
        feasibility="資料不足（参考総額のみ）",
    )


def calculate():
    source = json.loads(SOURCE.read_text())
    a = source["assumptions"]
    frozen = basis()
    b = frozen["cases"]["base"]["summary"]
    cfg = frozen["config"]["profiles"]["base"]
    nonrent = b["monthly_opex"] - cfg["rent_ex_tax"] * 1.1
    for c in source["candidates"]:
        c["cases"] = [reference(c, a, s) for s in a["saving_scenarios_direct_yen"]]
        zero = c["cases"][0]
        c["required_net_direct_saving_yen"] = max(
            0, (zero["reference_total_yen"] - a["budget_yen"]) / zero["multiplier"]
        )
        c["extra_direct_capacity_at_1200_yen"] = c["cases"][-1]["headroom_yen"] / zero["multiplier"]
        c["unpriced_extras_yen"] = None
        c["verified_reuse_saving_yen"] = None
        c["bath_use_permission"] = "未確認"
        c["fit_verified"] = False
    source["frozen_basis"] = dict(
        direct_yen=b["direct"],
        soft_yen=b["soft_cash"],
        nonrent_monthly_yen=nonrent,
        contractor_rate=cfg["contractor_rate"],
        contingency_rate=cfg["contingency_rate"],
        original_funding_3m_yen=b["funding_3m"],
    )
    return source


def write():
    DATA.mkdir(parents=True, exist_ok=True)
    d = calculate()
    (DATA / "calculations.json").write_text(json.dumps(d, ensure_ascii=False, indent=2))
    return d


if __name__ == "__main__":
    d = write()
    print(
        json.dumps(
            {
                "candidates": len(d["candidates"]),
                "results": [
                    {
                        "id": c["id"],
                        "totals_man": [
                            round(r["reference_total_yen"] / 10000, 2) for r in c["cases"]
                        ],
                        "required_saving_man": round(
                            c["required_net_direct_saving_yen"] / 10000, 2
                        ),
                    }
                    for c in d["candidates"]
                ],
            },
            ensure_ascii=False,
        )
    )
