from __future__ import annotations

from copy import deepcopy
from typing import Any

import pandas as pd

from src.model.lbo_model import load_model_inputs, run_lbo_case


def _base_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    inputs = load_model_inputs()
    return inputs["assumptions"], inputs["scenarios"], inputs["market_snapshot"]


def entry_premium_vs_exit_multiple(
    scenario_name: str = "Sponsor",
    premiums: list[float] | None = None,
    exit_multiples: list[float] | None = None,
) -> pd.DataFrame:
    assumptions, scenarios, market_snapshot = _base_inputs()
    premiums = premiums or [0.20, 0.30, 0.40, 0.50]
    exit_multiples = exit_multiples or [7.0, 8.0, 8.5, 9.0, 10.0]
    rows = []
    for premium in premiums:
        for multiple in exit_multiples:
            scenario = deepcopy(scenarios[scenario_name])
            scenario["exit_multiple"] = multiple
            summary, _ = run_lbo_case(scenario_name, premium, assumptions, scenario, market_snapshot)
            rows.append(
                {
                    "sensitivity": "entry_premium_vs_exit_multiple",
                    "premium": premium,
                    "exit_multiple": multiple,
                    "irr": summary["irr"],
                    "moic": summary["moic"],
                }
            )
    return pd.DataFrame(rows)


def debt_to_ebitda_vs_exit_multiple(
    scenario_name: str = "Sponsor",
    leverage_levels: list[float] | None = None,
    exit_multiples: list[float] | None = None,
    premium: float = 0.30,
) -> pd.DataFrame:
    assumptions, scenarios, market_snapshot = _base_inputs()
    leverage_levels = leverage_levels or [0.0, 0.5, 1.0, 1.25, 1.5]
    exit_multiples = exit_multiples or [7.0, 8.0, 8.5, 9.0, 10.0]
    rows = []
    for leverage in leverage_levels:
        for multiple in exit_multiples:
            scenario = deepcopy(scenarios[scenario_name])
            scenario["debt_to_ebitda"] = leverage
            scenario["exit_multiple"] = multiple
            summary, _ = run_lbo_case(scenario_name, premium, assumptions, scenario, market_snapshot)
            rows.append(
                {
                    "sensitivity": "debt_to_ebitda_vs_exit_multiple",
                    "debt_to_ebitda": leverage,
                    "exit_multiple": multiple,
                    "irr": summary["irr"],
                    "moic": summary["moic"],
                }
            )
    return pd.DataFrame(rows)


def margin_improvement_vs_revenue_growth(
    scenario_name: str = "Base",
    margin_deltas: list[float] | None = None,
    revenue_growth_deltas: list[float] | None = None,
    premium: float = 0.30,
) -> pd.DataFrame:
    assumptions, scenarios, market_snapshot = _base_inputs()
    margin_deltas = margin_deltas or [-0.02, -0.01, 0.0, 0.01, 0.02]
    revenue_growth_deltas = revenue_growth_deltas or [-0.04, -0.02, 0.0, 0.02, 0.04]
    rows = []
    for margin_delta in margin_deltas:
        for growth_delta in revenue_growth_deltas:
            scenario = deepcopy(scenarios[scenario_name])
            scenario["ebitda_margin"] = [max(0.01, x + margin_delta) for x in scenario["ebitda_margin"]]
            scenario["public_growth"] = [x + growth_delta for x in scenario["public_growth"]]
            scenario["mobility_dx_growth"] = [x + growth_delta for x in scenario["mobility_dx_growth"]]
            summary, _ = run_lbo_case(scenario_name, premium, assumptions, scenario, market_snapshot)
            rows.append(
                {
                    "sensitivity": "margin_improvement_vs_revenue_growth",
                    "margin_delta": margin_delta,
                    "revenue_growth_delta": growth_delta,
                    "irr": summary["irr"],
                    "moic": summary["moic"],
                }
            )
    return pd.DataFrame(rows)


def mobility_success_failure(premium: float = 0.30) -> pd.DataFrame:
    assumptions, scenarios, market_snapshot = _base_inputs()
    rows = []
    for scenario_name in ["Downside", "Base", "Upside", "Sponsor"]:
        summary, _ = run_lbo_case(scenario_name, premium, assumptions, scenarios[scenario_name], market_snapshot)
        rows.append(
            {
                "sensitivity": "mobility_success_failure",
                "case": scenario_name,
                "irr": summary["irr"],
                "moic": summary["moic"],
                "exit_ebitda": summary["exit_ebitda"],
            }
        )
    return pd.DataFrame(rows)


def cash_extraction_sensitivity(
    scenario_name: str = "Sponsor",
    cash_availability: list[float] | None = None,
    premium: float = 0.30,
) -> pd.DataFrame:
    assumptions, scenarios, market_snapshot = _base_inputs()
    cash_availability = cash_availability or [0.0, 0.35, 0.50, 0.65, 0.80]
    rows = []
    for availability in cash_availability:
        scenario = deepcopy(scenarios[scenario_name])
        scenario["excess_cash_availability_pct"] = availability
        summary, _ = run_lbo_case(scenario_name, premium, assumptions, scenario, market_snapshot)
        rows.append(
            {
                "sensitivity": "cash_extraction",
                "excess_cash_availability_pct": availability,
                "irr": summary["irr"],
                "moic": summary["moic"],
                "sponsor_equity": summary["sponsor_equity"],
            }
        )
    return pd.DataFrame(rows)


def investigation_cost_sensitivity(
    scenario_name: str = "Sponsor",
    costs: list[float] | None = None,
    premium: float = 0.30,
) -> pd.DataFrame:
    assumptions, scenarios, market_snapshot = _base_inputs()
    costs = costs or [0, 50, 100, 200, 400]
    rows = []
    for cost in costs:
        scenario = deepcopy(scenarios[scenario_name])
        scenario["investigation_cost_at_close"] = cost
        summary, _ = run_lbo_case(scenario_name, premium, assumptions, scenario, market_snapshot)
        rows.append(
            {
                "sensitivity": "investigation_cost",
                "investigation_cost": cost,
                "irr": summary["irr"],
                "moic": summary["moic"],
                "sponsor_equity": summary["sponsor_equity"],
            }
        )
    return pd.DataFrame(rows)


def run_all_sensitivities() -> pd.DataFrame:
    frames = [
        entry_premium_vs_exit_multiple(),
        debt_to_ebitda_vs_exit_multiple(),
        margin_improvement_vs_revenue_growth(),
        mobility_success_failure(),
        cash_extraction_sensitivity(),
        investigation_cost_sensitivity(),
    ]
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    from src.utils.sources import OUTPUT_DIR

    df = run_all_sensitivities()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_DIR / "sensitivity_outputs.csv", index=False)


if __name__ == "__main__":
    main()
