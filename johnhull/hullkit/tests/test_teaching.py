"""Tests for hullkit.teaching markdown scaffolds."""

from hullkit import teaching


def test_scaffold_has_three_labelled_lines():
    md = teaching.scaffold("core idea", "why it holds", "where it's used")
    assert "**核心**" in md
    assert "**直感**" in md
    assert "**実務**" in md
    # blockquote on every line so it renders as one box
    assert all(line.startswith(">") for line in md.splitlines())
    # three labelled lines joined by <br> hard breaks
    assert md.count("<br>") == 2


def test_practice_box_has_title_and_body():
    md = teaching.practice_box("マーケットメイク", "建値して動的ヘッジ")
    assert "実務での出番 — マーケットメイク" in md
    assert "建値して動的ヘッジ" in md
    assert all(line.startswith(">") for line in md.splitlines())


def test_caption_is_italic_reading_guide():
    md = teaching.caption("満期直前に段差が立つ")
    assert md.startswith("*図の読み方")
    assert md.endswith("*")
