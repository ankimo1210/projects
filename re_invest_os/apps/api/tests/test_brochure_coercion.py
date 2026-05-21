"""PropertyBrochureExtraction の型強制テスト (LLM 不要)。"""

from __future__ import annotations

from api.services.extractors.property_brochure import (
    PropertyBrochureExtraction,
    _postprocess,
)


def test_coerce_string_price():
    """'39,800,000' のような文字列価格を int に。"""
    d = PropertyBrochureExtraction.model_validate({"asking_price_yen": "39,800,000"})
    assert d.asking_price_yen == 39_800_000


def test_coerce_float_to_int():
    d = PropertyBrochureExtraction.model_validate({"asking_price_yen": 39800000.0})
    assert d.asking_price_yen == 39_800_000


def test_coerce_structure_japanese():
    d = PropertyBrochureExtraction.model_validate({"structure": "RC造"})
    assert d.structure == "rc"
    d = PropertyBrochureExtraction.model_validate({"structure": "鉄筋コンクリート"})
    assert d.structure == "rc"
    d = PropertyBrochureExtraction.model_validate({"structure": "木造"})
    assert d.structure == "wood"


def test_coerce_inferred_fields_dict_to_list():
    """LLM が dict で返してきても list に。"""
    d = PropertyBrochureExtraction.model_validate(
        {"inferred_fields": {"price": "推定", "yield": "計算"}}
    )
    assert set(d.inferred_fields) == {"price", "yield"}


def test_coerce_field_confidences_list_to_dict():
    d = PropertyBrochureExtraction.model_validate(
        {"field_confidences": ["asking_price_yen", "structure"]}
    )
    assert d.field_confidences == {"asking_price_yen": 1.0, "structure": 1.0}


def test_postprocess_yield_scale():
    """6.2% が 0.062 で返ってきたら ×100 補正。"""
    d = PropertyBrochureExtraction(gross_yield_pct=0.062)
    fixed, notes = _postprocess(d)
    assert fixed.gross_yield_pct is not None
    assert abs(fixed.gross_yield_pct - 6.2) < 0.01
    assert len(notes) > 0  # 何らかのnoteがある


def test_postprocess_build_year_month_normalize():
    d = PropertyBrochureExtraction(build_year_month="2011/4")
    fixed, _ = _postprocess(d)
    assert fixed.build_year_month == "2011-04"


def test_extra_fields_ignored():
    """LLM が余計なキーを足してきても落ちない。"""
    d = PropertyBrochureExtraction.model_validate(
        {
            "asking_price_yen": 1000000,
            "unexpected_extra": "anything",
        }
    )
    assert d.asking_price_yen == 1_000_000
