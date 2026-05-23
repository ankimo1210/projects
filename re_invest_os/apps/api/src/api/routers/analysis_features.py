"""bid_ranges + assumption_risks ルーター。

エンドポイント:
- POST /analysis_runs/{run_id}/bid_ranges        生成+保存 (上書き)
- GET  /analysis_runs/{run_id}/bid_ranges        最新を取得
- POST /analysis_runs/{run_id}/assumption_risks  生成+保存 (一括置換)
- GET  /analysis_runs/{run_id}/assumption_risks  最新を取得
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from re_engine.bid_ranges import BidRangesResult, bid_ranges
from re_engine.models import AnalysisResult, Assumptions
from re_engine.normalized import NormalizedProperty
from sqlalchemy import delete as sql_delete
from sqlalchemy import desc, select

from api.db import (
    AnalysisRunRecord,
    AssumptionRiskRecord,
    BidRangeRecord,
    get_session_factory,
)
from api.services.risk_engine import (
    AssumptionRisk,
    MarketBenchmark,
    assess_assumption_risks,
    summarize_risks,
)

router = APIRouter(tags=["analysis-features"])


# ────────────────────────────────────────
# bid_ranges
# ────────────────────────────────────────


class BidRangesGenerateRequest(BaseModel):
    market: dict[str, Any] | None = None  # 将来用、現状未使用
    model_config = ConfigDict(extra="forbid")


class BidRangesOut(BaseModel):
    id: str
    analysis_run_id: str
    asking_price_yen: int
    aggressive_price: int | None
    base_price: int | None
    conservative_price: int | None
    gap_to_base_price_yen: int | None
    gap_to_base_price_pct: float | None
    explanation: dict[str, Any]
    created_at: str
    model_config = ConfigDict(extra="forbid")


async def _load_assumptions(run_id: str) -> tuple[AnalysisRunRecord, Assumptions]:
    factory = get_session_factory()
    async with factory() as session:
        r = await session.get(AnalysisRunRecord, run_id)
        if r is None:
            raise HTTPException(status_code=404, detail=f"analysis_run not found: {run_id}")
    raw = json.loads(r.input_snapshot_json)
    try:
        a = Assumptions.model_validate(raw)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"corrupted assumptions: {e}") from e
    return r, a


def _serialize_bid(rec: BidRangeRecord, asking: int) -> BidRangesOut:
    expl = json.loads(rec.explanation_json) if rec.explanation_json else {}
    base = rec.base_price
    if base is not None:
        gap = base - asking
        gap_pct = gap / asking if asking else None
    else:
        gap = None
        gap_pct = None
    return BidRangesOut(
        id=rec.id,
        analysis_run_id=rec.analysis_run_id,
        asking_price_yen=asking,
        aggressive_price=rec.aggressive_price,
        base_price=rec.base_price,
        conservative_price=rec.conservative_price,
        gap_to_base_price_yen=gap,
        gap_to_base_price_pct=gap_pct,
        explanation=expl,
        created_at=rec.created_at.isoformat(),
    )


def _br_explanation_payload(res: BidRangesResult) -> dict[str, Any]:
    return {
        "aggressive": {
            "text": res.aggressive.explanation,
            "binding_constraints": res.aggressive.binding_constraints,
        },
        "base": {
            "text": res.base.explanation,
            "binding_constraints": res.base.binding_constraints,
        },
        "conservative": {
            "text": res.conservative.explanation,
            "binding_constraints": res.conservative.binding_constraints,
        },
        "monotonicity_enforced": res.monotonicity_enforced,
    }


@router.post(
    "/analysis_runs/{run_id}/bid_ranges",
    response_model=BidRangesOut,
    status_code=201,
)
async def generate_bid_ranges(run_id: str, _req: BidRangesGenerateRequest | None = None) -> BidRangesOut:
    _run, assumptions = await _load_assumptions(run_id)
    res = bid_ranges(assumptions)

    rec = BidRangeRecord(
        analysis_run_id=run_id,
        aggressive_price=res.aggressive.price_yen,
        base_price=res.base.price_yen,
        conservative_price=res.conservative.price_yen,
        explanation_json=json.dumps(_br_explanation_payload(res), ensure_ascii=False),
    )
    factory = get_session_factory()
    async with factory() as session:
        # 古い同一 run のレコードは消す (常に最新のみ保持)
        await session.execute(
            sql_delete(BidRangeRecord).where(BidRangeRecord.analysis_run_id == run_id)
        )
        session.add(rec)
        await session.commit()
        await session.refresh(rec)
    return _serialize_bid(rec, res.asking_price_yen)


@router.get("/analysis_runs/{run_id}/bid_ranges", response_model=BidRangesOut)
async def get_bid_ranges(run_id: str) -> BidRangesOut:
    factory = get_session_factory()
    async with factory() as session:
        run = await session.get(AnalysisRunRecord, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"analysis_run not found: {run_id}")
        rec = (
            await session.execute(
                select(BidRangeRecord)
                .where(BidRangeRecord.analysis_run_id == run_id)
                .order_by(desc(BidRangeRecord.created_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        if rec is None:
            raise HTTPException(status_code=404, detail="bid_ranges not generated yet")
    asking = json.loads(run.input_snapshot_json)["property"]["purchase_price_yen"]
    return _serialize_bid(rec, asking)


# ────────────────────────────────────────
# assumption_risks
# ────────────────────────────────────────


class AssumptionRisksGenerateRequest(BaseModel):
    market: MarketBenchmark | None = None
    model_config = ConfigDict(extra="forbid")


class AssumptionRiskOut(BaseModel):
    id: str
    category: str
    confidence: str
    risk_level: str
    reason: str
    source: str | None
    value_json: dict[str, Any] | None
    created_at: str
    model_config = ConfigDict(extra="forbid")


class AssumptionRisksListOut(BaseModel):
    analysis_run_id: str
    items: list[AssumptionRiskOut]
    summary: str
    model_config = ConfigDict(extra="forbid")


def _serialize_risk(rec: AssumptionRiskRecord) -> AssumptionRiskOut:
    return AssumptionRiskOut(
        id=rec.id,
        category=rec.category,
        confidence=rec.confidence,
        risk_level=rec.risk_level,
        reason=rec.reason,
        source=rec.source,
        value_json=json.loads(rec.value_json) if rec.value_json else None,
        created_at=rec.created_at.isoformat(),
    )


@router.post(
    "/analysis_runs/{run_id}/assumption_risks",
    response_model=AssumptionRisksListOut,
    status_code=201,
)
async def generate_assumption_risks(
    run_id: str,
    req: AssumptionRisksGenerateRequest | None = None,
) -> AssumptionRisksListOut:
    run, assumptions = await _load_assumptions(run_id)
    metrics = json.loads(run.metrics_json)
    try:
        result = AnalysisResult.model_validate(metrics["analysis"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"corrupted metrics: {e}") from e
    try:
        normalized = NormalizedProperty.model_validate(json.loads(run.normalized_property_json))
    except Exception:
        normalized = NormalizedProperty.all_user_input()

    market = req.market if req else None
    risks = assess_assumption_risks(assumptions, result, normalized, market)

    factory = get_session_factory()
    async with factory() as session:
        # 一括置換
        await session.execute(
            sql_delete(AssumptionRiskRecord).where(
                AssumptionRiskRecord.analysis_run_id == run_id
            )
        )
        records: list[AssumptionRiskRecord] = []
        for r in risks:
            rec = AssumptionRiskRecord(
                analysis_run_id=run_id,
                category=r.category,
                value_json=json.dumps(r.value_json, ensure_ascii=False) if r.value_json else None,
                confidence=r.confidence,
                risk_level=r.risk_level,
                reason=r.reason,
                source=r.source,
            )
            session.add(rec)
            records.append(rec)
        await session.commit()
        for rec in records:
            await session.refresh(rec)

    return AssumptionRisksListOut(
        analysis_run_id=run_id,
        items=[_serialize_risk(rec) for rec in records],
        summary=summarize_risks(risks),
    )


@router.get(
    "/analysis_runs/{run_id}/assumption_risks",
    response_model=AssumptionRisksListOut,
)
async def get_assumption_risks(run_id: str) -> AssumptionRisksListOut:
    factory = get_session_factory()
    async with factory() as session:
        run = await session.get(AnalysisRunRecord, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"analysis_run not found: {run_id}")
        rows = (
            await session.execute(
                select(AssumptionRiskRecord)
                .where(AssumptionRiskRecord.analysis_run_id == run_id)
                .order_by(AssumptionRiskRecord.category)
            )
        ).scalars().all()
    items = [_serialize_risk(r) for r in rows]
    # summary は再生成 (本質は永続化されたリスクから派生する 1 行)
    pseudo = [
        AssumptionRisk(
            category=i.category,  # type: ignore[arg-type]
            confidence=i.confidence,  # type: ignore[arg-type]
            risk_level=i.risk_level,  # type: ignore[arg-type]
            reason=i.reason,
        )
        for i in items
    ]
    return AssumptionRisksListOut(
        analysis_run_id=run_id,
        items=items,
        summary=summarize_risks(pseudo),
    )
