from __future__ import annotations

import pandas as pd


def build_chart_data(
    historical: pd.DataFrame,
    projections: pd.DataFrame,
    model_outputs: pd.DataFrame,
    sensitivities: pd.DataFrame,
) -> dict[str, object]:
    default_projection = projections[projections["premium"] == projections["premium"].min()].copy()
    scenario_projection: dict[str, list[dict[str, object]]] = {}
    for scenario, df in default_projection.groupby("scenario"):
        scenario_projection[scenario] = df[
            ["fiscal_year", "revenue", "ebitda", "ebitda_margin", "public_revenue", "mobility_dx_revenue"]
        ].to_dict("records")

    returns_by_premium = model_outputs[
        ["scenario", "premium", "irr", "moic", "entry_ev_ebitda", "sponsor_equity"]
    ].to_dict("records")

    heatmap = sensitivities[sensitivities["sensitivity"] == "entry_premium_vs_exit_multiple"].copy()
    heatmap["premium_label"] = (heatmap["premium"] * 100).round(0).astype(int).astype(str) + "%"
    heatmap["exit_label"] = heatmap["exit_multiple"].round(1).astype(str) + "x"
    pivot = heatmap.pivot(index="premium_label", columns="exit_label", values="irr").sort_index()

    return {
        "historical": historical[["fiscal_year", "revenue", "ebitda_estimated", "ebit_margin"]].to_dict("records"),
        "scenario_projection": scenario_projection,
        "returns_by_premium": returns_by_premium,
        "heatmap": {
            "x": list(pivot.columns),
            "y": list(pivot.index),
            "z": pivot.fillna(0).values.tolist(),
        },
    }
