import numpy as np
import pandas as pd
import pytest
from sector_leadlag.synthetic import circular_shift, plant, shift_amounts, stale_returns


def test_shifts_stay_away_from_the_original_alignment():
    shifts = shift_amounts(1000)
    assert len(shifts) == 20 and all(60 <= k < 940 for k in shifts)
    assert shifts == shift_amounts(1000)


def test_circular_shift_moves_values_not_dates():
    frame = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0]}, index=pd.bdate_range("2026-01-05", periods=4))
    out = circular_shift(frame, 1)
    assert out.index.equals(frame.index) and out["x"].tolist() == [4.0, 1.0, 2.0, 3.0]


def test_plant_adds_beta_times_the_signal_where_returns_exist():
    returns = pd.DataFrame([[0.01, np.nan]], columns=[1, 2])
    sz = pd.DataFrame([[1.0, -1.0]], columns=[1, 2])
    out = plant(returns, sz, 0.002)
    assert out.iloc[0, 0] == pytest.approx(0.012) and np.isnan(out.iloc[0, 1])


def test_stale_opens_replace_the_largest_gaps_first():
    o2c = pd.DataFrame([[0.01, 0.02, 0.03, 0.04]], columns=list("abcd"))
    c2c = pd.DataFrame([[0.11, 0.12, 0.13, 0.14]], columns=list("abcd"))
    c2o = pd.DataFrame([[0.001, -0.05, 0.002, 0.003]], columns=list("abcd"))
    out = stale_returns(o2c, c2c, c2o, 0.25, mode="largest_gap")
    assert out.iloc[0].tolist() == [0.01, 0.12, 0.03, 0.04]
    rng_out = stale_returns(o2c, c2c, c2o, 1.0, mode="random")
    assert rng_out.iloc[0].tolist() == c2c.iloc[0].tolist()
    with pytest.raises(ValueError, match="unknown mode"):
        stale_returns(o2c, c2c, c2o, 0.1, mode="other")
