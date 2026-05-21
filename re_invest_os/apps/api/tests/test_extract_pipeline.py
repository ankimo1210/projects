"""extract pipeline の E2E テスト。

LLM 呼び出しは monkeypatch でモック (CI に Ollama を要求しない)。
"""

from __future__ import annotations

from typing import Any

import pytest
from api.main import app
from api.services.llm_client import CallMeta, LLMResult
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _llm_result(data: dict[str, Any], prompt_id: str = "test:v1") -> LLMResult:
    return LLMResult(
        data=data,
        meta=CallMeta(
            provider="mock",
            model="mock",
            prompt_id=prompt_id,
            latency_ms=1,
            attempts=1,
            raw_response_snippet="(mocked)",
        ),
        warnings=[],
    )


@pytest.fixture
def mock_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """classify と brochure の chat_json をスタブ。"""
    from api.services.extractors import classify, property_brochure

    def fake_classify_chat(prompt, *, vars=None, model=None, timeout_s=60.0):
        return _llm_result(
            {
                "document_type": "property_brochure",
                "confidence": 0.95,
                "reason": "mocked",
            },
            prompt_id="classify_document:v1",
        )

    def fake_brochure_chat(prompt, *, vars=None, model=None, timeout_s=60.0):
        return _llm_result(
            {
                "property_name": "テストマンション",
                "address": "東京都新宿区西新宿1-2-3",
                "asking_price_yen": 39_800_000,
                "nearest_station": "新宿駅",
                "station_walk_min": 9,
                "exclusive_area_sqm": 38.4,
                "structure": "rc",
                "build_year_month": "2011-04",
                "gross_yield_pct": 4.37,
                "estimated_full_rent_monthly_yen": 145_000,
                "management_fee_monthly_yen": 12_000,
                "repair_reserve_monthly_yen": 8_000,
                "field_confidences": {
                    "asking_price_yen": 1.0,
                    "structure": 1.0,
                    "build_year_month": 1.0,
                },
                "inferred_fields": [],
            },
            prompt_id="property_brochure:v1",
        )

    monkeypatch.setattr(classify, "chat_json", fake_classify_chat)
    monkeypatch.setattr(property_brochure, "chat_json", fake_brochure_chat)


def test_extract_url_unsupported_host(client: TestClient) -> None:
    r = client.post("/extract/url", json={"url": "https://example.com/foo"})
    assert r.status_code == 400
    assert "許可リスト" in r.json()["detail"]


def test_extract_url_allowed_hosts_include_suumo(client: TestClient) -> None:
    """SUUMO が allowlist に含まれていることを確認 (URLエラーの内容で判別)。"""
    from api.services.extractors.source_url import ALLOWED_HOSTS

    assert "suumo.jp" in ALLOWED_HOSTS
    assert "www.suumo.jp" in ALLOWED_HOSTS


def test_extract_document_unsupported_content_type(client: TestClient) -> None:
    r = client.post(
        "/extract/document",
        files={"file": ("a.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 415


def test_extract_document_empty(client: TestClient) -> None:
    r = client.post(
        "/extract/document",
        files={"file": ("a.pdf", b"", "application/pdf")},
    )
    assert r.status_code == 422


def _minimal_pdf_with_text(text: str) -> bytes:
    """テキスト層つきの最小 PDF を生成 (pypdf テスト用)。"""
    import pypdf

    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=595, height=842)
    # 簡単のため固定文字列を流す: write side car
    # pypdf で content stream を直接書くのは面倒なので、PDF テスト fixture を別管理にする
    # ここでは reportlab があれば使う、無ければ skip
    try:
        import io

        from reportlab.pdfgen import canvas

        buf = io.BytesIO()
        c = canvas.Canvas(buf)
        for i, line in enumerate(text.split("\n")):
            c.drawString(50, 800 - i * 14, line)
        c.save()
        return buf.getvalue()
    except ImportError:
        pytest.skip("reportlab 未インストール — PDF E2E スキップ")


def test_extract_document_end_to_end(client: TestClient, mock_llm: None) -> None:
    """テキスト層つき PDF → 抽出 → assumptions 構築まで通る。"""
    text = (
        "物件概要書\n"
        "所在地: 東京都新宿区西新宿7-X-X\n"
        "価格: 3980万円\n"
        "構造: RC造\n"
        "築年月: 2011年4月\n"
        "専有面積: 38.4 sqm / 1LDK\n"
        "表面利回り: 4.37%\n"
        "管理費: 12000円/月\n"
    )
    pdf_bytes = _minimal_pdf_with_text(text)
    r = client.post(
        "/extract/document",
        files={"file": ("brochure.pdf", pdf_bytes, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source_type"] == "document"
    assert body["extracted"]["asking_price_yen"] == 39_800_000
    assert body["extracted"]["structure"] == "rc"
    assert body["assumptions"] is not None
    assert body["assumptions"]["property"]["purchase_price_yen"] == 39_800_000
    assert body["meta"]["engine_version"] == "0.1.0"
    assert body["meta"]["classification"]["document_type"] == "property_brochure"
    assert "classify_document" in body["meta"]["prompt_versions"]
    assert "property_brochure" in body["meta"]["prompt_versions"]


def test_extract_then_analyze(client: TestClient, mock_llm: None) -> None:
    """extract → analyze まで完走することの確認。"""
    text = "物件概要書\n価格: 3980万円\n構造: RC造\n築年月: 2011年4月\n専有面積: 38.4 sqm\n"
    pdf_bytes = _minimal_pdf_with_text(text)
    r = client.post(
        "/extract/document",
        files={"file": ("brochure.pdf", pdf_bytes, "application/pdf")},
    )
    assert r.status_code == 200
    assumptions = r.json()["assumptions"]
    assert assumptions is not None

    r2 = client.post("/analyze", json={"assumptions": assumptions})
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["analysis"]["kpi"]["cap_rate"] > 0
    assert "total" in body["score"]
