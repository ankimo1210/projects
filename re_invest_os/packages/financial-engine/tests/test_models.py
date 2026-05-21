"""モデル定義のバリデーション・受け渡しテスト。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from re_engine.models import (
    Assumptions,
    LoanAssumptions,
    PropertyAssumptions,
)


def test_base_assumptions_roundtrip(base_assumptions: Assumptions) -> None:
    """JSON でラウンドトリップしても等価。"""
    payload = base_assumptions.model_dump(mode="json", by_alias=True)
    restored = Assumptions.model_validate(payload)
    assert restored == base_assumptions


def test_property_rejects_negative_price() -> None:
    with pytest.raises(ValidationError):
        PropertyAssumptions(
            property_type="kuubun",
            purchase_price_yen=-1,
            land_value_yen=0,
            building_value_yen=0,
            structure="rc",
            building_completion_ym="2020-01",
            building_area_sqm=20.0,
            location_pref="13",
        )


def test_loan_rejects_invalid_rate() -> None:
    with pytest.raises(ValidationError):
        LoanAssumptions(loan_amount_yen=1_000_000, interest_rate=1.5, term_years=10)


def test_vacancy_rate_bounded() -> None:
    from re_engine.models import IncomeAssumptions

    with pytest.raises(ValidationError):
        IncomeAssumptions(gpi_monthly_yen=100_000, vacancy_rate=1.5)


def test_alias_exit_supported(base_assumptions: Assumptions) -> None:
    """`exit` キーワード回避のため `exit_` フィールドを使うが、エイリアスで `exit` も通る。"""
    data = base_assumptions.model_dump(by_alias=True)
    assert "exit" in data
    assert data["exit"]["hold_period_years"] == 10
