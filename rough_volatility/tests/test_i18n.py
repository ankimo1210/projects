from __future__ import annotations

from rough_volatility.i18n import (
    _CALLOUT_ANCHORS,
    _FIGURE_ANCHORS,
    _SECTION_ANCHORS,
    REQUIRED_KEYS,
    Translator,
    load_locale,
    validate_locales,
)
from rough_volatility.notebook import SECTIONS

from rough_volatility import report


def test_locale_key_sets_and_required_content_match() -> None:
    validate_locales()
    en = load_locale("en")
    ja = load_locale("ja")
    assert set(en) == set(ja)
    assert REQUIRED_KEYS <= set(en)


def test_translator_formats_placeholders() -> None:
    ja = Translator("ja")
    text = ja("report_subtitle", seed=1210, fingerprint="abcd1234")
    assert "1210" in text
    assert "abcd1234" in text


def test_japanese_chrome_is_actually_japanese() -> None:
    ja = load_locale("ja")
    joined = " ".join(ja.values())
    assert "ラフ" in joined  # "rough" appears in the JA title/subtitle


def test_anchor_tuples_stay_in_sync() -> None:
    assert _SECTION_ANCHORS == tuple(section.anchor for section in SECTIONS)
    assert _CALLOUT_ANCHORS == report._NARRATIVE_ANCHORS
    assert _FIGURE_ANCHORS == report.REPORT_FIGURE_ANCHORS


def test_ja_literature_catalog_is_complete_and_en_is_gated() -> None:
    from rough_volatility.literature import PRIOR_WORKS

    ja = load_locale("ja")
    en = load_locale("en")
    # JA carries the full literature prose; EN keeps the gate key empty until
    # the English edition is written, which omits the section from its report.
    assert ja["callout.prior-literature"]
    assert en["callout.prior-literature"] == ""
    fields = ("approach", "problem", "proposal", "findings", "future", "summary")
    for work in PRIOR_WORKS:
        for field in fields:
            assert ja[f"literature.{work.key}.{field}"], f"{work.key}.{field}"
