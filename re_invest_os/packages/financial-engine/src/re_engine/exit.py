"""売却シナリオ。

- 売却価格 = 保有最終年NOI / exit_cap_rate
- 売却諸費用 = 売却価格 * selling_cost_rate (仲介手数料・登記等)
- 簿価 = 取得価額 - 累計減価償却
- 譲渡所得 = 売却価格 - 売却諸費用 - 簿価
- 譲渡税 = 譲渡所得 * (5年超: long_rate / 5年以下: short_rate)
- 税引後手残り = 売却価格 - 売却諸費用 - 残債 - 譲渡税
"""

from __future__ import annotations

from re_engine.loan import loan_balance_at_month
from re_engine.models import (
    Assumptions,
    ExitResult,
    LoanScheduleRow,
    YearlyCashflow,
)
from re_engine.tax import capital_gain_tax


def compute_exit(
    a: Assumptions,
    yearly_cashflows: list[YearlyCashflow],
    loan_schedule: list[LoanScheduleRow],
) -> ExitResult:
    if not yearly_cashflows:
        raise ValueError("yearly_cashflows must not be empty")
    final_year = a.exit_.hold_period_years
    final_cf = yearly_cashflows[final_year - 1]

    # 売却価格 = 保有最終年NOI / 出口Cap
    sale_price = round(final_cf.noi_yen / a.exit_.exit_cap_rate)
    selling_costs = round(sale_price * a.exit_.selling_cost_rate)

    # 残債
    remaining_loan = loan_balance_at_month(loan_schedule, final_year * 12)

    # 簿価 = 取得価額 - 累計減価償却 (土地は償却しないので建物分のみ)
    total_dep = sum(cf.depreciation_yen for cf in yearly_cashflows)
    book_value = max(
        a.property.land_value_yen,  # 土地は簿価減らない
        a.property.purchase_price_yen - total_dep,
    )

    # 譲渡所得・譲渡税
    capital_gain = sale_price - selling_costs - book_value
    cg_tax = capital_gain_tax(
        sale_price_yen=sale_price,
        selling_costs_yen=selling_costs,
        book_value_yen=book_value,
        hold_period_years=final_year,
        short_rate=a.tax.capital_gain_short_rate,
        long_rate=a.tax.capital_gain_long_rate,
    )

    net_proceeds = sale_price - selling_costs - remaining_loan - cg_tax

    return ExitResult(
        sale_price_yen=sale_price,
        selling_costs_yen=selling_costs,
        remaining_loan_yen=remaining_loan,
        book_value_yen=book_value,
        capital_gain_yen=capital_gain,
        capital_gain_tax_yen=cg_tax,
        net_proceeds_yen=net_proceeds,
    )
