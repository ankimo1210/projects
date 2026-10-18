from types import SimpleNamespace

import numpy as np
import pandas as pd
from bond_timing.backtest import Forecasts
from bond_timing.oos_a import evaluate_instrument


def test_evaluate_instrument_reports_tests_and_robustness():
    index = pd.period_range("1998-01", "2004-12", freq="M")
    rng = np.random.default_rng(0)
    study = SimpleNamespace(
        zeros=pd.DataFrame({120: 0.05 + rng.normal(0, 0.002, len(index))}, index=index),
        bey=pd.Series(0.05, index=index),
    )
    outcomes = SimpleNamespace(
        excess=pd.DataFrame({"tlt": rng.normal(0.003, 0.03, len(index))}, index=index)
    )
    decisions = pd.period_range("2000-01", "2003-12", freq="M")
    predictions = {
        model: pd.DataFrame({0: rng.normal(0.01, 0.02, len(decisions))}, index=decisions)
        for model in ("ols_p", "ols_pm", "nn_fm", "et")
    }
    legs = pd.DataFrame({"in": 0.001, "out": -0.001}, index=decisions + 1)
    entry = evaluate_instrument(
        study, outcomes, decisions, Forecasts(predictions, {}), None, "slope", "tlt", legs
    )
    assert set(entry["robust"]) == {"P1", "P2", "P3", "P4", "P5"}
    assert set(entry["robust"]["P4"]) == {
        "vs_hold_4bp",
        "vs_p1_4bp",
        "vs_hold_delay",
        "vs_p1_delay",
    }
    assert entry["tests"]["vs_hold"]["P2"]["months"] == 48
    assert "summary_delay" in entry and "hold" in entry["summary_4bp"]
