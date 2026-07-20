from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
import pytest
from jhrmbs.artifacts import read_table, write_table
from jhrmbs.cashflow_service import create_issue_cashflow
from jhrmbs.config import AppConfig
from jhrmbs.forecast import fixed_psj_forecast, forecast_issue
from jhrmbs.paths import DataPaths
from jhrmbs.util import read_json


def test_forecast_walks_scheduled_path_with_champion_model(
    pipeline_config: AppConfig,
) -> None:
    forecast = forecast_issue(pipeline_config, "JHF-001", save=False)
    assert len(forecast) == 12
    assert forecast["model_name"].iloc[0] == "rate"
    assert forecast["predicted_smm"].between(0.0, 1.0).all()
    assert forecast["predicted_factor"].is_monotonic_decreasing


def test_model_cashflow_summary_has_finite_risk_measures(
    pipeline_config: AppConfig,
) -> None:
    frame, summary = create_issue_cashflow(
        pipeline_config, "JHF-001", scenario="model", save=False
    )
    assert not frame.empty
    assert float(summary["wal_years"]) > 0.0
    assert np.isfinite(float(summary["dirty_price_per_100"]))


def test_fixed_psj_forecast_falls_back_when_latest_wala_is_missing(
    pipeline_config: AppConfig,
) -> None:
    paths = DataPaths(pipeline_config.data_root)
    panel = read_table(paths.processed / "issue_month_panel.parquet")
    last_observed = panel[
        (panel["issue_id"] == "JHF-001") & panel["actual_factor"].notna()
    ]["payment_month"].max()
    mask = (panel["issue_id"] == "JHF-001") & (panel["payment_month"] == last_observed)
    panel.loc[mask, "wala_months"] = None
    write_table(panel, paths.processed / "issue_month_panel.parquet")

    forecast = fixed_psj_forecast(pipeline_config, "JHF-001", terminal_cpr_pct=6.0)
    assert forecast["predicted_cpr_pct"].notna().all()
    assert forecast["prediction_wala_months"].iloc[0] == pytest.approx(37.0)


def test_forecast_flags_issue_outside_training_population(
    pipeline_config: AppConfig, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="jhrmbs.forecast"):
        forecast_issue(pipeline_config, "JHF-S-01", save=True)
    assert any("training population" in message for message in caplog.messages)
    paths = DataPaths(pipeline_config.data_root)
    metadata = read_json(
        paths.predictions / "JHF-S-01" / "20260101T000000Z_rate.json"
    )
    assert metadata["series_type"] == "s"
    assert metadata["outside_training_population"] is True


def test_forecast_rate_feature_shift_moves_frozen_rate_feature(
    pipeline_config: AppConfig,
) -> None:
    base = forecast_issue(pipeline_config, "JHF-001", save=False)
    shifted = forecast_issue(
        pipeline_config, "JHF-001", save=False, rate_feature_shift_pct=0.5
    )
    assert shifted["rate_feature_pct"].iloc[0] == pytest.approx(
        base["rate_feature_pct"].iloc[0] + 0.5
    )
    assert not np.allclose(
        shifted["predicted_smm"].to_numpy(), base["predicted_smm"].to_numpy()
    )


def test_cashflow_can_include_published_decrements(
    pipeline_config: AppConfig,
) -> None:
    base_frame, base_summary = create_issue_cashflow(
        pipeline_config, "JHF-001", scenario="model", save=False
    )
    total_frame, total_summary = create_issue_cashflow(
        pipeline_config,
        "JHF-001",
        scenario="model",
        include_published_decrements=True,
        save=False,
    )
    assert str(total_summary["scenario"]).endswith("_totaldec")
    assert total_frame["smm"].iloc[0] > base_frame["smm"].iloc[0]
    assert float(total_summary["wal_years"]) < float(base_summary["wal_years"])


def test_cashflow_accepts_precomputed_forecast(
    pipeline_config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    forecast = forecast_issue(pipeline_config, "JHF-001", save=False)

    def _fail(*args: Any, **kwargs: Any) -> pd.DataFrame:
        raise AssertionError("forecast_issue must not be called twice")

    monkeypatch.setattr("jhrmbs.cashflow_service.forecast_issue", _fail)
    frame, summary = create_issue_cashflow(
        pipeline_config, "JHF-001", scenario="model", forecast=forecast, save=False
    )
    assert not frame.empty
    assert str(summary["scenario"]) == "model_rate"
