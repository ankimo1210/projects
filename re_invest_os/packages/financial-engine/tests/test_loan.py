"""ローン返済テスト。

既知の数値ケース:
- 30,000,000円 / 2.0% / 30年 (元利均等): 月返済 110,886円
  ※ 標準的な公式計算値。端数は最終回で吸収。
"""

from __future__ import annotations

import itertools

import pytest
from re_engine.loan import (
    amortized_schedule,
    annual_debt_service,
    annual_interest,
    annual_principal,
    loan_balance_at_month,
)


def test_amortized_schedule_length() -> None:
    sched = amortized_schedule(30_000_000, 0.020, 30)
    assert len(sched) == 360


def test_monthly_payment_known_case() -> None:
    """3,000万円・年2%・30年 → 月約110,886円。"""
    sched = amortized_schedule(30_000_000, 0.020, 30)
    # 最終回以外の支払額が一定
    payments = {row.payment_yen for row in sched[:-1]}
    assert payments == {110_886}


def test_balance_decreases_to_zero() -> None:
    sched = amortized_schedule(30_000_000, 0.020, 30)
    assert sched[-1].balance_yen == 0
    # 単調減少 (非増加)
    balances = [row.balance_yen for row in sched]
    for a, b in itertools.pairwise(balances):
        assert b <= a


def test_total_interest_reasonable() -> None:
    sched = amortized_schedule(30_000_000, 0.020, 30)
    total_interest = sum(r.interest_yen for r in sched)
    total_principal = sum(r.principal_yen for r in sched)
    # 元金は元本に一致
    assert total_principal == 30_000_000
    # 30年2%なら総利息はおよそ 990万円前後
    assert 9_500_000 <= total_interest <= 10_500_000


def test_zero_interest_linear_split() -> None:
    sched = amortized_schedule(12_000_000, 0.0, 1)  # 1年・金利0
    assert len(sched) == 12
    for row in sched:
        assert row.interest_yen == 0
    total_principal = sum(r.principal_yen for r in sched)
    assert total_principal == 12_000_000
    assert sched[-1].balance_yen == 0


def test_zero_principal_returns_zero_rows() -> None:
    sched = amortized_schedule(0, 0.02, 30)
    assert len(sched) == 360
    assert all(r.payment_yen == 0 for r in sched)
    assert all(r.balance_yen == 0 for r in sched)


def test_balance_at_month() -> None:
    sched = amortized_schedule(30_000_000, 0.020, 30)
    # 12ヶ月後 ≒ 約2,930万円残 (公式: 約29,300,000)
    bal_12 = loan_balance_at_month(sched, 12)
    assert 29_000_000 <= bal_12 <= 29_500_000
    # 全期間後は 0
    assert loan_balance_at_month(sched, 360) == 0


def test_annual_aggregates() -> None:
    sched = amortized_schedule(30_000_000, 0.020, 30)
    ds_y1 = annual_debt_service(sched, 1)
    int_y1 = annual_interest(sched, 1)
    prin_y1 = annual_principal(sched, 1)
    # 年間返済 ≒ 月110,886 × 12
    assert 1_320_000 <= ds_y1 <= 1_340_000
    # 利息 + 元金 ≒ 返済額 (端数±数円)
    assert abs(ds_y1 - (int_y1 + prin_y1)) <= 12


def test_grace_period() -> None:
    # 6ヶ月据置、その後の元利均等
    sched = amortized_schedule(12_000_000, 0.020, 10, grace_period_months=6)
    # 据置期間は元金返済 = 0
    for row in sched[:6]:
        assert row.principal_yen == 0
        assert row.interest_yen > 0
    # 据置後は元金返済が発生
    assert sched[6].principal_yen > 0
    assert sched[-1].balance_yen == 0


def test_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        amortized_schedule(-1, 0.02, 30)
    with pytest.raises(ValueError):
        amortized_schedule(1_000_000, -0.01, 30)
    with pytest.raises(ValueError):
        amortized_schedule(1_000_000, 0.02, 0)
    with pytest.raises(ValueError):
        amortized_schedule(1_000_000, 0.02, 1, grace_period_months=12)
