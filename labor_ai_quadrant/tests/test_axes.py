"""2軸のスコアリングと象限分割。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from labor_ai_quadrant.axes import ai_axis, rescale_0_100, sector_frame, shortage_axis
from labor_ai_quadrant.config import Q_CONSTRAINED, Q_ESCAPE, Q_MARGIN, Config
from labor_ai_quadrant.quadrant import assign_quadrants, escape_potential, thresholds
from labor_ai_quadrant.reference import load_reference


@pytest.fixture(scope="module")
def ref():
    return load_reference()


def test_rescale_maps_endpoints_to_0_and_100():
    s = pd.Series([1.0, 3.0, 5.0])
    out = rescale_0_100(s)
    assert out.iloc[0] == 0.0
    assert out.iloc[-1] == 100.0


def test_rescale_of_a_constant_series_is_midpoint():
    out = rescale_0_100(pd.Series([7.0, 7.0, 7.0]))
    assert (out == 50.0).all()


def test_shortage_scores_span_the_full_range(ref):
    df = shortage_axis(ref)
    assert df["shortage_score"].between(0, 100).all()
    assert df["shortage_score"].min() == 0.0
    assert df["shortage_score"].max() == 100.0


def test_construction_and_land_transport_are_the_most_labour_short(ref):
    """公表統計の向きの健全性チェック: 建設・陸運が最上位に来ること。"""
    df = shortage_axis(ref).sort_values("shortage_score", ascending=False)
    assert set(df.head(3).index) >= {"建設業", "陸運業"}


def test_ai_substitutable_share_is_a_weighted_average_of_potentials(ref):
    cfg = Config()
    df = ai_axis(cfg, ref)
    potential = (
        ref.occupations["llm_potential"] * (1 - cfg.robotics_weight)
        + ref.occupations["phys_potential"] * cfg.robotics_weight
    )
    # 加重平均なので、必ず職業別ポテンシャルの最小・最大の内側に収まる。
    assert df["ai_gross_share_pct"].between(potential.min(), potential.max()).all()
    assert (df["ai_substitutable_share_pct"] <= df["ai_gross_share_pct"] + 1e-9).all()


def test_information_services_tops_the_ai_axis(ref):
    df = ai_axis(Config(), ref)
    assert df["ai_score"].idxmax() == "情報・通信業"


def test_robotics_weight_shifts_physical_sectors_up(ref):
    llm_only = ai_axis(Config(robotics_weight=0.0), ref)["ai_substitutable_share_pct"]
    with_robots = ai_axis(Config(robotics_weight=0.8), ref)["ai_substitutable_share_pct"]
    # 倉庫・陸運は物理自動化の重みを上げると代替可能性が上がる。
    assert with_robots["倉庫・運輸関連業"] > llm_only["倉庫・運輸関連業"]
    assert with_robots["陸運業"] > llm_only["陸運業"]
    # 銀行は逆に下がる（LLM主体の業種）。
    assert with_robots["銀行業"] < llm_only["銀行業"]


def test_the_framework_core_tension_holds(ref):
    """建設と陸運は「人手不足は最深刻だがAIでは解けない」象限に落ちること。

    この2つが右上に来てしまう場合、AI代替ポテンシャルの設定か職業構成が壊れている。
    """
    df = sector_frame(Config(), ref)
    assert df.loc["建設業", "quadrant"] == Q_CONSTRAINED
    assert df.loc["陸運業", "quadrant"] == Q_CONSTRAINED
    assert df.loc["情報・通信業", "quadrant"] == Q_ESCAPE
    # 銀行は人手不足ではないがAI余地が大きい = 左上
    assert df.loc["銀行業", "quadrant"] == Q_MARGIN


def test_escape_potential_is_the_geometric_mean():
    shortage = pd.Series([100.0, 100.0, 0.0])
    ai = pd.Series([100.0, 0.0, 100.0])
    out = escape_potential(shortage, ai)
    assert out.tolist() == [100.0, 0.0, 0.0]


def test_escape_potential_penalises_one_sided_extremes():
    """算術平均なら同点になる2点が、幾何平均では明確に差がつくこと。"""
    balanced = escape_potential(pd.Series([60.0]), pd.Series([60.0])).iloc[0]
    lopsided = escape_potential(pd.Series([100.0]), pd.Series([20.0])).iloc[0]
    assert balanced > lopsided


def test_median_split_puts_roughly_a_quarter_in_each_quadrant(ref):
    df = sector_frame(Config(threshold_method="median"), ref)
    counts = df["quadrant"].value_counts()
    assert counts.max() <= len(df) * 0.45


def test_values_on_the_threshold_count_as_the_low_side():
    shortage = pd.Series([50.0, 60.0], index=["on", "above"])
    ai = pd.Series([50.0, 60.0], index=["on", "above"])
    cfg = Config(threshold_method="fixed", fixed_threshold=50.0)
    out = assign_quadrants(shortage, ai, cfg)
    assert out["on"] != Q_ESCAPE
    assert out["above"] == Q_ESCAPE


def test_fixed_thresholds_are_returned_verbatim():
    cfg = Config(threshold_method="fixed", fixed_threshold=42.0)
    x, y = thresholds(pd.Series([1.0, 99.0]), pd.Series([1.0, 99.0]), cfg)
    assert (x, y) == (42.0, 42.0)


def test_sector_frame_is_sorted_by_escape_potential(ref):
    df = sector_frame(Config(), ref)
    assert np.all(np.diff(df["escape_potential"].to_numpy()) <= 1e-9)
