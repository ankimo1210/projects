import json

import numpy as np
import pandas as pd
import pytest
from bond_timing.backtest import (
    REAL_TIME,
    V0,
    RefitTask,
    build_tasks,
    delayed_returns,
    fit_task,
    fractional_weights,
    run_forecasts,
    signal_weights,
    strategy_returns,
)
from bond_timing.features import YIELD_MONTHS
from bond_timing.models import ModelSpec, grid, ladder
from bond_timing.pit import LookaheadError


def month(text: str) -> pd.Period:
    return pd.Period(text, "M")


def panel(seed: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    index = pd.period_range("1971-08", "1990-12", freq="M")
    rng = np.random.default_rng(seed)
    level = 0.06 + np.cumsum(rng.normal(0, 0.001, len(index)))
    tilt = rng.normal(0, 0.005, len(index))
    yields = pd.DataFrame(
        {m: level + tilt * m / 120 + rng.normal(0, 1e-5, len(index)) for m in YIELD_MONTHS},
        index=index,
    )
    targets = pd.DataFrame({0: 3.0 * tilt + rng.normal(0, 0.0005, len(index))}, index=index)
    return yields, targets


def test_cost_is_charged_only_in_switch_months():
    decisions = pd.period_range("2000-01", periods=6, freq="M")
    weights = pd.Series([1, 1, 0, 0, 1, 1], index=decisions, dtype=float)
    excess = pd.Series(0.01, index=pd.period_range("2000-02", periods=6, freq="M"))
    r = strategy_returns(weights, excess, cost_bp=2.0)
    np.testing.assert_allclose(r.to_numpy(), [0.01, 0.01, -0.0002, 0.0, 0.0098, 0.01])
    assert r.index[0] == month("2000-02")


def test_always_hold_equals_the_instrument():
    decisions = pd.period_range("2000-01", periods=5, freq="M")
    excess = pd.Series(np.arange(1.0, 6.0) / 100, index=decisions + 1)
    r = strategy_returns(pd.Series(1.0, index=decisions), excess)
    pd.testing.assert_series_equal(r, excess, check_names=False)


def test_delayed_returns_use_the_legs_only_when_switching():
    decisions = pd.period_range("2000-01", periods=4, freq="M")
    weights = pd.Series([1, 1, 0, 1], index=decisions, dtype=float)
    months = decisions + 1
    excess = pd.Series(0.01, index=months)
    legs = pd.DataFrame({"in": 0.004, "out": 0.003}, index=months)
    r = delayed_returns(weights, excess, legs, cost_bp=2.0)
    np.testing.assert_allclose(r.to_numpy(), [0.01, 0.01, 0.003 - 0.0002, 0.004 - 0.0002])
    with pytest.raises(ValueError):
        delayed_returns(weights * 0.5, excess, legs)


def test_signal_weights_hold_cash_without_a_forecast():
    decisions = pd.period_range("2000-01", periods=3, freq="M")
    signal = pd.Series([0.2, np.nan], index=decisions[:2])
    assert signal_weights(signal, decisions).tolist() == [1.0, 0.0, 0.0]


def test_fractional_weights_are_clipped():
    index = pd.period_range("1995-01", periods=80, freq="M")
    excess = pd.Series(np.random.default_rng(0).normal(0, 0.02, 80), index=index)
    forecast = pd.Series(1.0, index=index)
    assert (fractional_weights(forecast, excess, index[-5:]) == 1.0).all()
    assert (fractional_weights(-forecast, excess, index[-5:]) == 0.0).all()


def test_build_tasks_skips_thin_years():
    yields, targets = panel()
    window = (month("1975-01"), month("1980-12"))
    tasks = build_tasks(
        yields,
        targets,
        None,
        refit_years=range(1975, 1981),
        window=window,
        horizon=12,
        rules=REAL_TIME,
    )
    assert [str(t.refit) for t in tasks] == ["1978-01", "1979-01", "1980-01"]
    assert tasks[0].starts.max() == month("1977-01") and len(tasks[0].starts) == 66
    with pytest.raises(ValueError):
        build_tasks(yields, targets, None, refit_years=[1980], window=window, horizon=12, rules=V0)


def test_forecasts_recover_a_linear_signal():
    yields, targets = panel()
    tasks = build_tasks(
        yields,
        targets,
        None,
        refit_years=range(1980, 1991),
        window=(month("1980-01"), month("1990-12")),
        horizon=12,
        rules=REAL_TIME,
    )
    out = run_forecasts(tasks, [ladder()["ols_p"]])
    prediction = out.predictions["ols_p"][0]
    assert len(prediction) == 132
    assert np.corrcoef(prediction, targets[0].reindex(prediction.index))[0, 1] > 0.95
    assert set(out.params["ols_p"]) == {f"{year}-01" for year in range(1980, 1991)}


def test_fixed_params_survive_a_json_round_trip():
    yields, targets = panel()
    tasks = build_tasks(
        yields,
        targets,
        None,
        refit_years=[1985],
        window=(month("1985-01"), month("1985-12")),
        horizon=12,
        rules=REAL_TIME,
    )
    spec = ModelSpec("tiny", "P", "mlp", grid(hidden_layer_sizes=((3,),), alpha=(1e-4, 1e-2)), 1)
    first = run_forecasts(tasks, [spec])
    again = run_forecasts(tasks, [spec], fixed=json.loads(json.dumps(first.params)))
    assert again.params == first.params
    np.testing.assert_array_equal(
        again.predictions["tiny"].to_numpy(), first.predictions["tiny"].to_numpy()
    )


def test_fit_task_refuses_a_target_that_ends_after_the_refit():
    yields, targets = panel()
    starts = pd.period_range("1974-01", "1979-07", freq="M")
    decisions = pd.period_range("1980-01", periods=2, freq="M")
    task = RefitTask(
        refit=month("1980-01"),
        decisions=decisions,
        starts=starts,
        Y=yields.reindex(starts).to_numpy(),
        M=None,
        y=targets.reindex(starts).to_numpy(),
        Y_pred=yields.reindex(decisions).to_numpy(),
        M_pred=None,
        horizon=12,
        rules=REAL_TIME,
    )
    with pytest.raises(LookaheadError):
        fit_task(task, ladder()["ols_p"])


def test_monthly_refits_give_each_decision_its_own_fit():
    yields, targets = panel()
    window = (month("1985-01"), month("1986-12"))
    common = {"refit_years": range(1985, 1987), "window": window, "horizon": 12}
    monthly = build_tasks(yields, targets, None, rules=REAL_TIME, refit_every=1, **common)
    assert [t.refit for t in monthly] == list(pd.period_range(*window, freq="M"))
    assert all(list(t.decisions) == [t.refit] for t in monthly)
    assert all(t.starts.max() == t.refit - 12 for t in monthly)
    leaky = build_tasks(
        yields, targets, None, rules=V0, refit_every=1, full_end=month("1990-12"), **common
    )
    assert all(t.starts.max() == t.refit - 1 for t in leaky)
    quarterly = build_tasks(yields, targets, None, rules=REAL_TIME, refit_every=3, **common)
    assert [t.refit.month for t in quarterly] == [1, 4, 7, 10] * 2
    assert all(len(t.decisions) == 3 for t in quarterly)
    with pytest.raises(ValueError, match="divide 12"):
        build_tasks(yields, targets, None, rules=REAL_TIME, refit_every=5, **common)
