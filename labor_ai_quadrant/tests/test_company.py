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


def test_pnl_layer_computes_uplift(ref):
    codes = list(ref.universe.index[:5])
    df = company_frame(Config(realization_rate=0.5), ref, financials=_fake_financials(codes))
    scored = df.loc[codes]
    expected = 300.0 * (scored["ai_substitutable_share_pct"] / 100.0) * 0.5 / 100.0 * 100.0
    assert np.allclose(scored["op_uplift_pct"], expected)
    assert np.allclose(scored["labor_cost_ratio"], 0.3)
    assert np.allclose(scored["revenue_per_employee"], 0.2)


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
