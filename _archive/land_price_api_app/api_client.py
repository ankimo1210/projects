"""
api_client.py
不動産情報ライブラリ API への HTTP アクセスを担う層。
- 認証ヘッダー付与
- リトライ（指数バックオフ）
- gzip 自動展開
- タイムアウト
- 429 / 5xx 時の待機

外部公開不要・Python サーバーサイドから呼ぶ構成。
"""

import gzip
import json
import time
from typing import Any

import requests
from config import (
    MAX_RETRIES,
    REINFOLIB_BASE_URL,
    REQUEST_TIMEOUT_SEC,
    RETRY_BACKOFF_BASE,
    get_logger,
    validate_api_key,
)

logger = get_logger(__name__)

# --------------------------------------------------------------------------
# ヘッダー
# --------------------------------------------------------------------------


def get_subscription_headers() -> dict[str, str]:
    """Ocp-Apim-Subscription-Key を含む共通ヘッダーを返す。"""
    api_key = validate_api_key()
    return {
        "Ocp-Apim-Subscription-Key": api_key,
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
    }


# --------------------------------------------------------------------------
# 汎用 GET
# --------------------------------------------------------------------------


def fetch_json(
    url: str,
    params: dict[str, Any] | None = None,
    *,
    timeout: int = REQUEST_TIMEOUT_SEC,
    max_retries: int = MAX_RETRIES,
) -> Any:
    """
    GET リクエストを送り、JSON をパースして返す。

    Parameters
    ----------
    url : str
        フルURL またはパス。
    params : dict, optional
        クエリパラメータ。
    timeout : int
        タイムアウト秒数。
    max_retries : int
        最大リトライ回数。

    Returns
    -------
    Any
        パース済み JSON オブジェクト。

    Raises
    ------
    requests.HTTPError
        4xx / 5xx のうちリトライ上限に達した場合。
    ValueError
        JSON パース失敗時。
    """
    headers = get_subscription_headers()
    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            logger.debug("GET %s params=%s (attempt %d)", url, params, attempt + 1)
            resp = requests.get(url, headers=headers, params=params, timeout=timeout)

            # 429 / 503 はバックオフして再試行
            if resp.status_code in (429, 503):
                wait = RETRY_BACKOFF_BASE**attempt
                logger.warning(
                    "HTTP %d: バックオフ %.1fs (attempt %d/%d)",
                    resp.status_code,
                    wait,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(wait)
                continue

            resp.raise_for_status()

            # requests は通常 gzip を自動展開するが、展開済み content に
            # Content-Encoding: gzip が残る場合があるため、マジックバイトで判定する
            content = resp.content
            if content[:2] == b"\x1f\x8b":  # gzip マジックバイト
                content = gzip.decompress(content)

            return json.loads(content.decode("utf-8"))

        except requests.exceptions.Timeout as exc:
            logger.warning("タイムアウト (attempt %d/%d): %s", attempt + 1, max_retries, exc)
            last_exc = exc
        except requests.exceptions.ConnectionError as exc:
            logger.warning("接続エラー (attempt %d/%d): %s", attempt + 1, max_retries, exc)
            last_exc = exc
            time.sleep(RETRY_BACKOFF_BASE**attempt)
        except requests.exceptions.HTTPError as exc:
            # 4xx はリトライ不要（429 は上で処理済み）
            logger.error("HTTP エラー: %s", exc)
            raise
        except json.JSONDecodeError as exc:
            logger.error("JSON パース失敗: %s", exc)
            raise ValueError(f"JSON パース失敗: {exc}") from exc

    raise requests.exceptions.RetryError(
        f"最大リトライ回数 ({max_retries}) に達しました: {url}"
    ) from last_exc


# --------------------------------------------------------------------------
# XPT002 タイル取得
# --------------------------------------------------------------------------


def fetch_geojson_tile_xpt002(
    z: int,
    x: int,
    y: int,
    year: int,
    price_classification: int = 0,
    use_category_codes: list[str] | None = None,
    response_format: str = "geojson",
) -> dict[str, Any]:
    """
    XPT002 (地価公示・地価調査API) から 1 タイル分の GeoJSON を取得する。

    Parameters
    ----------
    z, x, y : int
        XYZ タイル座標。
    year : int
        調査年 (例: 2026)。
    price_classification : int
        0=地価公示, 1=地価調査。
    use_category_codes : list[str], optional
        用途区分コードのリスト (例: ["01", "02"])。省略時は全用途。
    response_format : str
        "geojson" 固定推奨。

    Returns
    -------
    dict
        GeoJSON FeatureCollection。features が空リストの場合もある。
    """
    # XPT002 はパスではなくクエリパラメータで z/x/y を渡す
    url = f"{REINFOLIB_BASE_URL}/XPT002"
    params: dict[str, Any] = {
        "response_format": response_format,  # スネークケース（公式仕様）
        "z": z,
        "x": x,
        "y": y,
        "year": year,
        "priceClassification": price_classification,
    }
    if use_category_codes:
        params["useCategoryCode"] = use_category_codes

    data = fetch_json(url, params=params)

    # データなしタイルは HTTP 200 + 空 features の場合がある
    if not isinstance(data, dict):
        logger.debug("タイル z=%d/%d/%d: 予期しないレスポンス型 %s", z, x, y, type(data))
        return {"type": "FeatureCollection", "features": []}

    if "features" not in data:
        data["features"] = []

    feature_count = len(data.get("features", []))
    if feature_count > 0:
        logger.debug("タイル z=%d/%d/%d: %d features", z, x, y, feature_count)

    return data


# --------------------------------------------------------------------------
# XIT001 不動産取引価格情報
# --------------------------------------------------------------------------


def fetch_trade_prices_xit001(
    area: str,
    year: int,
    quarter: int,
    response_format: str = "geojson",
) -> dict[str, Any]:
    """
    XIT001 (不動産取引価格情報API) から GeoJSON を取得する。

    Parameters
    ----------
    area : str
        都道府県コード (2桁) または市区町村コード (5桁)。
    year : int
        取引年 (例: 2024)。
    quarter : int
        四半期 (1-4)。
    response_format : str
        "geojson" 固定推奨。

    Returns
    -------
    dict
        GeoJSON FeatureCollection。features が空リストの場合もある。
    """
    url = f"{REINFOLIB_BASE_URL}/XIT001"
    area_str = area.zfill(2) if len(str(area)) <= 2 else str(area)
    # XIT001 は {"status":"OK","data":[...]} 形式を返す（GeoJSONではない・座標なし）
    params: dict[str, Any] = {
        "area": area_str,
        "year": str(year),
        "quarter": str(quarter),
    }

    raw = fetch_json(url, params=params)

    if not isinstance(raw, dict):
        logger.debug(
            "XIT001 area=%s year=%d Q%d: 予期しないレスポンス型 %s", area, year, quarter, type(raw)
        )
        return []

    records = raw.get("data", [])
    if records:
        logger.debug("XIT001 area=%s year=%d Q%d: %d records", area, year, quarter, len(records))
    return records


# --------------------------------------------------------------------------
# XIT002 市区町村リスト
# --------------------------------------------------------------------------


def fetch_city_list(prefecture_code: str) -> list[dict[str, Any]]:
    """
    XIT002 (都道府県内市区町村一覧取得API) から市区町村リストを取得する。

    Parameters
    ----------
    prefecture_code : str
        都道府県コード (例: "13" for 東京都)。ゼロ埋め2桁。

    Returns
    -------
    list[dict]
        市区町村情報のリスト。
        各要素は {"cityCode": str, "cityName": str, ...} など。
    """
    url = f"{REINFOLIB_BASE_URL}/XIT002"
    # XIT002 は 'area' パラメータに都道府県コードを渡す（公式仕様）
    params = {"area": prefecture_code.zfill(2)}
    data = fetch_json(url, params=params)

    # レスポンス: {"status": "OK", "data": [{"id": "13101", "name": "千代田区"}, ...]}
    if isinstance(data, dict):
        return data.get("data", [])
    if isinstance(data, list):
        return data
    return []


# --------------------------------------------------------------------------
# スモークテスト
# --------------------------------------------------------------------------


def smoke_test_api_key() -> bool:
    """APIキーが読み込まれているか確認する。"""
    try:
        validate_api_key()
        logger.info("APIキー: OK")
        return True
    except OSError as exc:
        logger.error("APIキー: NG - %s", exc)
        return False


def smoke_test_xit002(prefecture_code: str = "13") -> bool:
    """XIT002 で東京都の市区町村が取得できるか確認する。"""
    try:
        cities = fetch_city_list(prefecture_code)
        logger.info("XIT002 疎通確認: %d 件取得 (都道府県コード=%s)", len(cities), prefecture_code)
        return len(cities) > 0
    except Exception as exc:
        logger.error("XIT002 疎通確認失敗: %s", exc)
        return False


def smoke_test_xpt002(z: int = 14, x: int = 14552, y: int = 6452, year: int = 2026) -> bool:
    """
    XPT002 で東京都心付近のタイルを取得できるか確認する。
    デフォルト座標: z=14, x=14552, y=6452 (東京都心付近)

    year=2026 が取得できない場合は year=2025 にフォールバックする。
    """
    for try_year in (year, year - 1):
        try:
            data = fetch_geojson_tile_xpt002(z, x, y, year=try_year)
            features = data.get("features", [])
            logger.info(
                "XPT002 疎通確認 (year=%d, z=%d/%d/%d): %d features",
                try_year,
                z,
                x,
                y,
                len(features),
            )
            return True
        except Exception as exc:
            logger.warning("XPT002 year=%d 取得失敗: %s", try_year, exc)
    return False
