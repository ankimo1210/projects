"""
sim_engine.py — Real Estate Investment Simulation Engine (v3)

Ported from real_estate_investment_sim_3.ipynb.
All computation logic: tax, depreciation, loan, simulation, metrics, scenarios.
"""

import math
import numpy as np
import pandas as pd
from copy import deepcopy
from datetime import date

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

JAPAN_INCOME_TAX_BRACKETS = [
    (1_950_000,    0.05, 0),
    (3_300_000,    0.10, 97_500),
    (6_950_000,    0.20, 427_500),
    (9_000_000,    0.23, 636_000),
    (18_000_000,   0.33, 1_536_000),
    (40_000_000,   0.40, 2_796_000),
    (float("inf"), 0.45, 4_796_000),
]

STATUTORY_USEFUL_LIFE = {
    ("wood",        "residential"): 22,
    ("wood_mortar", "residential"): 20,
    ("rc",          "residential"): 47,
    ("src",         "residential"): 47,
    ("steel",       "residential"): None,
}

STEEL_LIFE_BY_THICKNESS = {
    "residential": [
        (lambda mm: mm > 4,       34),
        (lambda mm: 3 < mm <= 4,  27),
        (lambda mm: mm <= 3,      19),
    ]
}

# ---------------------------------------------------------------------------
# Date / Building helpers
# ---------------------------------------------------------------------------

def parse_year_month(ym_str):
    parts = ym_str.strip().split("-")
    if len(parts) != 2:
        raise ValueError(f"Expected 'YYYY-MM' format, got: {ym_str!r}")
    return int(parts[0]), int(parts[1])


def parse_date(date_str):
    parts = date_str.strip().split("-")
    if len(parts) != 3:
        raise ValueError(f"Expected 'YYYY-MM-DD' format, got: {date_str!r}")
    return date(int(parts[0]), int(parts[1]), int(parts[2]))


def months_between(start_year, start_month, end_year, end_month):
    return (end_year - start_year) * 12 + (end_month - start_month)


def compute_building_age_at_purchase(transaction_date_str, building_completion_ym_str):
    tx = parse_date(transaction_date_str)
    comp_y, comp_m = parse_year_month(building_completion_ym_str)
    total_months = months_between(comp_y, comp_m, tx.year, tx.month)
    if total_months < 0:
        raise ValueError("building_completion_ym is after transaction_date")
    return total_months // 12


def lookup_statutory_useful_life(structure, usage, steel_thickness_mm=None):
    key = (structure, usage)
    if key not in STATUTORY_USEFUL_LIFE:
        raise ValueError(f"Unsupported structure/usage: {key}")
    life = STATUTORY_USEFUL_LIFE[key]
    if life is not None:
        return life
    if structure == "steel":
        if steel_thickness_mm is None:
            raise ValueError("steel_thickness_mm required for steel")
        for cond_fn, years in STEEL_LIFE_BY_THICKNESS.get(usage, []):
            if cond_fn(steel_thickness_mm):
                return years
        raise ValueError(f"No matching rule for steel {steel_thickness_mm}mm")
    raise ValueError(f"Cannot determine useful life for {key}")


def compute_used_asset_useful_life(stat_life, elapsed_years):
    if elapsed_years < 0:
        raise ValueError(f"elapsed_years must be >= 0, got {elapsed_years}")
    if elapsed_years >= stat_life:
        estimated = math.floor(stat_life * 0.2)
    else:
        estimated = math.floor((stat_life - elapsed_years) + elapsed_years * 0.2)
    return max(estimated, 2)

# ---------------------------------------------------------------------------
# Tax functions (v3)
# ---------------------------------------------------------------------------

def compute_progressive_income_tax(taxable_income):
    if taxable_income <= 0:
        return 0.0
    for upper, rate, deduction in JAPAN_INCOME_TAX_BRACKETS:
        if taxable_income <= upper:
            return taxable_income * rate - deduction
    return taxable_income * 0.45 - 4_796_000


def determine_individual_sale_term(acquisition_date_str, sale_date_str):
    acq = parse_date(acquisition_date_str)
    sale = parse_date(sale_date_str)
    jan1 = date(sale.year, 1, 1)
    if (jan1 - acq).days > 5 * 365:
        return "long_term"
    return "short_term"


def determine_individual_capital_gains_tax_rate(
    acquisition_date_str, sale_date_str,
    resident_tax_rate=0.05, reconstruction_special_tax_rate=0.021,
):
    term = determine_individual_sale_term(acquisition_date_str, sale_date_str)
    if term == "long_term":
        income_tax, res_tax = 0.15, resident_tax_rate
    else:
        income_tax, res_tax = 0.30, 0.09
    reconstruction = income_tax * reconstruction_special_tax_rate
    return {
        "sale_term_type": term,
        "income_tax_rate": income_tax,
        "resident_tax_rate": res_tax,
        "reconstruction_surtax_rate": reconstruction,
        "total_rate": income_tax + res_tax + reconstruction,
    }


def compute_holding_tax(taxable_income, params):
    if taxable_income <= 0:
        return 0.0
    ownership = params.get("ownership_type", "individual")
    if ownership == "corporate":
        return taxable_income * params["corporate_effective_tax_rate"]

    use_progressive = params.get("use_progressive_tax", False)
    if use_progressive:
        national_tax = compute_progressive_income_tax(taxable_income)
        reconstruction_rate = params.get("reconstruction_special_tax_rate", 0.021)
        reconstruction_surtax = national_tax * reconstruction_rate
        resident_tax = taxable_income * params.get("resident_tax_rate", 0.05)
        tax = national_tax + reconstruction_surtax + resident_tax
    else:
        tax = taxable_income * (params["income_tax_rate_national"] + params["resident_tax_rate"])

    biz_tax_rate = params.get("optional_business_tax_rate", 0.0)
    if biz_tax_rate > 0:
        tax += taxable_income * biz_tax_rate
    return tax


def compute_sale_tax(taxable_gain, params):
    if taxable_gain <= 0:
        return 0.0
    if params.get("ownership_type", "individual") == "corporate":
        return taxable_gain * params["corporate_effective_tax_rate"]
    return taxable_gain * params.get("sale_tax_info", {}).get("total_rate", 0.2)

# ---------------------------------------------------------------------------
# enrich_params (v3)
# ---------------------------------------------------------------------------

def enrich_params(params):
    p = deepcopy(params)

    p["building_age_years_at_purchase"] = compute_building_age_at_purchase(
        p["transaction_date"], p["building_completion_ym"])
    p["statutory_useful_life_years"] = lookup_statutory_useful_life(
        p["building_structure"], p["building_usage"], p.get("steel_thickness_mm"))
    p["building_useful_life_years"] = compute_used_asset_useful_life(
        p["statutory_useful_life_years"], p["building_age_years_at_purchase"])
    p["land_growth_rate"] = p["inflation_rate"] + p["land_real_appreciation_spread"]
    p["building_growth_rate"] = p["inflation_rate"] + p["building_real_appreciation_spread"]

    tx = parse_date(p["transaction_date"])
    sale_year = tx.year + p["hold_period_years"]
    try:
        p["inferred_sale_date"] = date(sale_year, tx.month, tx.day).isoformat()
    except ValueError:
        p["inferred_sale_date"] = date(sale_year, tx.month, tx.day - 1).isoformat()

    ownership = p.get("ownership_type", "individual")
    if ownership == "individual":
        sale_tax_info = determine_individual_capital_gains_tax_rate(
            p["transaction_date"], p["inferred_sale_date"],
            p.get("resident_tax_rate", 0.05), p.get("reconstruction_special_tax_rate", 0.021))
        p["sale_tax_info"] = sale_tax_info
        p["sale_term_type"] = sale_tax_info["sale_term_type"]
        p["holding_effective_tax_rate"] = p["income_tax_rate_national"] + p["resident_tax_rate"]
    else:
        p["sale_tax_info"] = {"total_rate": p["corporate_effective_tax_rate"]}
        p["sale_term_type"] = "corporate"
        p["holding_effective_tax_rate"] = p["corporate_effective_tax_rate"]

    p["income_tax_rate"] = p["holding_effective_tax_rate"]

    # v3 defaults
    p.setdefault("capex_treatment_mode", "expense_all")
    p.setdefault("capital_improvement_depr_life_years", 15)
    p.setdefault("capital_improvement_depr_method", "straight_line")
    p.setdefault("capex_expense_schedule", {})
    p.setdefault("capex_capital_schedule", {})
    p.setdefault("selling_expense_schedule_mode", "rate")
    p.setdefault("selling_expense_items", {})
    p.setdefault("use_deemed_acquisition_cost_fallback", False)
    p.setdefault("deemed_acquisition_cost_rate", 0.05)
    p.setdefault("use_progressive_tax", False)
    p.setdefault("optional_business_tax_rate", 0.0)
    p.setdefault("enable_refinance", False)
    p.setdefault("refinance_year", 5)
    p.setdefault("refinance_ltv", 0.70)
    p.setdefault("refinance_interest_rate", 0.02)
    p.setdefault("refinance_term_years", 25)
    p.setdefault("refinance_fee_rate", 0.01)
    p.setdefault("cash_out_to_equity", True)
    p.setdefault("prepayment_schedule", {})

    return p

# ---------------------------------------------------------------------------
# Revenue schedule
# ---------------------------------------------------------------------------

def build_revenue_schedule(params):
    hold = params["hold_period_years"]
    records = []
    for y in range(1, hold + 1):
        t = y - 1
        gross_rent = params["initial_gross_rent"] * (1 + params["rent_growth_rate"]) ** t
        vacancy_loss = gross_rent * params["vacancy_rate"]
        other_inc = params["other_income"] * (1 + params["other_income_growth_rate"]) ** t
        egi = gross_rent - vacancy_loss + other_inc
        opex = params["initial_operating_expenses"] * (1 + params["opex_growth_rate"]) ** t
        ptax = params["property_tax"] * (1 + params["property_tax_growth_rate"]) ** t
        repair = params["repair_cost"] * (1 + params["repair_growth_rate"]) ** t
        capex = params.get("capex_schedule", {}).get(y, 0)
        noi = egi - opex - ptax - repair
        records.append({
            "year": y, "gross_rent": gross_rent, "vacancy_loss": vacancy_loss,
            "other_income": other_inc, "egi": egi, "operating_expenses": opex,
            "property_tax": ptax, "repair_cost": repair, "capex": capex, "noi": noi,
        })
    return pd.DataFrame(records)

# ---------------------------------------------------------------------------
# Loan schedule (v3: refinance + prepayment)
# ---------------------------------------------------------------------------

def _calc_pmt(principal, rate, periods):
    if rate == 0:
        return principal / periods if periods > 0 else 0
    return principal * rate * (1 + rate) ** periods / ((1 + rate) ** periods - 1)


def build_loan_schedule(params):
    loan_amount = params["purchase_price"] * params["ltv"]
    rate = params["interest_rate"]
    n = params["loan_term_years"]
    hold = params["hold_period_years"]
    amort_type = params.get("amortization_type", "equal_payment")
    io_years = params.get("io_years", 0)
    enable_refi = params.get("enable_refinance", False)
    refi_year = params.get("refinance_year", 0)
    prepay_sched = params.get("prepayment_schedule", {})

    records = []
    balance = loan_amount
    annual_payment = None
    refinanced = False

    for y in range(1, hold + 1):
        year_refi_cash_out = 0.0
        year_refi_fee = 0.0

        # Refinance
        if enable_refi and y == refi_year and not refinanced:
            refi_ltv = params.get("refinance_ltv", 0.70)
            new_loan = params["purchase_price"] * refi_ltv
            refi_fee_rate = params.get("refinance_fee_rate", 0.01)
            year_refi_fee = new_loan * refi_fee_rate
            old_balance = balance

            if params.get("cash_out_to_equity", True) and new_loan > old_balance:
                year_refi_cash_out = new_loan - old_balance - year_refi_fee
            else:
                year_refi_cash_out = 0.0

            balance = new_loan
            rate = params.get("refinance_interest_rate", rate)
            n_remaining = params.get("refinance_term_years", 25)
            annual_payment = _calc_pmt(balance, rate, n_remaining)
            refinanced = True

        # Prepayment
        prepay = prepay_sched.get(y, 0)
        if prepay > 0 and balance > 0:
            prepay = min(prepay, balance)
            balance -= prepay
            if annual_payment is not None and balance > 0:
                if refinanced:
                    remaining_term = params.get("refinance_term_years", 25) - (y - refi_year)
                else:
                    remaining_term = n - y
                if remaining_term > 0:
                    annual_payment = _calc_pmt(balance, rate, remaining_term)

        if balance <= 0:
            records.append({
                "year": y, "interest": 0.0, "principal": 0.0,
                "debt_service": 0.0, "loan_balance_end": 0.0,
                "refinance_cash_out": year_refi_cash_out,
                "refinance_fee": year_refi_fee, "prepayment": prepay,
            })
            continue

        interest = balance * rate
        if amort_type == "interest_only_then_amortizing" and y <= io_years and not refinanced:
            principal_paid, ds = 0.0, interest
        else:
            if annual_payment is None:
                if amort_type == "equal_payment":
                    annual_payment = _calc_pmt(loan_amount, rate, n)
                else:
                    annual_payment = _calc_pmt(balance, rate, n - io_years)
            principal_paid = max(annual_payment - interest, 0.0)
            ds = annual_payment

        balance = max(balance - principal_paid, 0.0)
        records.append({
            "year": y, "interest": interest, "principal": principal_paid,
            "debt_service": ds, "loan_balance_end": balance,
            "refinance_cash_out": year_refi_cash_out,
            "refinance_fee": year_refi_fee, "prepayment": prepay,
        })
    return pd.DataFrame(records)

# ---------------------------------------------------------------------------
# Depreciation
# ---------------------------------------------------------------------------

def build_depreciation_schedule(params):
    bv = params["building_value"]
    life = params["building_useful_life_years"]
    hold = params["hold_period_years"]
    annual_dep = bv / life
    records = [{"year": y, "depreciation": annual_dep if y <= life else 0.0}
               for y in range(1, hold + 1)]
    return pd.DataFrame(records)

# ---------------------------------------------------------------------------
# CAPEX tax schedule (v3)
# ---------------------------------------------------------------------------

def build_capex_tax_schedule(params, years):
    mode = params.get("capex_treatment_mode", "expense_all")
    cap_life = params.get("capital_improvement_depr_life_years", 15)
    capex_sched = params.get("capex_schedule", {})
    capitalized_items = []

    records = []
    for y in years:
        total_capex = capex_sched.get(y, 0)
        if mode == "expense_all":
            expensed = total_capex
            capitalized = 0
        elif mode == "capitalize_all":
            expensed = 0
            capitalized = total_capex
        else:  # mixed_schedule
            expensed = params.get("capex_expense_schedule", {}).get(y, 0)
            capitalized = params.get("capex_capital_schedule", {}).get(y, 0)

        if capitalized > 0:
            capitalized_items.append((y, capitalized))

        cap_dep = 0.0
        for (cy, amt) in capitalized_items:
            if y >= cy and (y - cy) < cap_life:
                cap_dep += amt / cap_life

        cum_cap = sum(amt for (cy, amt) in capitalized_items if cy <= y)

        records.append({
            "year": y,
            "capex_expensed": expensed,
            "capex_capitalized": capitalized,
            "cumulative_capex_capitalized": cum_cap,
            "capitalized_capex_depreciation": cap_dep,
        })
    return pd.DataFrame(records)

# ---------------------------------------------------------------------------
# Core simulation (v3)
# ---------------------------------------------------------------------------

def run_simulation(params):
    rev_df = build_revenue_schedule(params)
    loan_df = build_loan_schedule(params)
    dep_df = build_depreciation_schedule(params)

    df = rev_df.merge(loan_df, on="year").merge(dep_df, on="year")
    capex_tax_df = build_capex_tax_schedule(params, df["year"].tolist())
    df = df.merge(capex_tax_df, on="year")

    df["total_depreciation"] = df["depreciation"] + df["capitalized_capex_depreciation"]
    df["btcf"] = (df["noi"] - df["debt_service"] - df["capex"]
                  - df["refinance_fee"] - df["prepayment"]
                  + df["refinance_cash_out"])
    df["taxable_income"] = (df["noi"] - df["interest"]
                            - df["depreciation"] - df["capex_expensed"]
                            - df["capitalized_capex_depreciation"])
    df["tax"] = df["taxable_income"].apply(lambda ti: compute_holding_tax(ti, params))
    df["atcf"] = df["btcf"] - df["tax"]

    total_acquisition = params["purchase_price"] * (1 + params["acquisition_cost_rate"]) + params["initial_capex"]
    loan_amount = params["purchase_price"] * params["ltv"]
    equity_invested = total_acquisition - loan_amount

    hold = params["hold_period_years"]
    terminal_noi = df.loc[df["year"] == hold, "noi"].values[0]

    sale_price_cap = terminal_noi / params["exit_cap_rate"] if params["exit_cap_rate"] > 0 else 0
    land_sv = params["land_value"] * (1 + params["land_growth_rate"]) ** hold
    bldg_sv = params["building_value"] * (1 + params["building_growth_rate"]) ** hold
    sale_price_comp = land_sv + bldg_sv

    method = params.get("exit_price_method", "cap_rate")
    sale_price = sale_price_comp if method == "component_growth" else sale_price_cap

    selling_costs = sale_price * params["closing_cost_on_sale_rate"]
    net_sale_price = sale_price - selling_costs
    loan_balance_at_sale = df.loc[df["year"] == hold, "loan_balance_end"].values[0]
    bt_sale_proceeds = net_sale_price - loan_balance_at_sale

    accumulated_dep = df["depreciation"].sum()
    accumulated_capex_dep = df["capitalized_capex_depreciation"].sum()
    total_capex_capitalized = df["cumulative_capex_capitalized"].iloc[-1] if len(df) > 0 else 0

    cost_basis = (params["purchase_price"] + params["purchase_price"] * params["acquisition_cost_rate"]
                  + params["initial_capex"] + total_capex_capitalized)
    adjusted_basis = cost_basis - accumulated_dep - accumulated_capex_dep

    if params.get("use_deemed_acquisition_cost_fallback", False):
        deemed_basis = sale_price * params.get("deemed_acquisition_cost_rate", 0.05)
        selected_basis = max(adjusted_basis, deemed_basis)
    else:
        deemed_basis = None
        selected_basis = adjusted_basis

    taxable_gain = net_sale_price - selected_basis
    capital_gains_tax = compute_sale_tax(taxable_gain, params)
    net_sale_proceeds = bt_sale_proceeds - capital_gains_tax

    df["sale_proceeds_net"] = 0.0
    df.loc[df["year"] == hold, "sale_proceeds_net"] = net_sale_proceeds
    df["total_equity_cf"] = df["atcf"] + df["sale_proceeds_net"]
    df["cumulative_atcf"] = df["atcf"].cumsum()
    df["cumulative_equity_cf"] = df["total_equity_cf"].cumsum()
    df["cumulative_equity_cf_with_initial"] = df["cumulative_equity_cf"] - equity_invested

    sale_tax_info = params.get("sale_tax_info", {})
    summary = {
        "total_acquisition_cost": total_acquisition,
        "loan_amount": loan_amount,
        "equity_invested": equity_invested,
        "sale_price_cap_rate": sale_price_cap,
        "sale_price_component_growth": sale_price_comp,
        "sale_price_selected": sale_price,
        "exit_price_method": method,
        "selling_costs": selling_costs,
        "net_sale_price": net_sale_price,
        "loan_balance_at_sale": loan_balance_at_sale,
        "bt_sale_proceeds": bt_sale_proceeds,
        "cost_basis": cost_basis,
        "accumulated_depreciation": accumulated_dep,
        "accumulated_capex_depreciation": accumulated_capex_dep,
        "adjusted_basis": adjusted_basis,
        "deemed_acquisition_cost": deemed_basis,
        "selected_tax_basis": selected_basis,
        "taxable_gain": taxable_gain,
        "capital_gains_tax": capital_gains_tax,
        "sale_tax_rate_applied": sale_tax_info.get("total_rate", None),
        "net_sale_proceeds": net_sale_proceeds,
        "terminal_noi": terminal_noi,
        "building_age_years_at_purchase": params.get("building_age_years_at_purchase"),
        "statutory_useful_life_years": params.get("statutory_useful_life_years"),
        "building_useful_life_years": params.get("building_useful_life_years"),
        "land_growth_rate": params.get("land_growth_rate"),
        "building_growth_rate": params.get("building_growth_rate"),
        "sale_term_type": params.get("sale_term_type"),
        "total_capex_capitalized": total_capex_capitalized,
    }
    return df, summary

# ---------------------------------------------------------------------------
# Metrics (v3)
# ---------------------------------------------------------------------------

def _compute_irr(cashflows, tol=1e-10, max_iter=1000):
    def npv(rate):
        return sum(cf / (1 + rate) ** t for t, cf in enumerate(cashflows))
    low, high = -0.50, 2.00
    npv_low, npv_high = npv(low), npv(high)
    if npv_low * npv_high > 0:
        return None
    for _ in range(max_iter):
        mid = (low + high) / 2.0
        npv_mid = npv(mid)
        if abs(npv_mid) < tol or (high - low) / 2 < tol:
            return mid
        if npv_low * npv_mid < 0:
            high, npv_high = mid, npv_mid
        else:
            low, npv_low = mid, npv_mid
    return (low + high) / 2.0


def compute_metrics(params, df, summary):
    equity = summary["equity_invested"]
    hold = params["hold_period_years"]
    year1_noi = df.loc[df["year"] == 1, "noi"].values[0]
    cap_rate = year1_noi / params["purchase_price"]
    df["cash_on_cash"] = df["btcf"] / equity if equity > 0 else 0
    df["dscr"] = df.apply(
        lambda r: r["noi"] / r["debt_service"] if r["debt_service"] > 0 else np.inf, axis=1)
    df["icr"] = df.apply(
        lambda r: r["noi"] / r["interest"] if r["interest"] > 0 else np.inf, axis=1)

    equity_cfs = [-equity] + df["total_equity_cf"].tolist()
    equity_irr = _compute_irr(equity_cfs)

    project_cfs = [-summary["total_acquisition_cost"]]
    for _, row in df.iterrows():
        cf = row["noi"] - row["capex"]
        if row["year"] == hold:
            cf += summary["net_sale_price"]
        project_cfs.append(cf)
    project_irr = _compute_irr(project_cfs)

    total_received = df["total_equity_cf"].sum()
    equity_multiple = total_received / equity if equity > 0 else 0

    cum_with_init = df["cumulative_equity_cf_with_initial"]
    be_rows = df.loc[cum_with_init > 0, "year"]
    break_even_year_cash = int(be_rows.iloc[0]) if len(be_rows) > 0 else None

    holding_tax_total = df["tax"].sum()
    sale_tax_total = summary["capital_gains_tax"]
    total_tax_paid = holding_tax_total + sale_tax_total
    interest_paid_total = df["interest"].sum()
    final_after_tax_wealth = summary["net_sale_proceeds"] + df["cumulative_atcf"].iloc[-1]

    gross_holding_income = df["noi"].sum()
    gross_sale_income = max(summary.get("taxable_gain", 0), 0)
    total_gross = gross_holding_income + gross_sale_income
    tax_drag_ratio = total_tax_paid / total_gross if total_gross > 0 else 0

    metrics = {
        "cap_rate": cap_rate,
        "avg_cash_on_cash": df["cash_on_cash"].mean(),
        "equity_irr": equity_irr,
        "project_irr": project_irr,
        "equity_multiple": equity_multiple,
        "min_dscr": df["dscr"].replace(np.inf, np.nan).min(),
        "avg_dscr": df["dscr"].replace(np.inf, np.nan).mean(),
        "min_icr": df["icr"].replace(np.inf, np.nan).min(),
        "avg_icr": df["icr"].replace(np.inf, np.nan).mean(),
        "break_even_year_cash": break_even_year_cash,
        "peak_negative_cf": cum_with_init.min(),
        "holding_tax_total": holding_tax_total,
        "sale_tax_total": sale_tax_total,
        "total_tax_paid": total_tax_paid,
        "interest_paid_total": interest_paid_total,
        "final_after_tax_wealth": final_after_tax_wealth,
        "tax_drag_ratio": tax_drag_ratio,
    }
    return metrics, df

# ---------------------------------------------------------------------------
# Part B: Analysis functions
# ---------------------------------------------------------------------------

def add_cumulative_cashflow_columns(df, params):
    equity = (params["purchase_price"] * (1 + params["acquisition_cost_rate"])
              + params["initial_capex"]) - params["purchase_price"] * params["ltv"]

    cum_cols = [
        "gross_rent", "vacancy_loss", "egi", "operating_expenses",
        "property_tax", "repair_cost", "noi", "capex",
        "interest", "principal", "debt_service", "depreciation",
        "tax", "btcf", "atcf", "sale_proceeds_net", "total_equity_cf",
    ]
    for col in cum_cols:
        if col in df.columns:
            df[f"cum_{col}"] = df[col].cumsum()

    df["cash_recovery_ratio"] = df["cum_total_equity_cf"] / equity if equity > 0 else 0

    cum_init = df["cumulative_equity_cf_with_initial"]
    be_rows = df.loc[cum_init > 0, "year"]
    break_even = int(be_rows.iloc[0]) if len(be_rows) > 0 else None

    cf_metrics = {
        "break_even_year_cash": break_even,
        "peak_negative_cumulative_cf": cum_init.min(),
        "cash_recovery_ratio_final": df["cash_recovery_ratio"].iloc[-1] if "cash_recovery_ratio" in df.columns else None,
    }
    return df, cf_metrics


def build_operating_pl_table(df, params):
    tax_rate = params["holding_effective_tax_rate"]
    pl = pd.DataFrame()
    pl["year"] = df["year"]
    pl["rental_revenue"] = df["gross_rent"] - df["vacancy_loss"]
    pl["other_income"] = df["other_income"]
    pl["effective_gross_income"] = df["egi"]
    pl["operating_expenses"] = df["operating_expenses"]
    pl["property_tax"] = df["property_tax"]
    pl["repair_cost"] = df["repair_cost"]
    pl["operating_profit_before_dep"] = (
        pl["effective_gross_income"] - pl["operating_expenses"]
        - pl["property_tax"] - pl["repair_cost"]
    )
    pl["depreciation"] = df["total_depreciation"] if "total_depreciation" in df.columns else df["depreciation"]
    pl["interest"] = df["interest"]
    pl["accounting_pre_tax_income"] = (
        pl["operating_profit_before_dep"] - pl["depreciation"] - pl["interest"]
    )
    pl["holding_tax"] = df["tax"]
    pl["accounting_after_tax_income"] = pl["accounting_pre_tax_income"] - pl["holding_tax"]
    pl["depreciation_tax_shield"] = pl["depreciation"] * tax_rate
    pl["interest_tax_shield"] = pl["interest"] * tax_rate
    return pl


def _compute_deferred_sale_tax_at_year(year, params, cum_dep, cum_capex_dep, cum_capex_cap, estimated_mv, selling_cost):
    adj_building_bv = max(params["building_value"] - cum_dep, 0)
    adj_tax_basis = params["land_value"] + adj_building_bv + cum_capex_cap - cum_capex_dep

    if params.get("use_deemed_acquisition_cost_fallback", False):
        deemed = estimated_mv * params.get("deemed_acquisition_cost_rate", 0.05)
        adj_tax_basis = max(adj_tax_basis, deemed)

    net_mv = estimated_mv - selling_cost
    unrealized_gain = net_mv - adj_tax_basis
    if unrealized_gain <= 0:
        return 0.0

    ownership = params.get("ownership_type", "individual")
    if ownership == "corporate":
        return unrealized_gain * params["corporate_effective_tax_rate"]

    tx = parse_date(params["transaction_date"])
    try:
        hypo_sale = date(tx.year + year, tx.month, tx.day)
    except ValueError:
        hypo_sale = date(tx.year + year, tx.month, tx.day - 1)

    tax_info = determine_individual_capital_gains_tax_rate(
        params["transaction_date"], hypo_sale.isoformat(),
        params.get("resident_tax_rate", 0.05),
        params.get("reconstruction_special_tax_rate", 0.021))
    return unrealized_gain * tax_info["total_rate"]


def build_nav_table(df, params):
    equity = (params["purchase_price"] * (1 + params["acquisition_cost_rate"])
              + params["initial_capex"]) - params["purchase_price"] * params["ltv"]
    method = params.get("exit_price_method", "cap_rate")

    records = []
    for _, row in df.iterrows():
        y = int(row["year"])
        if method == "component_growth":
            land_v = params["land_value"] * (1 + params["land_growth_rate"]) ** y
            bldg_v = params["building_value"] * (1 + params["building_growth_rate"]) ** y
            mv = land_v + bldg_v
        else:
            noi = row["noi"]
            mv = noi / params["exit_cap_rate"] if params["exit_cap_rate"] > 0 else 0

        selling_cost = mv * params["closing_cost_on_sale_rate"]
        cum_dep = df.loc[df["year"] <= y, "depreciation"].sum()
        cum_capex_dep = df.loc[df["year"] <= y, "capitalized_capex_depreciation"].sum() if "capitalized_capex_depreciation" in df.columns else 0
        cum_capex_cap = df.loc[df["year"] <= y, "capex_capitalized"].sum() if "capex_capitalized" in df.columns else 0

        adj_building_bv = max(params["building_value"] - cum_dep, 0)
        adj_tax_basis = params["land_value"] + adj_building_bv + cum_capex_cap - cum_capex_dep
        unrealized_pre = mv - adj_tax_basis - selling_cost
        deferred_tax = _compute_deferred_sale_tax_at_year(y, params, cum_dep, cum_capex_dep, cum_capex_cap, mv, selling_cost)

        nav_pre = mv - row["loan_balance_end"] - selling_cost
        nav_after = nav_pre - deferred_tax

        records.append({
            "year": y,
            "estimated_market_value": mv,
            "estimated_selling_cost": selling_cost,
            "adjusted_building_book_value": adj_building_bv,
            "adjusted_total_tax_basis": adj_tax_basis,
            "unrealized_gain_pre_tax": unrealized_pre,
            "deferred_sale_tax": deferred_tax,
            "nav_pre_tax": nav_pre,
            "nav_after_tax": nav_after,
            "loan_balance_end": row["loan_balance_end"],
        })

    nav_df = pd.DataFrame(records)
    nav_df["nav_change_after_tax"] = nav_df["nav_after_tax"].diff()
    nav_df.loc[nav_df.index[0], "nav_change_after_tax"] = (
        nav_df.loc[nav_df.index[0], "nav_after_tax"] - equity
    )
    nav_df["atcf"] = df["atcf"].values
    nav_df["economic_profit_after_tax"] = nav_df["atcf"] + nav_df["nav_change_after_tax"]

    be_nav_rows = nav_df.loc[nav_df["nav_after_tax"] >= equity, "year"]
    nav_df.attrs["break_even_year_nav"] = int(be_nav_rows.iloc[0]) if len(be_nav_rows) > 0 else None
    return nav_df


def compute_drawdown_series(years, values):
    dd = pd.DataFrame({"year": years, "value": values}).reset_index(drop=True)
    dd["running_peak"] = dd["value"].cummax()
    dd["running_peak"] = dd["running_peak"].clip(lower=0)
    dd["drawdown"] = dd["value"] - dd["running_peak"]
    dd["drawdown_pct"] = dd.apply(
        lambda r: r["drawdown"] / r["running_peak"] if r["running_peak"] > 0 else
                  (0.0 if r["value"] >= 0 else -1.0), axis=1)
    duration = []
    count = 0
    for _, r in dd.iterrows():
        if r["drawdown"] < -1e-6:
            count += 1
        else:
            count = 0
        duration.append(count)
    dd["drawdown_duration"] = duration
    return dd


def compute_path_risk_metrics(dd_df):
    min_dd_idx = dd_df["drawdown"].idxmin()
    max_dd_abs = dd_df.loc[min_dd_idx, "drawdown"]
    max_dd_pct = dd_df.loc[min_dd_idx, "drawdown_pct"]
    max_dd_year = int(dd_df.loc[min_dd_idx, "year"])
    duration_max = dd_df["drawdown_duration"].max()
    peak_reached = False
    recovery_year = None
    for _, r in dd_df.iterrows():
        if r["drawdown"] < -1e-6:
            peak_reached = True
        elif peak_reached and r["drawdown"] >= -1e-6:
            recovery_year = int(r["year"])
            break
    values = dd_df["value"].values
    worst_1y = np.inf
    for i in range(1, len(values)):
        worst_1y = min(worst_1y, values[i] - values[i - 1])
    worst_1y = worst_1y if worst_1y < np.inf else 0.0
    worst_3y = np.inf
    for i in range(3, len(values)):
        worst_3y = min(worst_3y, values[i] - values[i - 3])
    worst_3y = worst_3y if worst_3y < np.inf else 0.0
    return {
        "max_drawdown_abs": max_dd_abs,
        "max_drawdown_pct": max_dd_pct,
        "max_drawdown_year": max_dd_year,
        "drawdown_duration_max": duration_max,
        "recovery_year_if_any": recovery_year,
        "worst_1y_change": worst_1y,
        "worst_3y_change": worst_3y,
    }


def build_drawdown_analysis(df, nav_df, params):
    equity = (params["purchase_price"] * (1 + params["acquisition_cost_rate"])
              + params["initial_capex"]) - params["purchase_price"] * params["ltv"]
    years = df["year"]
    liquidity = df["cumulative_equity_cf_with_initial"]
    nav_at = nav_df["nav_after_tax"]
    total_return = df["cumulative_atcf"] + nav_at.values - equity
    results = {}
    for name, vals in [("Liquidity", liquidity), ("NAV After Tax", nav_at), ("Total Return", total_return)]:
        dd_df = compute_drawdown_series(years, vals)
        metrics = compute_path_risk_metrics(dd_df)
        results[name] = {"dd_df": dd_df, "metrics": metrics}
    return results

# ---------------------------------------------------------------------------
# Scenario helpers
# ---------------------------------------------------------------------------

def run_scenario(base_params, overrides):
    p = deepcopy(base_params)
    p.update(overrides)
    enrich_keys = {
        "transaction_date", "building_completion_ym", "building_structure",
        "building_usage", "steel_thickness_mm", "hold_period_years",
        "inflation_rate", "land_real_appreciation_spread",
        "building_real_appreciation_spread", "ownership_type",
        "income_tax_rate_national", "resident_tax_rate",
        "reconstruction_special_tax_rate",
    }
    if any(k in overrides for k in enrich_keys):
        p = enrich_params(p)
    df_s, summary_s = run_simulation(p)
    metrics_s, df_s = compute_metrics(p, df_s, summary_s)
    return df_s, summary_s, metrics_s, p


def build_extended_scenario_summary(base_params, scenario_list):
    rows = []
    for sc in scenario_list:
        label = sc["label"]
        overrides = sc["overrides"]
        df_s, summary_s, metrics_s, p_s = run_scenario(base_params, overrides)
        df_s, cf_m = add_cumulative_cashflow_columns(df_s, p_s)
        nav_s = build_nav_table(df_s, p_s)
        dd_s = build_drawdown_analysis(df_s, nav_s, p_s)
        final_nav_at = nav_s["nav_after_tax"].iloc[-1]
        row = {
            "Scenario": label,
            "Equity IRR": metrics_s.get("equity_irr"),
            "Equity Multiple": metrics_s.get("equity_multiple"),
            "Avg CoC": metrics_s.get("avg_cash_on_cash"),
            "Min DSCR": metrics_s.get("min_dscr"),
            "Min ICR": metrics_s.get("min_icr"),
            "BE Year (Cash)": cf_m.get("break_even_year_cash"),
            "Peak Neg CF (M)": cf_m.get("peak_negative_cumulative_cf", 0) / 1e6,
            "Final NAV AT (M)": final_nav_at / 1e6,
            "Max DD% Liq": dd_s["Liquidity"]["metrics"]["max_drawdown_pct"],
            "Max DD% NAV": dd_s["NAV After Tax"]["metrics"]["max_drawdown_pct"],
            "Max DD% TR": dd_s["Total Return"]["metrics"]["max_drawdown_pct"],
            "Tax Total (M)": metrics_s.get("total_tax_paid", 0) / 1e6,
            "Tax Drag": metrics_s.get("tax_drag_ratio", 0),
        }
        rows.append(row)
    return pd.DataFrame(rows)

# ---------------------------------------------------------------------------
# Part C: v3 new functions
# ---------------------------------------------------------------------------

def refine_sale_tax_calculation(params, summary):
    sale_price = summary["sale_price_selected"]
    mode = params.get("selling_expense_schedule_mode", "rate")
    if mode == "itemized":
        items = params.get("selling_expense_items", {})
        selling_total = sum(items.values())
    else:
        selling_total = sale_price * params["closing_cost_on_sale_rate"]

    net_sale = sale_price - selling_total
    actual_basis = summary.get("adjusted_basis", 0)
    total_capex_cap = summary.get("total_capex_capitalized", 0)
    accum_capex_dep = summary.get("accumulated_capex_depreciation", 0)
    actual_basis_with_capex = actual_basis + total_capex_cap - accum_capex_dep

    deemed_rate = params.get("deemed_acquisition_cost_rate", 0.05)
    deemed_basis = sale_price * deemed_rate

    if params.get("use_deemed_acquisition_cost_fallback", False):
        selected = max(actual_basis_with_capex, deemed_basis)
    else:
        selected = actual_basis_with_capex

    taxable_gain = net_sale - selected
    sale_tax_info = params.get("sale_tax_info", {})
    rate = sale_tax_info.get("total_rate", 0.2)
    tax_amount = max(taxable_gain * rate, 0.0)

    loan_bal = summary.get("loan_balance_at_sale", 0)
    bt_proceeds = net_sale - loan_bal
    net_after_tax = bt_proceeds - tax_amount

    return {
        "sale_price_gross": sale_price,
        "selling_expenses_total": selling_total,
        "net_sale_price": net_sale,
        "actual_tax_basis": actual_basis_with_capex,
        "deemed_tax_basis": deemed_basis,
        "selected_tax_basis": selected,
        "taxable_sale_gain": taxable_gain,
        "sale_tax_rate_applied": rate,
        "sale_tax_amount": tax_amount,
        "bt_sale_proceeds": bt_proceeds,
        "net_sale_proceeds_after_tax": net_after_tax,
    }


def run_ownership_comparison(base_params):
    results = {}
    for otype in ["individual", "corporate"]:
        overrides = {"ownership_type": otype}
        if otype == "individual":
            overrides["use_progressive_tax"] = base_params.get("use_progressive_tax", False)
        else:
            overrides["use_progressive_tax"] = False
        df_s, summary_s, metrics_s, p_s = run_scenario(base_params, overrides)
        df_s, cf_m = add_cumulative_cashflow_columns(df_s, p_s)
        nav_s = build_nav_table(df_s, p_s)
        dd_s = build_drawdown_analysis(df_s, nav_s, p_s)
        sale_detail = refine_sale_tax_calculation(p_s, summary_s)
        results[otype] = {
            "df": df_s, "summary": summary_s, "metrics": metrics_s, "params": p_s,
            "cf_metrics": cf_m, "nav_df": nav_s, "dd_results": dd_s,
            "sale_detail": sale_detail,
        }
    return results


def build_ownership_comparison_summary(results):
    rows = []
    for otype in ["individual", "corporate"]:
        r = results[otype]
        m = r["metrics"]
        cf = r["cf_metrics"]
        nav = r["nav_df"]
        dd = r["dd_results"]
        sd = r["sale_detail"]
        final_nav = nav["nav_after_tax"].iloc[-1]
        rows.append({
            "Ownership": otype.capitalize(),
            "Equity IRR": m.get("equity_irr"),
            "Equity Multiple": m.get("equity_multiple"),
            "Avg CoC": m.get("avg_cash_on_cash"),
            "Min DSCR": m.get("min_dscr"),
            "Final NAV AT (M)": final_nav / 1e6,
            "Holding Tax (M)": m.get("holding_tax_total", 0) / 1e6,
            "Sale Tax (M)": sd.get("sale_tax_amount", 0) / 1e6,
            "Total Tax (M)": m.get("total_tax_paid", 0) / 1e6,
            "Tax Drag": m.get("tax_drag_ratio", 0),
            "Final Wealth (M)": m.get("final_after_tax_wealth", 0) / 1e6,
            "BE Year (Cash)": cf.get("break_even_year_cash"),
            "Max DD% Liq": dd["Liquidity"]["metrics"]["max_drawdown_pct"],
            "Max DD% NAV": dd["NAV After Tax"]["metrics"]["max_drawdown_pct"],
        })
    return pd.DataFrame(rows)


def build_capital_events_table(df, params):
    events = []
    for _, row in df.iterrows():
        y = int(row["year"])
        if row.get("refinance_cash_out", 0) != 0 or row.get("refinance_fee", 0) != 0:
            events.append({
                "Year": y, "Event": "Refinance",
                "Amount": row.get("refinance_cash_out", 0),
                "Fee/Cost": row.get("refinance_fee", 0),
                "Loan Bal After": row["loan_balance_end"],
            })
        if row.get("prepayment", 0) > 0:
            events.append({
                "Year": y, "Event": "Prepayment",
                "Amount": -row["prepayment"],
                "Fee/Cost": 0,
                "Loan Bal After": row["loan_balance_end"],
            })
    if not events:
        events.append({"Year": 0, "Event": "None", "Amount": 0, "Fee/Cost": 0, "Loan Bal After": 0})
    return pd.DataFrame(events)


def build_tax_bridge_table(df, params, summary, sale_detail):
    holding_taxes = df[["year", "tax", "taxable_income"]].copy()
    holding_taxes = holding_taxes.rename(columns={"tax": "holding_tax"})
    total_holding = holding_taxes["holding_tax"].sum()
    bridge = {
        "Holding Tax Total": total_holding,
        "Sale Tax": sale_detail.get("sale_tax_amount", summary["capital_gains_tax"]),
        "Total Tax Paid": total_holding + sale_detail.get("sale_tax_amount", summary["capital_gains_tax"]),
    }
    return bridge, holding_taxes


def build_exit_waterfall_table(summary, sale_detail):
    rows = [
        ("Gross Sale Price", sale_detail["sale_price_gross"]),
        ("(-) Selling Expenses", -sale_detail["selling_expenses_total"]),
        ("= Net Sale Price", sale_detail["net_sale_price"]),
        ("(-) Loan Repayment", -summary["loan_balance_at_sale"]),
        ("= Before-Tax Sale Proceeds", sale_detail["bt_sale_proceeds"]),
        ("(-) Capital Gains Tax", -sale_detail["sale_tax_amount"]),
        ("= Net Sale Proceeds (After Tax)", sale_detail["net_sale_proceeds_after_tax"]),
    ]
    return pd.DataFrame(rows, columns=["Item", "Amount"])


def build_v3_extended_scenario_summary(base_params):
    axes = []
    for otype in ["individual", "corporate"]:
        for capex_mode in ["expense_all", "capitalize_all", "mixed_schedule"]:
            label = f"{otype[:4].title()}-{capex_mode}"
            overrides = {"ownership_type": otype, "capex_treatment_mode": capex_mode}
            if otype == "corporate":
                overrides["use_progressive_tax"] = False
            axes.append({"label": label, "overrides": overrides})

    axes.append({"label": "Indi-Refi ON", "overrides": {
        "ownership_type": "individual", "enable_refinance": True,
        "refinance_year": 5, "refinance_ltv": 0.70,
        "refinance_interest_rate": 0.018, "refinance_term_years": 25,
    }})
    axes.append({"label": "Indi-Deemed ON", "overrides": {
        "ownership_type": "individual", "use_deemed_acquisition_cost_fallback": True,
    }})
    return build_extended_scenario_summary(base_params, axes)

# ---------------------------------------------------------------------------
# High-level API for app.py
# ---------------------------------------------------------------------------

def run_full_analysis(params):
    """Run the complete analysis pipeline. Returns a dict of all results."""
    p = enrich_params(params)

    df, summary = run_simulation(p)
    metrics, df = compute_metrics(p, df, summary)
    df, cf_metrics = add_cumulative_cashflow_columns(df, p)
    pl_df = build_operating_pl_table(df, p)
    nav_df = build_nav_table(df, p)
    dd_results = build_drawdown_analysis(df, nav_df, p)
    sale_detail = refine_sale_tax_calculation(p, summary)
    tax_bridge, holding_taxes_df = build_tax_bridge_table(df, p, summary, sale_detail)
    cap_events_df = build_capital_events_table(df, p)
    wf_df = build_exit_waterfall_table(summary, sale_detail)

    return {
        "params": p,
        "annual_df": df,
        "summary": summary,
        "metrics": metrics,
        "cf_metrics": cf_metrics,
        "pl_df": pl_df,
        "nav_df": nav_df,
        "dd_results": dd_results,
        "sale_detail": sale_detail,
        "tax_bridge": tax_bridge,
        "holding_taxes_df": holding_taxes_df,
        "cap_events_df": cap_events_df,
        "wf_df": wf_df,
    }


def run_scenario_analysis(base_params, scenario_list=None):
    """Run multi-metric scenario comparison."""
    if scenario_list is None:
        scenario_list = [
            {"label": "Base Case",        "overrides": {}},
            {"label": "Rent -1%",         "overrides": {"rent_growth_rate": -0.01}},
            {"label": "Rent +2%",         "overrides": {"rent_growth_rate": 0.02}},
            {"label": "Exit Cap 4%",      "overrides": {"exit_cap_rate": 0.04}},
            {"label": "Exit Cap 6%",      "overrides": {"exit_cap_rate": 0.06}},
            {"label": "Component Growth", "overrides": {"exit_price_method": "component_growth"}},
            {"label": "High Repair (5%)", "overrides": {"repair_growth_rate": 0.05}},
            {"label": "Interest 3%",      "overrides": {"interest_rate": 0.03}},
            {"label": "Hold 20Y",         "overrides": {"hold_period_years": 20}},
        ]
    return build_extended_scenario_summary(base_params, scenario_list)
