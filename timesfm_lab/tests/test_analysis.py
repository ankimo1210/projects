import numpy as np
import pandas as pd
import pytest
from timesfm_lab.analysis import (
    BASELINE_NAMES,
    contamination_table,
    head_to_head,
    selector_skill,
    selector_table,
)
from timesfm_lab.tfm import MODEL_KEY


def _frame(records):
    """records: (series_id, cutoff, model, mase)"""
    return pd.DataFrame(
        [
            {"dataset": "d", "series_id": s, "cutoff": c, "model": m, "mase": v, "exposure": e}
            for s, c, m, v, e in records
        ]
    )


def _full_window(series, cutoff, values, exposure="held out"):
    out = []
    for model, v in values.items():
        out.append((series, cutoff, model, v, exposure))
    return out


def test_selector_carries_the_previous_windows_winner_forward():
    rows = []
    # window 1: fourier_ols is best. window 2: the selector must pick fourier_ols.
    rows += _full_window("s", 100, {"naive": 5.0, "seasonal_naive": 4.0, "theta": 3.0,
                                    "ets": 2.0, "fourier_ols": 1.0, MODEL_KEY: 9.0})
    rows += _full_window("s", 200, {"naive": 9.0, "seasonal_naive": 8.0, "theta": 7.0,
                                    "ets": 6.0, "fourier_ols": 5.0, MODEL_KEY: 1.0})
    sel = selector_table(_frame(rows))
    assert len(sel) == 1  # the first window has no predecessor
    assert sel.iloc[0].picked == "fourier_ols"
    assert sel.iloc[0].walkforward == pytest.approx(5.0)
    assert sel.iloc[0].oracle == pytest.approx(5.0)


def test_oracle_is_never_worse_than_the_walk_forward_selector():
    rng = np.random.default_rng(0)
    rows = []
    for c in range(1, 9):
        vals = {b: float(rng.uniform(0.5, 3.0)) for b in BASELINE_NAMES}
        vals[MODEL_KEY] = float(rng.uniform(0.5, 3.0))
        rows += _full_window("s", 100 * c, vals)
    sel = selector_table(_frame(rows))
    assert (sel.oracle <= sel.walkforward + 1e-12).all()


def test_selector_skill_separates_the_oracle_from_what_a_selector_can_reach():
    # The winning baseline alternates, so last window's winner is this window's
    # loser -- exactly the case where the oracle is unreachable.
    rows = []
    for c in range(1, 9):
        lo, hi = (1.0, 3.0) if c % 2 else (3.0, 1.0)
        rows += _full_window("s", 100 * c, {"naive": 4.0, "seasonal_naive": 4.0, "theta": 4.0,
                                            "ets": lo, "fourier_ols": hi, MODEL_KEY: 2.0})
    sk = selector_skill(selector_table(_frame(rows)))
    assert sk["oracle_mean"] == pytest.approx(1.0)
    assert sk["walkforward_mean"] == pytest.approx(3.0)
    assert sk["match_rate"] == pytest.approx(0.0)
    # TimesFM at 2.0 sits exactly halfway between the reachable 3.0 and the
    # unreachable 1.0.
    assert sk["gap_closed"] == pytest.approx(0.5)


def test_head_to_head_win_rate_and_pairing():
    rows = []
    for c in range(1, 11):
        rows += _full_window("s", 100 * c, {"naive": 2.0, "seasonal_naive": 2.0, "theta": 2.0,
                                            "ets": 2.0, "fourier_ols": 2.0,
                                            MODEL_KEY: 1.0 if c <= 7 else 3.0})
    sel = selector_table(_frame(rows))
    h = head_to_head(sel, ["walkforward"]).iloc[0]
    # The first window of the series is dropped for want of a predecessor, so
    # windows 2..10 are scored and TimesFM wins the six with cutoff <= 700.
    assert h.n == 9
    assert h.timesfm_win_rate == pytest.approx(6 / 9)


def test_contamination_table_normalises_away_window_difficulty():
    # Two windows of very different absolute difficulty but identical *relative*
    # standing: the normalisation must make them equal.
    rows = []
    rows += _full_window("s", 100, {"naive": 10.0, "seasonal_naive": 10.0, "theta": 10.0,
                                    "ets": 10.0, "fourier_ols": 10.0, MODEL_KEY: 5.0},
                         exposure="in corpus")
    rows += _full_window("s", 200, {"naive": 1.0, "seasonal_naive": 1.0, "theta": 1.0,
                                    "ets": 1.0, "fourier_ols": 1.0, MODEL_KEY: 0.5},
                         exposure="past corpus")
    tab = contamination_table(_frame(rows))
    t = tab[tab.model == MODEL_KEY]
    assert set(np.round(t.rel.to_numpy(), 6)) == {0.5}
