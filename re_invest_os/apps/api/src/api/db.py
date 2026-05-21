"""DB セットアップ。

環境変数:
  DATABASE_URL  sqlite+aiosqlite:///./reio.db (dev デフォルト)
                postgresql+asyncpg://... (Supabase 本番)

起動時に create_all を呼ぶ。Alembic は Phase 3+ で導入。
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import String, Text, event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import StaticPool

# ──────────────────────────────────────────────
# Engine / Session factory
# ──────────────────────────────────────────────

_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./reio.db",
)


def _build_engine(url: str) -> AsyncEngine:
    connect_args: dict[str, Any] = {}
    kwargs: dict[str, Any] = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    if url == "sqlite+aiosqlite:///:memory:":
        # in-memory DB: 接続ごとに別 DB になるのを防ぐため StaticPool で共有
        kwargs["poolclass"] = StaticPool
    return create_async_engine(url, connect_args=connect_args, echo=False, **kwargs)


_engine: AsyncEngine | None = None
_Session: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = _build_engine(_DATABASE_URL)
        if _DATABASE_URL.startswith("sqlite"):
            _enable_sqlite_wal(_engine)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _Session
    if _Session is None:
        _Session = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _Session


def _enable_sqlite_wal(engine: AsyncEngine) -> None:
    @event.listens_for(engine.sync_engine, "connect")
    def set_wal(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA journal_mode=WAL")
        dbapi_conn.execute("PRAGMA foreign_keys=ON")


# ──────────────────────────────────────────────
# ORM モデル
# ──────────────────────────────────────────────


class Base(DeclarativeBase):
    pass


class AnalysisRecord(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True, default=None)

    source_type: Mapped[str] = mapped_column(String(16))
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    engine_version: Mapped[str] = mapped_column(String(32))
    prompt_versions: Mapped[str] = mapped_column(Text)  # JSON
    extracted: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)  # JSON
    assumptions: Mapped[str] = mapped_column(Text)  # JSON
    analysis_result: Mapped[str] = mapped_column(Text)  # JSON
    score_total: Mapped[float]
    score_result: Mapped[str] = mapped_column(Text)  # JSON
    noi_cap: Mapped[float | None] = mapped_column(nullable=True, default=None)
    dscr_y1: Mapped[float | None] = mapped_column(nullable=True, default=None)
    atcf_y1: Mapped[int | None] = mapped_column(nullable=True, default=None)
    equity_irr: Mapped[float | None] = mapped_column(nullable=True, default=None)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)
    pii_redactions: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)  # JSON
    warnings: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)  # JSON


class ExtractionCorrectionRecord(Base):
    __tablename__ = "extraction_corrections"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    analysis_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    field_path: Mapped[str] = mapped_column(String(64))
    ai_value: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)  # JSON
    user_value: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)  # JSON
    prompt_id: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)


class UploadedDocumentRecord(Base):
    __tablename__ = "uploaded_documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    analysis_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    storage_path: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(String(64), default="application/pdf")
    size_bytes: Mapped[int | None] = mapped_column(nullable=True, default=None)
    delete_after: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC) + timedelta(days=30)
    )


# ──────────────────────────────────────────────
# DB 初期化
# ──────────────────────────────────────────────


async def init_db() -> None:
    """テーブルが存在しなければ作成。"""
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ──────────────────────────────────────────────
# CRUD ヘルパー
# ──────────────────────────────────────────────


def _j(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


async def save_analysis(
    *,
    source_type: str,
    source_ref: str | None,
    engine_version: str,
    prompt_versions: dict[str, str],
    extracted: dict[str, Any] | None,
    assumptions: dict[str, Any],
    analysis_result: dict[str, Any],
    score_total: float,
    score_result: dict[str, Any],
    noi_cap: float | None = None,
    dscr_y1: float | None = None,
    atcf_y1: int | None = None,
    equity_irr: float | None = None,
    user_id: str | None = None,
    pii_redactions: dict[str, int] | None = None,
    warnings: list[str] | None = None,
) -> str:
    """分析結果を保存して id を返す。"""
    record = AnalysisRecord(
        source_type=source_type,
        source_ref=source_ref,
        engine_version=engine_version,
        prompt_versions=_j(prompt_versions),
        extracted=_j(extracted) if extracted else None,
        assumptions=_j(assumptions),
        analysis_result=_j(analysis_result),
        score_total=score_total,
        score_result=_j(score_result),
        noi_cap=noi_cap,
        dscr_y1=dscr_y1,
        atcf_y1=atcf_y1,
        equity_irr=equity_irr,
        user_id=user_id,
        pii_redactions=_j(pii_redactions) if pii_redactions else None,
        warnings=_j(warnings) if warnings else None,
    )
    factory = get_session_factory()
    async with factory() as session:
        session.add(record)
        await session.commit()
        return record.id


async def get_analysis(analysis_id: str) -> dict[str, Any] | None:
    """id から分析結果を取得。deleted_at は問わず返す (フロントで判断)。"""
    factory = get_session_factory()
    async with factory() as session:
        rec = await session.get(AnalysisRecord, analysis_id)
        if rec is None:
            return None
        return {
            "id": rec.id,
            "created_at": rec.created_at.isoformat(),
            "deleted_at": rec.deleted_at.isoformat() if rec.deleted_at else None,
            "source_type": rec.source_type,
            "source_ref": rec.source_ref,
            "engine_version": rec.engine_version,
            "prompt_versions": json.loads(rec.prompt_versions),
            "extracted": json.loads(rec.extracted) if rec.extracted else None,
            "assumptions": json.loads(rec.assumptions),
            "analysis_result": json.loads(rec.analysis_result),
            "score_total": rec.score_total,
            "score_result": json.loads(rec.score_result),
            "noi_cap": rec.noi_cap,
            "dscr_y1": rec.dscr_y1,
            "atcf_y1": rec.atcf_y1,
            "equity_irr": rec.equity_irr,
            "user_id": rec.user_id,
            "pii_redactions": json.loads(rec.pii_redactions) if rec.pii_redactions else {},
            "warnings": json.loads(rec.warnings) if rec.warnings else [],
        }
