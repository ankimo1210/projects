"""Label-layer tests: forward alignment, the no-future-fabrication tail, and the
explicit availability date used for embargo.

Labels are forward-looking *by design*. The contract is that the future-unknown
tail stays NaN, the value matches the realized forward return exactly, and each
label declares when it becomes known (``t + horizon``).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from irp import labels as L


def _series(vals):
    idx = pd.bdate_range("2020-01-01", periods=len(vals))
    return pd.Series(vals, index=idx, dtype="float64")


def test_forward_return_is_realized_future_and_tail_is_nan():
    s = _series([100, 110, 121])
    fr = L.forward_return(s, horizon=1)
    assert fr.iloc[0] == pytest.approx(0.1)  # 110/100 - 1
    assert fr.iloc[1] == pytest.approx(0.1)  # 121/110 - 1
    assert np.isnan(fr.iloc[2])  # no future -> NaN, never fabricated


def test_forward_return_horizon_two():
    s = _series([100, 110, 121, 133.1])
    fr = L.forward_return(s, horizon=2)
    assert fr.iloc[0] == pytest.approx(121 / 100 - 1)
    assert fr.iloc[1] == pytest.approx(133.1 / 110 - 1)
    assert fr.iloc[2:].isna().all()  # last `horizon` rows NaN
    with pytest.raises(ValueError):
        L.forward_return(s, horizon=0)


def test_label_available_date_is_t_plus_horizon():
    idx = pd.bdate_range("2020-01-01", periods=5)
    avail = L.label_available_date(idx, horizon=2)
    assert avail.iloc[0] == idx[2]
    assert avail.iloc[1] == idx[3]
    assert avail.iloc[3:].isna().all()  # last `horizon` have no known date yet


def test_binary_and_ternary_labels_preserve_nan():
    fr = _series([0.10, -0.05, np.nan])
    b = L.binary_label(fr, threshold=0.0)
    assert b.iloc[0] == 1.0 and b.iloc[1] == 0.0 and np.isnan(b.iloc[2])
    t = L.ternary_label(_series([0.10, 0.0, -0.10]), upper=0.05)
    assert t.tolist() == [1.0, 0.0, -1.0]


def test_triple_barrier_first_touch():
    # up first
    up = L.triple_barrier(_series([100, 106, 100, 100]), horizon=3, up=0.05, down=0.05)
    assert up["label"].iloc[0] == 1.0 and up["touch_offset"].iloc[0] == 1
    # down first
    dn = L.triple_barrier(_series([100, 94, 100, 100]), horizon=3, up=0.05, down=0.05)
    assert dn["label"].iloc[0] == -1.0 and dn["touch_offset"].iloc[0] == 1
    # neither barrier hit within horizon -> time barrier (0), tail NaN
    tb = L.triple_barrier(_series([100, 101, 102, 103]), horizon=3, up=0.05, down=0.05)
    assert tb["label"].iloc[0] == 0.0 and tb["touch_offset"].iloc[0] == 3
    assert np.isnan(tb["label"].iloc[1])  # only 2 future bars < horizon -> NaN


def test_forward_return_panel_aligns_per_column():
    idx = pd.bdate_range("2020-01-01", periods=3)
    df = pd.DataFrame({"A": [100, 110, 121], "B": [50, 55, 60.5]}, index=idx)
    fr = L.forward_return(df, horizon=1)
    assert fr["A"].iloc[0] == pytest.approx(0.1)
    assert fr["B"].iloc[0] == pytest.approx(0.1)
    assert fr.iloc[2].isna().all()
