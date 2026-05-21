-- v1: 分析結果・抽出訂正・アップロード資料
-- 対応 DB: PostgreSQL 15+ (Supabase) / SQLite 3.35+ (ローカル dev)

-- ============================================================
-- 1. analyses
-- ============================================================
CREATE TABLE IF NOT EXISTS analyses (
    id              TEXT        PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-'
                                || lower(hex(randomblob(2))) || '-'
                                || lower(hex(randomblob(2))) || '-'
                                || lower(hex(randomblob(2))) || '-'
                                || lower(hex(randomblob(6)))),
    created_at      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at      DATETIME    NULL,

    -- 入力
    source_type     TEXT        NOT NULL CHECK (source_type IN ('url','document','manual')),
    source_ref      TEXT        NULL,           -- URL or ファイル名
    engine_version  TEXT        NOT NULL,       -- "0.1.0" 等
    prompt_versions TEXT        NOT NULL,       -- JSON {"classify_document":"v1","property_brochure":"v4"}
    extracted       TEXT        NULL,           -- JSON (PropertyBrochureExtraction)
    assumptions     TEXT        NOT NULL,       -- JSON (Assumptions)

    -- 結果
    analysis_result TEXT        NOT NULL,       -- JSON (AnalysisResult)
    score_total     REAL        NOT NULL,       -- 検索・ソート用
    score_result    TEXT        NOT NULL,       -- JSON (ScoreResult)

    -- 主要 KPI 列 (ソート / フィルタ用)
    noi_cap         REAL        NULL,           -- NOI Cap Rate
    dscr_y1         REAL        NULL,           -- DSCR Year1
    atcf_y1         INTEGER     NULL,           -- ATCF Year1 (yen)
    equity_irr      REAL        NULL,           -- Equity IRR (null=未収束)

    -- メタ
    user_id         TEXT        NULL,           -- Phase 3 で外部キー設定
    pii_redactions  TEXT        NULL,           -- JSON {"PHONE":2,...}
    warnings        TEXT        NULL            -- JSON array
);

CREATE INDEX IF NOT EXISTS idx_analyses_created   ON analyses (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analyses_user      ON analyses (user_id, created_at DESC) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_analyses_score     ON analyses (score_total DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_analyses_deleted   ON analyses (deleted_at) WHERE deleted_at IS NOT NULL;


-- ============================================================
-- 2. extraction_corrections
--    AI が抽出した値 vs ユーザーが確認画面で訂正した値
--    プロンプト改善のフィードバックループに使う
-- ============================================================
CREATE TABLE IF NOT EXISTS extraction_corrections (
    id              TEXT        PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    analysis_id     TEXT        NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    created_at      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    field_path      TEXT        NOT NULL,   -- "asking_price_yen"
    ai_value        TEXT        NULL,       -- JSON
    user_value      TEXT        NULL,       -- JSON
    prompt_id       TEXT        NULL        -- "property_brochure:v4"
);

CREATE INDEX IF NOT EXISTS idx_corrections_analysis ON extraction_corrections (analysis_id);
CREATE INDEX IF NOT EXISTS idx_corrections_field    ON extraction_corrections (field_path, created_at DESC);


-- ============================================================
-- 3. uploaded_documents
--    PDF 等のバイナリ参照。30日後に物理削除。
-- ============================================================
CREATE TABLE IF NOT EXISTS uploaded_documents (
    id              TEXT        PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    analysis_id     TEXT        NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    created_at      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    storage_path    TEXT        NOT NULL,   -- Supabase Storage path or local path
    content_type    TEXT        NOT NULL DEFAULT 'application/pdf',
    size_bytes      INTEGER     NULL,
    delete_after    DATETIME    NOT NULL    -- created_at + 30 days
);

CREATE INDEX IF NOT EXISTS idx_docs_delete ON uploaded_documents (delete_after);
