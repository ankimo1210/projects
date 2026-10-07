"""Hull §35.5 temperature units and independent weather cash replication."""

import numpy as np
import pytest
from hullkit import _commodity_foundations as c


def test_source_temperature_and_capped_hdd_contract():
    a = c.degree_days_from_extremes([68], [44])
    assert [a["average"][0], a["hdd"], a["cdd"]] == pytest.approx([56, 9, 0])
    contract = c.index_call_cash(820, 700, 10000, cap=1500000)
    assert contract["gross"] == pytest.approx(1200000)
    assert contract["upper_strike"] == pytest.approx(850)
    assert c.index_call_cash(900, 700, 10000, cap=1500000)["gross"] == pytest.approx(1500000)


def test_independent_daily_budget_and_capped_call_spread():
    highs = np.array([68, 80, 60, 72])
    lows = np.array([44, 60, 30, 58])
    daily = [(h + l) / 2 for h, l in zip(highs, lows, strict=True)]
    result = c.degree_days_from_extremes(highs, lows)
    hdd = sum(65 - x for x in daily if x < 65)
    cdd = sum(x - 65 for x in daily if x > 65)
    assert [result["hdd"], result["cdd"]] == pytest.approx([hdd, cdd])
    assert np.maximum(65 - result["average"], 0) * np.maximum(
        result["average"] - 65, 0
    ) == pytest.approx(np.zeros(4))
    totals = np.array([0, 699, 700, 701, 820, 850, 900])
    expected = 10000 * (np.maximum(totals - 700, 0) - np.maximum(totals - 850, 0))
    client = c.index_call_cash(totals, 700, 10000, cap=1500000, premium=250000)
    seller = c.index_call_cash(totals, 700, 10000, cap=1500000, premium=250000, side="short")
    assert client["gross"] == pytest.approx(expected)
    assert client["net"] + seller["net"] == pytest.approx(np.zeros(len(totals)))
    cel = c.degree_days_from_extremes(
        (highs - 32) * 5 / 9, (lows - 32) * 5 / 9, base=(65 - 32) * 5 / 9
    )
    assert [cel["hdd"], cel["cdd"]] == pytest.approx(np.array([hdd, cdd]) * 5 / 9)
    assert c.index_call_cash(cel["hdd"], 0, 10000 * 9 / 5)["gross"] == pytest.approx(
        c.index_call_cash(hdd, 0, 10000)["gross"]
    )
