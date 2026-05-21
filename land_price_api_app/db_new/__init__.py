"""
db.py
DuckDB への保存・読込・集計を担う層。

テーブル: land_prices_public_notice
主キー相当: (point_id, year)
upsert: 既存行を削除して再挿入（DuckDB は INSERT OR REPLACE 非対応のため）
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import duckdb
import pandas as pd

from config import DUCKDB_PATH, get_logger

logger = get_logger(__name__)


def _wal_path_for_db(db_path: Path) -> Path:
    return db_path.parent / f"{db_path.name}.wal"


def _is_wal_replay_error(exc: Exception) -> bool:
    msg = str(exc)
    return "Failure while replaying WAL file" in msg


def _quarantine_corrupt_wal(db_path: Path) -> Optional[Path]:
    wal_path = _wal_path_for_db(db_path)
    if not wal_path.exists():
        return None
    backup_dir = db_path.parent / "recovery_backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = backup_dir / f"{db_path.name}.wal.corrupt_{timestamp}"
    wal_path.replace(target)
    return target

# --------------------------------------------------------------------------
# DDL
# --------------------------------------------------------------------------

_DDL_MAIN = """
CREATE TABLE IF NOT EXISTS land_prices_public_notice (
    point_id                     VARCHAR NOT NULL,
    year                         INTEGER NOT NULL,
    price_classification         INTEGER,
    survey_source                VARCHAR,
    prefecture_code              VARCHAR,
    prefecture_name              VARCHAR,
    city_code                    VARCHAR,
    city_name                    VARCHAR,
    standard_land_number         VARCHAR,
    location_text                VARCHAR,
    price_yen_per_sqm            DOUBLE,
    last_year_price_yen_per_sqm  DOUBLE,
    yoy_change_pct               DOUBLE,
    area_sqm                     DOUBLE,
    use_category_code            VARCHAR,
    use_category_name            VARCHAR,
    usage_status_name            VARCHAR,
    building_structure_name      VARCHAR,
    current_use_name             VARCHAR,
    front_road_name              VARCHAR,
    zoning_name                  VARCHAR,
    building_coverage_ratio      DOUBLE,
    floor_area_ratio             DOUBLE,
    lon                          DOUBLE,
    lat                          DOUBLE,
    raw_properties               VARCHAR,
    PRIMARY KEY (point_id, year)
)
"""

_DDL_CITY_SUMMARY = """
CREATE OR REPLACE VIEW city_summary AS
SELECT
    year,
    prefecture_code,
    prefecture_name,
    city_code,
    city_name,
    use_category_name,
    COUNT(*)                        AS point_count,
    AVG(price_yen_per_sqm)          AS avg_price,
    MEDIAN(price_yen_per_sqm)       AS median_price,
    MAX(price_yen_per_sqm)          AS max_price,
    MIN(price_yen_per_sqm)          AS min_price,
    AVG(yoy_change_pct)             AS avg_yoy_pct
FROM land_prices_public_notice
WHERE price_yen_per_sqm IS NOT NULL
GROUP BY year, prefecture_code, prefecture_name,
         city_code, city_name, use_category_name
"""

_DDL_PREF_SUMMARY = """
CREATE OR REPLACE VIEW pref_summary AS
SELECT
    year,
    prefecture_code,
    prefecture_name,
    COUNT(*)                        AS point_count,
    AVG(price_yen_per_sqm)          AS avg_price,
    MEDIAN(price_yen_per_sqm)       AS median_price,
    AVG(yoy_change_pct)             AS avg_yoy_pct
FROM land_prices_public_notice
WHERE price_yen_per_sqm IS NOT NULL
GROUP BY year, prefecture_code, prefecture_name
"""

_DDL_TRADE = """
CREATE TABLE IF NOT EXISTS trade_prices (
    trade_id                    VARCHAR NOT NULL,
    year                        INTEGER NOT NULL,
    quarter                     INTEGER NOT NULL,
    trade_type                  VARCHAR,
    prefecture_code             VARCHAR,
    prefecture_name             VARCHAR,
    city_code                   VARCHAR,
    city_name                   VARCHAR,
    district_name               VARCHAR,
    trade_price_total           DOUBLE,
    trade_price_per_sqm         DOUBLE,
    area_sqm                    DOUBLE,
    floor_plan                  VARCHAR,
    land_shape                  VARCHAR,
    frontage                    DOUBLE,
    total_floor_area_sqm        DOUBLE,
    build_year                  INTEGER,
    building_structure          VARCHAR,
    use_name                    VARCHAR,
    purpose_name                VARCHAR,
    front_road_direction        VARCHAR,
    front_road_type             VARCHAR,
    front_road_breadth          DOUBLE,
    city_planning               VARCHAR,
    coverage_ratio              DOUBLE,
    floor_area_ratio            DOUBLE,
    renovation                  VARCHAR,
    remarks                     VARCHAR,
    period_str                  VARCHAR,
    lon                         DOUBLE,
    lat                         DOUBLE,
    raw_properties              VARCHAR,
    PRIMARY KEY (trade_id, year, quarter)
)
"""

_DDL_TRADE_CITY_SUMMARY = """
CREATE OR REPLACE VIEW trade_city_summary AS
SELECT
    year,
    quarter,
    prefecture_code,
    prefecture_name,
    city_code,
    city_name,
    trade_type,
    COUNT(*)                         AS trade_count,
    AVG(trade_price_per_sqm)         AS avg_price_per_sqm,
    MEDIAN(trade_price_per_sqm)      AS median_price_per_sqm,
    AVG(trade_price_total)           AS avg_total_price,
    AVG(area_sqm)                    AS avg_area_sqm
FROM trade_prices
WHERE trade_price_per_sqm IS NOT NULL
GROUP BY year, quarter, prefecture_code, prefecture_name,
         city_code, city_name, trade_type
"""

_DDL_SYNC_LOG = """
CREATE TABLE IF NOT EXISTS sync_log (
    id           INTEGER PRIMARY KEY,
    year         INTEGER,
    z            INTEGER,
    started_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at  TIMESTAMP,
    tile_count   INTEGER DEFAULT 0,
    feature_count INTEGER DEFAULT 0,
    status       VARCHAR DEFAULT 'running'
)
"""

_DDL_RENT_MARKET = """
CREATE TABLE IF NOT EXISTS rent_market (
    city_code       VARCHAR NOT NULL,
    survey_year     INTEGER NOT NULL,
    ownership_type  VARCHAR NOT NULL,
    rent_per_sqm    DOUBLE,
    PRIMARY KEY (city_code, survey_year, ownership_type)
)
"""

_DDL_SUUMO_RENT_MARKET = """
CREATE TABLE IF NOT EXISTS suumo_rent_market (
    source              VARCHAR NOT NULL,
    prefecture_slug     VARCHAR NOT NULL,
    prefecture_code     VARCHAR,
    prefecture_name     VARCHAR,
    city_name           VARCHAR NOT NULL,
    property_type       VARCHAR NOT NULL,
    property_type_label VARCHAR NOT NULL,
    floor_plan_bucket   VARCHAR NOT NULL,
    monthly_rent_yen    DOUBLE,
    updated_date        DATE,
    source_url          VARCHAR,
    fetched_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source, prefecture_slug, city_name, property_type, floor_plan_bucket)
)
"""

_DDL_LISTING_MASTER = """
CREATE TABLE IF NOT EXISTS listing_master (
    listing_id               VARCHAR NOT NULL,
    source                   VARCHAR NOT NULL,
    source_property_id       VARCHAR,
    source_url               VARCHAR NOT NULL,
    region_label             VARCHAR,
    property_name            VARCHAR,
    address                  VARCHAR,
    city_code                VARCHAR,
    lat                      DOUBLE,
    lon                      DOUBLE,
    asking_price_yen         BIGINT,
    gross_rent_monthly_yen   BIGINT,
    gross_rent_annual_yen    BIGINT,
    gross_yield_pct          DOUBLE,
    build_year_month         VARCHAR,
    age_years                INTEGER,
    structure                VARCHAR,
    property_type            VARCHAR,
    building_area_sqm        DOUBLE,
    land_area_sqm            DOUBLE,
    land_rights              VARCHAR,
    legal_far_pct            DOUBLE,
    bcr_pct                  DOUBLE,
    num_units                INTEGER,
    road_frontage            VARCHAR,
    nearest_station          VARCHAR,
    station_walk_min         INTEGER,
    floor_plan               VARCHAR,
    num_floors               INTEGER,
    land_category            VARCHAR,
    city_planning_area       VARCHAR,
    updated_date             VARCHAR,
    transaction_type         VARCHAR,
    listing_date             VARCHAR,
    platform                 VARCHAR,
    extraction_confidence    VARCHAR,
    raw_extraction_json      VARCHAR,
    llm_filled_fields_json   VARCHAR,
    first_seen_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (listing_id)
)
"""

_DDL_LISTING_RAW = """
CREATE TABLE IF NOT EXISTS listing_raw (
    raw_id                    VARCHAR NOT NULL,
    source                    VARCHAR NOT NULL,
    source_property_id        VARCHAR,
    source_url                VARCHAR NOT NULL,
    region_label              VARCHAR,
    fetched_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    html_hash                 VARCHAR,
    html_text                 VARCHAR,
    extraction_json           VARCHAR,
    status                    VARCHAR DEFAULT 'fetched',
    error_message             VARCHAR,
    PRIMARY KEY (raw_id)
)
"""

_DDL_LOCATION_FEATURES = """
CREATE TABLE IF NOT EXISTS location_features (
    location_key                 VARCHAR NOT NULL,
    lat                          DOUBLE NOT NULL,
    lon                          DOUBLE NOT NULL,
    city_code                    VARCHAR,
    feature_version              INTEGER DEFAULT 1,
    facility_radius_m            INTEGER,
    terrain_radius_m             INTEGER,
    convenience_count_500m       INTEGER,
    convenience_count_1000m      INTEGER,
    convenience_nearest_m        DOUBLE,
    supermarket_count_500m       INTEGER,
    supermarket_count_1000m      INTEGER,
    supermarket_nearest_m        DOUBLE,
    transit_count_500m           INTEGER,
    transit_count_1000m          INTEGER,
    transit_nearest_m            DOUBLE,
    pachinko_count_500m          INTEGER,
    pachinko_count_1000m         INTEGER,
    pachinko_nearest_m           DOUBLE,
    food_count_500m              INTEGER,
    food_count_1000m             INTEGER,
    food_nearest_m               DOUBLE,
    school_count_500m            INTEGER,
    school_count_1000m           INTEGER,
    school_nearest_m             DOUBLE,
    medical_count_500m           INTEGER,
    medical_count_1000m          INTEGER,
    medical_nearest_m            DOUBLE,
    park_count_500m              INTEGER,
    park_count_1000m             INTEGER,
    park_nearest_m               DOUBLE,
    elevation_m                  DOUBLE,
    elevation_band               VARCHAR,
    elevation_source             VARCHAR,
    nearest_water_m              DOUBLE,
    water_count_1000m            INTEGER,
    fetched_at                   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (location_key)
)
"""

_DDL_LISTING_FEATURE_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS listing_feature_snapshots (
    listing_id                         VARCHAR NOT NULL,
    snapshot_date                      DATE NOT NULL,
    location_key                       VARCHAR,
    feature_version                    INTEGER DEFAULT 1,
    asking_price_yen                   BIGINT,
    unit_area_basis                    VARCHAR,
    unit_area_sqm                      DOUBLE,
    unit_price_yen_per_sqm             DOUBLE,
    nearby_land_count                  INTEGER,
    nearby_trade_count                 INTEGER,
    land_unit_price_p25_yen_per_sqm    DOUBLE,
    land_unit_price_p75_yen_per_sqm    DOUBLE,
    trade_unit_price_median_yen_per_sqm DOUBLE,
    public_notice_gap_pct              DOUBLE,
    trade_gap_pct                      DOUBLE,
    land_price_estimate_low_yen        DOUBLE,
    land_price_estimate_high_yen       DOUBLE,
    building_residual_low_yen          DOUBLE,
    building_residual_high_yen         DOUBLE,
    saved_at                           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (listing_id, snapshot_date)
)
"""

_DDL_VALUATION_RESULTS = """
CREATE TABLE IF NOT EXISTS valuation_results (
    listing_id                  VARCHAR NOT NULL,
    valuation_date              DATE NOT NULL,
    valuation_version           INTEGER DEFAULT 1,
    model_name                  VARCHAR DEFAULT 'rules_v1',
    fair_value_yen              DOUBLE,
    gap_pct                     DOUBLE,
    adjusted_gap_pct            DOUBLE,
    cheap_or_expensive          VARCHAR,
    confidence                  VARCHAR,
    life_convenience_score      DOUBLE,
    family_score                DOUBLE,
    negative_facility_score     DOUBLE,
    terrain_caution_score       DOUBLE,
    reasons_json                VARCHAR,
    saved_at                    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (listing_id, valuation_date)
)
"""

_DDL_PUBLIC_NOTICE_LOCATION_FEATURES = """
CREATE TABLE IF NOT EXISTS public_notice_location_features (
    point_id                    VARCHAR NOT NULL,
    year                        INTEGER NOT NULL,
    location_key                VARCHAR NOT NULL,
    feature_version             INTEGER DEFAULT 1,
    computed_at                 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (point_id, year)
)
"""

_DDL_TRADE_LOCATION_FEATURES = """
CREATE TABLE IF NOT EXISTS trade_location_features (
    trade_id                    VARCHAR NOT NULL,
    year                        INTEGER NOT NULL,
    quarter                     INTEGER NOT NULL,
    location_key                VARCHAR NOT NULL,
    feature_version             INTEGER DEFAULT 1,
    computed_at                 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_id, year, quarter)
)
"""

_DDL_SEARCH_JOBS = """
CREATE TABLE IF NOT EXISTS search_jobs (
    job_id                      VARCHAR NOT NULL,
    source                      VARCHAR NOT NULL,
    search_url                  VARCHAR NOT NULL,
    region_label                VARCHAR,
    status                      VARCHAR,
    max_pages                   INTEGER,
    max_listings                INTEGER,
    collected_pages             INTEGER DEFAULT 0,
    collected_urls              INTEGER DEFAULT 0,
    imported_done               INTEGER DEFAULT 0,
    imported_failed             INTEGER DEFAULT 0,
    feature_done                INTEGER DEFAULT 0,
    feature_failed              INTEGER DEFAULT 0,
    error_message               VARCHAR,
    started_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at                 TIMESTAMP,
    PRIMARY KEY (job_id)
)
"""

_DDL_SEARCH_RESULT_URLS = """
CREATE TABLE IF NOT EXISTS search_result_urls (
    job_id                      VARCHAR NOT NULL,
    detail_url                  VARCHAR NOT NULL,
    page_no                     INTEGER,
    position                    INTEGER,
    collected_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (job_id, detail_url)
)
"""

_DDL_FACILITY_POIS = """
CREATE TABLE IF NOT EXISTS facility_pois (
    location_key                VARCHAR NOT NULL,
    category                    VARCHAR NOT NULL,
    osm_type                    VARCHAR,
    osm_id                      VARCHAR,
    name                        VARCHAR,
    brand                       VARCHAR,
    operator                    VARCHAR,
    lat                         DOUBLE NOT NULL,
    lon                         DOUBLE NOT NULL,
    distance_m                  DOUBLE,
    fetched_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

_DDL_WATER_FEATURES = """
CREATE TABLE IF NOT EXISTS water_features (
    location_key                VARCHAR NOT NULL,
    osm_type                    VARCHAR,
    osm_id                      VARCHAR,
    name                        VARCHAR,
    type_label                  VARCHAR,
    lat                         DOUBLE NOT NULL,
    lon                         DOUBLE NOT NULL,
    distance_m                  DOUBLE,
    fetched_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

_DDL_POPULATION_STATS = """
CREATE TABLE IF NOT EXISTS population_stats (
    city_code               VARCHAR NOT NULL,
    survey_year             INTEGER NOT NULL,
    total_population        BIGINT,
    households              BIGINT,
    pop_change_pct          DOUBLE,
    households_change_pct   DOUBLE,
    aging_rate              DOUBLE,
    net_migration           BIGINT,
    PRIMARY KEY (city_code, survey_year)
)
"""

# --------------------------------------------------------------------------
# 接続
# --------------------------------------------------------------------------

def get_connection(
    db_path: Optional[Path] = None,
    read_only: bool = False,
) -> duckdb.DuckDBPyConnection:
    """
    DuckDB 接続を返す。

    Parameters
    ----------
    db_path : Path, optional
        DB ファイルパス。省略時は config.DUCKDB_PATH を使用。
    read_only : bool
        True の場合、読み取り専用で接続する。
        ノートブックなど複数プロセスから同時参照する場合に使用。

    Returns
    -------
    duckdb.DuckDBPyConnection
    """
    path = db_path or DUCKDB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        conn = duckdb.connect(str(path), read_only=read_only)
    except duckdb.IOException:
        # 書き込みロックが取れない場合は read_only にフォールバック
        logger.warning(
            "書き込みロック取得失敗。read_only モードで接続します: %s", path
        )
        conn = duckdb.connect(str(path), read_only=True)
    except Exception as exc:
        if not _is_wal_replay_error(exc):
            raise
        recovered_wal = _quarantine_corrupt_wal(path)
        if recovered_wal is None:
            raise
        logger.error(
            "WAL 再生に失敗したため退避しました: %s -> %s",
            _wal_path_for_db(path),
            recovered_wal,
        )
        conn = duckdb.connect(str(path), read_only=read_only)
    logger.debug("DuckDB 接続: %s (read_only=%s)", path, read_only)
    return conn


# --------------------------------------------------------------------------
# テーブル初期化
# --------------------------------------------------------------------------

def create_tables_if_needed(conn: duckdb.DuckDBPyConnection) -> None:
    """必要なテーブル・ビューを作成する（冪等）。"""
    conn.execute(_DDL_MAIN)
    conn.execute(_DDL_CITY_SUMMARY)
    conn.execute(_DDL_PREF_SUMMARY)
    conn.execute(_DDL_SYNC_LOG)
    conn.execute(_DDL_TRADE)
    conn.execute(_DDL_TRADE_CITY_SUMMARY)
    conn.execute(_DDL_RENT_MARKET)
    conn.execute(_DDL_SUUMO_RENT_MARKET)
    conn.execute(_DDL_LISTING_RAW)
    conn.execute(_DDL_LISTING_MASTER)
    conn.execute(_DDL_LOCATION_FEATURES)
    conn.execute(_DDL_LISTING_FEATURE_SNAPSHOTS)
    conn.execute(_DDL_VALUATION_RESULTS)
    conn.execute(_DDL_PUBLIC_NOTICE_LOCATION_FEATURES)
    conn.execute(_DDL_TRADE_LOCATION_FEATURES)
    conn.execute(_DDL_SEARCH_JOBS)
    conn.execute(_DDL_SEARCH_RESULT_URLS)
    conn.execute(_DDL_FACILITY_POIS)
    conn.execute(_DDL_WATER_FEATURES)
    conn.execute(_DDL_POPULATION_STATS)
    _migrate_feature_tables(conn)
    logger.debug("テーブル初期化完了")


# --------------------------------------------------------------------------
# Upsert
# --------------------------------------------------------------------------

def upsert_land_prices(
    conn: duckdb.DuckDBPyConnection,
    df: pd.DataFrame,
) -> int:
    """
    land_prices_public_notice テーブルへ DataFrame を upsert する。

    同一 (point_id, year) の既存行を削除してから挿入する方式。
    Returns 挿入件数。
    """
    if df.empty:
        return 0

    # テーブルに存在するカラムのみ残す
    table_cols = _get_table_columns(conn)
    df_to_insert = _align_df_to_schema(df, table_cols)

    # DELETE + INSERT（upsert 代替）
    keys_df = df_to_insert[["point_id", "year"]].drop_duplicates()
    # 一時テーブルに key を登録してから DELETE
    conn.execute("CREATE TEMP TABLE IF NOT EXISTS _upsert_keys (point_id VARCHAR, year INTEGER)")
    conn.execute("DELETE FROM _upsert_keys")
    conn.execute("INSERT INTO _upsert_keys SELECT point_id, year FROM keys_df")
    conn.execute(
        """
        DELETE FROM land_prices_public_notice
        WHERE (point_id, year) IN (SELECT point_id, year FROM _upsert_keys)
        """
    )
    conn.execute(
        "INSERT INTO land_prices_public_notice SELECT * FROM df_to_insert"
    )
    inserted = len(df_to_insert)
    logger.debug("upsert: %d 件挿入", inserted)
    return inserted


def _get_table_columns(conn: duckdb.DuckDBPyConnection, table_name: str = "land_prices_public_notice") -> list[str]:
    """テーブルのカラム名リストを返す。"""
    result = conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = ? "
        "ORDER BY ordinal_position",
        [table_name],
    ).fetchall()
    return [r[0] for r in result]


def _align_df_to_schema(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """DataFrame をテーブルスキーマに合わせる（不足列は None、余剰列は除外）。"""
    for col in cols:
        if col not in df.columns:
            df = df.copy()
            df[col] = None
    return df[cols]


def make_location_key(lat: float, lon: float, precision: int = 5) -> str:
    """座標丸めベースの location_key を返す。"""
    return f"{round(float(lat), precision):.{precision}f},{round(float(lon), precision):.{precision}f}"


def _normalize_json_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _migrate_feature_tables(conn: duckdb.DuckDBPyConnection) -> None:
    """後方互換のため listing/location 系テーブルへ不足列を追加する。"""
    statements = [
        "ALTER TABLE location_features ADD COLUMN IF NOT EXISTS life_convenience_score DOUBLE",
        "ALTER TABLE location_features ADD COLUMN IF NOT EXISTS family_score DOUBLE",
        "ALTER TABLE location_features ADD COLUMN IF NOT EXISTS negative_facility_score DOUBLE",
        "ALTER TABLE location_features ADD COLUMN IF NOT EXISTS terrain_caution_score DOUBLE",
        "ALTER TABLE location_features ADD COLUMN IF NOT EXISTS flood_risk_flag BOOLEAN",
        "ALTER TABLE location_features ADD COLUMN IF NOT EXISTS flood_depth_rank VARCHAR",
        "ALTER TABLE location_features ADD COLUMN IF NOT EXISTS landslide_risk_flag BOOLEAN",
        "ALTER TABLE location_features ADD COLUMN IF NOT EXISTS hazard_source_summary VARCHAR",
        "ALTER TABLE listing_master ADD COLUMN IF NOT EXISTS region_label VARCHAR",
        "ALTER TABLE listing_feature_snapshots ADD COLUMN IF NOT EXISTS unit_area_basis VARCHAR",
        "ALTER TABLE listing_feature_snapshots ADD COLUMN IF NOT EXISTS unit_area_sqm DOUBLE",
        "ALTER TABLE listing_feature_snapshots ADD COLUMN IF NOT EXISTS unit_price_yen_per_sqm DOUBLE",
        "ALTER TABLE listing_feature_snapshots ADD COLUMN IF NOT EXISTS public_notice_gap_pct DOUBLE",
        "ALTER TABLE listing_feature_snapshots ADD COLUMN IF NOT EXISTS trade_gap_pct DOUBLE",
    ]
    for stmt in statements:
        conn.execute(stmt)


# --------------------------------------------------------------------------
# 読込
# --------------------------------------------------------------------------

def read_land_prices(
    conn: duckdb.DuckDBPyConnection,
    filters: Optional[dict[str, Any]] = None,
    limit: Optional[int] = None,
) -> pd.DataFrame:
    """
    land_prices_public_notice からデータを読み込む。

    Parameters
    ----------
    filters : dict, optional
        {'year': 2026, 'prefecture_code': '13', 'city_code': '13101',
         'use_category_code': '01'}
        None の値は無視する。
    limit : int, optional
        最大取得件数。

    Returns
    -------
    pd.DataFrame
    """
    where_clauses: list[str] = []
    params: list[Any] = []

    if filters:
        for col, val in filters.items():
            if val is None:
                continue
            if col == "min_price":
                where_clauses.append("price_yen_per_sqm >= ?")
                params.append(val)
            elif col == "max_price":
                where_clauses.append("price_yen_per_sqm <= ?")
                params.append(val)
            elif isinstance(val, (list, tuple)):
                placeholders = ", ".join(["?"] * len(val))
                where_clauses.append(f"{col} IN ({placeholders})")
                params.extend(val)
            else:
                where_clauses.append(f"{col} = ?")
                params.append(val)

    query = "SELECT * FROM land_prices_public_notice"
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    query += " ORDER BY year DESC, prefecture_code, city_code, point_id"
    if limit:
        query += f" LIMIT {limit}"

    df = conn.execute(query, params).df()
    logger.debug("read_land_prices: %d 件", len(df))
    return df


def get_point_history(
    conn: duckdb.DuckDBPyConnection,
    point_id: str,
) -> pd.DataFrame:
    """point_id の全年度データを年昇順で返す。"""
    df = conn.execute(
        "SELECT * FROM land_prices_public_notice "
        "WHERE point_id = ? ORDER BY year",
        [point_id],
    ).df()
    return df


def get_city_history(
    conn: duckdb.DuckDBPyConnection,
    city_name: str,
) -> pd.DataFrame:
    """city_summary から市区町村の年次加重平均を返す。"""
    return conn.execute(
        """SELECT year,
               SUM(avg_price * point_count) / SUM(point_count) AS avg_price,
               SUM(avg_yoy_pct * point_count) / SUM(point_count) AS avg_yoy_pct,
               SUM(point_count) AS point_count
          FROM city_summary WHERE city_name = ?
          GROUP BY year ORDER BY year""",
        [city_name],
    ).df()


def get_city_summary(
    conn: duckdb.DuckDBPyConnection,
    year: Optional[int] = None,
) -> pd.DataFrame:
    """city_summary ビューを返す（year 指定時はフィルタ）。"""
    if year:
        return conn.execute(
            "SELECT * FROM city_summary WHERE year = ? ORDER BY avg_price DESC",
            [year],
        ).df()
    return conn.execute("SELECT * FROM city_summary ORDER BY year DESC, avg_price DESC").df()


# --------------------------------------------------------------------------
# 利用可能な年一覧
# --------------------------------------------------------------------------

def get_available_years(conn: duckdb.DuckDBPyConnection) -> list[int]:
    """DB に存在する年度一覧を降順で返す。"""
    rows = conn.execute(
        "SELECT DISTINCT year FROM land_prices_public_notice ORDER BY year DESC"
    ).fetchall()
    return [r[0] for r in rows]


def get_multiyear_city_summary(
    conn: duckdb.DuckDBPyConnection,
    pref_codes: list[str],
    year_range: tuple[int, int],
    use_category_name: Optional[str] = None,
) -> pd.DataFrame:
    """
    city_summary VIEW から複数都道府県・年範囲のデータを返す。

    生データではなく集計済みビューを使用するため高速。
    7都府県×20年≈28,000行程度のため、都市トレンドタブのキャッシュ対象。

    Parameters
    ----------
    pref_codes : list[str]
        都道府県コードのリスト（例: ["47", "13"]）
    year_range : tuple[int, int]
        (開始年, 終了年)
    use_category_name : str, optional
        用途区分名でフィルタ（例: "住宅地"）。None の場合は全用途。
    """
    if not pref_codes:
        return pd.DataFrame()

    placeholders = ", ".join(["?"] * len(pref_codes))
    params: list[Any] = list(pref_codes) + [year_range[0], year_range[1]]

    query = (
        f"SELECT * FROM city_summary "
        f"WHERE prefecture_code IN ({placeholders}) "
        f"AND year BETWEEN ? AND ?"
    )
    if use_category_name:
        query += " AND use_category_name = ?"
        params.append(use_category_name)

    query += " ORDER BY year, prefecture_code, city_code, use_category_name"

    df = conn.execute(query, params).df()
    logger.debug("get_multiyear_city_summary: %d 件 (prefs=%s, years=%s-%s)", len(df), pref_codes, *year_range)
    return df


def get_stats(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """DB の基本統計を返す。"""
    total = conn.execute(
        "SELECT COUNT(*) FROM land_prices_public_notice"
    ).fetchone()[0]
    years = get_available_years(conn)
    return {
        "total_records": total,
        "available_years": years,
        "year_counts": {
            r[0]: r[1]
            for r in conn.execute(
                "SELECT year, COUNT(*) FROM land_prices_public_notice GROUP BY year ORDER BY year DESC"
            ).fetchall()
        },
    }


# --------------------------------------------------------------------------
# 派生テーブル再構築
# --------------------------------------------------------------------------

def rebuild_derived_tables(conn: duckdb.DuckDBPyConnection) -> None:
    """ビューを再作成する（スキーマ変更後などに実行）。"""
    conn.execute(_DDL_CITY_SUMMARY)
    conn.execute(_DDL_PREF_SUMMARY)
    logger.info("派生テーブル（ビュー）を再構築しました")


# --------------------------------------------------------------------------
# DB スモークテスト
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# 取引価格 (trade_prices) 操作
# --------------------------------------------------------------------------

def upsert_trade_prices(
    conn: duckdb.DuckDBPyConnection,
    df: pd.DataFrame,
) -> int:
    """trade_prices テーブルへ DataFrame を upsert する。"""
    if df.empty:
        return 0

    cols = conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'trade_prices' ORDER BY ordinal_position"
    ).fetchall()
    table_cols = [r[0] for r in cols]

    df_to_insert = _align_df_to_schema(df.copy(), table_cols)

    keys_df = df_to_insert[["trade_id", "year", "quarter"]].drop_duplicates()
    conn.execute(
        "CREATE TEMP TABLE IF NOT EXISTS _trade_upsert_keys "
        "(trade_id VARCHAR, year INTEGER, quarter INTEGER)"
    )
    conn.execute("DELETE FROM _trade_upsert_keys")
    conn.execute("INSERT INTO _trade_upsert_keys SELECT trade_id, year, quarter FROM keys_df")
    conn.execute(
        "DELETE FROM trade_prices WHERE (trade_id, year, quarter) IN "
        "(SELECT trade_id, year, quarter FROM _trade_upsert_keys)"
    )
    conn.execute("INSERT INTO trade_prices SELECT * FROM df_to_insert")
    inserted = len(df_to_insert)
    logger.debug("trade_prices upsert: %d 件", inserted)
    return inserted


def read_trade_prices(
    conn: duckdb.DuckDBPyConnection,
    filters: Optional[dict[str, Any]] = None,
    limit: Optional[int] = None,
) -> pd.DataFrame:
    """
    trade_prices からデータを読み込む。

    filters に対応するキー: year, quarter, prefecture_code, city_code, trade_type,
                            min_price (trade_price_per_sqm >=), max_price (<= )
    """
    where_clauses: list[str] = []
    params: list[Any] = []

    if filters:
        for col, val in filters.items():
            if val is None:
                continue
            if col == "min_price":
                where_clauses.append("trade_price_per_sqm >= ?")
                params.append(val)
            elif col == "max_price":
                where_clauses.append("trade_price_per_sqm <= ?")
                params.append(val)
            elif isinstance(val, (list, tuple)):
                placeholders = ", ".join(["?"] * len(val))
                where_clauses.append(f"{col} IN ({placeholders})")
                params.extend(val)
            else:
                where_clauses.append(f"{col} = ?")
                params.append(val)

    query = "SELECT * FROM trade_prices"
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    query += " ORDER BY year DESC, quarter DESC, prefecture_code, city_code"
    if limit:
        query += f" LIMIT {limit}"

    df = conn.execute(query, params).df()
    logger.debug("read_trade_prices: %d 件", len(df))
    return df


def get_trade_available_years(conn: duckdb.DuckDBPyConnection) -> list[int]:
    """trade_prices に存在する年度一覧を降順で返す。"""
    rows = conn.execute(
        "SELECT DISTINCT year FROM trade_prices ORDER BY year DESC"
    ).fetchall()
    return [r[0] for r in rows]


def read_trade_prices_by_city(
    conn: duckdb.DuckDBPyConnection,
    city_name: Optional[str] = None,
    prefecture_name: Optional[str] = None,
    year: Optional[int] = None,
    limit: int = 100,
) -> pd.DataFrame:
    """
    市区町村名・都道府県名で取引価格を取得する。
    lat/lon が NULL で近傍検索できない場合のフォールバック用。
    """
    where_clauses: list[str] = []
    params: list[Any] = []

    if prefecture_name:
        where_clauses.append("prefecture_name = ?")
        params.append(prefecture_name)
    if city_name:
        where_clauses.append("city_name = ?")
        params.append(city_name)
    if year:
        where_clauses.append("year = ?")
        params.append(year)
    where_clauses.append("trade_price_per_sqm IS NOT NULL")
    where_clauses.append("trade_price_per_sqm > 0")

    query = "SELECT * FROM trade_prices WHERE " + " AND ".join(where_clauses)
    query += " ORDER BY year DESC, quarter DESC"
    query += f" LIMIT {limit}"

    return conn.execute(query, params).df()


def update_trade_latlon(
    conn: duckdb.DuckDBPyConnection,
    updates: list[dict],
) -> int:
    """
    trade_prices の lat/lon を一括更新する。

    Parameters
    ----------
    updates : list of {"prefecture_name": str, "city_name": str, "district_name": str, "lat": float, "lon": float}
    """
    updated = 0
    for u in updates:
        rows = conn.execute(
            """
            UPDATE trade_prices
            SET lat = ?, lon = ?
            WHERE prefecture_name = ?
              AND city_name = ?
              AND (district_name = ? OR (district_name IS NULL AND ? IS NULL))
              AND lat IS NULL
            """,
            [
                u["lat"],
                u["lon"],
                u["prefecture_name"],
                u["city_name"],
                u.get("district_name"),
                u.get("district_name"),
            ],
        ).rowcount
        updated += rows or 0
    logger.info("update_trade_latlon: %d 件更新", updated)
    return updated


def get_trade_ungeocoded_locations(
    conn: duckdb.DuckDBPyConnection,
    limit: int = 5000,
) -> pd.DataFrame:
    """lat IS NULL の (city_name, district_name, prefecture_name) ユニーク組み合わせを返す。"""
    return conn.execute(
        """
        SELECT DISTINCT city_name, district_name, prefecture_name
        FROM trade_prices
        WHERE lat IS NULL AND city_name IS NOT NULL
        LIMIT ?
        """,
        [limit],
    ).df()


# --------------------------------------------------------------------------
# 賃貸相場 (rent_market)
# --------------------------------------------------------------------------

def upsert_rent_market(conn: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> int:
    """rent_market テーブルに upsert する。df には city_code, survey_year, ownership_type, rent_per_sqm が必要。"""
    if df.empty:
        return 0
    for year in df["survey_year"].unique():
        conn.execute("DELETE FROM rent_market WHERE survey_year = ?", [int(year)])
    conn.execute("INSERT INTO rent_market SELECT city_code, survey_year, ownership_type, rent_per_sqm FROM df")
    n = len(df)
    logger.info("rent_market upsert: %d 件", n)
    return n


def get_rent_market(conn: duckdb.DuckDBPyConnection, city_code: str) -> pd.DataFrame:
    """指定市区町村の賃貸相場データを返す。"""
    return conn.execute(
        "SELECT survey_year, ownership_type, rent_per_sqm FROM rent_market WHERE city_code = ? ORDER BY survey_year DESC",
        [city_code],
    ).df()


def read_rent_market_overview(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """e-Stat 賃貸相場データを市区町村ラベル付きで返す。"""
    create_tables_if_needed(conn)
    return conn.execute(
        """
        WITH city_labels AS (
            SELECT
                city_code,
                MAX(city_name) AS city_name,
                MAX(prefecture_name) AS prefecture_name
            FROM (
                SELECT city_code, city_name, prefecture_name
                FROM land_prices_public_notice
                WHERE city_code IS NOT NULL
                UNION ALL
                SELECT city_code, city_name, prefecture_name
                FROM trade_prices
                WHERE city_code IS NOT NULL
            )
            GROUP BY city_code
        )
        SELECT
            r.city_code,
            SUBSTR(r.city_code, 1, 2) AS prefecture_code,
            cl.prefecture_name,
            cl.city_name,
            r.survey_year,
            r.ownership_type,
            r.rent_per_sqm
        FROM rent_market r
        LEFT JOIN city_labels cl ON r.city_code = cl.city_code
        ORDER BY r.survey_year DESC, r.rent_per_sqm DESC
        """
    ).df()


def upsert_suumo_rent_market(conn: duckdb.DuckDBPyConnection, df: pd.DataFrame, *, prefecture_slug: str) -> int:
    """SUUMO 家賃相場データを都道府県単位で置き換える。"""
    create_tables_if_needed(conn)
    conn.execute(
        "DELETE FROM suumo_rent_market WHERE source = 'suumo' AND prefecture_slug = ?",
        [prefecture_slug],
    )
    if df.empty:
        return 0
    payload = _align_df_to_schema(df, _get_table_columns(conn, "suumo_rent_market"))
    conn.execute("INSERT INTO suumo_rent_market SELECT * FROM payload")
    n = len(payload)
    logger.info("suumo_rent_market upsert: %d 件 (%s)", n, prefecture_slug)
    return n


def read_suumo_rent_market(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """保存済み SUUMO 家賃相場データを返す。"""
    create_tables_if_needed(conn)
    return conn.execute(
        """
        SELECT *
        FROM suumo_rent_market
        ORDER BY updated_date DESC NULLS LAST, prefecture_code, city_name, property_type, floor_plan_bucket
        """
    ).df()


def get_trade_city_summary(
    conn: duckdb.DuckDBPyConnection,
    year: Optional[int] = None,
    pref_codes: Optional[list[str]] = None,
) -> pd.DataFrame:
    """trade_city_summary ビューを返す。"""
    where_clauses: list[str] = []
    params: list[Any] = []
    if year:
        where_clauses.append("year = ?")
        params.append(year)
    if pref_codes:
        placeholders = ", ".join(["?"] * len(pref_codes))
        where_clauses.append(f"prefecture_code IN ({placeholders})")
        params.extend(pref_codes)

    query = "SELECT * FROM trade_city_summary"
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    query += " ORDER BY year DESC, quarter DESC, avg_price_per_sqm DESC"
    return conn.execute(query, params).df()


# --------------------------------------------------------------------------
# 掲載物件・特徴量
# --------------------------------------------------------------------------

def upsert_listing_master(
    conn: duckdb.DuckDBPyConnection,
    listing: dict[str, Any],
) -> str:
    """listing_master に 1 件 upsert する。"""
    create_tables_if_needed(conn)
    listing_id = str(listing["listing_id"])
    row = dict(listing)
    row["listing_id"] = listing_id
    row["raw_extraction_json"] = _normalize_json_text(row.get("raw_extraction_json"))
    row["llm_filled_fields_json"] = _normalize_json_text(row.get("llm_filled_fields_json"))

    row_df = pd.DataFrame([row])
    table_cols = _get_table_columns(conn, "listing_master")
    row_df = _align_df_to_schema(row_df, table_cols)

    existing = conn.execute(
        "SELECT first_seen_at FROM listing_master WHERE listing_id = ?",
        [listing_id],
    ).fetchone()
    first_seen_at = existing[0] if existing else None

    if existing:
        conn.execute("DELETE FROM listing_master WHERE listing_id = ?", [listing_id])
        row_df["first_seen_at"] = first_seen_at
        row_df["last_seen_at"] = None
        conn.execute(
            """
            INSERT INTO listing_master (
                listing_id,
                source,
                source_property_id,
                source_url,
                region_label,
                property_name,
                address,
                city_code,
                lat,
                lon,
                asking_price_yen,
                gross_rent_monthly_yen,
                gross_rent_annual_yen,
                gross_yield_pct,
                build_year_month,
                age_years,
                structure,
                property_type,
                building_area_sqm,
                land_area_sqm,
                land_rights,
                legal_far_pct,
                bcr_pct,
                num_units,
                road_frontage,
                nearest_station,
                station_walk_min,
                floor_plan,
                num_floors,
                land_category,
                city_planning_area,
                updated_date,
                transaction_type,
                listing_date,
                platform,
                extraction_confidence,
                raw_extraction_json,
                llm_filled_fields_json,
                first_seen_at,
                last_seen_at
            )
            SELECT
                listing_id,
                source,
                source_property_id,
                source_url,
                region_label,
                property_name,
                address,
                city_code,
                lat,
                lon,
                asking_price_yen,
                gross_rent_monthly_yen,
                gross_rent_annual_yen,
                gross_yield_pct,
                build_year_month,
                age_years,
                structure,
                property_type,
                building_area_sqm,
                land_area_sqm,
                land_rights,
                legal_far_pct,
                bcr_pct,
                num_units,
                road_frontage,
                nearest_station,
                station_walk_min,
                floor_plan,
                num_floors,
                land_category,
                city_planning_area,
                updated_date,
                transaction_type,
                listing_date,
                platform,
                extraction_confidence,
                raw_extraction_json,
                llm_filled_fields_json,
                COALESCE(first_seen_at, CURRENT_TIMESTAMP),
                CURRENT_TIMESTAMP
            FROM row_df
            """
        )
    else:
        row_df["first_seen_at"] = None
        row_df["last_seen_at"] = None
        conn.execute(
            """
            INSERT INTO listing_master (
                listing_id,
                source,
                source_property_id,
                source_url,
                region_label,
                property_name,
                address,
                city_code,
                lat,
                lon,
                asking_price_yen,
                gross_rent_monthly_yen,
                gross_rent_annual_yen,
                gross_yield_pct,
                build_year_month,
                age_years,
                structure,
                property_type,
                building_area_sqm,
                land_area_sqm,
                land_rights,
                legal_far_pct,
                bcr_pct,
                num_units,
                road_frontage,
                nearest_station,
                station_walk_min,
                floor_plan,
                num_floors,
                land_category,
                city_planning_area,
                updated_date,
                transaction_type,
                listing_date,
                platform,
                extraction_confidence,
                raw_extraction_json,
                llm_filled_fields_json,
                first_seen_at,
                last_seen_at
            )
            SELECT
                listing_id,
                source,
                source_property_id,
                source_url,
                region_label,
                property_name,
                address,
                city_code,
                lat,
                lon,
                asking_price_yen,
                gross_rent_monthly_yen,
                gross_rent_annual_yen,
                gross_yield_pct,
                build_year_month,
                age_years,
                structure,
                property_type,
                building_area_sqm,
                land_area_sqm,
                land_rights,
                legal_far_pct,
                bcr_pct,
                num_units,
                road_frontage,
                nearest_station,
                station_walk_min,
                floor_plan,
                num_floors,
                land_category,
                city_planning_area,
                updated_date,
                transaction_type,
                listing_date,
                platform,
                extraction_confidence,
                raw_extraction_json,
                llm_filled_fields_json,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            FROM row_df
            """
        )
    logger.debug("listing_master upsert: %s", listing_id)
    return listing_id


def upsert_location_features(
    conn: duckdb.DuckDBPyConnection,
    features: dict[str, Any],
) -> str:
    """location_features に 1 件 upsert する。"""
    create_tables_if_needed(conn)
    location_key = str(features["location_key"])
    row_df = pd.DataFrame([features])
    table_cols = _get_table_columns(conn, "location_features")
    row_df = _align_df_to_schema(row_df, table_cols)

    conn.execute("DELETE FROM location_features WHERE location_key = ?", [location_key])
    conn.execute(
        """
        INSERT INTO location_features (
            location_key,
            lat,
            lon,
            city_code,
            feature_version,
            facility_radius_m,
            terrain_radius_m,
            convenience_count_500m,
            convenience_count_1000m,
            convenience_nearest_m,
            supermarket_count_500m,
            supermarket_count_1000m,
            supermarket_nearest_m,
            transit_count_500m,
            transit_count_1000m,
            transit_nearest_m,
            pachinko_count_500m,
            pachinko_count_1000m,
            pachinko_nearest_m,
            food_count_500m,
            food_count_1000m,
            food_nearest_m,
            school_count_500m,
            school_count_1000m,
            school_nearest_m,
            medical_count_500m,
            medical_count_1000m,
            medical_nearest_m,
            park_count_500m,
            park_count_1000m,
            park_nearest_m,
            elevation_m,
            elevation_band,
            elevation_source,
            nearest_water_m,
            water_count_1000m,
            life_convenience_score,
            family_score,
            negative_facility_score,
            terrain_caution_score,
            flood_risk_flag,
            flood_depth_rank,
            landslide_risk_flag,
            hazard_source_summary,
            fetched_at
        )
        SELECT
            location_key,
            lat,
            lon,
            city_code,
            feature_version,
            facility_radius_m,
            terrain_radius_m,
            convenience_count_500m,
            convenience_count_1000m,
            convenience_nearest_m,
            supermarket_count_500m,
            supermarket_count_1000m,
            supermarket_nearest_m,
            transit_count_500m,
            transit_count_1000m,
            transit_nearest_m,
            pachinko_count_500m,
            pachinko_count_1000m,
            pachinko_nearest_m,
            food_count_500m,
            food_count_1000m,
            food_nearest_m,
            school_count_500m,
            school_count_1000m,
            school_nearest_m,
            medical_count_500m,
            medical_count_1000m,
            medical_nearest_m,
            park_count_500m,
            park_count_1000m,
            park_nearest_m,
            elevation_m,
            elevation_band,
            elevation_source,
            nearest_water_m,
            water_count_1000m,
            life_convenience_score,
            family_score,
            negative_facility_score,
            terrain_caution_score,
            flood_risk_flag,
            flood_depth_rank,
            landslide_risk_flag,
            hazard_source_summary,
            CURRENT_TIMESTAMP
        FROM row_df
        """
    )
    logger.debug("location_features upsert: %s", location_key)
    return location_key


def get_cached_location_features(
    conn: duckdb.DuckDBPyConnection,
    location_key: str,
    max_age_days: int = 30,
) -> Optional[dict[str, Any]]:
    """location_features からキャッシュ行を返す。max_age_days 以内のみ有効。"""
    row = conn.execute(
        """
        SELECT * FROM location_features
        WHERE location_key = ?
          AND fetched_at >= CURRENT_TIMESTAMP - INTERVAL (?) DAY
        LIMIT 1
        """,
        [location_key, max_age_days],
    ).fetchdf()
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def upsert_facility_pois(
    conn: duckdb.DuckDBPyConnection,
    location_key: str,
    pois: list[dict[str, Any]],
) -> int:
    """facility_pois に POI リストを upsert する（同一 location_key は全削除→再挿入）。"""
    create_tables_if_needed(conn)
    conn.execute("DELETE FROM facility_pois WHERE location_key = ?", [location_key])
    if not pois:
        return 0
    df = pd.DataFrame(pois)
    df["location_key"] = location_key
    table_cols = _get_table_columns(conn, "facility_pois")
    df = _align_df_to_schema(df, table_cols)
    conn.execute("INSERT INTO facility_pois SELECT * FROM df")
    logger.debug("facility_pois upsert: %s (%d rows)", location_key, len(df))
    return len(df)


def upsert_water_features(
    conn: duckdb.DuckDBPyConnection,
    location_key: str,
    features: list[dict[str, Any]],
) -> int:
    """water_features に水辺リストを upsert する（同一 location_key は全削除→再挿入）。"""
    create_tables_if_needed(conn)
    conn.execute("DELETE FROM water_features WHERE location_key = ?", [location_key])
    if not features:
        return 0
    df = pd.DataFrame(features)
    df["location_key"] = location_key
    table_cols = _get_table_columns(conn, "water_features")
    df = _align_df_to_schema(df, table_cols)
    conn.execute("INSERT INTO water_features SELECT * FROM df")
    logger.debug("water_features upsert: %s (%d rows)", location_key, len(df))
    return len(df)


def get_cached_facility_pois(
    conn: duckdb.DuckDBPyConnection,
    location_key: str,
    max_age_days: int = 30,
) -> dict[str, list[dict[str, Any]]]:
    """facility_pois から category 別の POI dict を返す。キャッシュなし or 期限切れは {}。"""
    df = conn.execute(
        """
        SELECT * FROM facility_pois
        WHERE location_key = ?
          AND fetched_at >= CURRENT_TIMESTAMP - INTERVAL (?) DAY
        """,
        [location_key, max_age_days],
    ).fetchdf()
    if df.empty:
        return {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in df.to_dict("records"):
        cat = row.get("category", "unknown")
        grouped.setdefault(cat, []).append(row)
    return grouped


def get_cached_water_features(
    conn: duckdb.DuckDBPyConnection,
    location_key: str,
    max_age_days: int = 30,
) -> list[dict[str, Any]]:
    """water_features からキャッシュ行を返す。キャッシュなし or 期限切れは []。"""
    df = conn.execute(
        """
        SELECT * FROM water_features
        WHERE location_key = ?
          AND fetched_at >= CURRENT_TIMESTAMP - INTERVAL (?) DAY
        """,
        [location_key, max_age_days],
    ).fetchdf()
    if df.empty:
        return []
    return df.to_dict("records")


def upsert_listing_feature_snapshot(
    conn: duckdb.DuckDBPyConnection,
    snapshot: dict[str, Any],
) -> None:
    """listing_feature_snapshots に日次スナップショットを upsert する。"""
    create_tables_if_needed(conn)
    listing_id = str(snapshot["listing_id"])
    snapshot_date = snapshot["snapshot_date"]
    row_df = pd.DataFrame([snapshot])
    table_cols = _get_table_columns(conn, "listing_feature_snapshots")
    row_df = _align_df_to_schema(row_df, table_cols)

    conn.execute(
        "DELETE FROM listing_feature_snapshots WHERE listing_id = ? AND snapshot_date = ?",
        [listing_id, snapshot_date],
    )
    conn.execute(
        """
        INSERT INTO listing_feature_snapshots (
            listing_id,
            snapshot_date,
            location_key,
            feature_version,
            asking_price_yen,
            unit_area_basis,
            unit_area_sqm,
            unit_price_yen_per_sqm,
            nearby_land_count,
            nearby_trade_count,
            land_unit_price_p25_yen_per_sqm,
            land_unit_price_p75_yen_per_sqm,
            trade_unit_price_median_yen_per_sqm,
            public_notice_gap_pct,
            trade_gap_pct,
            land_price_estimate_low_yen,
            land_price_estimate_high_yen,
            building_residual_low_yen,
            building_residual_high_yen,
            saved_at
        )
        SELECT
            listing_id,
            snapshot_date,
            location_key,
            feature_version,
            asking_price_yen,
            unit_area_basis,
            unit_area_sqm,
            unit_price_yen_per_sqm,
            nearby_land_count,
            nearby_trade_count,
            land_unit_price_p25_yen_per_sqm,
            land_unit_price_p75_yen_per_sqm,
            trade_unit_price_median_yen_per_sqm,
            public_notice_gap_pct,
            trade_gap_pct,
            land_price_estimate_low_yen,
            land_price_estimate_high_yen,
            building_residual_low_yen,
            building_residual_high_yen,
            CURRENT_TIMESTAMP
        FROM row_df
        """
    )
    logger.debug("listing_feature_snapshots upsert: %s %s", listing_id, snapshot_date)


def list_saved_listings(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """保存済み掲載物件の一覧を取得（ドロップダウン表示用）。"""
    create_tables_if_needed(conn)
    return conn.execute(
        """
        SELECT
            listing_id,
            property_name,
            address,
            property_type,
            asking_price_yen,
            gross_yield_pct,
            age_years,
            structure,
            source_url,
            lat,
            lon,
            city_code,
            gross_rent_monthly_yen,
            gross_rent_annual_yen,
            build_year_month,
            building_area_sqm,
            land_area_sqm,
            land_rights,
            legal_far_pct,
            bcr_pct,
            num_units,
            road_frontage,
            nearest_station,
            station_walk_min,
            floor_plan,
            num_floors,
            land_category,
            city_planning_area,
            updated_date,
            transaction_type,
            listing_date,
            platform,
            extraction_confidence,
            raw_extraction_json,
            llm_filled_fields_json,
            first_seen_at
        FROM listing_master
        ORDER BY first_seen_at DESC
        """
    ).df()


def get_listing_master(conn: duckdb.DuckDBPyConnection, listing_id: str) -> pd.DataFrame:
    """listing_id の掲載物件レコードを返す。"""
    create_tables_if_needed(conn)
    return conn.execute(
        "SELECT * FROM listing_master WHERE listing_id = ?",
        [listing_id],
    ).df()


def get_location_features(conn: duckdb.DuckDBPyConnection, location_key: str) -> pd.DataFrame:
    """location_key の特徴量レコードを返す。"""
    create_tables_if_needed(conn)
    return conn.execute(
        "SELECT * FROM location_features WHERE location_key = ?",
        [location_key],
    ).df()


def get_latest_listing_feature_snapshot(
    conn: duckdb.DuckDBPyConnection,
    listing_id: str,
) -> pd.DataFrame:
    """掲載物件の最新スナップショットを返す。"""
    create_tables_if_needed(conn)
    return conn.execute(
        """
        SELECT *
        FROM listing_feature_snapshots
        WHERE listing_id = ?
        ORDER BY snapshot_date DESC
        LIMIT 1
        """,
        [listing_id],
    ).df()


def upsert_listing_raw(conn: duckdb.DuckDBPyConnection, row: dict[str, Any]) -> str:
    """listing_raw に 1 件 upsert する。"""
    create_tables_if_needed(conn)
    raw_id = str(row["raw_id"])
    payload = dict(row)
    payload["raw_id"] = raw_id
    payload["extraction_json"] = _normalize_json_text(payload.get("extraction_json"))
    row_df = _align_df_to_schema(pd.DataFrame([payload]), _get_table_columns(conn, "listing_raw"))
    conn.execute("DELETE FROM listing_raw WHERE raw_id = ?", [raw_id])
    conn.execute("INSERT INTO listing_raw SELECT * FROM row_df")
    return raw_id


def upsert_valuation_result(conn: duckdb.DuckDBPyConnection, row: dict[str, Any]) -> None:
    """valuation_results に日次評価結果を upsert する。"""
    create_tables_if_needed(conn)
    listing_id = str(row["listing_id"])
    valuation_date = row["valuation_date"]
    payload = dict(row)
    payload["reasons_json"] = _normalize_json_text(payload.get("reasons_json"))
    row_df = _align_df_to_schema(pd.DataFrame([payload]), _get_table_columns(conn, "valuation_results"))
    conn.execute(
        "DELETE FROM valuation_results WHERE listing_id = ? AND valuation_date = ?",
        [listing_id, valuation_date],
    )
    conn.execute("INSERT INTO valuation_results SELECT * FROM row_df")


def upsert_public_notice_location_feature(conn: duckdb.DuckDBPyConnection, row: dict[str, Any]) -> None:
    create_tables_if_needed(conn)
    payload = _align_df_to_schema(pd.DataFrame([row]), _get_table_columns(conn, "public_notice_location_features"))
    conn.execute(
        "DELETE FROM public_notice_location_features WHERE point_id = ? AND year = ?",
        [row["point_id"], row["year"]],
    )
    conn.execute("INSERT INTO public_notice_location_features SELECT * FROM payload")


def upsert_trade_location_feature(conn: duckdb.DuckDBPyConnection, row: dict[str, Any]) -> None:
    create_tables_if_needed(conn)
    payload = _align_df_to_schema(pd.DataFrame([row]), _get_table_columns(conn, "trade_location_features"))
    conn.execute(
        "DELETE FROM trade_location_features WHERE trade_id = ? AND year = ? AND quarter = ?",
        [row["trade_id"], row["year"], row["quarter"]],
    )
    conn.execute("INSERT INTO trade_location_features SELECT * FROM payload")


def upsert_search_job(conn: duckdb.DuckDBPyConnection, row: dict[str, Any]) -> str:
    """search_jobs に 1 件 upsert する。"""
    create_tables_if_needed(conn)
    job_id = str(row["job_id"])
    payload = dict(row)
    payload["job_id"] = job_id
    existing = conn.execute(
        "SELECT started_at FROM search_jobs WHERE job_id = ?",
        [job_id],
    ).fetchone()
    if existing and payload.get("started_at") is None:
        payload["started_at"] = existing[0]
    row_df = _align_df_to_schema(pd.DataFrame([payload]), _get_table_columns(conn, "search_jobs"))
    conn.execute("DELETE FROM search_jobs WHERE job_id = ?", [job_id])
    conn.execute("INSERT INTO search_jobs SELECT * FROM row_df")
    return job_id


def replace_search_job_urls(
    conn: duckdb.DuckDBPyConnection,
    job_id: str,
    rows: list[dict[str, Any]],
) -> None:
    """search_result_urls を job_id 単位で置き換える。"""
    create_tables_if_needed(conn)
    conn.execute("DELETE FROM search_result_urls WHERE job_id = ?", [job_id])
    if not rows:
        return
    payload = _align_df_to_schema(pd.DataFrame(rows), _get_table_columns(conn, "search_result_urls"))
    conn.execute("INSERT INTO search_result_urls SELECT * FROM payload")


def read_listings(
    conn: duckdb.DuckDBPyConnection,
    filters: Optional[dict[str, Any]] = None,
    limit: Optional[int] = None,
) -> pd.DataFrame:
    """掲載物件一覧を最新スナップショット・特徴量・評価結果付きで返す。"""
    create_tables_if_needed(conn)
    where_clauses: list[str] = []
    params: list[Any] = []

    if filters:
        for col, val in filters.items():
            if val is None or val == "":
                continue
            if col == "keyword":
                where_clauses.append(
                    "(COALESCE(lm.address, '') ILIKE ? OR COALESCE(lm.property_name, '') ILIKE ? OR COALESCE(lm.nearest_station, '') ILIKE ?)"
                )
                keyword = f"%{val}%"
                params.extend([keyword, keyword, keyword])
            elif col == "min_price":
                where_clauses.append("lm.asking_price_yen >= ?")
                params.append(val)
            elif col == "max_price":
                where_clauses.append("lm.asking_price_yen <= ?")
                params.append(val)
            elif col == "min_yield":
                where_clauses.append("lm.gross_yield_pct >= ?")
                params.append(val)
            elif col == "max_yield":
                where_clauses.append("lm.gross_yield_pct <= ?")
                params.append(val)
            elif col == "cheap_or_expensive":
                where_clauses.append("vr.cheap_or_expensive = ?")
                params.append(val)
            elif isinstance(val, (list, tuple)):
                placeholders = ", ".join(["?"] * len(val))
                where_clauses.append(f"lm.{col} IN ({placeholders})")
                params.extend(val)
            else:
                where_clauses.append(f"lm.{col} = ?")
                params.append(val)

    query = """
    WITH latest_snapshot AS (
        SELECT *
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY listing_id ORDER BY snapshot_date DESC) AS rn
            FROM listing_feature_snapshots
        )
        WHERE rn = 1
    ),
    latest_valuation AS (
        SELECT *
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY listing_id ORDER BY valuation_date DESC) AS rn
            FROM valuation_results
        )
        WHERE rn = 1
    )
    SELECT
        lm.*,
        ls.snapshot_date,
        ls.unit_area_basis,
        ls.unit_area_sqm,
        ls.unit_price_yen_per_sqm,
        ls.nearby_land_count,
        ls.nearby_trade_count,
        ls.land_unit_price_p25_yen_per_sqm,
        ls.land_unit_price_p75_yen_per_sqm,
        ls.trade_unit_price_median_yen_per_sqm,
        ls.public_notice_gap_pct,
        ls.trade_gap_pct,
        ls.land_price_estimate_low_yen,
        ls.land_price_estimate_high_yen,
        ls.building_residual_low_yen,
        ls.building_residual_high_yen,
        lf.life_convenience_score,
        lf.family_score,
        lf.negative_facility_score,
        lf.terrain_caution_score,
        lf.elevation_m,
        lf.elevation_band,
        lf.nearest_water_m,
        lf.flood_risk_flag,
        lf.flood_depth_rank,
        lf.landslide_risk_flag,
        vr.fair_value_yen,
        vr.gap_pct,
        vr.adjusted_gap_pct,
        vr.cheap_or_expensive,
        vr.confidence,
        vr.reasons_json
    FROM listing_master lm
    LEFT JOIN latest_snapshot ls ON lm.listing_id = ls.listing_id
    LEFT JOIN location_features lf ON ls.location_key = lf.location_key
    LEFT JOIN latest_valuation vr ON lm.listing_id = vr.listing_id
    """
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    query += " ORDER BY lm.last_seen_at DESC"
    if limit:
        query += f" LIMIT {int(limit)}"
    return conn.execute(query, params).df()


def read_recent_search_jobs(
    conn: duckdb.DuckDBPyConnection,
    limit: int = 20,
) -> pd.DataFrame:
    """最近の検索収集ジョブ一覧を返す。"""
    create_tables_if_needed(conn)
    return conn.execute(
        """
        SELECT *
        FROM search_jobs
        ORDER BY started_at DESC
        LIMIT ?
        """,
        [limit],
    ).df()


def get_listings_for_recompute(
    conn: duckdb.DuckDBPyConnection,
    limit: int = 100,
    stale_days: int = 7,
) -> pd.DataFrame:
    """特徴量再計算対象の掲載物件を返す。"""
    create_tables_if_needed(conn)
    return conn.execute(
        """
        SELECT
            lm.*,
            lf.fetched_at
        FROM listing_master lm
        LEFT JOIN location_features lf
          ON lf.location_key = CASE
                WHEN lm.lat IS NOT NULL AND lm.lon IS NOT NULL
                THEN printf('%.5f,%.5f', round(lm.lat, 5), round(lm.lon, 5))
                ELSE NULL
             END
        WHERE lm.lat IS NOT NULL
          AND lm.lon IS NOT NULL
          AND (
              lf.location_key IS NULL OR
              date_diff('day', lf.fetched_at, CURRENT_TIMESTAMP) >= ?
          )
        ORDER BY lm.last_seen_at DESC
        LIMIT ?
        """,
        [stale_days, limit],
    ).df()


def get_listings_by_ids(
    conn: duckdb.DuckDBPyConnection,
    listing_ids: list[str],
) -> pd.DataFrame:
    """指定 listing_id の掲載物件を返す。"""
    create_tables_if_needed(conn)
    if not listing_ids:
        return pd.DataFrame()
    placeholders = ", ".join(["?"] * len(listing_ids))
    query = f"""
        SELECT *
        FROM listing_master
        WHERE listing_id IN ({placeholders})
          AND lat IS NOT NULL
          AND lon IS NOT NULL
        ORDER BY last_seen_at DESC
    """
    return conn.execute(query, listing_ids).df()


def get_public_notice_feature_targets(
    conn: duckdb.DuckDBPyConnection,
    year: Optional[int] = None,
    limit: int = 500,
) -> pd.DataFrame:
    create_tables_if_needed(conn)
    where = ["lon IS NOT NULL", "lat IS NOT NULL"]
    params: list[Any] = []
    if year is not None:
        where.append("year = ?")
        params.append(year)
    query = """
        SELECT point_id, year, city_code, lon, lat
        FROM land_prices_public_notice
        WHERE """ + " AND ".join(where) + """
        ORDER BY year DESC
        LIMIT ?
    """
    params.append(limit)
    return conn.execute(query, params).df()


def get_trade_feature_targets(
    conn: duckdb.DuckDBPyConnection,
    year: Optional[int] = None,
    limit: int = 500,
) -> pd.DataFrame:
    create_tables_if_needed(conn)
    where = ["lon IS NOT NULL", "lat IS NOT NULL"]
    params: list[Any] = []
    if year is not None:
        where.append("year = ?")
        params.append(year)
    query = """
        SELECT trade_id, year, quarter, city_code, lon, lat
        FROM trade_prices
        WHERE """ + " AND ".join(where) + """
        ORDER BY year DESC, quarter DESC
        LIMIT ?
    """
    params.append(limit)
    return conn.execute(query, params).df()


# --------------------------------------------------------------------------
# DB スモークテスト
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# 人口統計 (population_stats)
# --------------------------------------------------------------------------

def upsert_population_stats(conn: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> int:
    """population_stats テーブルに upsert する。"""
    if df.empty:
        return 0
    for year in df["survey_year"].unique():
        conn.execute("DELETE FROM population_stats WHERE survey_year = ?", [int(year)])
    payload = _align_df_to_schema(df, _get_table_columns(conn, "population_stats"))
    conn.execute("INSERT INTO population_stats SELECT * FROM payload")
    n = len(df)
    logger.info("population_stats upsert: %d 件", n)
    return n


def get_population_stats(conn: duckdb.DuckDBPyConnection, city_code: str) -> pd.DataFrame:
    """指定市区町村の人口統計データを年次昇順で返す。"""
    return conn.execute(
        """
        SELECT survey_year, total_population, households,
               pop_change_pct, households_change_pct, aging_rate, net_migration
        FROM population_stats
        WHERE city_code = ?
        ORDER BY survey_year ASC
        """,
        [city_code],
    ).df()


def get_population_latest(conn: duckdb.DuckDBPyConnection, city_code: str) -> dict:
    """指定市区町村の最新年の人口統計を dict で返す。データ無し時は空dict。"""
    df = conn.execute(
        """
        SELECT survey_year, total_population, households,
               pop_change_pct, households_change_pct, aging_rate, net_migration
        FROM population_stats
        WHERE city_code = ?
        ORDER BY survey_year DESC
        LIMIT 1
        """,
        [city_code],
    ).df()
    return df.iloc[0].to_dict() if not df.empty else {}


def smoke_test_db(db_path: Optional[Path] = None) -> bool:
    """DB への書込・読込が動作するか確認する。"""
    try:
        conn = get_connection(db_path)
        create_tables_if_needed(conn)
        # テスト行を挿入
        test_df = pd.DataFrame(
            [{"point_id": "__smoke_test__", "year": 0, "price_classification": -1}]
        )
        upsert_land_prices(conn, test_df)
        # 削除
        conn.execute(
            "DELETE FROM land_prices_public_notice WHERE point_id = '__smoke_test__'"
        )
        conn.close()
        logger.info("DB スモークテスト: OK")
        return True
    except Exception as exc:
        logger.error("DB スモークテスト失敗: %s", exc)
        return False
