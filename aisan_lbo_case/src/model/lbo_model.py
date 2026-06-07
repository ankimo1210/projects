from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.model.debt_schedule import build_debt_schedule
from src.model.financial_projection import project_financials
from src.model.returns import calculate_returns
from src.utils.sources import CONFIG_DIR, OUTPUT_DIR, PROJECT_ROOT, load_yaml, write_json
from src.utils.validation import (
    validate_ev_bridge,
    validate_exit_equity,
    validate_share_price_bridge,
    validate_sources_uses,
)


def load_model_inputs() -> dict[str, Any]:
    assumptions = load_yaml(CONFIG_DIR / "assumptions.yaml")
    scenarios = load_yaml(CONFIG_DIR / "scenarios.yaml")["scenarios"]
    market_snapshot = _load_market_snapshot(assumptions)
    return {
        "assumptions": assumptions,
        "scenarios": scenarios,
        "market_snapshot": market_snapshot,
    }


def _load_market_snapshot(assumptions: dict[str, Any]) -> dict[str, Any]:
    path = PROJECT_ROOT / "data" / "processed" / "market_snapshot.csv"
    if path.exists():
        df = pd.read_csv(path)
        if not df.empty:
            row = df.iloc[0].to_dict()
            if pd.notna(row.get("close_price_jpy")):
                return row
    return assumptions["market_snapshot_manual_fallback"].copy()


def _entry_ebitda(assumptions: dict[str, Any]) -> float:
    latest = assumptions["historical_financials"]["rows"][-1]
    d_and_a = latest["revenue"] * assumptions["projection_defaults"]["d_and_a_pct_revenue"]
    return float(latest["ebit"] + d_and_a)


def run_lbo_case(
    scenario_name: str,
    premium: float,
    assumptions: dict[str, Any],
    scenario: dict[str, Any],
    market_snapshot: dict[str, Any],
) -> tuple[dict[str, Any], pd.DataFrame]:
    share_data = assumptions["share_data"]
    defaults = assumptions["projection_defaults"]
    transaction = assumptions["transaction_assumptions"]
    latest_bs = assumptions["latest_balance_sheet_reference"]
    hold_years = int(transaction["hold_years"])

    close_price = float(market_snapshot["close_price_jpy"])
    diluted_shares = float(share_data["shares_outstanding"])
    offer_price = close_price * (1 + premium)
    equity_purchase_price = offer_price * diluted_shares / 1_000_000
    cash_balance = float(latest_bs["cash"])
    existing_debt = float(latest_bs["debt"])
    headline_enterprise_value = equity_purchase_price + existing_debt - cash_balance

    entry_ebitda = _entry_ebitda(assumptions)
    new_debt = entry_ebitda * float(scenario["debt_to_ebitda"])
    transaction_fees = equity_purchase_price * float(transaction["transaction_fee_pct_equity_value"])
    financing_fees = new_debt * float(transaction["financing_fee_pct_new_debt"])
    investigation_cost = float(scenario.get("investigation_cost_at_close", transaction["investigation_cost_at_close"]))
    min_cash = float(defaults["min_cash"])
    excess_cash_availability_pct = float(
        scenario.get("excess_cash_availability_pct", transaction["excess_cash_availability_pct"])
    )
    excess_cash_available = max(0.0, cash_balance - min_cash) * excess_cash_availability_pct

    total_uses = equity_purchase_price + existing_debt + transaction_fees + financing_fees + investigation_cost
    sponsor_equity = total_uses - new_debt - excess_cash_available
    total_sources = sponsor_equity + new_debt + excess_cash_available
    post_close_cash = cash_balance - excess_cash_available

    projection = project_financials(scenario_name, scenario, assumptions)
    debt_schedule = build_debt_schedule(
        projection=projection,
        opening_debt=new_debt,
        opening_cash=post_close_cash,
        min_cash=min_cash,
        interest_rate=float(defaults["interest_rate"]),
        cash_tax_rate=float(defaults["cash_tax_rate"]),
        cash_sweep_pct=float(scenario.get("cash_sweep_pct", defaults["cash_sweep_pct"])),
    )
    detail = projection.merge(debt_schedule, on=["scenario", "year", "fiscal_year"], how="left")

    exit_ebitda = float(detail.iloc[-1]["ebitda"])
    exit_multiple = float(scenario["exit_multiple"])
    exit_enterprise_value = exit_ebitda * exit_multiple
    exit_debt = float(detail.iloc[-1]["ending_debt"])
    exit_cash = float(detail.iloc[-1]["ending_cash"])
    exit_net_debt = exit_debt - exit_cash
    exit_equity_value = exit_enterprise_value - exit_net_debt
    returns = calculate_returns(exit_equity_value, sponsor_equity, hold_years)

    summary = {
        "scenario": scenario_name,
        "scenario_label": scenario.get("label", scenario_name),
        "premium": premium,
        "market_price": close_price,
        "offer_price": offer_price,
        "diluted_shares": diluted_shares,
        "equity_purchase_price": equity_purchase_price,
        "cash_balance": cash_balance,
        "existing_debt": existing_debt,
        "headline_enterprise_value": headline_enterprise_value,
        "entry_ebitda": entry_ebitda,
        "entry_ev_ebitda": headline_enterprise_value / entry_ebitda,
        "new_debt": new_debt,
        "entry_debt_to_ebitda": new_debt / entry_ebitda,
        "excess_cash_available": excess_cash_available,
        "post_close_cash": post_close_cash,
        "transaction_fees": transaction_fees,
        "financing_fees": financing_fees,
        "investigation_cost": investigation_cost,
        "total_uses": total_uses,
        "sponsor_equity": sponsor_equity,
        "total_sources": total_sources,
        "exit_year": detail.iloc[-1]["fiscal_year"],
        "exit_ebitda": exit_ebitda,
        "exit_multiple": exit_multiple,
        "exit_enterprise_value": exit_enterprise_value,
        "exit_debt": exit_debt,
        "exit_cash": exit_cash,
        "exit_net_debt": exit_net_debt,
        "exit_equity_value": exit_equity_value,
        "moic": returns["moic"],
        "irr": returns["irr"],
        "min_cash": min_cash,
        "source_type": scenario.get("source_type", "estimated"),
    }
    _validate_case(summary, detail)
    return summary, detail


def _validate_case(summary: dict[str, Any], detail: pd.DataFrame) -> None:
    validate_sources_uses(summary)
    validate_ev_bridge(summary)
    validate_share_price_bridge(summary)
    validate_exit_equity(summary)
    if (detail["ending_debt"] < -1e-9).any():
        raise AssertionError("Debt schedule produced negative debt.")
    if (detail["ending_cash"] + 1e-9 < summary["min_cash"]).any():
        raise AssertionError("Ending cash fell below minimum cash.")


def run_all_cases() -> tuple[pd.DataFrame, pd.DataFrame]:
    inputs = load_model_inputs()
    assumptions = inputs["assumptions"]
    scenarios = inputs["scenarios"]
    market_snapshot = inputs["market_snapshot"]
    premiums = assumptions["transaction_assumptions"]["tob_premiums"]

    summaries: list[dict[str, Any]] = []
    details: list[pd.DataFrame] = []
    for scenario_name, scenario in scenarios.items():
        for premium in premiums:
            summary, detail = run_lbo_case(
                scenario_name=scenario_name,
                premium=float(premium),
                assumptions=assumptions,
                scenario=scenario,
                market_snapshot=market_snapshot,
            )
            summaries.append(summary)
            detail = detail.copy()
            detail["premium"] = float(premium)
            details.append(detail)
    return pd.DataFrame(summaries), pd.concat(details, ignore_index=True)


def recommendation_from_outputs(outputs: pd.DataFrame, assumptions: dict[str, Any]) -> dict[str, Any]:
    default_premium = float(assumptions["transaction_assumptions"]["default_premium"])
    default_case = outputs[
        (outputs["scenario"] == "Sponsor") & (outputs["premium"].round(6) == round(default_premium, 6))
    ].iloc[0]
    low_premium_case = outputs[(outputs["scenario"] == "Sponsor") & (outputs["premium"].round(6) == 0.20)].iloc[0]
    thresholds = assumptions["return_thresholds"]
    gating_issue = True
    clears_15 = bool(default_case["irr"] >= thresholds["irr"][0] and default_case["moic"] >= thresholds["moic"][0])

    if gating_issue:
        recommendation = "Too early; proceed to confirmatory DD only"
    elif clears_15:
        recommendation = "Recommend with conditions"
    else:
        recommendation = "Do not recommend"

    return {
        "recommendation": recommendation,
        "primary_case": "Sponsor at 30% TOB premium",
        "primary_case_irr": float(default_case["irr"]),
        "primary_case_moic": float(default_case["moic"]),
        "low_premium_case_irr": float(low_premium_case["irr"]),
        "low_premium_case_moic": float(low_premium_case["moic"]),
        "clears_15pct_irr_2x_moic_at_default": clears_15,
        "gating_issue": "FY2026 subsidiary investigation and delayed annual results remain unresolved in public sources.",
        "investment_view": (
            "Not a classic leverage-driven LBO. AISAN screens as a possible small-cap growth-oriented "
            "take-private only if accounting / governance DD clears, excess cash is legally usable, "
            "and the entry premium is disciplined."
        ),
    }


def write_model_outputs() -> dict[str, Any]:
    summaries, details = run_all_cases()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summaries.to_csv(OUTPUT_DIR / "model_outputs.csv", index=False)
    details.to_csv(PROJECT_ROOT / "data" / "processed" / "projection_detail.csv", index=False)

    inputs = load_model_inputs()
    recommendation = recommendation_from_outputs(summaries, inputs["assumptions"])
    summary_json = {
        "company": inputs["assumptions"]["company"],
        "market_snapshot": inputs["market_snapshot"],
        "recommendation": recommendation,
        "case_count": int(len(summaries)),
        "default_outputs": summaries[
            summaries["premium"].round(6)
            == round(float(inputs["assumptions"]["transaction_assumptions"]["default_premium"]), 6)
        ].to_dict("records"),
    }
    write_json(OUTPUT_DIR / "model_summary.json", summary_json)
    return summary_json


def main() -> None:
    write_model_outputs()


if __name__ == "__main__":
    main()
