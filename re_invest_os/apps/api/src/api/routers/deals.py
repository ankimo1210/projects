"""deals + analysis_runs CRUD ルーター。

エンドポイント:
- POST   /deals                                      新規 deal 作成
- GET    /deals                                      deal 一覧
- GET    /deals/{deal_id}                            deal 詳細 (最新 analysis_run 同梱)
- PATCH  /deals/{deal_id}                            status / title 更新
- DELETE /deals/{deal_id}                            削除 (cascade)
- POST   /deals/{deal_id}/analysis_runs              新規分析実行を保存
- GET    /deals/{deal_id}/analysis_runs              run 一覧
- GET    /analysis_runs/{run_id}                     run 詳細
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from re_engine import ENGINE_VERSION
from re_engine.analyze import run_full_analysis
from re_engine.models import Assumptions
from re_engine.score import total_score
from sqlalchemy import desc, select

from api.db import (
    AnalysisRunRecord,
    DealRecord,
    get_session_factory,
)

router = APIRouter(tags=["deals"])


# ────────────────────────────────────────
# Schemas
# ────────────────────────────────────────


_ALLOWED_STATUSES = {
    "analyzing",
    "waiting_for_broker",
    "ready_to_bid",
    "bid_submitted",
    "rejected",
    "passed",
    "archived",
}


class CreateDealRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    source_type: str = Field(pattern="^(url|document|manual)$")
    source_url: str | None = Field(default=None, max_length=2048)
    property_type: str | None = Field(default=None, max_length=32)
    status: str | None = None
    model_config = ConfigDict(extra="forbid")


class PatchDealRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    status: str | None = None
    property_type: str | None = Field(default=None, max_length=32)
    source_url: str | None = Field(default=None, max_length=2048)
    model_config = ConfigDict(extra="forbid")


class DealOut(BaseModel):
    id: str
    user_id: str | None
    title: str
    source_type: str
    source_url: str | None
    property_type: str | None
    status: str
    created_at: str
    updated_at: str
    latest_analysis_run_id: str | None = None
    model_config = ConfigDict(extra="forbid")


class CreateAnalysisRunRequest(BaseModel):
    """新規分析実行。

    assumptions を渡すとサーバ側で run_full_analysis を呼ぶ。
    metrics_json などを直接渡したい場合は precomputed=True にする (テスト・移行用)。
    """

    assumptions: dict[str, Any]
    normalized_property: dict[str, Any] | None = None
    prompt_versions: dict[str, str] | None = None
    sensitivity_json: dict[str, Any] | None = None
    max_bid_json: dict[str, Any] | None = None
    model_config = ConfigDict(extra="forbid")


class AnalysisRunOut(BaseModel):
    id: str
    deal_id: str
    engine_version: str
    prompt_versions: dict[str, str] | None
    input_snapshot_json: dict[str, Any]
    normalized_property_json: dict[str, Any]
    metrics_json: dict[str, Any]
    sensitivity_json: dict[str, Any] | None
    max_bid_json: dict[str, Any] | None
    created_at: str
    model_config = ConfigDict(extra="forbid")


# ────────────────────────────────────────
# Helpers
# ────────────────────────────────────────


def _serialize_deal(d: DealRecord, latest_run_id: str | None = None) -> DealOut:
    return DealOut(
        id=d.id,
        user_id=d.user_id,
        title=d.title,
        source_type=d.source_type,
        source_url=d.source_url,
        property_type=d.property_type,
        status=d.status,
        created_at=d.created_at.isoformat(),
        updated_at=d.updated_at.isoformat(),
        latest_analysis_run_id=latest_run_id,
    )


def _serialize_run(r: AnalysisRunRecord) -> AnalysisRunOut:
    return AnalysisRunOut(
        id=r.id,
        deal_id=r.deal_id,
        engine_version=r.engine_version,
        prompt_versions=json.loads(r.prompt_versions) if r.prompt_versions else None,
        input_snapshot_json=json.loads(r.input_snapshot_json),
        normalized_property_json=json.loads(r.normalized_property_json),
        metrics_json=json.loads(r.metrics_json),
        sensitivity_json=json.loads(r.sensitivity_json) if r.sensitivity_json else None,
        max_bid_json=json.loads(r.max_bid_json) if r.max_bid_json else None,
        created_at=r.created_at.isoformat(),
    )


# ────────────────────────────────────────
# Endpoints: deals
# ────────────────────────────────────────


@router.post("/deals", response_model=DealOut, status_code=201)
async def create_deal(req: CreateDealRequest) -> DealOut:
    status = req.status or "analyzing"
    if status not in _ALLOWED_STATUSES:
        raise HTTPException(status_code=400, detail=f"invalid status: {status}")
    record = DealRecord(
        title=req.title,
        source_type=req.source_type,
        source_url=req.source_url,
        property_type=req.property_type,
        status=status,
    )
    factory = get_session_factory()
    async with factory() as session:
        session.add(record)
        await session.commit()
        await session.refresh(record)
    return _serialize_deal(record)


@router.get("/deals")
async def list_deals(limit: int = 50, status: str | None = None) -> dict[str, Any]:
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(DealRecord).order_by(desc(DealRecord.updated_at)).limit(min(limit, 200))
        if status:
            if status not in _ALLOWED_STATUSES:
                raise HTTPException(status_code=400, detail=f"invalid status: {status}")
            stmt = stmt.where(DealRecord.status == status)
        rows = (await session.execute(stmt)).scalars().all()
    return {"items": [_serialize_deal(d).model_dump() for d in rows], "count": len(rows)}


@router.get("/deals/{deal_id}", response_model=DealOut)
async def get_deal(deal_id: str) -> DealOut:
    factory = get_session_factory()
    async with factory() as session:
        d = await session.get(DealRecord, deal_id)
        if d is None:
            raise HTTPException(status_code=404, detail=f"deal not found: {deal_id}")
        latest = (
            await session.execute(
                select(AnalysisRunRecord.id)
                .where(AnalysisRunRecord.deal_id == deal_id)
                .order_by(desc(AnalysisRunRecord.created_at))
                .limit(1)
            )
        ).scalar_one_or_none()
    return _serialize_deal(d, latest_run_id=latest)


@router.patch("/deals/{deal_id}", response_model=DealOut)
async def patch_deal(deal_id: str, req: PatchDealRequest) -> DealOut:
    if req.status is not None and req.status not in _ALLOWED_STATUSES:
        raise HTTPException(status_code=400, detail=f"invalid status: {req.status}")
    factory = get_session_factory()
    async with factory() as session:
        d = await session.get(DealRecord, deal_id)
        if d is None:
            raise HTTPException(status_code=404, detail=f"deal not found: {deal_id}")
        if req.title is not None:
            d.title = req.title
        if req.status is not None:
            d.status = req.status
        if req.property_type is not None:
            d.property_type = req.property_type
        if req.source_url is not None:
            d.source_url = req.source_url
        d.updated_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(d)
    return _serialize_deal(d)


@router.delete("/deals/{deal_id}", status_code=204)
async def delete_deal(deal_id: str) -> None:
    factory = get_session_factory()
    async with factory() as session:
        d = await session.get(DealRecord, deal_id)
        if d is None:
            raise HTTPException(status_code=404, detail=f"deal not found: {deal_id}")
        # cascade は SQLite では FK ON が必要だが、子テーブルも手動で削る方が確実
        from sqlalchemy import delete as sql_delete

        from api.db import (
            AssumptionRiskRecord,
            BidRangeRecord,
            ChecklistItemRecord,
            InvestmentMemoRecord,
            MarketEvidenceCardRecord,
            WatchlistItemRecord,
        )

        run_ids = (
            await session.execute(
                select(AnalysisRunRecord.id).where(AnalysisRunRecord.deal_id == deal_id)
            )
        ).scalars().all()
        if run_ids:
            await session.execute(
                sql_delete(BidRangeRecord).where(BidRangeRecord.analysis_run_id.in_(run_ids))
            )
            await session.execute(
                sql_delete(AssumptionRiskRecord).where(
                    AssumptionRiskRecord.analysis_run_id.in_(run_ids)
                )
            )
        await session.execute(
            sql_delete(AnalysisRunRecord).where(AnalysisRunRecord.deal_id == deal_id)
        )
        await session.execute(sql_delete(ChecklistItemRecord).where(ChecklistItemRecord.deal_id == deal_id))
        await session.execute(sql_delete(InvestmentMemoRecord).where(InvestmentMemoRecord.deal_id == deal_id))
        await session.execute(sql_delete(WatchlistItemRecord).where(WatchlistItemRecord.deal_id == deal_id))
        await session.execute(
            sql_delete(MarketEvidenceCardRecord).where(MarketEvidenceCardRecord.deal_id == deal_id)
        )
        await session.delete(d)
        await session.commit()


# ────────────────────────────────────────
# Endpoints: analysis_runs
# ────────────────────────────────────────


@router.post("/deals/{deal_id}/analysis_runs", response_model=AnalysisRunOut, status_code=201)
async def create_analysis_run(deal_id: str, req: CreateAnalysisRunRequest) -> AnalysisRunOut:
    """assumptions を受け取り、サーバで full 分析を実行して保存する。"""
    factory = get_session_factory()
    async with factory() as session:
        d = await session.get(DealRecord, deal_id)
        if d is None:
            raise HTTPException(status_code=404, detail=f"deal not found: {deal_id}")

    try:
        assumptions = Assumptions.model_validate(req.assumptions)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"invalid assumptions: {e}") from e

    analysis = run_full_analysis(assumptions)
    score = total_score(analysis)
    metrics = {
        "analysis": analysis.model_dump(mode="json", by_alias=True),
        "score": score.model_dump(mode="json"),
    }

    normalized = req.normalized_property or {"field_sources": {}}

    rec = AnalysisRunRecord(
        deal_id=deal_id,
        engine_version=ENGINE_VERSION,
        prompt_versions=json.dumps(req.prompt_versions, ensure_ascii=False)
        if req.prompt_versions
        else None,
        input_snapshot_json=json.dumps(assumptions.model_dump(mode="json", by_alias=True), ensure_ascii=False),
        normalized_property_json=json.dumps(normalized, ensure_ascii=False),
        metrics_json=json.dumps(metrics, ensure_ascii=False),
        sensitivity_json=json.dumps(req.sensitivity_json, ensure_ascii=False)
        if req.sensitivity_json
        else None,
        max_bid_json=json.dumps(req.max_bid_json, ensure_ascii=False) if req.max_bid_json else None,
    )
    factory = get_session_factory()
    async with factory() as session:
        session.add(rec)
        # deal の updated_at を更新
        d2 = await session.get(DealRecord, deal_id)
        if d2 is not None:
            d2.updated_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(rec)
    return _serialize_run(rec)


@router.get("/deals/{deal_id}/analysis_runs")
async def list_analysis_runs(deal_id: str, limit: int = 20) -> dict[str, Any]:
    factory = get_session_factory()
    async with factory() as session:
        rows = (
            await session.execute(
                select(AnalysisRunRecord)
                .where(AnalysisRunRecord.deal_id == deal_id)
                .order_by(desc(AnalysisRunRecord.created_at))
                .limit(min(limit, 100))
            )
        ).scalars().all()
    return {"items": [_serialize_run(r).model_dump() for r in rows], "count": len(rows)}


@router.get("/analysis_runs/{run_id}", response_model=AnalysisRunOut)
async def get_analysis_run(run_id: str) -> AnalysisRunOut:
    factory = get_session_factory()
    async with factory() as session:
        r = await session.get(AnalysisRunRecord, run_id)
        if r is None:
            raise HTTPException(status_code=404, detail=f"analysis_run not found: {run_id}")
    return _serialize_run(r)
