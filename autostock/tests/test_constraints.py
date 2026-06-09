import pandas as pd

import prepare


def _frame(rows, cols=("A", "B", "C")):
    idx = pd.date_range("2020-01-01", periods=len(rows), freq="D")
    return pd.DataFrame(rows, index=idx, columns=list(cols))


def test_per_name_cap():
    w = _frame([[0.8, -0.7, 0.0]])
    tradeable = _frame([[True, True, True]])
    out = prepare.enforce_constraints(w, tradeable)
    # clipped to +/-0.5; gross = 1.0 == MAX_GROSS so no scaling
    assert out.iloc[0]["A"] == 0.5
    assert out.iloc[0]["B"] == -0.5


def test_gross_scaled_down():
    w = _frame([[0.5, 0.5, 0.5]])
    tradeable = _frame([[True, True, True]])
    out = prepare.enforce_constraints(w, tradeable)
    # gross 1.5 -> scaled by 1/1.5 -> each 1/3; gross now 1.0
    assert abs(out.iloc[0]["A"] - 1.0 / 3.0) < 1e-9
    assert abs(out.iloc[0].abs().sum() - 1.0) < 1e-9


def test_undersized_gross_not_levered_up():
    w = _frame([[0.1, 0.0, 0.0]])
    tradeable = _frame([[True, True, True]])
    out = prepare.enforce_constraints(w, tradeable)
    assert out.iloc[0]["A"] == 0.1  # never scaled up


def test_missing_asset_zeroed():
    w = _frame([[0.4, 0.4, 0.4]])
    tradeable = _frame([[True, False, True]])  # B not tradeable
    out = prepare.enforce_constraints(w, tradeable)
    assert out.iloc[0]["B"] == 0.0
