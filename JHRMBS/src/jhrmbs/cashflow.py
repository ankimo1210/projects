from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import date

from jhrmbs.metrics import cpr_to_smm


@dataclass(frozen=True)
class CashflowAssumptions:
    face_amount: float
    coupon_rate: float
    current_factor: float
    current_scheduled_factor: float
    cleanup_threshold: float | None = None
    cleanup_lag_months: int = 1


@dataclass(frozen=True)
class CashflowPoint:
    payment_date: date
    scheduled_factor: float
    annual_cpr: float


@dataclass(frozen=True)
class CashflowRow:
    payment_date: date
    beginning_balance: float
    scheduled_principal: float
    voluntary_prepayment: float
    cleanup_principal: float
    total_principal: float
    interest: float
    total_cashflow: float
    ending_balance: float
    ending_factor: float
    scheduled_factor: float
    annual_cpr: float
    smm: float
    cleanup_exercised: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _validate_assumptions(assumptions: CashflowAssumptions) -> None:
    if assumptions.face_amount <= 0.0:
        raise ValueError("face_amount must be positive")
    if not 0.0 <= assumptions.coupon_rate <= 1.0:
        raise ValueError("coupon_rate must be in decimal annual units")
    if not 0.0 <= assumptions.current_factor <= 1.0:
        raise ValueError("current_factor must be between 0 and 1")
    if not 0.0 < assumptions.current_scheduled_factor <= 1.0:
        raise ValueError("current_scheduled_factor must be in (0, 1]")
    if assumptions.cleanup_threshold is not None and not 0.0 < assumptions.cleanup_threshold < 1.0:
        raise ValueError("cleanup_threshold must be in (0, 1)")
    if assumptions.cleanup_lag_months < 1:
        raise ValueError("cleanup_lag_months must be at least 1")


def generate_cashflows(
    assumptions: CashflowAssumptions,
    schedule: Sequence[CashflowPoint],
) -> list[CashflowRow]:
    """Generate monthly pass-through cash flows as a deterministic pure function.

    Scheduled principal is applied first using the ratio of consecutive JHF
    scheduled factors. Voluntary SMM is then applied to the post-schedule balance.
    """
    _validate_assumptions(assumptions)
    beginning_balance = assumptions.face_amount * assumptions.current_factor
    previous_scheduled_factor = assumptions.current_scheduled_factor
    cleanup_countdown: int | None = (
        assumptions.cleanup_lag_months
        if assumptions.cleanup_threshold is not None
        and assumptions.current_factor <= assumptions.cleanup_threshold
        else None
    )
    rows: list[CashflowRow] = []
    previous_date: date | None = None

    for point in schedule:
        if previous_date is not None and point.payment_date <= previous_date:
            raise ValueError("cashflow dates must be strictly increasing")
        previous_date = point.payment_date
        if not 0.0 <= point.scheduled_factor <= previous_scheduled_factor + 1e-10:
            raise ValueError("scheduled factors must be non-increasing and in [0, 1]")
        if not 0.0 <= point.annual_cpr <= 1.0:
            raise ValueError("annual_cpr must be in decimal units between 0 and 1")

        interest = beginning_balance * assumptions.coupon_rate / 12.0
        cleanup_exercised = False
        cleanup_principal = 0.0
        scheduled_principal = 0.0
        voluntary_prepayment = 0.0
        smm = float(cpr_to_smm(point.annual_cpr))

        if cleanup_countdown == 1:
            cleanup_principal = beginning_balance
            ending_balance = 0.0
            cleanup_exercised = True
            cleanup_countdown = None
        else:
            scheduled_ratio = point.scheduled_factor / previous_scheduled_factor
            balance_after_schedule = beginning_balance * scheduled_ratio
            scheduled_principal = max(beginning_balance - balance_after_schedule, 0.0)
            voluntary_prepayment = balance_after_schedule * smm
            ending_balance = max(balance_after_schedule - voluntary_prepayment, 0.0)
            if cleanup_countdown is not None:
                cleanup_countdown -= 1

        total_principal = scheduled_principal + voluntary_prepayment + cleanup_principal
        ending_factor = ending_balance / assumptions.face_amount
        rows.append(
            CashflowRow(
                payment_date=point.payment_date,
                beginning_balance=beginning_balance,
                scheduled_principal=scheduled_principal,
                voluntary_prepayment=voluntary_prepayment,
                cleanup_principal=cleanup_principal,
                total_principal=total_principal,
                interest=interest,
                total_cashflow=total_principal + interest,
                ending_balance=ending_balance,
                ending_factor=ending_factor,
                scheduled_factor=point.scheduled_factor,
                annual_cpr=point.annual_cpr,
                smm=smm,
                cleanup_exercised=cleanup_exercised,
            )
        )
        beginning_balance = ending_balance
        previous_scheduled_factor = point.scheduled_factor
        if ending_balance <= 1e-8:
            break
        if (
            assumptions.cleanup_threshold is not None
            and cleanup_countdown is None
            and ending_factor <= assumptions.cleanup_threshold
        ):
            cleanup_countdown = assumptions.cleanup_lag_months
    return rows
