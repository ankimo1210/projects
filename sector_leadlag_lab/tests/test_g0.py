import json

import numpy as np
import pandas as pd
import pytest
from sector_leadlag.g0 import (
    PUBLISHED,
    choose,
    dividend_events,
    run_g0,
    split_events,
    zero_volume,
)


def _row(ar: float, passed: bool) -> dict:
    return {"original": {"ar": ar}, "pass": passed}


def test_the_passing_pairing_closest_to_the_papers_ar_is_chosen():
    assert choose({"same_date": _row(0.10, True), "lagged": _row(0.30, True)}) == "lagged"
    assert choose({"same_date": _row(0.20, True), "lagged": _row(0.24, False)}) == "same_date"
    assert choose({"same_date": _row(0.20, False), "lagged": _row(0.24, False)}) is None
    tie = PUBLISHED["ar"]
    assert choose({"same_date": _row(tie - 0.01, True), "lagged": _row(tie + 0.01, True)}) == (
        "same_date"
    )


DAYS = pd.bdate_range("2026-01-05", periods=4)


def test_zero_volume_days_and_stale_closes_are_counted(make_panel):
    close = pd.DataFrame({1: [100.0, 100.0, 101.0, 101.0]}, index=DAYS)
    volume = pd.DataFrame({1: [5.0, 0.0, 0.0, 5.0]}, index=DAYS)
    out = zero_volume(make_panel(close, close, volume=volume), (DAYS[0], DAYS[-1]))
    assert out["1"] == {"days": 4, "zero": 2, "share": 0.5, "stale": 0.5}


def test_an_unadjusted_split_is_flagged(make_panel):
    close = pd.DataFrame({"a": [500.0, 505.0, 101.0, 102.0], "b": [100.0] * 4}, index=DAYS)
    splits = pd.DataFrame({"a": [0.0, 0.0, 5.0, 0.0], "b": [0.0, 5.0, 0.0, 0.0]}, index=DAYS)
    out = split_events(make_panel(close, close, splits=splits), (DAYS[0], DAYS[-1]))
    assert out["events"] == 2 and out["flagged_count"] == 1
    assert out["flagged"][0]["name"] == "a" and out["flagged"][0]["c2o"] == pytest.approx(-0.8)


def test_dividends_bring_the_ex_date_gap_back_towards_zero(make_panel):
    close = pd.DataFrame({"a": [100.0, 98.0, 98.0, 98.0]}, index=DAYS)
    open_ = pd.DataFrame({"a": [100.0, 97.5, 98.0, 98.0]}, index=DAYS)
    dividends = pd.DataFrame({"a": [0.0, 2.5, 0.0, 0.0]}, index=DAYS)
    out = dividend_events(make_panel(open_, close, dividends=dividends), (DAYS[0], DAYS[-1]))
    assert out["events"] == 1
    assert out["mean_abs_c2o_with"] == pytest.approx(0.0)
    assert out["mean_abs_c2o_without"] == pytest.approx(0.025)


def test_g0_reproduces_the_decay_and_picks_a_pairing(decayed_world):
    out = run_g0(decayed_world, {})
    assert out["pass"] and out["selected"] in ("same_date", "lagged")
    chosen = out["variants"][out["selected"]]
    assert chosen["fit_a"]["p"] < 0.05 and chosen["b1"]["mean_ann"] < 0
    assert out["checks"]["names"]["with_prices"] == 34
    assert set(out["checks"]["etf_zero_volume"]) == {str(k) for k in range(1, 18)}
    assert len(out["checks"]["coverage"]["1"]) == 12  # 2015 to 2026
    assert np.isfinite(chosen["original"]["ar"])


def test_g0_reads_no_etf_value_after_b1(decayed_world):
    from dataclasses import replace

    from sector_leadlag.study import B2

    def scramble(frame: pd.DataFrame) -> pd.DataFrame:
        out = frame.copy()
        out.loc[B2[0] :] = 1.0
        return out

    etf = decayed_world.etf
    fields = ("open", "close", "adj_close", "volume")
    late = replace(etf, **{name: scramble(getattr(etf, name)) for name in fields})
    scrambled = replace(decayed_world, etf=late)
    same = [json.dumps(run_g0(world, {}), default=str) for world in (scrambled, decayed_world)]
    assert same[0] == same[1]
