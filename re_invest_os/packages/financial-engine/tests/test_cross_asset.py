"""クロスアセット比較のテスト。"""

from __future__ import annotations

from re_engine.cross_asset import (
    DEFAULT_BENCHMARKS,
    CrossAssetRequest,
    cross_asset_comparison,
)


def test_default_benchmarks_have_all_classes() -> None:
    classes = {b.asset_class for b in DEFAULT_BENCHMARKS}
    assert "world_equity" in classes
    assert "us_equity" in classes
    assert "jp_bonds" in classes
    assert "jpy_deposit" in classes


def test_premium_calculated_against_irr() -> None:
    req = CrossAssetRequest(re_after_tax_irr=0.04)
    res = cross_asset_comparison(req)
    # 米国株 6% - 不動産 4% = +2pt
    us = next(r for r in res.rows if r.asset_class == "us_equity")
    assert abs(us.premium_over_re_pt - 2.0) < 0.01


def test_negative_premium_when_re_outperforms() -> None:
    """不動産IRRが10% → 米国株6%との差は -4pt (不動産のほうが高い)。"""
    req = CrossAssetRequest(re_after_tax_irr=0.10)
    res = cross_asset_comparison(req)
    us = next(r for r in res.rows if r.asset_class == "us_equity")
    assert us.premium_over_re_pt < 0


def test_none_irr_treated_as_zero() -> None:
    """IRR算出不能 (None) のときは 0% として扱う。"""
    req = CrossAssetRequest(re_after_tax_irr=None)
    res = cross_asset_comparison(req)
    deposit = next(r for r in res.rows if r.asset_class == "jpy_deposit")
    # 預金 0.3% - 0% = +0.3pt
    assert abs(deposit.premium_over_re_pt - 0.3) < 0.01


def test_disclaimer_present() -> None:
    req = CrossAssetRequest(re_after_tax_irr=0.04)
    res = cross_asset_comparison(req)
    # 法務リスク回避のため免責が含まれる
    assert "推奨" in res.disclaimer
    assert "ユーザー" in res.disclaimer


def test_custom_benchmarks() -> None:
    from re_engine.cross_asset import AssetBenchmark

    custom = [
        AssetBenchmark(
            asset_class="world_equity",
            label_jp="グローバル株",
            expected_return_annual=0.07,
            liquidity="high",
            diversification="high",
            effort="low",
            leverage_risk=False,
            fx_risk=True,
        )
    ]
    req = CrossAssetRequest(re_after_tax_irr=0.04, benchmarks=custom)
    res = cross_asset_comparison(req)
    assert len(res.rows) == 1
    assert abs(res.rows[0].premium_over_re_pt - 3.0) < 0.01
