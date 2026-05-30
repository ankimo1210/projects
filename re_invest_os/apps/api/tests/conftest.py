"""API テスト共通フィクスチャ。"""

from __future__ import annotations

import pytest
from re_engine.models import (
    AcquisitionAssumptions,
    Assumptions,
    ExitAssumptions,
    IncomeAssumptions,
    LoanAssumptions,
    OpexAssumptions,
    PropertyAssumptions,
    TaxAssumptions,
)


@pytest.fixture
def base_assumptions() -> Assumptions:
    """西新宿レジデンス 504号 (モックアップの仮想物件)。

    engine 側 conftest と同一物件。価格 3,980万円 / RC造 / 1LDK 38.4㎡ /
    月額賃料 145,000円 / LTV 70% / 金利 2.0% / 30年 / 自己資金 約1,200万円。
    """
    return Assumptions(
        property=PropertyAssumptions(
            property_type="kuubun",
            purchase_price_yen=39_800_000,
            land_value_yen=8_000_000,
            building_value_yen=31_800_000,
            structure="rc",
            building_completion_ym="2011-04",
            acquisition_year=2026,
            building_area_sqm=38.4,
            location_pref="13",
            location_city="新宿区",
        ),
        income=IncomeAssumptions(
            gpi_monthly_yen=145_000,
            other_income_monthly_yen=0,
            vacancy_rate=0.05,
            rent_growth_rate=-0.005,
        ),
        opex=OpexAssumptions(
            management_fee_rate=0.05,
            building_mgmt_yen=240_000,
            fixed_property_tax_yen=120_000,
            insurance_yen=20_000,
        ),
        loan=LoanAssumptions(
            loan_amount_yen=27_860_000,
            interest_rate=0.020,
            term_years=30,
        ),
        tax=TaxAssumptions(),
        exit=ExitAssumptions(
            hold_period_years=10,
            exit_cap_rate=0.060,
        ),
        acquisition=AcquisitionAssumptions(
            equity_yen=12_000_000,
            acquisition_cost_rate=0.07,
        ),
    )
