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
    """公表統計の向きの健全性チェック: 建設・陸運が最上位に来ること。

    建設は6指標のうち欠員率・短観DI・有効求人倍率の3つで首位なので、
    ここが崩れたら符号の向きかマッピングが壊れている。
    """
    df = shortage_axis(ref).sort_values("shortage_score", ascending=False)
    assert df.index[0] == "建設業"
    assert set(df.head(5).index) >= {"建設業", "陸運業"}


def test_employment_di_is_flipped_to_the_shortage_direction(ref):
    """短観DIは「過剰-不足」なので、反転して「高いほど不足」に揃っていること。"""
    di = ref.shortage["employment_di_shortage"]
    assert di["建設業"] > di["銀行業"]  # 建設 -59 → +59 / 銀行 -18 → +18
    assert (di > 0).all()


def test_ai_substitutable_share_is_a_weighted_average_of_potentials(ref):
    df = ai_axis(Config(), ref)
    potential = ref.occupations["ai_potential"]
    # 加重平均なので、必ず職業別ポテンシャルの最小・最大の内側に収まる。
    assert df["ai_exposure_gross_pct"].between(potential.min(), potential.max()).all()
    assert (df["ai_exposure_pct"] <= df["ai_exposure_gross_pct"] + 1e-9).all()


def test_clerical_occupations_carry_the_ai_axis(ref):
    """ILO の指数では事務系が最上位・現場系が最下位になっていること。"""
    pot = ref.occupations["ai_potential"]
    assert pot["clerk_general"] == pot.max()
    assert pot["construction"] == pot.min()
    assert pot["clerk_general"] > pot["service"] > pot["construction"]


def test_finance_and_information_top_the_ai_axis(ref):
    """事務・営業に寄った金融と、技術者に寄った情報通信が上位に来ること。"""
    df = ai_axis(Config(), ref).sort_values("ai_score", ascending=False)
    assert set(df.head(6).index) >= {"その他金融業", "銀行業", "情報・通信業", "卸売業"}
    assert df["ai_score"].idxmin() == "水産・農林業"


def test_the_four_finance_sectors_share_one_occupation_mix(ref):
    """労働力調査は金融業，保険業を割らないので、4業種のAI軸は規制ドラッグでしか動かない。

    仕様として明示しておく。ここが落ちたら、より細かい産業分類に差し替えたということ。
    """
    finance = ["銀行業", "証券、商品先物取引業", "保険業", "その他金融業"]
    assert ref.mix.loc[finance].nunique().max() == 1
    gross = ai_axis(Config(), ref).loc[finance, "ai_exposure_gross_pct"]
    assert gross.nunique() == 1


def test_the_framework_core_tension_holds(ref):
    """建設と陸運は「人手不足は最深刻だがAIでは解けない」象限に落ちること。

    この2つが右上に来てしまう場合、AI代替ポテンシャルの設定か職業構成が壊れている。
    """
    df = sector_frame(Config(), ref)
    assert df.loc["建設業", "quadrant"] == Q_CONSTRAINED
    assert df.loc["陸運業", "quadrant"] == Q_CONSTRAINED
    assert df.loc["情報・通信業", "quadrant"] == Q_ESCAPE
    # 銀行は公表統計では最も人手不足でない（短観DI -18、欠員率0.4%）ので左上に落ちる。
    assert df.loc["銀行業", "quadrant"] == Q_MARGIN
    assert df.loc["銀行業", "shortage_score"] == df["shortage_score"].min()


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
