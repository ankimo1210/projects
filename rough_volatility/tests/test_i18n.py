from __future__ import annotations

from rough_volatility import report
from rough_volatility.i18n import (
    REQUIRED_KEYS,
    Translator,
    _CALLOUT_ANCHORS,
    _FIGURE_ANCHORS,
    _SECTION_ANCHORS,
    load_locale,
    validate_locales,
)
from rough_volatility.notebook import SECTIONS


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
