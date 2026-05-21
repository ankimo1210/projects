"""prompt loader のテスト。"""

from __future__ import annotations

from api.services import prompts


def test_load_classify_document():
    p = prompts.load("classify_document")
    assert p.name == "classify_document"
    assert p.version == "v1"
    assert "不動産投資資料を分類" in p.system
    assert "{{document_text}}" in p.user_template


def test_load_property_brochure():
    p = prompts.load("property_brochure")
    # バージョンは常に最新 (v4 以降で更新される)
    assert p.version >= "v4"
    assert "テンプレート" in p.system or "埋め" in p.system


def test_render_user():
    p = prompts.load("classify_document")
    rendered = p.render_user(document_text="価格 3980万円")
    assert "{{document_text}}" not in rendered
    assert "価格 3980万円" in rendered


def test_all_versions_contains_known():
    versions = prompts.all_versions()
    assert versions["classify_document"] == "v1"
    assert versions["property_brochure"] >= "v4"


def test_output_schema_for_classify():
    p = prompts.load("classify_document")
    assert p.output_schema is not None
    assert p.output_schema.get("type") == "object"
    enum_vals = p.output_schema["properties"]["document_type"]["enum"]
    assert "property_brochure" in enum_vals


def test_unknown_prompt_raises():
    import pytest

    with pytest.raises(KeyError):
        prompts.load("nonexistent_prompt")
