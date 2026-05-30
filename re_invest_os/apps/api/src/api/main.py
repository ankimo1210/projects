"""FastAPI app entry point。

エンドポイント:
- GET  /health              ヘルスチェック
- GET  /version             エンジン・APIバージョン
- POST /analyze             Assumptions → AnalysisResult + Score
- GET  /sample/nishi-shinjuku  デモ物件のサンプル分析 (フロント検証用)
- POST /extract/url         URL → 抽出 + Assumptions
- POST /extract/document    PDF → 抽出 + Assumptions
- POST /analyses            分析結果を保存 → id を返す
- GET  /analyses            分析履歴一覧
- GET  /analyses/{id}       共有 URL 用: id から分析結果を取得
- POST /summarize           3行サマリー + 確認質問
- POST /critique            前提甘さ検出 + warning_flags
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from re_engine import ENGINE_VERSION
from re_engine.analyze import run_full_analysis
from re_engine.cross_asset import CrossAssetRequest, CrossAssetResult, cross_asset_comparison
from re_engine.max_offer import InvestorTargets, MaxOfferResult, max_offer_price
from re_engine.models import (
    AcquisitionAssumptions,
    AnalysisResult,
    Assumptions,
    ExitAssumptions,
    IncomeAssumptions,
    LoanAssumptions,
    OpexAssumptions,
    PropertyAssumptions,
    TaxAssumptions,
)
from re_engine.normalized import NormalizedProperty
from re_engine.sensitivity import SensitivityResult, sensitivity_grid

from api import __version__
from api.db import get_analysis, init_db, save_analysis
from api.services import prompts as prompt_loader
from api.services.extractors import classify as classify_mod
from api.services.extractors import property_brochure as brochure_mod
from api.services.extractors import rent_roll as rent_roll_mod
from api.services.extractors import source_pdf, source_url
from api.services.extractors.property_brochure import BrochureResult, PropertyBrochureExtraction
from api.services.extractors.to_assumptions import to_assumptions
from api.services.llm_client import CallMeta as _LLMCallMeta
from api.services.risk_engine import AssumptionScore, assess_assumption_score
from api.services.summarizer import generate_critique, generate_inquiry, generate_summary


@contextlib.asynccontextmanager
async def _lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="re_invest_os API",
    description="個人投資家のための不動産投資DD・買付前監査ツール — 分析エンジンAPI",
    version=__version__,
    lifespan=_lifespan,
)

# CORS: 開発時は緩く、本番では設定で絞る
_allowed_origins = os.getenv(
    "CORS_ALLOW_ORIGINS",
    "http://localhost:3000,https://loves-pin-poll-penalty.trycloudflare.com",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _allowed_origins if o.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# v2: Deal Workspace ルーター
from api.routers import analysis_features as _af_router
from api.routers import deals as _deals_router

app.include_router(_deals_router.router)
app.include_router(_af_router.router)


class AnalyzeRequest(BaseModel):
    assumptions: Assumptions
    normalized_property: dict | None = None
    model_config = ConfigDict(extra="forbid")


class AnalyzeResponse(BaseModel):
    analysis: AnalysisResult
    assumption_score: AssumptionScore
    model_config = ConfigDict(extra="forbid")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/version")
def version() -> dict[str, str]:
    return {
        "api": __version__,
        "engine": ENGINE_VERSION,
    }


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    result = run_full_analysis(req.assumptions)
    norm = (
        NormalizedProperty.model_validate(req.normalized_property)
        if req.normalized_property
        else NormalizedProperty.all_user_input()
    )
    score = assess_assumption_score(req.assumptions, result, norm)
    return AnalyzeResponse(analysis=result, assumption_score=score)


def _sample_assumptions() -> Assumptions:
    """西新宿レジデンス 504号 (モック)。"""
    return Assumptions(
        property=PropertyAssumptions(
            property_type="kuubun",
            purchase_price_yen=39_800_000,
            land_value_yen=8_000_000,
            building_value_yen=31_800_000,
            structure="rc",
            building_completion_ym="2011-04",
            acquisition_year=2026,
            building_area_sqm=38.4,
            location_pref="13",
            location_city="新宿区",
        ),
        income=IncomeAssumptions(
            gpi_monthly_yen=145_000,
            vacancy_rate=0.05,
            rent_growth_rate=-0.005,
        ),
        opex=OpexAssumptions(
            management_fee_rate=0.05,
            building_mgmt_yen=240_000,
            fixed_property_tax_yen=120_000,
            insurance_yen=20_000,
        ),
        loan=LoanAssumptions(
            loan_amount_yen=27_860_000,
            interest_rate=0.020,
            term_years=30,
        ),
        tax=TaxAssumptions(),
        exit=ExitAssumptions(hold_period_years=10, exit_cap_rate=0.060),
        acquisition=AcquisitionAssumptions(
            equity_yen=12_000_000,
            acquisition_cost_rate=0.07,
        ),
    )


@app.get("/sample/nishi-shinjuku", response_model=AnalyzeResponse)
def sample_nishi_shinjuku() -> AnalyzeResponse:
    """デモ物件のサンプル分析 (フロント検証用)。"""
    a = _sample_assumptions()
    result = run_full_analysis(a)
    score = assess_assumption_score(a, result, NormalizedProperty.all_user_input())
    return AnalyzeResponse(analysis=result, assumption_score=score)


class MaxOfferRequest(BaseModel):
    assumptions: Assumptions
    targets: InvestorTargets | None = None
    model_config = ConfigDict(extra="forbid")


@app.post("/max_offer", response_model=MaxOfferResult)
def post_max_offer(req: MaxOfferRequest) -> MaxOfferResult:
    return max_offer_price(req.assumptions, req.targets)


class SensitivityRequest(BaseModel):
    assumptions: Assumptions
    model_config = ConfigDict(extra="forbid")


@app.post("/sensitivity", response_model=SensitivityResult)
def post_sensitivity(req: SensitivityRequest) -> SensitivityResult:
    return sensitivity_grid(req.assumptions)


@app.post("/cross_asset", response_model=CrossAssetResult)
def post_cross_asset(req: CrossAssetRequest) -> CrossAssetResult:
    return cross_asset_comparison(req)


# ===== /extract =====


class ExtractionMeta(BaseModel):
    engine_version: str
    prompt_versions: dict[str, str]
    pii_redactions: dict[str, int]
    classification: dict[str, object]
    llm: dict[str, object]
    completeness_score: float = 0.0  # 0–100: 主要フィールドの充足率
    warnings: list[str] = Field(default_factory=list)
    needs_confirmation: list[str] = Field(default_factory=list)
    missing_required: list[str] = Field(default_factory=list)
    derived: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


def _compute_completeness(brochure: PropertyBrochureExtraction, doc_type: str) -> float:
    """主要フィールドの充足率 (0–100)。"""
    if doc_type == "rent_roll":
        return 100.0  # rent_roll は別パスで評価
    # property_brochure の P0 必須フィールド
    required = [
        brochure.asking_price_yen,
        brochure.structure,
        brochure.build_year_month,
        brochure.exclusive_area_sqm or brochure.building_area_sqm,
        brochure.estimated_full_rent_monthly_yen or brochure.gross_yield_pct,
    ]
    filled = sum(1 for v in required if v is not None)
    return round(filled / len(required) * 100, 1)


class ExtractionResponse(BaseModel):
    """抽出 API のレスポンス。

    - assumptions が None の場合は missing_required を埋めてから /analyze を呼ぶ。
    - assumptions が埋まっている場合でも meta.needs_confirmation は確認画面で表示する。
    - rent_roll が含まれる場合は rent_roll フィールドに JSON が入る。
    """

    source_type: str  # "url" | "document"
    source_ref: str | None
    extracted: PropertyBrochureExtraction
    assumptions: Assumptions | None
    rent_roll: dict | None = None  # RentRollExtraction (document_type=rent_roll 時)
    meta: ExtractionMeta

    model_config = ConfigDict(extra="forbid")


class ExtractUrlRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    model_config = ConfigDict(extra="forbid")


def _build_response(
    *,
    source_type: str,
    source_ref: str | None,
    text: str,
    extra_warnings: list[str],
) -> ExtractionResponse:
    if not text.strip():
        raise HTTPException(status_code=422, detail="抽出元テキストが空です")

    # 1) classify
    cls = classify_mod.classify(text)
    warnings = list(extra_warnings)

    # 2a) レントロールの場合は専用 extractor に分岐
    rent_roll_data: dict | None = None
    if cls.document_type == "rent_roll":
        try:
            rr = rent_roll_mod.extract(text)
            rent_roll_data = rr.data.model_dump()
            warnings.extend(rr.warnings)
        except Exception as e:
            warnings.append(f"レントロール抽出失敗: {e}")

    # 2b) 販売図面抽出
    # rent_roll はすでに専用 extractor を呼んでいるので brochure は空モデルで代替 (LLM 節約)
    if cls.document_type == "rent_roll":
        br = BrochureResult(
            data=PropertyBrochureExtraction(),
            meta=_LLMCallMeta(
                provider="skipped", model="skipped", prompt_id="skipped", latency_ms=0
            ),
            pii_redactions={},
            warnings=[],
        )
    else:
        if cls.document_type != "property_brochure":
            warnings.append(
                f"分類: {cls.document_type} (conf={cls.confidence:.2f}) — 販売図面抽出も試みます"
            )
        br = brochure_mod.extract(text)
    warnings.extend(br.warnings)

    # 3) map → Assumptions (失敗してもエラーにはせず、missing_required で返す)
    assumptions: Assumptions | None = None
    needs_confirmation: list[str] = []
    derived: list[str] = []
    missing_required: list[str] = []
    try:
        mapping = to_assumptions(br.data, acquisition_year=_dt.date.today().year)
        assumptions = mapping.assumptions
        needs_confirmation = mapping.needs_confirmation
        derived = mapping.derived
    except ValueError as e:
        missing_required.append("asking_price_yen")
        warnings.append(f"Assumptions 組み立て失敗: {e}")

    # PII 合算
    pii: dict[str, int] = {}
    for d in (cls.pii_redactions, br.pii_redactions):
        for k, v in d.items():
            pii[k] = pii.get(k, 0) + v

    completeness = _compute_completeness(br.data, cls.document_type)

    return ExtractionResponse(
        source_type=source_type,
        source_ref=source_ref,
        extracted=br.data,
        assumptions=assumptions,
        rent_roll=rent_roll_data,
        meta=ExtractionMeta(
            engine_version=ENGINE_VERSION,
            prompt_versions=prompt_loader.all_versions(),
            pii_redactions=pii,
            completeness_score=completeness,
            classification={
                "document_type": cls.document_type,
                "confidence": cls.confidence,
                "reason": cls.reason,
            },
            llm={
                "classify": {
                    "provider": cls.meta.provider,
                    "model": cls.meta.model,
                    "latency_ms": cls.meta.latency_ms,
                    "prompt_id": cls.meta.prompt_id,
                },
                "brochure": {
                    "provider": br.meta.provider,
                    "model": br.meta.model,
                    "latency_ms": br.meta.latency_ms,
                    "prompt_id": br.meta.prompt_id,
                },
            },
            warnings=warnings,
            needs_confirmation=needs_confirmation,
            missing_required=missing_required,
            derived=derived,
        ),
    )


@app.post("/extract/url", response_model=ExtractionResponse)
def post_extract_url(req: ExtractUrlRequest) -> ExtractionResponse:
    try:
        page = source_url.fetch(req.url)
    except source_url.UnsupportedHostError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"URL 取得失敗: {e}") from e
    return _build_response(
        source_type="url",
        source_ref=req.url,
        text=page.text,
        extra_warnings=[],
    )


@app.post("/extract/document", response_model=ExtractionResponse)
async def post_extract_document(file: UploadFile = File(...)) -> ExtractionResponse:
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(
            status_code=415,
            detail=f"unsupported content_type: {file.content_type} (v1 supports PDF only)",
        )
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status_code=422, detail="empty file")
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="file too large (>20MB)")

    pdf = source_pdf.extract_text(data)
    if pdf.is_scanned:
        raise HTTPException(
            status_code=422,
            detail="テキスト層が取得できません。スキャン PDF は v1 では非対応です。",
        )
    return _build_response(
        source_type="document",
        source_ref=file.filename,
        text=pdf.text,
        extra_warnings=pdf.warnings,
    )


# ===== /analyses =====


class SaveAnalysisRequest(BaseModel):
    source_type: str = "manual"
    source_ref: str | None = None
    extracted: dict | None = None
    assumptions: dict
    analysis_result: dict
    score_result: dict
    pii_redactions: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    model_config = ConfigDict(extra="forbid")


class SaveAnalysisResponse(BaseModel):
    id: str
    model_config = ConfigDict(extra="forbid")


@app.post("/analyses", response_model=SaveAnalysisResponse, status_code=201)
async def post_save_analysis(req: SaveAnalysisRequest) -> SaveAnalysisResponse:
    score = req.score_result.get("total", 0.0)
    kpi = req.analysis_result.get("kpi", {})
    analysis_id = await save_analysis(
        source_type=req.source_type,
        source_ref=req.source_ref,
        engine_version=ENGINE_VERSION,
        prompt_versions=prompt_loader.all_versions(),
        extracted=req.extracted,
        assumptions=req.assumptions,
        analysis_result=req.analysis_result,
        score_total=float(score),
        score_result=req.score_result,
        noi_cap=kpi.get("cap_rate"),
        dscr_y1=kpi.get("dscr_year1"),
        atcf_y1=kpi.get("atcf_first_year_yen"),
        equity_irr=kpi.get("equity_irr"),
        pii_redactions=req.pii_redactions,
        warnings=req.warnings,
    )
    return SaveAnalysisResponse(id=analysis_id)


@app.get("/analyses/{analysis_id}")
async def get_analysis_by_id(analysis_id: str) -> dict:
    data = await get_analysis(analysis_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"analysis not found: {analysis_id}")
    return data


# ===== /summarize =====


class SummarizeRequest(BaseModel):
    analysis_result: dict
    score_result: dict
    needs_confirmation: list[str] = Field(default_factory=list)
    model_config = ConfigDict(extra="forbid")


class InquiryQuestionOut(BaseModel):
    category: str
    question: str
    rationale: str
    model_config = ConfigDict(extra="forbid")


class SummarizeResponse(BaseModel):
    summary_lines: list[str]  # 3行サマリー
    questions: list[InquiryQuestionOut]  # 確認質問 (最大8件)
    ng_filtered: bool
    model: str
    model_config = ConfigDict(extra="forbid")


@app.post("/admin/purge-expired-documents")
async def purge_expired_documents() -> dict[str, int]:
    """delete_after < now() の uploaded_documents を削除。本番では cron で叩く。"""
    from datetime import UTC, datetime

    from sqlalchemy import delete

    from api.db import UploadedDocumentRecord, get_session_factory

    now = datetime.now(UTC)
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            delete(UploadedDocumentRecord).where(
                UploadedDocumentRecord.delete_after < now  # type: ignore[operator]
            )
        )
        await session.commit()
    return {"deleted": result.rowcount}


@app.post("/summarize", response_model=SummarizeResponse)
def post_summarize(req: SummarizeRequest) -> SummarizeResponse:
    summary = generate_summary(req.analysis_result, req.score_result)
    inquiry = generate_inquiry(req.score_result, req.analysis_result, req.needs_confirmation)
    return SummarizeResponse(
        summary_lines=summary.lines,
        questions=[
            InquiryQuestionOut(
                category=q.category,
                question=q.question,
                rationale=q.rationale,
            )
            for q in inquiry.questions
        ],
        ng_filtered=summary.ng_filtered,
        model=summary.model,
    )


# ===== /critique =====


class CritiqueRequest(BaseModel):
    analysis_result: dict
    score_result: dict
    assumptions: dict
    model_config = ConfigDict(extra="forbid")


class CritiqueItem(BaseModel):
    flag_type: str
    severity: str
    explanation: str
    verification: str
    model_config = ConfigDict(extra="forbid")


class CritiqueResponse(BaseModel):
    critiques: list[CritiqueItem]
    rule_flags: list[str] = Field(default_factory=list)
    model: str
    model_config = ConfigDict(extra="forbid")


@app.post("/critique", response_model=CritiqueResponse)
def post_critique(req: CritiqueRequest) -> CritiqueResponse:
    result = generate_critique(req.analysis_result, req.score_result, req.assumptions)
    return CritiqueResponse(
        critiques=[
            CritiqueItem(
                flag_type=c.flag_type,
                severity=c.severity,
                explanation=c.explanation,
                verification=c.verification,
            )
            for c in result.critiques
        ],
        rule_flags=result.rule_flags,
        model=result.model,
    )


# ===== GET /analyses (履歴一覧) =====


@app.get("/analyses")
async def list_analyses(limit: int = 20) -> dict:
    from sqlalchemy import select

    from api.db import AnalysisRecord, get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        rows = await session.execute(
            select(
                AnalysisRecord.id,
                AnalysisRecord.created_at,
                AnalysisRecord.source_type,
                AnalysisRecord.source_ref,
                AnalysisRecord.score_total,
                AnalysisRecord.noi_cap,
                AnalysisRecord.dscr_y1,
                AnalysisRecord.atcf_y1,
                AnalysisRecord.engine_version,
            )
            .where(AnalysisRecord.deleted_at.is_(None))
            .order_by(AnalysisRecord.created_at.desc())
            .limit(min(limit, 100))
        )
        items = [
            {
                "id": r.id,
                "created_at": r.created_at.isoformat(),
                "source_type": r.source_type,
                "source_ref": r.source_ref,
                "score_total": r.score_total,
                "noi_cap": r.noi_cap,
                "dscr_y1": r.dscr_y1,
                "atcf_y1": r.atcf_y1,
                "engine_version": r.engine_version,
            }
            for r in rows.all()
        ]
    return {"items": items, "count": len(items)}
