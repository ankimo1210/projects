from __future__ import annotations

from typing import Any, cast

import pandas as pd

from jhrmbs.artifacts import read_table, write_table
from jhrmbs.cashflow import CashflowAssumptions, CashflowPoint, generate_cashflows
from jhrmbs.config import AppConfig
from jhrmbs.exceptions import ModelError
from jhrmbs.forecast import fixed_psj_forecast, forecast_issue
from jhrmbs.paths import DataPaths
from jhrmbs.risk import risk_summary
from jhrmbs.util import atomic_write_json, utc_now


def create_issue_cashflow(
    config: AppConfig,
    issue_id: str,
    *,
    scenario: str = "model",
    model_name: str = "champion",
    run_id: str | None = None,
    psj_terminal_cpr_pct: float = 6.0,
    valuation_yield_pct: float | None = None,
    cleanup_call: bool = False,
    save: bool = True,
) -> tuple[pd.DataFrame, dict[str, float | str | bool]]:
    paths = DataPaths(config.data_root)
    panel = read_table(paths.processed / "issue_month_panel.parquet")
    issues = read_table(paths.processed / "issues.parquet")
    issue_rows = panel[panel["issue_id"] == issue_id].sort_values("payment_month")
    if issue_rows.empty:
        raise ModelError(f"unknown issue: {issue_id}")
    observed = issue_rows[issue_rows["actual_factor"].notna()]
    if observed.empty:
        raise ModelError(f"issue has no actual factor: {issue_id}")
    current = observed.iloc[-1]
    issue = issues[issues["issue_id"] == issue_id].iloc[0]
    if scenario == "model":
        forecast = forecast_issue(config, issue_id, model_name=model_name, run_id=run_id, save=save)
        selected_model = str(forecast["model_name"].iloc[0])
        scenario_name = f"model_{selected_model}"
    elif scenario == "psj":
        forecast = fixed_psj_forecast(config, issue_id, terminal_cpr_pct=psj_terminal_cpr_pct)
        scenario_name = f"psj_{psj_terminal_cpr_pct:g}pct"
    else:
        raise ModelError(f"unsupported cashflow scenario: {scenario}")
    points = [
        CashflowPoint(
            payment_date=pd.Timestamp(cast(Any, row.payment_month)).date(),
            scheduled_factor=float(cast(Any, row.scheduled_factor)),
            annual_cpr=float(cast(Any, row.predicted_cpr_pct)) / 100.0,
        )
        for row in forecast.itertuples(index=False)
    ]
    assumptions = CashflowAssumptions(
        face_amount=float(issue["face_amount_jpy"]),
        coupon_rate=float(issue["coupon_pct"]) / 100.0,
        current_factor=float(current["actual_factor"]),
        current_scheduled_factor=float(current["scheduled_factor"]),
        cleanup_threshold=config.cashflow.cleanup_threshold if cleanup_call else None,
        cleanup_lag_months=config.cashflow.cleanup_lag_months,
    )
    rows = generate_cashflows(assumptions, points)
    frame = pd.DataFrame(row.to_dict() for row in rows)
    if frame.empty:
        raise ModelError(f"cashflow engine produced no rows: {issue_id}")
    frame.insert(0, "issue_id", issue_id)
    frame.insert(1, "scenario", scenario_name)
    yield_pct = (
        valuation_yield_pct
        if valuation_yield_pct is not None
        else config.cashflow.valuation_yield_pct
    )
    summary: dict[str, float | str | bool] = {
        "issue_id": issue_id,
        "scenario": scenario_name,
        "valuation_date": str(pd.Timestamp(current["payment_month"]).date()),
        "cleanup_call_assumed": cleanup_call,
        **risk_summary(
            rows,
            valuation_date=pd.Timestamp(current["payment_month"]).date(),
            current_balance=float(issue["face_amount_jpy"] * current["actual_factor"]),
            annual_effective_yield=yield_pct / 100.0,
        ),
    }
    if save:
        output_directory = paths.cashflows / issue_id
        output_path = output_directory / f"{scenario_name}.parquet"
        write_table(frame, output_path)
        atomic_write_json(
            output_directory / f"{scenario_name}_summary.json",
            {
                "generated_at": utc_now().isoformat(),
                "units": {
                    "amounts": "JPY",
                    "rates": "decimal inside cashflow rows; percentages carry _pct suffix",
                    "duration": "years",
                    "yield": "annual effective rate",
                },
                "method": "scheduled-factor ratio, then voluntary SMM, then optional cleanup call",
                **summary,
            },
        )
    return frame, summary
