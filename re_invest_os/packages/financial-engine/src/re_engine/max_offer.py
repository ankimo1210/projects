"""最大買付価格 (制約付き最適化、二分探索)。

仕様: docs/architecture/calculation_engine_spec.md §5.7

価格を変動させ、LTVを維持しながら以下の制約をすべて満たす最大価格を探す。
- DSCR ≥ min_dscr
- IRR ≥ min_irr (定義されている場合)
- 初年度ATCF ≥ min_first_year_atcf_yen
- 自己資金 ≤ max_equity_yen (定義されている場合)
- 金利ストレス時の DSCR ≥ min_dscr (定義されている場合)

binding_constraints: 最大価格を制約していた要因のリスト
"""

from __future__ import annotations

import copy

from pydantic import BaseModel, ConfigDict, Field

from re_engine.analyze import run_full_analysis
from re_engine.models import Assumptions


class InvestorTargets(BaseModel):
    min_dscr: float = 1.25
    min_irr: float = 0.08
    min_first_year_atcf_yen: int = 0
    max_equity_yen: int | None = None
    stress_interest_rate: float | None = None  # 金利+1%等を指定。Noneなら無視
    model_config = ConfigDict(extra="forbid")


class MaxOfferResult(BaseModel):
    current_price_yen: int
    max_price_yen: int
    safe_price_yen: int  # max - 5% (バッファ)
    required_discount_yen: int  # 現価格との差分 (負なら指値が必要)
    binding_constraints: list[str] = Field(default_factory=list)
    iterations: int
    converged: bool
    model_config = ConfigDict(extra="forbid")


def _rebuild_at_price(base: Assumptions, new_price: int) -> Assumptions:
    """価格だけ変更した新しい Assumptions を返す。

    LTV比率は維持 (loan_amount = new_price * 元LTV)。
    土地・建物比率も維持。
    """
    if base.property.purchase_price_yen <= 0:
        raise ValueError("base price must be > 0")
    ratio = new_price / base.property.purchase_price_yen
    a = copy.deepcopy(base)
    a.property.purchase_price_yen = new_price
    a.property.land_value_yen = round(base.property.land_value_yen * ratio)
    a.property.building_value_yen = round(base.property.building_value_yen * ratio)
    a.loan.loan_amount_yen = round(base.loan.loan_amount_yen * ratio)
    a.acquisition.equity_yen = round(base.acquisition.equity_yen * ratio)
    return a


def _check_constraints(a: Assumptions, targets: InvestorTargets) -> list[str]:
    """この Assumptions が制約を満たすかチェック。違反した制約名のリストを返す。"""
    violations: list[str] = []
    result = run_full_analysis(a)
    k = result.kpi

    if k.dscr_min < targets.min_dscr:
        violations.append(f"dscr_min ({k.dscr_min:.2f} < {targets.min_dscr})")
    if k.equity_irr is None or k.equity_irr < targets.min_irr:
        irr_str = "None" if k.equity_irr is None else f"{k.equity_irr * 100:.2f}%"
        violations.append(f"irr ({irr_str} < {targets.min_irr * 100:.2f}%)")
    if k.atcf_first_year_yen < targets.min_first_year_atcf_yen:
        violations.append(
            f"atcf_year1 (¥{k.atcf_first_year_yen:,} < ¥{targets.min_first_year_atcf_yen:,})"
        )
    if targets.max_equity_yen is not None and a.acquisition.equity_yen > targets.max_equity_yen:
        violations.append(f"equity (¥{a.acquisition.equity_yen:,} > ¥{targets.max_equity_yen:,})")
    # 金利ストレス
    if targets.stress_interest_rate is not None:
        stressed = copy.deepcopy(a)
        stressed.loan.interest_rate = targets.stress_interest_rate
        stress_result = run_full_analysis(stressed)
        if stress_result.kpi.dscr_min < targets.min_dscr:
            violations.append(
                f"dscr_stress (@{targets.stress_interest_rate * 100:.2f}%: "
                f"{stress_result.kpi.dscr_min:.2f})"
            )
    return violations


def max_offer_price(
    base: Assumptions,
    targets: InvestorTargets | None = None,
    search_range: tuple[int, int] | None = None,
    tolerance_yen: int = 100_000,
    max_iterations: int = 30,
) -> MaxOfferResult:
    """最大買付価格を二分探索。

    制約をすべて満たす最大価格を探す。価格が変動するとローン・自己資金・土地建物配分も同比率で変動する。
    """
    targets = targets or InvestorTargets()
    current = base.property.purchase_price_yen
    if search_range is None:
        lo = int(current * 0.30)
        hi = int(current * 1.05)
    else:
        lo, hi = search_range

    iterations = 0
    last_violations_at_hi: list[str] = []

    # 上限で制約を満たすなら、現在価格でもOK
    upper_a = _rebuild_at_price(base, hi)
    upper_violations = _check_constraints(upper_a, targets)
    if not upper_violations:
        # 制約満たす → 最大価格 = hi
        max_price = hi
        binding: list[str] = []
        iterations = 1
        converged = True
    else:
        # 下限で違反するなら、購入不可
        lower_a = _rebuild_at_price(base, lo)
        lower_violations = _check_constraints(lower_a, targets)
        if lower_violations:
            return MaxOfferResult(
                current_price_yen=current,
                max_price_yen=0,
                safe_price_yen=0,
                required_discount_yen=current,
                binding_constraints=lower_violations,
                iterations=2,
                converged=False,
            )

        # 二分探索: lo は満たす、hi は満たさない、その中間で境界を探す
        while hi - lo > tolerance_yen and iterations < max_iterations:
            mid = (lo + hi) // 2
            mid_a = _rebuild_at_price(base, mid)
            v = _check_constraints(mid_a, targets)
            if v:
                hi = mid
                last_violations_at_hi = v
            else:
                lo = mid
            iterations += 1

        max_price = lo
        binding = last_violations_at_hi
        converged = (hi - lo) <= tolerance_yen

    safe_price = int(max_price * 0.95)
    required_discount = current - max_price  # 正なら指値が必要

    return MaxOfferResult(
        current_price_yen=current,
        max_price_yen=max_price,
        safe_price_yen=safe_price,
        required_discount_yen=required_discount,
        binding_constraints=binding,
        iterations=iterations,
        converged=converged,
    )
