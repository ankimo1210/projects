from __future__ import annotations

from rough_volatility.i18n import REQUIRED_KEYS, Translator, load_locale, validate_locales


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
