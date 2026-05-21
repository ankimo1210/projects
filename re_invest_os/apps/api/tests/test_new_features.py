"""新機能の回帰テスト: レントロール・completeness_score・critique・history。

LLM 呼び出しは monkeypatch でモック。
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


def _llm(data: dict[str, Any], prompt_id: str = "test:v1") -> LLMResult:
    return LLMResult(
        data=data,
        meta=CallMeta(provider="mock", model="mock", prompt_id=prompt_id, latency_ms=1),
        warnings=[],
    )


# ─── completeness_score ───────────────────────────────────


def test_completeness_score_full(monkeypatch, client):
    """全必須フィールド揃い → completeness 100%。"""
    from api.services.extractors import classify, property_brochure

    monkeypatch.setattr(
        classify,
        "chat_json",
        lambda *a, **kw: _llm(
            {"document_type": "property_brochure", "confidence": 0.95, "reason": "mock"},
            "classify_document:v1",
        ),
    )
    monkeypatch.setattr(
        property_brochure,
        "chat_json",
        lambda *a, **kw: _llm(
            {
                "asking_price_yen": 39_800_000,
                "structure": "rc",
                "build_year_month": "2011-04",
                "exclusive_area_sqm": 38.4,
                "gross_yield_pct": 4.37,
                "field_confidences": {},
                "inferred_fields": [],
            }
        ),
    )

    from api.main import _build_response

    resp = _build_response(
        source_type="document", source_ref="test.pdf", text="dummy", extra_warnings=[]
    )
    assert resp.meta.completeness_score == 100.0


def test_completeness_score_partial(monkeypatch, client):
    """price だけ → 20%。"""
    from api.services.extractors import classify, property_brochure

    monkeypatch.setattr(
        classify,
        "chat_json",
        lambda *a, **kw: _llm(
            {"document_type": "property_brochure", "confidence": 0.9, "reason": "mock"},
        ),
    )
    monkeypatch.setattr(
        property_brochure,
        "chat_json",
        lambda *a, **kw: _llm(
            {
                "asking_price_yen": 30_000_000,
                "field_confidences": {},
                "inferred_fields": [],
            }
        ),
    )

    from api.main import _build_response

    resp = _build_response(source_type="document", source_ref=None, text="dummy", extra_warnings=[])
    assert resp.meta.completeness_score == 20.0


# ─── rent_roll 分岐 ───────────────────────────────────────


def test_rent_roll_dispatch(monkeypatch, client):
    """classify=rent_roll の場合 rent_roll フィールドが埋まる。"""
    from api.services.extractors import classify, property_brochure, rent_roll

    monkeypatch.setattr(
        classify,
        "chat_json",
        lambda *a, **kw: _llm(
            {"document_type": "rent_roll", "confidence": 0.95, "reason": "mock"},
        ),
    )
    monkeypatch.setattr(
        property_brochure,
        "chat_json",
        lambda *a, **kw: _llm(
            {
                "field_confidences": {},
                "inferred_fields": [],
            }
        ),
    )
    monkeypatch.setattr(
        rent_roll,
        "chat_json",
        lambda *a, **kw: _llm(
            {
                "units": [{"unit_number": "101", "contract_rent_yen": 72000, "is_occupied": True}],
                "rent_roll_date": None,
                "total_monthly_rent_yen": None,
                "occupancy_rate": None,
                "raw_table_markdown": None,
                "field_confidences": {},
            }
        ),
    )

    from api.main import _build_response

    resp = _build_response(source_type="document", source_ref=None, text="dummy", extra_warnings=[])
    assert resp.rent_roll is not None
    assert len(resp.rent_roll["units"]) == 1
    # compute_totals が機能しているか
    assert resp.rent_roll["total_monthly_rent_yen"] == 72000


# ─── rent_roll extractor 単体 ──────────────────────────────


def test_rent_roll_compute_totals():
    """with_computed_totals が units から total / occupancy_rate を計算。"""
    from api.services.extractors.rent_roll import RentRollExtraction, RentRollUnit

    rr = RentRollExtraction(
        units=[
            RentRollUnit(unit_number="101", contract_rent_yen=72000, is_occupied=True),
            RentRollUnit(unit_number="102", contract_rent_yen=72000, is_occupied=False),
        ]
    )
    assert rr.total_monthly_rent_yen is None  # with_computed_totals 前は None
    filled = rr.with_computed_totals()
    assert filled.total_monthly_rent_yen == 72000
    assert filled.total_annual_rent_yen == 72000 * 12
    assert filled.occupancy_rate == pytest.approx(0.5)
    # 元のオブジェクトは変更されていない (immutable)
    assert rr.total_monthly_rent_yen is None


# ─── critique ─────────────────────────────────────────────


def test_critique_rule_flags():
    """ルールベース flag: repair_missing / property_tax_missing。"""
    from api.services.summarizer import _detect_rule_flags

    analysis = {"kpi": {"cap_rate": 0.03, "dscr_min": 1.1, "ltv": 0.7}}
    assumptions = {
        "property": {"purchase_price_yen": 30_000_000},
        "income": {"gpi_monthly_yen": 100_000, "vacancy_rate": 0.05},
        "opex": {},  # repair, tax とも未設定
        "exit": {"exit_cap_rate": 0.03},  # cap と同じ → exit_cap_unrealistic
    }
    flags = _detect_rule_flags(analysis, assumptions)
    assert "repair_missing" in flags
    assert "property_tax_missing" in flags
    assert "exit_cap_unrealistic" in flags


def test_critique_endpoint(monkeypatch, client):
    """POST /critique が 200 を返す。
    api.main は generate_critique を直接インポートしているため
    api.main モジュールの参照を置き換える。
    """
    import api.main as main_mod
    from api.services.summarizer import CritiqueItem, CritiqueResult

    def mock_critique(*a, **kw):
        return CritiqueResult(
            critiques=[
                CritiqueItem(
                    flag_type="repair_missing",
                    severity="warn",
                    explanation="テスト",
                    verification="テスト",
                )
            ],
            rule_flags=["repair_missing"],
            latency_ms=1,
            model="mock",
        )

    monkeypatch.setattr(main_mod, "generate_critique", mock_critique)

    r = client.post(
        "/critique",
        json={
            "analysis_result": {"kpi": {"cap_rate": 0.03, "dscr_min": 1.1, "ltv": 0.7}},
            "score_result": {"total": 40.0, "evaluation": "要注意"},
            "assumptions": {
                "property": {"purchase_price_yen": 30_000_000},
                "income": {"gpi_monthly_yen": 100_000, "vacancy_rate": 0.05},
                "opex": {},
                "exit": {"exit_cap_rate": 0.03},
            },
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "critiques" in body
    assert len(body["critiques"]) == 1
    assert body["critiques"][0]["flag_type"] == "repair_missing"


# ─── history (GET /analyses) ──────────────────────────────


def test_history_endpoint(monkeypatch):
    """GET /analyses が 200 かつ items リストを返す (独立した in-memory DB)。"""
    import asyncio

    import api.db as db_module

    test_engine = db_module._build_engine("sqlite+aiosqlite:///:memory:")
    monkeypatch.setattr(db_module, "_engine", test_engine)
    monkeypatch.setattr(db_module, "_Session", None)

    asyncio.run(db_module.init_db())

    c = TestClient(app)
    r = c.get("/analyses?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "count" in body
    assert isinstance(body["items"], list)
    assert body["count"] == 0  # 空 DB
