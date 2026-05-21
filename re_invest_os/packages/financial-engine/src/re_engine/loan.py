"""融資返済表・残債・年間DS/利息/元金の計算。

すべて純粋関数。金額は円(int)。利率は年率(float)。
"""

from __future__ import annotations

from re_engine.models import LoanScheduleRow

_EPS = 1e-12


def amortized_schedule(
    principal: int,
    annual_rate: float,
    term_years: int,
    grace_period_months: int = 0,
) -> list[LoanScheduleRow]:
    """元利均等返済スケジュール。

    - 月返済額 = P * r / (1 - (1+r)^-n)、ただし r=0 のときは線形分割
    - 各回は整数円に丸め、最終回で残債を吸収して残高=0 にする
    - 据置期間中は利息のみ、元金返済は0
    """
    if principal < 0:
        raise ValueError("principal must be >= 0")
    if annual_rate < 0:
        raise ValueError("annual_rate must be >= 0")
    if term_years <= 0:
        raise ValueError("term_years must be > 0")
    if grace_period_months < 0:
        raise ValueError("grace_period_months must be >= 0")
    if grace_period_months >= term_years * 12:
        raise ValueError("grace_period_months must be < total months")

    total_months = term_years * 12
    schedule: list[LoanScheduleRow] = []

    if principal == 0:
        # 借入0: 空ではなく全0行を返す方が下流処理が楽
        for m in range(1, total_months + 1):
            schedule.append(
                LoanScheduleRow(
                    period_month=m,
                    payment_yen=0,
                    interest_yen=0,
                    principal_yen=0,
                    balance_yen=0,
                )
            )
        return schedule

    monthly_rate = annual_rate / 12.0
    balance = float(principal)

    # 据置期間: 利息のみ
    for m in range(1, grace_period_months + 1):
        interest = round(balance * monthly_rate)
        schedule.append(
            LoanScheduleRow(
                period_month=m,
                payment_yen=interest,
                interest_yen=interest,
                principal_yen=0,
                balance_yen=round(balance),
            )
        )

    # 残り期間で元利均等
    remaining = total_months - grace_period_months
    if monthly_rate < _EPS:
        # 金利0: 線形分割
        monthly_payment = balance / remaining
    else:
        denom = 1.0 - (1.0 + monthly_rate) ** (-remaining)
        monthly_payment = balance * monthly_rate / denom

    monthly_payment_int = round(monthly_payment)

    for m in range(grace_period_months + 1, total_months + 1):
        is_last = m == total_months
        interest = round(balance * monthly_rate) if monthly_rate >= _EPS else 0
        if is_last:
            # 最終回: 残債を全額返済
            principal_pay = round(balance)
            payment = principal_pay + interest
            new_balance = 0.0
        else:
            principal_pay = monthly_payment_int - interest
            if principal_pay < 0:
                # 異常: 利息が支払額を超える。利息のみ
                principal_pay = 0
                payment = interest
            else:
                payment = monthly_payment_int
            new_balance = balance - principal_pay

        schedule.append(
            LoanScheduleRow(
                period_month=m,
                payment_yen=payment,
                interest_yen=interest,
                principal_yen=principal_pay,
                balance_yen=round(new_balance),
            )
        )
        balance = new_balance

    return schedule


def loan_balance_at_month(schedule: list[LoanScheduleRow], month: int) -> int:
    """指定月末時点の残債。month は 1-indexed。0 のときは初月直前の借入額。"""
    if month <= 0:
        if not schedule:
            return 0
        # 初月の元金返済前 = 初月末残高 + 初月元金
        first = schedule[0]
        return first.balance_yen + first.principal_yen
    if month > len(schedule):
        return 0
    return schedule[month - 1].balance_yen


def _slice_year(schedule: list[LoanScheduleRow], year: int) -> list[LoanScheduleRow]:
    """指定年 (1-indexed) の12ヶ月分。"""
    if year <= 0:
        return []
    start = (year - 1) * 12
    end = year * 12
    return schedule[start:end]


def annual_debt_service(schedule: list[LoanScheduleRow], year: int) -> int:
    """指定年の年間返済額合計。"""
    return sum(row.payment_yen for row in _slice_year(schedule, year))


def annual_interest(schedule: list[LoanScheduleRow], year: int) -> int:
    return sum(row.interest_yen for row in _slice_year(schedule, year))


def annual_principal(schedule: list[LoanScheduleRow], year: int) -> int:
    return sum(row.principal_yen for row in _slice_year(schedule, year))
