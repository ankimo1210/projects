from __future__ import annotations

from typing import Any

import pandas as pd


FISCAL_YEARS = ["FY2026E", "FY2027E", "FY2028E", "FY2029E", "FY2030E"]


def _require_five(values: list[float], label: str) -> None:
    if len(values) != len(FISCAL_YEARS):
        raise ValueError(f"{label} must have {len(FISCAL_YEARS)} annual values.")


def validate_scenario(scenario: dict[str, Any]) -> None:
    for key in [
        "public_growth",
        "mobility_dx_growth",
        "other_growth",
        "ebitda_margin",
        "public_company_cost_savings",
    ]:
        _require_five(scenario[key], key)
    if scenario["debt_to_ebitda"] < 0:
        raise ValueError("debt_to_ebitda must be non-negative.")
    if scenario["exit_multiple"] <= 0:
        raise ValueError("exit_multiple must be positive.")


def project_financials(
    scenario_name: str,
    scenario: dict[str, Any],
    assumptions: dict[str, Any],
) -> pd.DataFrame:
    validate_scenario(scenario)
    segment_rows = assumptions["segments"]["rows"]
    base_segment = next(row for row in segment_rows if row["fiscal_year"] == "FY2025A")
    defaults = assumptions["projection_defaults"]

    public_revenue = float(base_segment["public_revenue"])
    mobility_revenue = float(base_segment["mobility_dx_revenue"])
    other_revenue = float(base_segment["other_revenue"])
    prior_total_revenue = public_revenue + mobility_revenue + other_revenue

    rows: list[dict[str, float | str | int]] = []
    for i, fiscal_year in enumerate(FISCAL_YEARS):
        public_revenue *= 1 + float(scenario["public_growth"][i])
        mobility_revenue *= 1 + float(scenario["mobility_dx_growth"][i])
        other_revenue *= 1 + float(scenario["other_growth"][i])
        total_revenue = public_revenue + mobility_revenue + other_revenue
        revenue_change = total_revenue - prior_total_revenue
        ebitda = total_revenue * float(scenario["ebitda_margin"][i]) + float(
            scenario["public_company_cost_savings"][i]
        )
        d_and_a = total_revenue * float(defaults["d_and_a_pct_revenue"])
        ebit = ebitda - d_and_a
        capex = total_revenue * float(defaults["capex_pct_revenue"])
        change_nwc = max(0.0, revenue_change * float(defaults["nwc_pct_of_revenue_change"]))
        rows.append(
            {
                "scenario": scenario_name,
                "year": i + 1,
                "fiscal_year": fiscal_year,
                "public_revenue": public_revenue,
                "mobility_dx_revenue": mobility_revenue,
                "other_revenue": other_revenue,
                "revenue": total_revenue,
                "revenue_growth": revenue_change / prior_total_revenue,
                "ebitda": ebitda,
                "ebitda_margin": ebitda / total_revenue,
                "d_and_a": d_and_a,
                "ebit": ebit,
                "ebit_margin": ebit / total_revenue,
                "capex": capex,
                "change_nwc": change_nwc,
                "source_type": scenario.get("source_type", "estimated"),
            }
        )
        prior_total_revenue = total_revenue
    return pd.DataFrame(rows)
