from __future__ import annotations

from optimal_execution.i18n import REQUIRED_KEYS, Translator, load_locale, validate_locales


def test_locale_key_sets_and_required_content_match() -> None:
    validate_locales()
    en = load_locale("en")
    ja = load_locale("ja")
    assert set(en) == set(ja)
    assert REQUIRED_KEYS <= set(en)


def test_translator_formats_and_preserves_strategy_ids() -> None:
    en = Translator("en")
    ja = Translator("ja")
    assert en.strategy("ac") == "Almgren–Chriss"
    assert "Almgren–Chriss" in ja.strategy("ac")
    assert ja.strategy("unknown_policy") == "unknown_policy"
    assert "1210" in ja(
        "profile_note_template",
        profile="quick",
        seed=1210,
        horizon=1800,
        inventory=60000,
        price=100,
    )


def test_japanese_report_content_is_structured_not_string_replacement() -> None:
    ja = load_locale("ja")
    joined = " ".join(ja.values())
    for phrase in ("市場インパクト", "実装ショートフォール", "板の回復力", "注文不均衡"):
        assert phrase in joined
