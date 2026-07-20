from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from jhrmbs.artifacts import write_table
from jhrmbs.config import AppConfig
from jhrmbs.features import build_features
from jhrmbs.models.fractional_logit import FractionalLogitModel
from jhrmbs.paths import DataPaths
from jhrmbs.util import atomic_write_json

OBSERVED_MONTHS = 36
FUTURE_MONTHS = 12
RUN_ID = "20260101T000000Z"


def _issue_panel(issue_id: str, series_type: str) -> pd.DataFrame:
    months = pd.date_range("2023-01-01", periods=OBSERVED_MONTHS + FUTURE_MONTHS, freq="MS")
    rows: list[dict[str, object]] = []
    for index, month in enumerate(months, start=1):
        observed = index <= OBSERVED_MONTHS
        scheduled = 1.0 - 0.012 * index
        actual = scheduled * (1.0 - 0.004) ** index if observed else None
        rows.append(
            {
                "issue_id": issue_id,
                "issue_name": issue_id,
                "series_type": series_type,
                "issue_date": pd.Timestamp("2022-12-15"),
                "vintage_year": 2023,
                "face_amount_jpy": 10_000_000_000.0,
                "coupon_pct": 1.5,
                "payment_month": month,
                "scheduled_factor": scheduled,
                "actual_factor": actual,
                "wac_pct": 3.0 - 0.002 * index if observed else None,
                "wam_years": 35.0 - index / 12.0 if observed else None,
                "wala_months": float(index) if observed else None,
                "voluntary_cpr_pct": (
                    6.0 + np.sin(index / 6.0) if observed else None
                ),
                "rescheduled_factor": None,
                "long_delinquency_pct_monthly": 0.01 if observed else None,
                "other_cancellation_pct_monthly": 0.02 if observed else None,
            }
        )
    return pd.DataFrame(rows)


@pytest.fixture
def pipeline_config(tmp_path: Path) -> AppConfig:
    """A miniature data root with panel, features and a trained 'rate' model run."""
    config = AppConfig(data_root=tmp_path)
    paths = DataPaths(tmp_path)
    paths.ensure()

    issues = pd.DataFrame(
        [
            {
                "issue_id": issue_id,
                "issue_name": issue_id,
                "series_type": series_type,
                "issue_date": pd.Timestamp("2022-12-15"),
                "vintage_year": 2023,
                "face_amount_jpy": 10_000_000_000.0,
                "coupon_pct": 1.5,
                "initial_wac_pct": 3.0,
                "initial_wam_years": 35.0,
                "initial_wala_months": 0.0,
            }
            for issue_id, series_type in (("JHF-001", "monthly"), ("JHF-S-01", "s"))
        ]
    )
    panel = pd.concat(
        [_issue_panel("JHF-001", "monthly"), _issue_panel("JHF-S-01", "s")],
        ignore_index=True,
    )
    jgb = pd.DataFrame(
        {
            "month": pd.date_range("2022-11-01", periods=OBSERVED_MONTHS + 4, freq="MS"),
            "jgb_10y_pct": 1.0,
        }
    )
    features = build_features(panel, issues, jgb=jgb, config=config.features)

    write_table(issues, paths.processed / "issues.parquet")
    write_table(panel, paths.processed / "issue_month_panel.parquet")
    write_table(features, paths.features / "model_features.parquet")

    train = features[
        features["target_smm"].notna()
        & features["exposure_jpy"].notna()
        & (features["series_type"] == "monthly")
    ]
    model = FractionalLogitModel(("seasoning_ratio", "rate_feature_pct")).fit(
        train, train["target_smm"], sample_weight=train["exposure_jpy"]
    )
    run_directory = paths.models / RUN_ID
    (run_directory / "models").mkdir(parents=True)
    model.save(run_directory / "models" / "rate.json")
    atomic_write_json(
        run_directory / "run.json",
        {
            "schema_version": 1,
            "run_id": RUN_ID,
            "champion_model": "rate",
            "feature_configuration": asdict(config.features),
        },
    )
    atomic_write_json(
        paths.models / "latest_run.json",
        {"run_id": RUN_ID, "run_path": f"models/{RUN_ID}"},
    )

    metric_rows = []
    for split, winner in (("time", "rate"), ("vintage", "seasoning")):
        for model_name, rmse in (
            ("fixed_psj", 3.0),
            ("seasoning", 1.4 if winner != "seasoning" else 1.0),
            ("rate", 1.0 if winner == "rate" else 1.4),
            ("full", 1.6),
        ):
            metric_rows.append(
                {
                    "split": split,
                    "split_description": f"{split} holdout",
                    "model": model_name,
                    "train_rows": 500,
                    "test_rows": 120 if split == "time" else 24,
                    "test_issues": 2,
                    "rate_proxy_share": 1.0,
                    "mae_cpr_pct": rmse * 0.8,
                    "rmse_cpr_pct": rmse,
                    "weighted_mae_cpr_pct": rmse * 0.8,
                    "weighted_rmse_cpr_pct": rmse,
                    "cashflow_cumulative_principal_mae_pct": 1.0,
                    "truncated_wal_mae_years": 0.02,
                }
            )
    write_table(pd.DataFrame(metric_rows), run_directory / "metrics.parquet")
    atomic_write_json(
        paths.processed / "data_quality_report.json",
        {
            "panel": {
                "row_count": len(panel),
                "issue_count": 2,
                "critical_count": 0,
                "latest_observed_payment_month": "2025-12-01",
            },
            "features": {"rate_feature_missing_rate": 0.0},
        },
    )
    return config
