"""
geocoder.py
国土地理院アドレス検索API を使って日本語住所を (lat, lon) に変換する。

API: https://msearch.gsi.go.jp/address-search/AddressSearch?q=<address>
APIキー不要・無料・商用利用可。
"""
from dataclasses import dataclass
from typing import Optional

import requests

from config import get_logger

logger = get_logger(__name__)

_GSI_URL = "https://msearch.gsi.go.jp/address-search/AddressSearch"


class GeocodingError(Exception):
    pass


@dataclass
class GeocodingResult:
    lat: float
    lon: float
    matched_address: str
    score: float
    city_code: Optional[str] = None  # 国土地理院 muniCd（5桁市区町村コード）


def geocode_address(address: str, timeout: int = 10) -> GeocodingResult:
    """
    日本語住所を (lat, lon) に変換する。

    Parameters
    ----------
    address : str
        住所文字列（例: "東京都新宿区西新宿2-8-1"）
    timeout : int
        タイムアウト秒数

    Returns
    -------
    GeocodingResult

    Raises
    ------
    GeocodingError
        住所が見つからない場合、またはAPIリクエスト失敗時
    """
    if not address or not address.strip():
        raise GeocodingError("住所が空です。")

    try:
        resp = requests.get(_GSI_URL, params={"q": address.strip()}, timeout=timeout)
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise GeocodingError(f"国土地理院APIへの接続に失敗しました: {exc}") from exc

    try:
        results = resp.json()
    except ValueError as exc:
        raise GeocodingError(f"APIレスポンスのパースに失敗しました: {exc}") from exc

    if not results:
        raise GeocodingError(f"住所が見つかりませんでした: {address!r}")

    best = results[0]
    # GeoJSON 仕様: coordinates = [longitude, latitude]
    coords = best.get("geometry", {}).get("coordinates", [])
    if len(coords) < 2:
        raise GeocodingError(f"座標データが不正です: {best}")

    lon, lat = float(coords[0]), float(coords[1])
    props = best.get("properties", {})
    matched = props.get("title", address)
    score = float(props.get("score", 1.0))
    city_code = props.get("muniCd")  # 5桁市区町村コード（例: "13104"）

    logger.debug("ジオコーディング: %r → (%.6f, %.6f) score=%.2f city_code=%s", address, lat, lon, score, city_code)
    return GeocodingResult(lat=lat, lon=lon, matched_address=matched, score=score, city_code=city_code)
