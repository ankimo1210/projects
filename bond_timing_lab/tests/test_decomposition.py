import numpy as np
import pandas as pd
import pytest
from bond_timing.backtest import Forecasts
from bond_timing.decomposition import MONTHLY_SETTINGS, SETTINGS, monthly_reading, r2_table


def test_r2_table_scores_each_maturity_and_the_average():
    index = pd.period_range("1980-01", "1995-12", freq="M")
    rng = np.random.default_rng(1)
    targets = pd.DataFrame(
        {2: rng.normal(size=len(index)), 3: rng.normal(size=len(index))}, index=index
    )
    decisions = pd.period_range("1990-01", "1993-12", freq="M")
    perfect = Forecasts({"ols_p": targets.reindex(decisions).set_axis([0, 1], axis=1)}, {})
    assert r2_table(targets, perfect, decisions, complete=True) == {
        "ols_p": {"2": 1.0, "3": 1.0, "avg": 1.0}
    }


def test_settings_add_one_rule_at_a_time():
    rules = {name: setting[2] for name, setting in SETTINGS.items()}
    assert not any(vars(rules["V0_gsw"]).values())
    assert rules["V1"].complete_targets and not rules["V1"].embargo
    assert rules["V2"].embargo and rules["V2"].in_window and not rules["V2"].real_time_macro
    assert all(vars(rules["V3"]).values())
    assert SETTINGS["V3"][1] == "realtime" and SETTINGS["V2"][1] == "final"


def test_monthly_settings_mirror_the_annual_ones():
    assert MONTHLY_SETTINGS["V0m_liuwu"] == SETTINGS["V0_liuwu"]
    assert MONTHLY_SETTINGS["V0m_gsw"] == SETTINGS["V0_gsw"]
    assert MONTHLY_SETTINGS["V1m_gsw"] == SETTINGS["V1"]
    assert MONTHLY_SETTINGS["V1m_liuwu"] == ("liuwu", *SETTINGS["V1"][1:])


def nn(avg: float) -> dict:
    return {"nn_fm": {"avg": avg}}


@pytest.mark.parametrize(
    ("v0m", "v1m", "reading"),
    [
        (0.25, 0.05, "leak_explains_paper"),
        (0.25, 0.20, "reproduced_without_leak"),
        (-0.10, -0.30, "leak_partial"),
        (0.05, 0.00, "leak_not_explaining"),
    ],
)
def test_monthly_reading_follows_prereg_section_5(v0m, v1m, reading):
    out = monthly_reading({"V0m_liuwu": nn(v0m), "V1m_liuwu": nn(v1m)}, {"V0_liuwu": nn(-0.14)})
    assert out["reading"] == reading
    assert out["leak_gap"] == pytest.approx(v0m - v1m)
    assert out["dilution"] == pytest.approx(v0m + 0.14)
    assert out["dilution_large"] == (v0m + 0.14 >= 0.10)
