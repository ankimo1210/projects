"""
config.py
アプリ全体の設定を .env から読み込んで提供する。
"""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# ---- プロジェクトルートの解決 ----------------------------------------
PROJECT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = PROJECT_DIR.parent
_ROOT = PROJECT_DIR
load_dotenv(PROJECT_DIR / ".env", override=False)

LEGACY_DATA_DIR = PROJECT_DIR / "data"
WORKSPACE_LAND_PRICE_DIR = WORKSPACE_DIR / "_data" / "land_price"
LEGACY_RAW_DIR = LEGACY_DATA_DIR / "raw"
LEGACY_PROCESSED_DIR = LEGACY_DATA_DIR / "processed"
WORKSPACE_RAW_DIR = WORKSPACE_LAND_PRICE_DIR / "raw"
WORKSPACE_PROCESSED_DIR = WORKSPACE_LAND_PRICE_DIR / "processed"
LEGACY_DUCKDB_PATH = LEGACY_PROCESSED_DIR / "land_prices.duckdb"
WORKSPACE_DUCKDB_PATH = WORKSPACE_PROCESSED_DIR / "land_prices.duckdb"
DEFAULT_LOG_DIR = WORKSPACE_DIR / "_logs" / "app" / "land_price_api_app"

# ---- API ----------------------------------------------------------------
REINFOLIB_API_KEY: str = os.getenv("REINFOLIB_API_KEY", "")
REINFOLIB_BASE_URL: str = "https://www.reinfolib.mlit.go.jp/ex-api/external"
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
ESTAT_APP_ID: str = os.getenv("ESTAT_APP_ID", "")

# ---- DB / ファイルパス --------------------------------------------------
def _resolve_path_from_env(var_name: str) -> Path | None:
    raw = os.getenv(var_name, "").strip()
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_absolute() else (PROJECT_DIR / raw).resolve()


def _prefer_workspace_equivalent(candidate: Path, workspace_path: Path, legacy_path: Path) -> Path:
    if candidate.resolve() == legacy_path.resolve() and workspace_path.exists():
        return workspace_path
    return candidate


def _prefer_workspace_path(workspace_path: Path, legacy_path: Path) -> Path:
    if workspace_path.exists():
        return workspace_path
    return legacy_path


def _resolve_dir(var_name: str, workspace_path: Path, legacy_path: Path) -> Path:
    env_path = _resolve_path_from_env(var_name)
    if env_path is not None:
        return _prefer_workspace_equivalent(env_path, workspace_path, legacy_path)
    return _prefer_workspace_path(workspace_path, legacy_path)


def _resolve_db_path() -> Path:
    """DUCKDB_PATH を解決する。未指定時は workspace 優先、未移行なら legacy を使う。"""
    env_path = _resolve_path_from_env("DUCKDB_PATH")
    if env_path is not None:
        return _prefer_workspace_equivalent(
            env_path,
            WORKSPACE_DUCKDB_PATH,
            LEGACY_DUCKDB_PATH,
        )
    return _prefer_workspace_path(WORKSPACE_DUCKDB_PATH, LEGACY_DUCKDB_PATH)


DATA_DIR: Path = _resolve_dir("LAND_PRICE_DATA_DIR", WORKSPACE_LAND_PRICE_DIR, LEGACY_DATA_DIR)
RAW_DIR: Path = _resolve_dir("LAND_PRICE_RAW_DIR", WORKSPACE_RAW_DIR, LEGACY_RAW_DIR)
PROCESSED_DIR: Path = _resolve_dir(
    "LAND_PRICE_PROCESSED_DIR",
    WORKSPACE_PROCESSED_DIR,
    LEGACY_PROCESSED_DIR,
)
DUCKDB_PATH: Path = _resolve_db_path()
LOG_DIR: Path = _resolve_dir("LAND_PRICE_LOG_DIR", DEFAULT_LOG_DIR, PROJECT_DIR)
STREAMLIT_LOG_PATH: Path = LOG_DIR / "streamlit.log"

# ---- 同期設定 -----------------------------------------------------------
DEFAULT_ZOOM: int = 13
DEFAULT_PRICE_CLASSIFICATION: int = 0  # 0=地価公示, 1=地価調査
REQUEST_INTERVAL_SEC: float = 0.3      # タイルAPI間の待機秒数
REQUEST_TIMEOUT_SEC: int = 30
MAX_RETRIES: int = 3
RETRY_BACKOFF_BASE: float = 2.0        # 指数バックオフの底

# ---- 日本の大まかなバウンディングボックス --------------------------------
JAPAN_LON_MIN: float = 122.0
JAPAN_LON_MAX: float = 154.0
JAPAN_LAT_MIN: float = 24.0
JAPAN_LAT_MAX: float = 46.5

# ---- ロギング -----------------------------------------------------------
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def get_logger(name: str) -> logging.Logger:
    """モジュール別ロガーを返す。"""
    return logging.getLogger(name)


def validate_anthropic_key() -> str:
    """Anthropic APIキーを返す。未設定なら EnvironmentError を送出する。"""
    key = ANTHROPIC_API_KEY
    if not key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY が設定されていません。.env を確認してください。"
        )
    return key


def validate_api_key() -> str:
    """APIキーを返す。未設定なら EnvironmentError を送出する。"""
    key = REINFOLIB_API_KEY
    if not key:
        raise EnvironmentError(
            "REINFOLIB_API_KEY が設定されていません。"
            " .env.example を参考に .env ファイルを作成してください。"
        )
    return key


def ensure_dirs() -> None:
    """必要なデータディレクトリを作成する。"""
    for d in (RAW_DIR, PROCESSED_DIR, LOG_DIR, DUCKDB_PATH.parent):
        d.mkdir(parents=True, exist_ok=True)
