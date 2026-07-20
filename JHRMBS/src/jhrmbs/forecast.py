from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from jhrmbs.artifacts import read_table, write_table
from jhrmbs.config import AppConfig
from jhrmbs.exceptions import ModelError
from jhrmbs.metrics import psj_cpr, smm_to_cpr
from jhrmbs.models.training import load_model, resolve_model_name, resolve_run_directory
from jhrmbs.paths import DataPaths
from jhrmbs.util import atomic_write_json, read_json, utc_now

LOGGER = logging.getLogger("jhrmbs.forecast")


def _last_non_null(frame: pd.DataFrame, column: str, default: float = 0.0) -> float:
    values = (
        pd.to_numeric(frame[column], errors="coerce").dropna()
        if column in frame
        else pd.Series(dtype=float)
    )
    return float(values.iloc[-1]) if not values.empty else default


def forecast_issue(
    config: AppConfig,
    issue_id: str,
    *,
    model_name: str = "champion",
    run_id: str | None = None,
    mortgage_rate_pct: float | None = None,
    jgb_10y_pct: float | None = None,
    rate_feature_shift_pct: float = 0.0,
    save: bool = True,
) -> pd.DataFrame:
    paths = DataPaths(config.data_root)
    panel = read_table(paths.processed / "issue_month_panel.parquet")
    issues = read_table(paths.processed / "issues.parquet")
    features = read_table(paths.features / "model_features.parquet")
    issue_rows = panel[panel["issue_id"] == issue_id].sort_values("payment_month")
    if issue_rows.empty:
        raise ModelError(f"unknown issue: {issue_id}")
    observed = issue_rows[issue_rows["actual_factor"].notna()]
    if observed.empty:
        raise ModelError(f"issue has no observed factor: {issue_id}")
    current = observed.iloc[-1]
    future = issue_rows[issue_rows["payment_month"] > current["payment_month"]].copy()
    if future.empty:
        raise ModelError(f"issue has no future scheduled factor path: {issue_id}")
    issue = issues.loc[issues["issue_id"] == issue_id].iloc[0]
    series_type = str(issue["series_type"])
    outside_training_population = series_type != "monthly"
    if outside_training_population:
        LOGGER.warning(
            "issue %s has series_type=%s, outside the monthly-only training population; "
            "the fitted model is extrapolating",
            issue_id,
            series_type,
        )
    run_directory = resolve_run_directory(config, run_id)
    selected_model_name = resolve_model_name(config, model_name, run_id)
    model = load_model(config, model_name=selected_model_name, run_id=run_id)

    run_metadata = read_json(run_directory / "run.json", {})
    feature_metadata = (
        run_metadata.get("feature_configuration", {}) if isinstance(run_metadata, dict) else {}
    )
    rate_feature_mode = (
        str(feature_metadata.get("rate_feature_mode", "jgb_proxy"))
        if isinstance(feature_metadata, dict)
        else "jgb_proxy"
    )
    first_future_month = pd.Timestamp(future["payment_month"].min())
    issue_features = features[features["issue_id"] == issue_id].sort_values("payment_month")
    current_information = issue_features[
        (issue_features["payment_month"] <= first_future_month)
        & issue_features["rate_feature_pct"].notna()
    ]
    if current_information.empty and "rate_feature_pct" in model.feature_names:
        raise ModelError(
            f"no {rate_feature_mode} observation is available for forecasting {issue_id}"
        )
    reference = (
        current_information.iloc[-1] if not current_information.empty else issue_features.iloc[-1]
    )
    current_wac = float(
        current["wac_pct"] if pd.notna(current["wac_pct"]) else issue["initial_wac_pct"]
    )
    current_wala = float(
        current["wala_months"] if pd.notna(current["wala_months"]) else issue["initial_wala_months"]
    )
    rate_feature = float(reference.get("rate_feature_pct", 0.0))
    rate_is_proxy = rate_feature_mode == "jgb_proxy"
    if mortgage_rate_pct is not None:
        if rate_feature_mode != "mortgage_rate":
            raise ModelError(
                "this model run was trained with jgb_proxy; use --jgb-10y-pct or retrain "
                "with features.rate_feature_mode=mortgage_rate"
            )
        rate_feature = current_wac - mortgage_rate_pct
        rate_is_proxy = False
    elif jgb_10y_pct is not None:
        if rate_feature_mode != "jgb_proxy":
            raise ModelError(
                "this model run was trained with mortgage_rate; use --mortgage-rate-pct"
            )
        rate_feature = current_wac - jgb_10y_pct
        rate_is_proxy = True
    rate_feature += rate_feature_shift_pct

    predicted_factor = float(current["actual_factor"])
    previous_scheduled = float(current["scheduled_factor"])
    housing_yoy = _last_non_null(features.sort_values("payment_month"), "housing_starts_yoy_pct")
    m3_yoy = _last_non_null(features.sort_values("payment_month"), "m3_yoy_pct")
    rows: list[dict[str, object]] = []
    for step, (_, scheduled_row) in enumerate(future.iterrows(), start=1):
        month = pd.Timestamp(scheduled_row["payment_month"])
        prediction_wala = current_wala + step
        burnout = max((previous_scheduled - predicted_factor) / previous_scheduled, 0.0)
        feature_row = pd.DataFrame(
            [
                {
                    "seasoning_ratio": min(
                        prediction_wala / float(config.features.psj_seasoning_months), 1.0
                    ),
                    "rate_feature_pct": rate_feature,
                    "burnout_lag1": burnout,
                    "month_sin": np.sin(2.0 * np.pi * month.month / 12.0),
                    "month_cos": np.cos(2.0 * np.pi * month.month / 12.0),
                    "vintage_year_numeric": float(issue["vintage_year"]),
                    "housing_starts_yoy_pct": housing_yoy,
                    "m3_yoy_pct": m3_yoy,
                }
            ]
        )
        predicted_smm = float(model.predict_smm(feature_row)[0])
        predicted_cpr = float(smm_to_cpr(predicted_smm))
        scheduled_factor = float(scheduled_row["scheduled_factor"])
        balance_after_schedule_factor = predicted_factor * scheduled_factor / previous_scheduled
        ending_factor = balance_after_schedule_factor * (1.0 - predicted_smm)
        rows.append(
            {
                "issue_id": issue_id,
                "payment_month": month,
                "scheduled_factor": scheduled_factor,
                "prediction_wala_months": prediction_wala,
                "predicted_smm": predicted_smm,
                "predicted_cpr_pct": predicted_cpr * 100.0,
                "predicted_factor": ending_factor,
                "rate_feature_pct": rate_feature,
                "rate_feature_is_proxy": rate_is_proxy,
                "rate_feature_mode": rate_feature_mode,
                "model_name": selected_model_name,
                "run_id": run_directory.name,
            }
        )
        predicted_factor = ending_factor
        previous_scheduled = scheduled_factor
        if predicted_factor <= 1e-12:
            break
    result = pd.DataFrame(rows)
    if save:
        output_directory = paths.predictions / issue_id
        output_path = output_directory / f"{run_directory.name}_{selected_model_name}.parquet"
        write_table(result, output_path)
        atomic_write_json(
            output_directory / f"{run_directory.name}_{selected_model_name}.json",
            {
                "generated_at": utc_now().isoformat(),
                "issue_id": issue_id,
                "requested_model_name": model_name,
                "model_name": selected_model_name,
                "run_id": run_directory.name,
                "current_observation_month": str(pd.Timestamp(current["payment_month"]).date()),
                "series_type": series_type,
                "outside_training_population": outside_training_population,
                "rate_feature_pct": rate_feature,
                "rate_feature_is_proxy": rate_is_proxy,
                "rate_feature_mode": rate_feature_mode,
                "rate_feature_shift_pct": rate_feature_shift_pct,
                "mortgage_rate_override_pct": mortgage_rate_pct,
                "jgb_10y_override_pct": jgb_10y_pct,
                "unmodeled_components": ["long delinquency", "other cancellations", "cleanup call"],
            },
        )
        LOGGER.info("forecast %s model=%s rows=%d", issue_id, selected_model_name, len(result))
    return result


def _current_wala_months(observed: pd.DataFrame, issue_id: str) -> float:
    """WALA at the latest observed month, advanced from the last published value."""
    with_wala = observed[pd.to_numeric(observed["wala_months"], errors="coerce").notna()]
    if with_wala.empty:
        raise ModelError(f"WALA is not published for any observed month: {issue_id}")
    last = with_wala.iloc[-1]
    current_month = pd.Timestamp(observed["payment_month"].iloc[-1]).to_period("M")
    last_month = pd.Timestamp(last["payment_month"]).to_period("M")
    return float(last["wala_months"]) + float(current_month.ordinal - last_month.ordinal)


def fixed_psj_forecast(
    config: AppConfig,
    issue_id: str,
    *,
    terminal_cpr_pct: float,
) -> pd.DataFrame:
    panel = read_table(DataPaths(config.data_root).processed / "issue_month_panel.parquet")
    issue_rows = panel[panel["issue_id"] == issue_id].sort_values("payment_month")
    observed = issue_rows[issue_rows["actual_factor"].notna()]
    if observed.empty:
        raise ModelError(f"unknown or unobserved issue: {issue_id}")
    current = observed.iloc[-1]
    future = issue_rows[issue_rows["payment_month"] > current["payment_month"]].copy()
    wala = _current_wala_months(observed, issue_id)
    future["prediction_wala_months"] = wala + np.arange(1, len(future) + 1)
    future["predicted_cpr_pct"] = (
        np.asarray(
            psj_cpr(
                future["prediction_wala_months"].to_numpy(float),
                terminal_cpr_pct / 100.0,
                seasoning_months=config.features.psj_seasoning_months,
            )
        )
        * 100.0
    )
    future["model_name"] = f"fixed_psj_{terminal_cpr_pct:g}pct"
    result: pd.DataFrame = future[
        [
            "issue_id",
            "payment_month",
            "scheduled_factor",
            "prediction_wala_months",
            "predicted_cpr_pct",
            "model_name",
        ]
    ].reset_index(drop=True)
    return result
