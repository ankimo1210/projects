from __future__ import annotations

import numpy as np
import pandas as pd

from jhrmbs.config import FeatureConfig
from jhrmbs.metrics import cpr_to_smm


def _merge_monthly(
    frame: pd.DataFrame,
    monthly: pd.DataFrame | None,
    columns: list[str],
) -> pd.DataFrame:
    if monthly is None or monthly.empty:
        for column in columns:
            frame[column] = np.nan
        return frame
    available = [column for column in columns if column in monthly.columns]
    return frame.merge(
        monthly[["month", *available]].drop_duplicates("month", keep="last"),
        left_on="information_month",
        right_on="month",
        how="left",
    ).drop(columns="month")


def build_features(
    panel: pd.DataFrame,
    issues: pd.DataFrame,
    *,
    jgb: pd.DataFrame | None = None,
    mortgage_rates: pd.DataFrame | None = None,
    housing: pd.DataFrame | None = None,
    m3: pd.DataFrame | None = None,
    config: FeatureConfig | None = None,
) -> pd.DataFrame:
    settings = config or FeatureConfig()
    frame = panel.sort_values(["issue_id", "payment_month"]).copy()
    issue_initial = issues.set_index("issue_id")
    grouped = frame.groupby("issue_id", sort=False)

    lag_pairs = {
        "actual_factor": "factor_lag1",
        "scheduled_factor": "scheduled_factor_lag1",
        "wac_pct": "wac_pct_lag1",
        "wam_years": "wam_years_lag1",
        "wala_months": "wala_months_lag1",
        "voluntary_cpr_pct": "cpr_pct_lag1",
    }
    for source, target in lag_pairs.items():
        frame[target] = grouped[source].shift(1)

    initial_map = {
        "factor_lag1": pd.Series(1.0, index=frame.index),
        "scheduled_factor_lag1": pd.Series(1.0, index=frame.index),
        "wac_pct_lag1": frame["issue_id"].map(issue_initial["initial_wac_pct"]),
        "wam_years_lag1": frame["issue_id"].map(issue_initial["initial_wam_years"]),
        "wala_months_lag1": frame["issue_id"].map(issue_initial["initial_wala_months"]),
    }
    for column, initial in initial_map.items():
        frame[column] = frame[column].fillna(initial)

    cpr_decimal = pd.to_numeric(frame["voluntary_cpr_pct"], errors="coerce") / 100.0
    frame["target_smm"] = cpr_to_smm(cpr_decimal.to_numpy())
    frame.loc[cpr_decimal.isna(), "target_smm"] = np.nan
    frame["prediction_wala_months"] = frame["wala_months_lag1"] + 1.0
    frame["seasoning_ratio"] = (
        frame["prediction_wala_months"] / float(settings.psj_seasoning_months)
    ).clip(0.0, 1.0)
    frame["burnout_lag1"] = (
        (frame["scheduled_factor_lag1"] - frame["factor_lag1"])
        / frame["scheduled_factor_lag1"].replace(0.0, np.nan)
    ).clip(lower=0.0)
    frame["exposure_jpy"] = frame["face_amount_jpy"] * frame["factor_lag1"]
    frame["scheduled_surviving_factor"] = (
        frame["factor_lag1"]
        * frame["scheduled_factor"]
        / frame["scheduled_factor_lag1"].replace(0.0, np.nan)
    )
    month_number = frame["payment_month"].dt.month.astype(float)
    frame["month_sin"] = np.sin(2.0 * np.pi * month_number / 12.0)
    frame["month_cos"] = np.cos(2.0 * np.pi * month_number / 12.0)
    frame["vintage_year_numeric"] = frame["vintage_year"].astype(float)
    frame["information_month"] = frame["payment_month"] - pd.DateOffset(
        months=settings.publication_lag_months
    )

    frame = _merge_monthly(frame, jgb, ["jgb_10y_pct"])
    frame = _merge_monthly(frame, mortgage_rates, ["mortgage_rate_mode_pct"])
    frame = _merge_monthly(
        frame,
        housing,
        ["housing_starts_total", "housing_starts_yoy_pct"],
    )
    frame = _merge_monthly(frame, m3, ["m3_100m_jpy", "m3_yoy_pct"])
    frame["refi_incentive_pct"] = frame["wac_pct_lag1"] - frame["mortgage_rate_mode_pct"]
    frame["wac_minus_jgb_10y_pct"] = frame["wac_pct_lag1"] - frame["jgb_10y_pct"]
    if settings.rate_feature_mode == "mortgage_rate":
        frame["rate_feature_pct"] = frame["refi_incentive_pct"]
        frame["rate_feature_is_proxy"] = False
    else:
        frame["rate_feature_pct"] = frame["wac_minus_jgb_10y_pct"]
        frame["rate_feature_is_proxy"] = frame["rate_feature_pct"].notna()
    frame["rate_feature_mode"] = settings.rate_feature_mode
    return frame.sort_values(["issue_id", "payment_month"]).reset_index(drop=True)
