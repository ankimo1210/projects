"""企業レベルの展開と、人件費経由の P/L 換算。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from labor_ai_quadrant.company import FINANCIAL_COLUMNS, company_frame, load_financials
from labor_ai_quadrant.config import Config
from labor_ai_quadrant.reference import load_reference


@pytest.fixture(scope="module")
def ref():
    return load_reference()


@pytest.fixture(scope="module")
def companies(ref):
    return company_frame(Config(), ref)


def test_every_universe_member_is_scored(ref, companies):
    assert len(companies) == len(ref.universe)
    assert companies[["shortage_score", "ai_score", "escape_potential"]].notna().all().all()


def test_scores_stay_within_bounds(companies):
    assert companies["shortage_score"].between(0, 100).all()
    assert companies["ai_score"].between(0, 100).all()
    assert companies["ai_substitutable_share_pct"].between(0, 100).all()


def test_tilts_do_not_collapse_onto_the_ceiling(ref):
    """企業 tilt を正規化前に当てているので、上限張り付きで差が消えないこと。

    正規化後に tilt を足す実装だと、首位業種の企業が全部 100 に張り付いて
    within-sector の差が消える。これがそのリグレッションテスト。
    """
    df = company_frame(Config(), ref)
    it = df[df["sector33"] == "情報・通信業"]
    assert it["ai_score"].nunique() > 1
    assert (it["ai_score"] == 100.0).sum() < len(it)


def test_labour_intensity_tilt_moves_the_shortage_axis(ref):
    df = company_frame(Config(), ref)
    same_sector = df[df["sector33"] == "小売業"]
    high = same_sector[same_sector["labor_intensity"] == "high"]["shortage_score"]
    mid = same_sector[same_sector["labor_intensity"] == "mid"]["shortage_score"]
    assert high.min() > mid.max()


def test_knowledge_tilt_moves_the_ai_axis(ref):
    df = company_frame(Config(), ref)
    same_sector = df[df["sector33"] == "サービス業"]
    high = same_sector[same_sector["knowledge_tilt"] == "high"]["ai_score"]
    low = same_sector[same_sector["knowledge_tilt"] == "low"]["ai_score"]
    assert high.min() > low.max()


def test_zero_tilt_points_reproduces_pure_sector_scores(ref):
    df = company_frame(Config(tilt_points=0.0), ref)
    for sector, group in df.groupby("sector33"):
        assert group["ai_score"].nunique() == 1, sector
        assert group["shortage_score"].nunique() == 1, sector


def _fake_financials(codes: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "revenue": [1000.0] * len(codes),
            "operating_profit": [100.0] * len(codes),
            "labor_cost": [300.0] * len(codes),
            "employees": [5000] * len(codes),
        },
        index=pd.Index(codes, name="code"),
    )


def test_pnl_layer_translates_relief_into_recovered_revenue(ref):
    """経路は AI → 人手不足の緩和 → 取り逃していた売上の回復 → 利益増。"""
    codes = list(ref.universe.index[:5])
    df = company_frame(Config(realization_rate=0.5), ref, financials=_fake_financials(codes))
    scored = df.loc[codes]

    # 限界利益率 = (営業利益 + 人件費) / 売上。人を増やさないので人件費は固定費。
    assert np.allclose(scored["contribution_margin"], (100.0 + 300.0) / 1000.0)
    closable = scored["closable_gap_pct"] / 100.0
    assert np.allclose(scored["recovered_revenue"], 1000.0 * closable)
    assert np.allclose(scored["expected_profit_gain"], 1000.0 * closable * 0.4)
    # 押上げ幅(pp) は 埋められる欠員 × 限界利益率 で、企業規模には依存しない。
    assert np.allclose(scored["op_margin_uplift_pp"], closable * 0.4 * 100.0)
    assert np.allclose(scored["op_uplift_pct"], 1000.0 * closable * 0.4 / 100.0 * 100.0)
    assert np.allclose(scored["labor_cost_ratio"], 0.3)
    assert np.allclose(scored["revenue_per_employee"], 0.2)


def test_closable_gap_is_capped_by_the_vacancy_rate(ref):
    """空いた労働は、足りていないぶんを超えては不足の緩和にならない。"""
    df = company_frame(Config(realization_rate=1.0), ref)
    assert (df["closable_gap_pct"] <= df["vacancy_rate_pct"] + 1e-9).all()
    assert (df["closable_gap_pct"] <= df["ai_freed_labor_pct"] + 1e-9).all()
    # 実現率 1.0 でも、AI代替割合(20-45%)は欠員率(0.3-4.1%)より大きいので上限は欠員率側。
    assert np.allclose(df["closable_gap_pct"], df["vacancy_rate_pct"])


def test_freed_labor_binds_when_ai_substitution_is_small(ref):
    """逆に代替割合が小さければ、欠員を埋めきれない側が上限になる。"""
    df = company_frame(Config(realization_rate=0.001), ref)
    assert np.allclose(df["closable_gap_pct"], df["ai_freed_labor_pct"])
    assert (df["closable_gap_pct"] < df["vacancy_rate_pct"]).all()


def test_companies_without_financials_get_nan_not_an_error(ref):
    codes = list(ref.universe.index[:3])
    df = company_frame(Config(), ref, financials=_fake_financials(codes))
    uncovered = df.drop(index=codes)
    assert uncovered["op_uplift_pct"].isna().all()


def test_non_positive_operating_profit_yields_nan_not_infinity(ref):
    codes = list(ref.universe.index[:2])
    fin = _fake_financials(codes)
    fin.loc[codes[0], "operating_profit"] = 0.0
    fin.loc[codes[1], "operating_profit"] = -50.0
    df = company_frame(Config(), ref, financials=fin)
    assert df.loc[codes, "op_uplift_pct"].isna().all()


def test_missing_financial_columns_raise(ref):
    bad = pd.DataFrame({"revenue": [1.0]}, index=pd.Index(["7203"], name="code"))
    with pytest.raises(ValueError, match="missing required columns"):
        company_frame(Config(), ref, financials=bad)


def test_load_financials_round_trip(tmp_path, ref):
    codes = list(ref.universe.index[:4])
    path = tmp_path / "fin.csv"
    _fake_financials(codes).reset_index().to_csv(path, index=False)
    loaded = load_financials(path)
    assert list(loaded.index) == codes
    assert set(FINANCIAL_COLUMNS).issubset(loaded.columns)


def test_load_financials_rejects_unknown_format(tmp_path):
    path = tmp_path / "fin.txt"
    path.write_text("nope", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported financials format"):
        load_financials(path)


def test_margin_uplift_is_not_hostage_to_a_thin_operating_profit():
    """営業利益で割る比率は、利益が薄い会社を分母の小ささだけで首位にする。

    TOPIX 全体では上位が単体営業利益 1億円未満の小型株で埋まり、900% のような値が出た。
    売上で割る pp 版は 人件費率 × AI代替割合 × 実現率 が上限なので、その暴れ方をしない。
    """
    import pandas as pd
    from labor_ai_quadrant.company import company_frame
    from labor_ai_quadrant.reference import load_reference

    ref = load_reference()
    codes = ref.universe.index[:2]
    thin, fat = codes[0], codes[1]
    financials = pd.DataFrame(
        {
            "revenue": [10_000.0, 10_000.0],
            "operating_profit": [1.0, 2_000.0],  # 同じ売上・人件費で利益だけ違う
            "labor_cost": [3_000.0, 3_000.0],
            "employees": [100.0, 100.0],
        },
        index=pd.Index([thin, fat], name="code"),
    )
    df = company_frame(ref=ref, financials=financials)

    # 利益の薄い会社は op_uplift_pct では桁違いに上に来る…
    assert df.loc[thin, "op_uplift_pct"] > 100 * df.loc[fat, "op_uplift_pct"]
    # …が pp 版では逆に下に来る。限界利益率 (営業利益+人件費)/売上 が薄いから。
    assert df.loc[thin, "op_margin_uplift_pp"] < df.loc[fat, "op_margin_uplift_pp"]
    assert df.loc[thin, "contribution_margin"] == pytest.approx(3_001.0 / 10_000.0)
    assert df.loc[fat, "contribution_margin"] == pytest.approx(5_000.0 / 10_000.0)


def test_margin_uplift_is_bounded_by_the_vacancy_rate():
    """押上げ幅(pp) = 埋められる欠員 × 限界利益率。限界利益率は1以下なので欠員率が天井。"""
    import pandas as pd
    from labor_ai_quadrant.company import company_frame
    from labor_ai_quadrant.reference import load_reference

    ref = load_reference()
    code = ref.universe.index[0]
    financials = pd.DataFrame(
        {"revenue": [1_000.0], "operating_profit": [100.0],
         "labor_cost": [400.0], "employees": [10.0]},
        index=pd.Index([code], name="code"),
    )
    df = company_frame(ref=ref, financials=financials)
    assert 0 < df.loc[code, "op_margin_uplift_pp"] <= df.loc[code, "vacancy_rate_pct"]


def test_contribution_margin_rejects_values_that_cannot_be_one():
    """人件費が売上を超える持株会社では限界利益率が1を超える。桁を壊すより落とす。"""
    import pandas as pd
    from labor_ai_quadrant.company import company_frame
    from labor_ai_quadrant.reference import load_reference

    ref = load_reference()
    holding, loss = ref.universe.index[0], ref.universe.index[1]
    financials = pd.DataFrame(
        {
            "revenue": [100.0, 1_000.0],
            "operating_profit": [10.0, -900.0],   # 持株会社 / 人件費を食い潰した赤字
            "labor_cost": [400.0, 100.0],
            "employees": [50.0, 50.0],
        },
        index=pd.Index([holding, loss], name="code"),
    )
    df = company_frame(ref=ref, financials=financials)
    assert df.loc[[holding, loss], "contribution_margin"].isna().all()
    assert df.loc[[holding, loss], "op_margin_uplift_pp"].isna().all()


def test_thin_parent_scope_is_flagged():
    """単体従業員が連結の20%未満なら、単体基準のP/Lは事業の実態を表さない。"""
    import pandas as pd
    from labor_ai_quadrant.company import (
        PARENT_SCOPE_FLAG,
        PARENT_SCOPE_FLAG_THRESHOLD,
        company_frame,
    )
    from labor_ai_quadrant.reference import load_reference

    ref = load_reference()
    box, real, unknown = ref.universe.index[0], ref.universe.index[1], ref.universe.index[2]
    financials = pd.DataFrame(
        {
            "revenue": [1_000.0] * 3,
            "operating_profit": [100.0] * 3,
            "labor_cost": [300.0] * 3,
            "employees": [100.0] * 3,
            "parent_employee_share": [0.02, 0.65, float("nan")],
        },
        index=pd.Index([box, real, unknown], name="code"),
    )
    df = company_frame(ref=ref, financials=financials)
    assert PARENT_SCOPE_FLAG_THRESHOLD == 0.20
    assert df.loc[box, "parent_scope_flag"] == PARENT_SCOPE_FLAG
    assert df.loc[real, "parent_scope_flag"] == ""
    # 比率が分からない行に ※ を立てると「空箱と判明した」ように読めるので立てない。
    assert df.loc[unknown, "parent_scope_flag"] == ""


def test_rankable_excludes_rows_the_parent_pnl_cannot_carry():
    """順位付けから外すのは、値が無い行と、値が論理的にあり得ない行の2つだけ。"""
    import pandas as pd
    from labor_ai_quadrant.quadrant import rankable

    df = pd.DataFrame(
        {
            "op_uplift_pct": [12.0, float("nan"), 40.0],
            "labor_cost_ratio": [0.30, 0.30, 1.33],
        },
        index=["ok", "loss_making", "holding_shell"],
    )
    assert rankable(df).tolist() == [True, False, False]


def test_rankable_is_a_no_op_without_a_pnl_layer():
    import pandas as pd
    from labor_ai_quadrant.quadrant import rankable

    df = pd.DataFrame({"escape_potential": [50.0, 60.0]}, index=["a", "b"])
    assert rankable(df).all()
