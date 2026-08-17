"""静的レポート（自己完結SVG版）。"""

from __future__ import annotations

import re

import pytest
from labor_ai_quadrant.axes import sector_frame
from labor_ai_quadrant.config import SCENARIOS, Config
from labor_ai_quadrant.report_static import (
    LABEL_SLOTS,
    B,
    L,
    R,
    T,
    _label_targets,
    _place_labels,
    build_static_report,
    px,
    py,
    render,
)


@pytest.fixture(scope="module")
def sectors():
    return sector_frame(Config())


def test_axis_mapping_spans_the_plot_box():
    assert px(0) == L
    assert px(100) == R
    assert py(0) == B
    assert py(100) == T


def test_labels_cover_the_leaders_and_both_extremes(sectors):
    targets = _label_targets(sectors)
    # 建設業・陸運業は「人手不足は最大だがAIでは解けない」側の代表なので、
    # マップ上に必ず名前が出ること。これが出ないと図が主張を運べない。
    assert {"建設業", "情報・通信業", "銀行業"} <= targets
    # 銀行業は人手不足スコアの下端、水産・農林業はAI軸の下端として必ず入る。
    assert {"銀行業", "水産・農林業"} <= targets
    assert len(targets) <= 12


def test_every_labelled_point_gets_a_slot(sectors):
    placed = _place_labels(sectors)
    assert set(placed) == _label_targets(sectors)
    assert all(slot in LABEL_SLOTS for slot in placed.values())


def test_labels_do_not_overlap_each_other(sectors):
    """重なり判定は生成側と同じ矩形近似で行う。回帰したらここで落ちる。"""
    placed = _place_labels(sectors)
    boxes = []
    for name, (_anchor, dx, dy) in placed.items():
        row = sectors.loc[name]
        boxes.append((name, px(row["shortage_score"]) + dx, py(row["ai_score"]) + dy, len(name) * 6.4))

    for i, (n1, x1, y1, h1) in enumerate(boxes):
        for n2, x2, y2, h2 in boxes[i + 1 :]:
            overlapping = abs(y1 - y2) < 15 and abs(x1 - x2) < h1 + h2
            assert not overlapping, f"{n1} と {n2} のラベルが重なっている"


def test_static_report_is_far_smaller_than_the_plotly_one():
    doc = render()
    # 自己完結だがプロットライブラリを積まないので、共有できるサイズに収まること。
    assert len(doc.encode("utf-8")) < 200_000
    assert "<svg" in doc
    assert "plotly" not in doc.lower()


def test_static_report_loads_nothing_at_view_time():
    doc = render()
    assert "<script" not in doc
    assert "<link " not in doc
    assert "http://" not in doc


def test_every_colour_is_declared_on_bare_root():
    """テーマトークンが :root だけに無い状態を防ぐ。

    media query や [data-theme] の中でしか定義されていない色があると、
    テーマ未指定（system）の閲覧者にだけ壊れて見える。
    """
    doc = render()
    bare_root = doc.split(":root{", 1)[1].split("}", 1)[0]
    declared = set(re.findall(r"(--[a-z0-9-]+):", bare_root))
    used = set(re.findall(r"var\((--[a-z0-9-]+)\)", doc))
    assert used <= declared, f"bare :root で未定義のトークン: {sorted(used - declared)}"


def test_both_theme_scopes_are_present():
    doc = render()
    assert '@media (prefers-color-scheme: dark)' in doc
    assert ':root:not([data-theme="light"])' in doc
    assert ':root[data-theme="dark"]' in doc


def test_full_document_and_fragment_shapes_differ():
    full = render()
    fragment = render(fragment=True)
    assert full.startswith("<!doctype html>")
    assert not fragment.startswith("<!doctype")
    assert fragment.startswith("<title>")
    for doc in (full, fragment):
        assert "<title>" in doc


def test_scenario_changes_the_rendered_numbers():
    base = render(SCENARIOS["base"])
    conservative = render(SCENARIOS["conservative_adoption"])
    assert base != conservative


def test_build_static_report_writes_the_file(tmp_path):
    out = build_static_report(tmp_path / "sub" / "r.html")
    assert out.exists()
    assert out.read_text(encoding="utf-8").startswith("<!doctype html>")


def test_cli_build_defaults_to_the_static_format(tmp_path):
    from labor_ai_quadrant.cli import main

    out = tmp_path / "r.html"
    assert main(["build", "--out", str(out)]) == 0
    assert out.stat().st_size < 200_000


def _financials_for(codes, **overrides):
    """A financials frame covering ``codes``; overrides replace one row."""
    import pandas as pd

    frame = pd.DataFrame(
        {
            "revenue": 100_000.0,
            "operating_profit": 10_000.0,
            "labor_cost": 30_000.0,
            "employees": 1_000.0,
        },
        index=pd.Index(list(codes), name="code"),
    )
    for code, row in overrides.items():
        for column, value in row.items():
            frame.loc[code, column] = value
    return frame


def test_static_report_carries_the_pnl_columns_when_financials_are_given():
    """静的版が --financials を黙って捨てていた（interactive 限定だった）。"""
    from labor_ai_quadrant.company import company_frame
    from labor_ai_quadrant.reference import load_reference

    codes = load_reference().universe.index
    doc = render(financials=_financials_for(codes))
    assert "営業利益率の押上げ幅（pp）順" in doc
    assert "営業利益押上げ余地%" in doc
    # 押上げは「売上回復 × 限界利益率」なので、欠員率と限界利益率が並んでいること。
    assert "欠員率" in doc
    assert "限界利益率" in doc
    assert "回復売上(億)" in doc
    assert company_frame(Config()).shape[0] > 0  # ユニバースが空でないことの確認

    plain = render()
    assert "脱出ポテンシャル" in plain
    assert "営業利益押上げ余地%" not in plain


def test_static_report_shows_missing_pnl_as_a_dash_not_zero():
    """0埋めすると「人件費ゼロの会社」が上位に来る。欠損は欠損のまま出す。"""
    from labor_ai_quadrant.reference import load_reference

    codes = load_reference().universe.index
    financials = _financials_for(codes)
    financials["revenue"] = float("nan")  # 人件費率が全社 NaN になる
    doc = render(financials=financials)
    assert "—" in doc
    assert "nan" not in doc.lower()
