"""フル分析オーケストレーター: Assumptions → AnalysisResult。

各サブモジュールを呼び出して結果を組み立てる。
"""

from __future__ import annotations

from re_engine import ENGINE_VERSION
from re_engine.cashflow import project_cashflows
from re_engine.exit import compute_exit
from re_engine.irr import (
    cap_rate,
    cash_on_cash,
    dscr,
    equity_irr,
    equity_multiple,
    ltv,
    payback_years,
)
from re_engine.loan import amortized_schedule
from re_engine.models import KPI, AnalysisResult, Assumptions


def _equity_invested(a: Assumptions) -> int:
    """自己資金 = ユーザー入力 equity または (価格 - 借入額) + 取得諸費用。"""
    if a.acquisition.equity_yen > 0:
        return a.acquisition.equity_yen
    down = max(0, a.property.purchase_price_yen - a.loan.loan_amount_yen)
    acq_cost = round(a.property.purchase_price_yen * a.acquisition.acquisition_cost_rate)
    return down + acq_cost


def run_full_analysis(a: Assumptions) -> AnalysisResult:
    """Assumptions → AnalysisResult (純粋関数)。"""
    sched = amortized_schedule(
        a.loan.loan_amount_yen,
        a.loan.interest_rate,
        a.loan.term_years,
        a.loan.grace_period_months,
    )
    cfs = project_cashflows(a, sched)
    exit_result = compute_exit(a, cfs, sched)

    equity = _equity_invested(a)
    atcfs = [cf.atcf_yen for cf in cfs]

    irr = equity_irr(equity, atcfs, exit_result.net_proceeds_yen)
    total_dist = sum(atcfs) + exit_result.net_proceeds_yen
    em = equity_multiple(equity, total_dist)
    payback = payback_years(equity, atcfs)

    dscr_year1 = dscr(cfs[0].noi_yen, cfs[0].debt_service_yen)
    dscr_min = min(dscr(cf.noi_yen, cf.debt_service_yen) for cf in cfs)
    coc = cash_on_cash(cfs[0].btcf_yen, equity)
    cap = cap_rate(cfs[0].noi_yen, a.property.purchase_price_yen)
    ltv_ratio = ltv(a.loan.loan_amount_yen, a.property.purchase_price_yen)

    kpi = KPI(
        cap_rate=cap,
        cash_on_cash=coc,
        dscr_min=dscr_min,
        dscr_year1=dscr_year1,
        ltv=ltv_ratio,
        equity_irr=irr,
        equity_multiple=em,
        payback_years=payback,
        btcf_first_year_yen=cfs[0].btcf_yen,
        atcf_first_year_yen=cfs[0].atcf_yen,
    )

    return AnalysisResult(
        engine_version=ENGINE_VERSION,
        assumptions=a,
        yearly_cashflows=cfs,
        loan_schedule=sched,
        exit=exit_result,
        kpi=kpi,
    )
