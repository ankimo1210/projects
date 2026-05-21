"""税務計算: 減価償却、課税所得、所得税、譲渡税。

注意:
- これは参考試算であり、税務助言ではない。実際の申告は税理士確認が必要。
- 不動産所得が赤字のとき、土地利息部分は損益通算できない (措置法41-4) を考慮。
"""

from __future__ import annotations

from re_engine.constants import (
    Structure,
    depreciation_rate,
    remaining_life_years,
)


def annual_depreciation(
    building_value_yen: int,
    structure: Structure,
    completion_year: int,
    evaluation_year: int,
) -> int:
    """年間減価償却費 (定額法)。

    中古資産は簡便法による残存耐用年数を使用。
    """
    if building_value_yen <= 0:
        return 0
    life = remaining_life_years(structure, completion_year, evaluation_year)
    rate = depreciation_rate(life)
    return round(building_value_yen * rate)


def disallowed_land_interest(interest_yen: int, land_value_yen: int, total_price_yen: int) -> int:
    """土地に対応する利息で、不動産所得の赤字に損益通算できない部分。

    措置法41-4 (土地等の取得に係る借入金利子の特例)。
    """
    if total_price_yen <= 0 or interest_yen <= 0 or land_value_yen <= 0:
        return 0
    return round(interest_yen * land_value_yen / total_price_yen)


def taxable_income(
    noi_yen: int,
    interest_yen: int,
    depreciation_yen: int,
    land_value_yen: int = 0,
    total_price_yen: int = 0,
) -> int:
    """不動産所得の課税所得 (給与所得との損益通算後)。

    課税所得 = NOI - 利息 - 減価償却
    ただし赤字のとき、土地利息部分は損益通算から除外する。
    """
    raw = noi_yen - interest_yen - depreciation_yen
    if raw >= 0:
        return raw
    # 赤字: 土地利息分は通算できないため、その分赤字額を減らす
    disallowed = disallowed_land_interest(interest_yen, land_value_yen, total_price_yen)
    return raw + min(disallowed, -raw)


def income_tax(taxable_yen: int, income_tax_rate: float, resident_tax_rate: float) -> int:
    """所得税 + 住民税の概算。

    給与所得との合算課税を想定し、不動産所得分にユーザーの限界税率を当てる。
    赤字は 0 (還付や繰越はここでは扱わない、給与側で吸収する想定)。
    """
    if taxable_yen <= 0:
        return 0
    return round(taxable_yen * (income_tax_rate + resident_tax_rate))


def capital_gain_tax(
    sale_price_yen: int,
    selling_costs_yen: int,
    book_value_yen: int,
    hold_period_years: int,
    short_rate: float,
    long_rate: float,
) -> int:
    """譲渡所得税の概算。

    保有5年超なら長期譲渡 (約20%)、5年以下なら短期譲渡 (約39%)。
    譲渡所得 = 売却価格 - 売却諸費用 - 簿価
    """
    gain = sale_price_yen - selling_costs_yen - book_value_yen
    if gain <= 0:
        return 0
    rate = long_rate if hold_period_years > 5 else short_rate
    return round(gain * rate)
