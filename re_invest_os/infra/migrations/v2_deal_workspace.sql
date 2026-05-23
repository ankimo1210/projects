-- v2: Deal Workspace (Top7 新機能)
-- 既存 analyses は触らない。並行系統として追加。
-- 対応 DB: PostgreSQL 15+ (Supabase) / SQLite 3.35+ (ローカル dev)

-- ============================================================
-- 1. deals (物件検討単位)
-- ============================================================
CREATE TABLE IF NOT EXISTS deals (
    id            TEXT     PRIMARY KEY,
    user_id       TEXT     NULL,
    title         TEXT     NOT NULL,
    source_type   TEXT     NOT NULL CHECK (source_type IN ('url','document','manual')),
    source_url    TEXT     NULL,
    property_type TEXT     NULL,
    status        TEXT     NOT NULL DEFAULT 'analyzing'
                  CHECK (status IN ('analyzing','waiting_for_broker','ready_to_bid',
                                    'bid_submitted','rejected','passed','archived')),
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_deals_user    ON deals (user_id, updated_at DESC) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_deals_updated ON deals (updated_at DESC);


-- ============================================================
-- 2. analysis_runs (deal に対する分析実行履歴)
-- ============================================================
CREATE TABLE IF NOT EXISTS analysis_runs (
    id                        TEXT     PRIMARY KEY,
    deal_id                   TEXT     NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    engine_version            TEXT     NOT NULL,
    prompt_versions           TEXT     NULL,        -- JSON
    input_snapshot_json       TEXT     NOT NULL,    -- Assumptions
    normalized_property_json  TEXT     NOT NULL,    -- NormalizedProperty (field_sources 含む)
    metrics_json              TEXT     NOT NULL,    -- AnalysisResult
    sensitivity_json          TEXT     NULL,
    max_bid_json              TEXT     NULL,
    created_at                DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_runs_deal ON analysis_runs (deal_id, created_at DESC);


-- ============================================================
-- 3. bid_ranges
-- ============================================================
CREATE TABLE IF NOT EXISTS bid_ranges (
    id                 TEXT     PRIMARY KEY,
    analysis_run_id    TEXT     NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    aggressive_price   INTEGER  NULL,
    base_price         INTEGER  NULL,
    conservative_price INTEGER  NULL,
    explanation_json   TEXT     NULL,
    created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_bid_ranges_run ON bid_ranges (analysis_run_id, created_at DESC);


-- ============================================================
-- 4. assumption_risks
-- ============================================================
CREATE TABLE IF NOT EXISTS assumption_risks (
    id              TEXT     PRIMARY KEY,
    analysis_run_id TEXT     NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    category        TEXT     NOT NULL CHECK (category IN
                    ('rent','vacancy','opex','repair','interest_rate','exit_price','tax')),
    value_json      TEXT     NULL,
    confidence      TEXT     NOT NULL CHECK (confidence IN ('A','B','C','D')),
    risk_level      TEXT     NOT NULL CHECK (risk_level IN ('low','medium','high','unknown')),
    reason          TEXT     NOT NULL,
    source          TEXT     NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_risks_run ON assumption_risks (analysis_run_id);


-- ============================================================
-- 5. checklist_items (仲介確認)
-- ============================================================
CREATE TABLE IF NOT EXISTS checklist_items (
    id              TEXT     PRIMARY KEY,
    deal_id         TEXT     NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    analysis_run_id TEXT     NULL REFERENCES analysis_runs(id) ON DELETE SET NULL,
    category        TEXT     NOT NULL,
    priority        TEXT     NOT NULL CHECK (priority IN ('high','medium','low')),
    question        TEXT     NOT NULL,
    reason          TEXT     NOT NULL,
    status          TEXT     NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open','answered','not_applicable','dismissed')),
    answer          TEXT     NULL,
    evidence_url    TEXT     NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_checklist_deal ON checklist_items (deal_id, status, priority);


-- ============================================================
-- 6. market_evidence_cards
-- ============================================================
CREATE TABLE IF NOT EXISTS market_evidence_cards (
    id              TEXT     PRIMARY KEY,
    deal_id         TEXT     NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    analysis_run_id TEXT     NULL REFERENCES analysis_runs(id) ON DELETE SET NULL,
    card_type       TEXT     NOT NULL CHECK (card_type IN
                    ('rent_market','price_market','land_price','demographics','hazard','liquidity')),
    title           TEXT     NOT NULL,
    summary         TEXT     NOT NULL,
    payload_json    TEXT     NULL,
    confidence      TEXT     NOT NULL DEFAULT 'unknown'
                    CHECK (confidence IN ('high','medium','low','unknown')),
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_evidence_deal ON market_evidence_cards (deal_id, card_type);


-- ============================================================
-- 7. investment_memos
-- ============================================================
CREATE TABLE IF NOT EXISTS investment_memos (
    id                  TEXT     PRIMARY KEY,
    deal_id             TEXT     NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    analysis_run_id     TEXT     NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    memo_markdown       TEXT     NOT NULL,
    memo_snapshot_json  TEXT     NOT NULL,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_memos_deal ON investment_memos (deal_id, created_at DESC);


-- ============================================================
-- 8. watchlist_items
-- ============================================================
CREATE TABLE IF NOT EXISTS watchlist_items (
    id                   TEXT     PRIMARY KEY,
    user_id              TEXT     NULL,
    deal_id              TEXT     NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    watch_status         TEXT     NOT NULL DEFAULT 'active'
                         CHECK (watch_status IN ('active','paused','removed')),
    target_bid_price     INTEGER  NULL,
    latest_asking_price  INTEGER  NULL,
    last_checked_at      DATETIME NULL,
    created_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_watchlist_user ON watchlist_items (user_id, updated_at DESC) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_watchlist_deal ON watchlist_items (deal_id);
