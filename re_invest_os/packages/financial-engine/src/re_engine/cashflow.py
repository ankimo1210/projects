"""キャッシュフロー・プロジェクション (純粋関数)。

各年:
  GPI         = 月額賃料合計 * 12 * (1 + rent_growth)^(t-1)
  Vacancy     = GPI * vacancy_rate
  BadDebt     = (GPI - Vacancy) * bad_debt_rate
  EGI         = GPI - Vacancy - BadDebt
  OPEX        = 管理費(GPI比) + 修繕積立 + 固都税 + 保険 + 建物管理 + その他
                (固定費は opex_growth で複利成長)
  NOI         = EGI - OPEX
  DebtService = 年間返済額 (loan schedule から)
  BTCF        = NOI - DebtService
  Taxable     = NOI - Interest - Depreciation (土地利息損益通算除外考慮)
  Tax         = Taxable * (所得税率 + 住民税率) (正のとき)
  ATCF        = BTCF - Tax
"""

from __future__ import annotations

from re_engine.loan import annual_debt_service, annual_interest, annual_principal
from re_engine.models import Assumptions, LoanScheduleRow, YearlyCashflow
from re_engine.tax import (
    annual_depreciation,
    income_tax,
    taxable_income,
)


def _gpi_year(a: Assumptions, year: int) -> int:
    """年間 GPI (満室想定総収入)。"""
    base = (a.income.gpi_monthly_yen + a.income.other_income_monthly_yen) * 12
    growth = (1.0 + a.income.rent_growth_rate) ** (year - 1)
    return round(base * growth)


def _opex_year(a: Assumptions, year: int, egi_yen: int) -> int:
    """年間 OPEX。管理費は EGI 比、その他固定費は opex_growth で複利成長。"""
    growth = (1.0 + a.opex.opex_growth_rate) ** (year - 1)
    management = round(egi_yen * a.opex.management_fee_rate)
    repair_reserve = round(a.opex.repair_reserve_monthly_yen * 12 * growth)
    fixed_property_tax = round(a.opex.fixed_property_tax_yen * growth)
    insurance = round(a.opex.insurance_yen * growth)
    building_mgmt = round(a.opex.building_mgmt_yen * growth)
    other = round(a.opex.other_opex_yen * growth)
    return management + repair_reserve + fixed_property_tax + insurance + building_mgmt + other


def _completion_year(building_completion_ym: str) -> int:
    return int(building_completion_ym.split("-")[0])


def project_cashflows(
    a: Assumptions,
    loan_schedule: list[LoanScheduleRow],
) -> list[YearlyCashflow]:
    """保有期間分のキャッシュフローを年次で算出。"""
    completion_year = _completion_year(a.property.building_completion_ym)
    # 減価償却は取得時点で確定し、保有期間中は一定
    annual_dep = annual_depreciation(
        a.property.building_value_yen,
        a.property.structure,
        completion_year,
        a.property.acquisition_year,
    )
    out: list[YearlyCashflow] = []

    for year in range(1, a.exit_.hold_period_years + 1):
        gpi = _gpi_year(a, year)
        vacancy = round(gpi * a.income.vacancy_rate)
        bad_debt = round((gpi - vacancy) * a.income.bad_debt_rate)
        egi = gpi - vacancy - bad_debt
        opex = _opex_year(a, year, egi)
        noi = egi - opex

        ds = annual_debt_service(loan_schedule, year)
        interest = annual_interest(loan_schedule, year)
        principal = annual_principal(loan_schedule, year)
        btcf = noi - ds

        dep = annual_dep

        taxable = taxable_income(
            noi_yen=noi,
            interest_yen=interest,
            depreciation_yen=dep,
            land_value_yen=a.property.land_value_yen,
            total_price_yen=a.property.purchase_price_yen,
        )
        tax = income_tax(taxable, a.tax.income_tax_rate, a.tax.resident_tax_rate)
        atcf = btcf - tax

        # 年末残債
        if year * 12 <= len(loan_schedule):
            balance_end = loan_schedule[year * 12 - 1].balance_yen
        else:
            balance_end = 0

        out.append(
            YearlyCashflow(
                year=year,
                gpi_yen=gpi,
                vacancy_loss_yen=vacancy,
                bad_debt_yen=bad_debt,
                egi_yen=egi,
                opex_yen=opex,
                noi_yen=noi,
                debt_service_yen=ds,
                btcf_yen=btcf,
                depreciation_yen=dep,
                interest_expense_yen=interest,
                principal_payment_yen=principal,
                taxable_income_yen=taxable,
                tax_yen=tax,
                atcf_yen=atcf,
                loan_balance_end_yen=balance_end,
            )
        )

    return out
