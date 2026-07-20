from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from jhrmbs.exceptions import ModelError
from jhrmbs.models.fractional_logit import FractionalLogitModel
from jhrmbs.models.training import ensure_rate_definition_coverage, select_champion


def _definition_frame(definitions: list[str | None]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "rate_feature_pct": [
                1.0 if definition is not None else None for definition in definitions
            ],
            "mortgage_rate_definition": definitions,
        }
    )


def test_mortgage_mode_requires_single_definition_to_cover_ninety_percent() -> None:
    mixed = _definition_frame(["official"] * 17 + ["manual"] * 3)
    with pytest.raises(ModelError, match="85"):
        ensure_rate_definition_coverage(mixed, "mortgage_rate")

    dominant = _definition_frame(["official"] * 19 + ["manual"])
    ensure_rate_definition_coverage(dominant, "mortgage_rate")


def test_mortgage_mode_counts_missing_rates_against_coverage() -> None:
    sparse = _definition_frame(["official"] * 17 + [None] * 3)
    with pytest.raises(ModelError, match="85"):
        ensure_rate_definition_coverage(sparse, "mortgage_rate")


def test_jgb_proxy_mode_skips_definition_coverage_check() -> None:
    mixed = _definition_frame(["official"] * 10 + [None] * 10)
    ensure_rate_definition_coverage(mixed, "jgb_proxy")


def test_fractional_logit_fits_predicts_and_round_trips(tmp_path: Path) -> None:
    x = np.linspace(-2.0, 2.0, 200)
    target = pd.Series(1.0 / (1.0 + np.exp(-(-3.0 + 1.2 * x))))
    frame = pd.DataFrame({"x": x})
    model = FractionalLogitModel(("x",)).fit(frame, target)
    prediction = model.predict_smm(pd.DataFrame({"x": [-1.0, 1.0]}))
    assert 0.0 < prediction[0] < prediction[1] < 1.0

    path = tmp_path / "model.json"
    model.save(path)
    loaded = FractionalLogitModel.load(path)
    np.testing.assert_allclose(loaded.predict_smm(frame), model.predict_smm(frame))


def test_champion_uses_cross_split_rank_before_average_error() -> None:
    metrics = pd.DataFrame(
        [
            {"split": "time", "model": "seasoning", "weighted_rmse_cpr_pct": 3.0},
            {"split": "time", "model": "rate", "weighted_rmse_cpr_pct": 1.0},
            {"split": "time", "model": "full", "weighted_rmse_cpr_pct": 1.2},
            {"split": "vintage", "model": "seasoning", "weighted_rmse_cpr_pct": 1.0},
            {"split": "vintage", "model": "rate", "weighted_rmse_cpr_pct": 1.1},
            {"split": "vintage", "model": "full", "weighted_rmse_cpr_pct": 2.0},
        ]
    )
    champion, selection = select_champion(metrics)
    assert champion == "rate"
    assert selection.loc[0, "selection_rank"] == 1
