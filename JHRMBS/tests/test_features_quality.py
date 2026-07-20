from __future__ import annotations

import pandas as pd
import pytest
from jhrmbs.config import FeatureConfig
from jhrmbs.exceptions import DataQualityError
from jhrmbs.features import build_features
from jhrmbs.quality import validate_features, validate_panel


def _issues() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "issue_id": "JHF-001",
                "initial_wac_pct": 3.0,
                "initial_wam_years": 30.0,
                "initial_wala_months": 0.0,
            }
        ]
    )


def _panel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "issue_id": ["JHF-001", "JHF-001"],
            "series_type": ["monthly", "monthly"],
            "vintage_year": [2008, 2008],
            "payment_month": pd.to_datetime(["2008-02-01", "2008-03-01"]),
            "actual_factor": [0.99, 0.97],
            "scheduled_factor": [0.995, 0.990],
            "wac_pct": [3.0, 2.9],
            "wam_years": [29.9, 29.8],
            "wala_months": [1.0, 2.0],
            "voluntary_cpr_pct": [5.0, 6.0],
            "face_amount_jpy": [100_000_000.0, 100_000_000.0],
            "coupon_pct": [1.2, 1.2],
        }
    )


def test_features_use_prior_month_pool_state() -> None:
    features = build_features(_panel(), _issues())
    assert features.loc[0, "factor_lag1"] == pytest.approx(1.0)
    assert features.loc[1, "factor_lag1"] == pytest.approx(0.99)
    assert features.loc[1, "wac_pct_lag1"] == pytest.approx(3.0)
    assert features.loc[1, "target_smm"] != features.loc[0, "target_smm"]


def test_initial_lag_fill_applies_only_to_first_issue_row() -> None:
    panel = _panel()
    extra = panel.iloc[[1]].assign(
        payment_month=pd.to_datetime(["2008-04-01"]),
        actual_factor=[0.95],
        scheduled_factor=[0.985],
        voluntary_cpr_pct=[5.5],
    )
    gap = panel.copy()
    gap.loc[1, "actual_factor"] = None
    gap.loc[1, "wac_pct"] = None
    panel = pd.concat([gap, extra], ignore_index=True)

    features = build_features(panel, _issues())
    assert features.loc[0, "factor_lag1"] == pytest.approx(1.0)
    assert features.loc[0, "wac_pct_lag1"] == pytest.approx(3.0)
    assert pd.isna(features.loc[2, "factor_lag1"])
    assert pd.isna(features.loc[2, "wac_pct_lag1"])
    assert pd.isna(features.loc[2, "exposure_jpy"])


def test_rate_feature_mode_does_not_mix_mortgage_and_jgb_definitions() -> None:
    jgb = pd.DataFrame(
        {
            "month": pd.to_datetime(["2008-01-01", "2008-02-01"]),
            "jgb_10y_pct": [1.0, 1.1],
        }
    )
    mortgage = pd.DataFrame(
        {
            "month": pd.to_datetime(["2008-01-01", "2008-02-01"]),
            "mortgage_rate_mode_pct": [2.0, 2.1],
        }
    )
    proxy = build_features(
        _panel(),
        _issues(),
        jgb=jgb,
        mortgage_rates=mortgage,
        config=FeatureConfig(rate_feature_mode="jgb_proxy"),
    )
    direct = build_features(
        _panel(),
        _issues(),
        jgb=jgb,
        mortgage_rates=mortgage,
        config=FeatureConfig(rate_feature_mode="mortgage_rate"),
    )
    assert proxy.loc[0, "rate_feature_pct"] == pytest.approx(2.0)
    assert bool(proxy.loc[0, "rate_feature_is_proxy"])
    assert direct.loc[0, "rate_feature_pct"] == pytest.approx(1.0)
    assert not bool(direct.loc[0, "rate_feature_is_proxy"])


def test_features_carry_mortgage_rate_definition_for_coverage_checks() -> None:
    mortgage = pd.DataFrame(
        {
            "month": pd.to_datetime(["2008-01-01", "2008-02-01"]),
            "mortgage_rate_mode_pct": [2.0, 2.1],
            "mortgage_rate_definition": ["official flat35", "official flat35"],
        }
    )
    features = build_features(
        _panel(),
        _issues(),
        mortgage_rates=mortgage,
        config=FeatureConfig(rate_feature_mode="mortgage_rate"),
    )
    assert features.loc[0, "mortgage_rate_definition"] == "official flat35"


def test_quality_rejects_duplicate_issue_month() -> None:
    panel = pd.concat([_panel(), _panel().iloc[[0]]], ignore_index=True)
    with pytest.raises(DataQualityError, match="grain_uniqueness"):
        validate_panel(panel)


def test_feature_quality_raises_on_invalid_target() -> None:
    features = build_features(_panel(), _issues())
    features.loc[0, "target_smm"] = 1.5
    with pytest.raises(DataQualityError, match="invalid_target_rows"):
        validate_features(features)
    report = validate_features(features, fail_on_invalid=False)
    assert report["status"] == "fail"


def test_feature_quality_raises_on_duplicate_grain() -> None:
    features = build_features(_panel(), _issues())
    duplicated = pd.concat([features, features.iloc[[0]]], ignore_index=True)
    with pytest.raises(DataQualityError, match="duplicate_rows"):
        validate_features(duplicated)
