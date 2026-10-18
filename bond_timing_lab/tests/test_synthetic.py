import numpy as np
import pandas as pd
import pytest
from bond_timing.backtest import strategy_returns
from bond_timing.evaluate import cer
from bond_timing.returns import Outcomes, world_outcomes
from bond_timing.synthetic import (
    calibrate_k,
    fit_spanning_null,
    plant,
    resample_rows,
    simulate,
    w0_world,
)


def outcomes(seed: int = 0, periods: int = 120) -> Outcomes:
    index = pd.period_range("2000-01", periods=periods, freq="M")
    rng = np.random.default_rng(seed)
    log_excess = pd.DataFrame(
        {n: rng.normal(0.001 * n, 0.003 * n, periods) for n in range(2, 11)}, index=index
    )
    excess = pd.DataFrame(
        {
            "tlt": rng.normal(0.003, 0.03, periods),
            "ief": rng.normal(0.002, 0.015, periods),
            "z10": rng.normal(0.0025, 0.02, periods),
        },
        index=index,
    )
    return world_outcomes(log_excess, excess)


def test_resample_rows_draws_whole_rows():
    index = pd.period_range("2000-01", periods=10, freq="M")
    frame = pd.DataFrame({"a": np.arange(10.0), "b": np.arange(10.0) * 10}, index=index)
    target = pd.period_range("2001-01", periods=25, freq="M")
    out = resample_rows(frame, target, seed=3)
    assert out.index.equals(target)
    np.testing.assert_allclose(out["b"], out["a"] * 10)
    assert set(out["a"]) <= set(frame["a"])


def test_w0_world_rebuilds_rx12_from_the_drawn_months():
    real = outcomes()
    index = pd.period_range("2010-01", periods=60, freq="M")
    world = w0_world(real, index, seed=5)
    s = index[10]
    assert world.rx12[10][s] == pytest.approx(
        world.monthly_log_excess[10].loc[s + 1 : s + 12].sum()
    )
    assert world.excess.index.equals(index)
    again = w0_world(real, index, seed=5)
    np.testing.assert_array_equal(again.excess.to_numpy(), world.excess.to_numpy())


def test_plant_adds_the_lagged_component_scaled_by_duration():
    world = outcomes()
    planted = plant(world, pd.Series(1.0, index=world.excess.index), k=0.002)
    p, first = world.excess.index[5], world.excess.index[0]
    assert planted.excess.loc[p, "tlt"] - world.excess.loc[p, "tlt"] == pytest.approx(0.002 * 1.7)
    assert planted.monthly_log_excess.loc[p, 5] - world.monthly_log_excess.loc[
        p, 5
    ] == pytest.approx(0.001)
    assert planted.excess.loc[first, "tlt"] == world.excess.loc[first, "tlt"]


def test_calibrate_k_finds_the_smallest_size_with_the_target_gain():
    index = pd.period_range("2000-01", periods=229, freq="M")
    rng = np.random.default_rng(4)
    excess = pd.Series(rng.normal(0.003, 0.03, 229), index=index)
    z = pd.Series(rng.normal(size=229), index=index)
    decisions = index[:-1]
    k = calibrate_k(excess, z, decisions)

    def gain(size: float) -> float:
        shifted = excess + size * 1.7 * z.shift(1).reindex(index).fillna(0.0)
        oracle = strategy_returns((z.reindex(decisions) > 0).astype(float), shifted).dropna()
        hold = strategy_returns(pd.Series(1.0, index=decisions), shifted).dropna()
        return cer(oracle) - cer(hold)

    assert k > 0 and gain(k) >= 0.04 and gain(0.98 * k) < 0.04


def test_spanning_null_worlds_have_the_right_shape_and_are_reproducible():
    index = pd.period_range("1980-01", periods=240, freq="M")
    rng = np.random.default_rng(6)
    factors = np.zeros((240, 3))
    for t in range(1, 240):
        factors[t] = 0.95 * factors[t - 1] + rng.normal(0, 0.002, 3)
    loadings = rng.normal(size=(19, 3))
    zeros = pd.DataFrame(
        0.05 + factors @ loadings.T + rng.normal(0, 1e-4, (240, 19)), index=index, columns=range(19)
    )
    macro = pd.DataFrame(
        rng.normal(size=(240, 12)), index=index, columns=[f"m{j}" for j in range(12)]
    )
    null = fit_spanning_null(zeros, macro)
    y1, m1 = simulate(null, seed=1)
    y2, _ = simulate(null, seed=1)
    assert y1.shape == (240, 19) and m1.shape == (240, 12)
    pd.testing.assert_frame_equal(y1, y2)
    assert not y1.equals(simulate(null, seed=2)[0])
    np.testing.assert_allclose(y1.iloc[0], zeros.iloc[0])
    assert abs(y1.to_numpy().mean() - zeros.to_numpy().mean()) < 0.02
    assert 0.0 < null.max_eigenvalue < 1.0
