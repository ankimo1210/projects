"""買付価格レンジ (aggressive / base / conservative) の純粋関数。

各ポリシー (BidPolicy) は:
- min_dscr, min_after_tax_irr  → 制約
- rent_shock, vacancy_shock, rate_shock, opex_shock  → ベース前提に対するストレス

各ポリシーごとに:
1. base Assumptions に shock を適用したストレス Assumptions を作る
2. その上で既存 max_offer_price の二分探索を回す
3. 制約 (DSCR / IRR / ATCF) を満たす最大価格を得る

最後に単調性 (conservative <= base <= aggressive) を後処理で保証する。
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from re_engine.max_offer import InvestorTargets, max_offer_price
from re_engine.models import Assumptions


@dataclass(frozen=True)
class BidPolicy:
    name: str
    min_dscr: float
    min_after_tax_irr: float
    rent_shock: float  # 賃料変化率 (例: -0.05 = -5%)
    vacancy_shock: float  # 空室率の加算 (例: 0.02 = +2pt)
    rate_shock: float  # 金利の加算 (例: 0.005 = +0.5pt)
    opex_shock: float  # OPEX 倍率増 (例: 0.05 = +5%)


DEFAULT_BID_POLICIES: list[BidPolicy] = [
    BidPolicy(
        name="aggressive",
        min_dscr=1.20,
        min_after_tax_irr=0.075,
        rent_shock=0.00,
        vacancy_shock=0.00,
        rate_shock=0.00,
        opex_shock=0.00,
    ),
    BidPolicy(
        name="base",
        min_dscr=1.25,
        min_after_tax_irr=0.080,
        rent_shock=-0.03,
        vacancy_shock=0.02,
        rate_shock=0.005,
        opex_shock=0.05,
    ),
    BidPolicy(
        name="conservative",
        min_dscr=1.35,
        min_after_tax_irr=0.090,
        rent_shock=-0.07,
        vacancy_shock=0.05,
        rate_shock=0.010,
        opex_shock=0.10,
    ),
]


def apply_shocks(base: Assumptions, policy: BidPolicy) -> Assumptions:
    """policy の shock を base に適用した新しい Assumptions を返す。

    - rent: gpi_monthly_yen *= (1 + rent_shock)
    - vacancy: vacancy_rate += vacancy_shock (clamp [0, 1])
    - rate: loan.interest_rate += rate_shock (clamp [0, 1])
    - opex: 円建て OPEX フィールドを (1 + opex_shock) 倍
            (management_fee_rate は % なので非対象)
    """
    a = copy.deepcopy(base)
    # rent
    if policy.rent_shock != 0:
        a.income.gpi_monthly_yen = max(
            1, round(a.income.gpi_monthly_yen * (1 + policy.rent_shock))
        )
    # vacancy
    if policy.vacancy_shock != 0:
        a.income.vacancy_rate = min(1.0, max(0.0, a.income.vacancy_rate + policy.vacancy_shock))
    # rate
    if policy.rate_shock != 0:
        a.loan.interest_rate = min(1.0, max(0.0, a.loan.interest_rate + policy.rate_shock))
    # opex (円建てフィールドのみ)
    if policy.opex_shock != 0:
        mul = 1 + policy.opex_shock
        a.opex.repair_reserve_monthly_yen = round(a.opex.repair_reserve_monthly_yen * mul)
        a.opex.fixed_property_tax_yen = round(a.opex.fixed_property_tax_yen * mul)
        a.opex.insurance_yen = round(a.opex.insurance_yen * mul)
        a.opex.building_mgmt_yen = round(a.opex.building_mgmt_yen * mul)
        a.opex.other_opex_yen = round(a.opex.other_opex_yen * mul)
    return a


class BidRangeEntry(BaseModel):
    name: str
    price_yen: int | None  # None = 成立不能
    binding_constraints: list[str] = Field(default_factory=list)
    converged: bool
    explanation: str
    model_config = ConfigDict(extra="forbid")


class BidRangesResult(BaseModel):
    asking_price_yen: int
    aggressive: BidRangeEntry
    base: BidRangeEntry
    conservative: BidRangeEntry
    gap_to_base_price_yen: int | None  # base_price - asking_price (負ならディスカウント必要)
    gap_to_base_price_pct: float | None
    monotonicity_enforced: bool  # 単調性違反を後処理で補正したか
    model_config = ConfigDict(extra="forbid")


def _explain(policy: BidPolicy) -> str:
    """ポリシー条件の人間可読な説明 (UI 透過用)。"""
    rent = f"賃料 {policy.rent_shock * 100:+.1f}%" if policy.rent_shock else ""
    vac = f"空室率 +{policy.vacancy_shock * 100:.1f}pt" if policy.vacancy_shock else ""
    rate = f"金利 +{policy.rate_shock * 100:.2f}pt" if policy.rate_shock else ""
    opex = f"OPEX +{policy.opex_shock * 100:.0f}%" if policy.opex_shock else ""
    shocks = ", ".join(s for s in (rent, vac, rate, opex) if s) or "現状前提"
    return (
        f"{shocks} の条件で、DSCR {policy.min_dscr:.2f} / "
        f"税後IRR {policy.min_after_tax_irr * 100:.1f}% を満たす価格"
    )


def _solve_one(base: Assumptions, policy: BidPolicy) -> BidRangeEntry:
    shocked = apply_shocks(base, policy)
    targets = InvestorTargets(
        min_dscr=policy.min_dscr,
        min_irr=policy.min_after_tax_irr,
        min_first_year_atcf_yen=0,
    )
    res = max_offer_price(shocked, targets)
    price: int | None
    if res.max_price_yen <= 0:
        price = None
    else:
        price = res.max_price_yen
    return BidRangeEntry(
        name=policy.name,
        price_yen=price,
        binding_constraints=list(res.binding_constraints),
        converged=res.converged,
        explanation=_explain(policy),
    )


def _enforce_monotonicity(
    aggressive: BidRangeEntry, base: BidRangeEntry, conservative: BidRangeEntry
) -> tuple[BidRangeEntry, BidRangeEntry, BidRangeEntry, bool]:
    """単調性 conservative <= base <= aggressive を保証。

    上位が下位より低い場合、上位を下位に揃える (クランプ)。
    None は最弱と見なす (= 0)。
    """
    enforced = False

    def _val(e: BidRangeEntry) -> int:
        return e.price_yen if e.price_yen is not None else 0

    # base が aggressive を超えないようにクランプ
    if _val(base) > _val(aggressive) and aggressive.price_yen is not None:
        base = base.model_copy(update={"price_yen": aggressive.price_yen})
        enforced = True
    # conservative が base を超えないようにクランプ
    if _val(conservative) > _val(base) and base.price_yen is not None:
        conservative = conservative.model_copy(update={"price_yen": base.price_yen})
        enforced = True
    return aggressive, base, conservative, enforced


def bid_ranges(
    base: Assumptions,
    policies: list[BidPolicy] | None = None,
) -> BidRangesResult:
    """3 ポリシーで買付価格レンジを計算する。"""
    pols = policies or DEFAULT_BID_POLICIES
    by_name: dict[str, BidRangeEntry] = {}
    for p in pols:
        by_name[p.name] = _solve_one(base, p)
    aggressive = by_name["aggressive"]
    base_e = by_name["base"]
    conservative = by_name["conservative"]
    aggressive, base_e, conservative, enforced = _enforce_monotonicity(
        aggressive, base_e, conservative
    )
    asking = base.property.purchase_price_yen
    if base_e.price_yen is not None:
        gap = base_e.price_yen - asking
        gap_pct = gap / asking
    else:
        gap = None
        gap_pct = None
    return BidRangesResult(
        asking_price_yen=asking,
        aggressive=aggressive,
        base=base_e,
        conservative=conservative,
        gap_to_base_price_yen=gap,
        gap_to_base_price_pct=gap_pct,
        monotonicity_enforced=enforced,
    )
