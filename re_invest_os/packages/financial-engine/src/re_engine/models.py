"""Pydantic v2 モデル: Assumptions と AnalysisResult。

仕様: docs/architecture/calculation_engine_spec.md §3-4
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from re_engine.constants import PropertyType, RepaymentType, Structure


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


# ===== Input: Assumptions =====


class PropertyAssumptions(_Base):
    property_type: PropertyType
    purchase_price_yen: int = Field(gt=0)
    land_value_yen: int = Field(ge=0)
    building_value_yen: int = Field(ge=0)
    structure: Structure
    building_completion_ym: str  # "YYYY-MM"
    acquisition_year: int = Field(gt=1900, lt=2200)  # 購入年。減価償却計算の基準
    building_area_sqm: float = Field(gt=0)
    land_area_sqm: float | None = None
    num_units: int | None = None
    location_pref: str  # "13" 等
    location_city: str | None = None


class IncomeAssumptions(_Base):
    gpi_monthly_yen: int = Field(gt=0)
    other_income_monthly_yen: int = 0
    vacancy_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    rent_growth_rate: float = -0.005
    bad_debt_rate: float = Field(default=0.0, ge=0.0, le=1.0)


class OpexAssumptions(_Base):
    management_fee_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    repair_reserve_monthly_yen: int = 0
    fixed_property_tax_yen: int = 0  # 固都税年額
    insurance_yen: int = 0
    building_mgmt_yen: int = 0  # 区分の管理費・修繕積立金 年額
    other_opex_yen: int = 0
    opex_growth_rate: float = 0.005


class LoanAssumptions(_Base):
    loan_amount_yen: int = Field(ge=0)
    interest_rate: float = Field(ge=0.0, le=1.0)
    term_years: int = Field(gt=0)
    repayment_type: RepaymentType = "amortized"
    grace_period_months: int = Field(default=0, ge=0)


class TaxAssumptions(_Base):
    income_tax_rate: float = 0.20
    resident_tax_rate: float = 0.10
    business_tax_rate: float = 0.0
    capital_gain_short_rate: float = 0.39
    capital_gain_long_rate: float = 0.20


class ExitAssumptions(_Base):
    hold_period_years: int = Field(default=10, gt=0)
    exit_cap_rate: float = Field(default=0.060, gt=0.0, le=1.0)
    selling_cost_rate: float = Field(default=0.04, ge=0.0, le=1.0)


class AcquisitionAssumptions(_Base):
    equity_yen: int = Field(ge=0)
    acquisition_cost_rate: float = Field(default=0.07, ge=0.0, le=1.0)


class Assumptions(_Base):
    engine_version: str = "0.1.0"
    property: PropertyAssumptions
    income: IncomeAssumptions
    opex: OpexAssumptions
    loan: LoanAssumptions
    tax: TaxAssumptions = Field(default_factory=TaxAssumptions)
    exit_: ExitAssumptions = Field(default_factory=ExitAssumptions, alias="exit")
    acquisition: AcquisitionAssumptions

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


# ===== Output: AnalysisResult =====


class YearlyCashflow(_Base):
    year: int
    gpi_yen: int
    vacancy_loss_yen: int
    bad_debt_yen: int
    egi_yen: int
    opex_yen: int
    noi_yen: int
    debt_service_yen: int
    btcf_yen: int
    depreciation_yen: int
    interest_expense_yen: int
    principal_payment_yen: int
    taxable_income_yen: int
    tax_yen: int
    atcf_yen: int
    loan_balance_end_yen: int


class LoanScheduleRow(_Base):
    period_month: int  # 1-indexed
    payment_yen: int
    interest_yen: int
    principal_yen: int
    balance_yen: int


class ExitResult(_Base):
    sale_price_yen: int
    selling_costs_yen: int
    remaining_loan_yen: int
    book_value_yen: int
    capital_gain_yen: int
    capital_gain_tax_yen: int
    net_proceeds_yen: int


class KPI(_Base):
    cap_rate: float
    cash_on_cash: float
    dscr_min: float
    dscr_year1: float
    ltv: float
    equity_irr: float | None
    equity_multiple: float
    payback_years: float | None
    btcf_first_year_yen: int
    atcf_first_year_yen: int


class AnalysisResult(_Base):
    engine_version: str
    assumptions: Assumptions
    yearly_cashflows: list[YearlyCashflow]
    loan_schedule: list[LoanScheduleRow]
    exit_: ExitResult = Field(alias="exit")
    kpi: KPI

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
