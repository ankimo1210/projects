from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from jhrmbs.models.fractional_logit import FractionalLogitModel
from jhrmbs.models.training import select_champion


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
