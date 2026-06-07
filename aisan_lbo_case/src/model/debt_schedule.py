from __future__ import annotations

import pandas as pd


def build_debt_schedule(
    projection: pd.DataFrame,
    opening_debt: float,
    opening_cash: float,
    min_cash: float,
    interest_rate: float,
    cash_tax_rate: float,
    cash_sweep_pct: float,
) -> pd.DataFrame:
    debt = float(opening_debt)
    cash = float(opening_cash)
    rows: list[dict[str, float | int | str]] = []

    for row in projection.to_dict("records"):
        beginning_debt = debt
        beginning_cash = cash
        cash_interest = beginning_debt * interest_rate
        taxable_income = max(0.0, float(row["ebit"]) - cash_interest)
        cash_taxes = taxable_income * cash_tax_rate
        fcf_before_interest = (
            float(row["ebitda"])
            - cash_taxes
            - float(row["capex"])
            - float(row["change_nwc"])
        )
        fcf_after_interest = fcf_before_interest - cash_interest

        if fcf_after_interest >= 0:
            debt_repayment = min(beginning_debt, fcf_after_interest * cash_sweep_pct)
            revolver_draw = 0.0
            debt = beginning_debt - debt_repayment
            cash = beginning_cash + fcf_after_interest - debt_repayment
        else:
            debt_repayment = 0.0
            cash = beginning_cash + fcf_after_interest
            if cash < min_cash:
                revolver_draw = min_cash - cash
                debt = beginning_debt + revolver_draw
                cash = min_cash
            else:
                revolver_draw = 0.0
                debt = beginning_debt

        rows.append(
            {
                "scenario": row["scenario"],
                "year": row["year"],
                "fiscal_year": row["fiscal_year"],
                "beginning_debt": beginning_debt,
                "beginning_cash": beginning_cash,
                "cash_interest": cash_interest,
                "cash_taxes": cash_taxes,
                "fcf_before_interest": fcf_before_interest,
                "fcf_after_interest": fcf_after_interest,
                "debt_repayment": debt_repayment,
                "revolver_draw": revolver_draw,
                "ending_debt": debt,
                "ending_cash": cash,
                "ending_net_debt": debt - cash,
            }
        )
    return pd.DataFrame(rows)
