"""
tiles.py
XYZ スライシングスキームによるタイル座標演算と
日本全国タイル走査ユーティリティ。

XPT002 は XYZ タイル API なので、全国取得には
Japan の bounding box をタイルインデックスに変換して走査する。
"""
import math
from typing import Iterator

from config import (
    JAPAN_LAT_MAX,
    JAPAN_LAT_MIN,
    JAPAN_LON_MAX,
    JAPAN_LON_MIN,
    get_logger,
)

logger = get_logger(__name__)


# --------------------------------------------------------------------------
# 座標 <-> タイルインデックス変換
# --------------------------------------------------------------------------

def lonlat_to_tile_indices(lon: float, lat: float, z: int) -> tuple[int, int]:
    """
    経緯度 → XYZ タイルインデックスへ変換する（Web Mercator / Slippy Map）。

    Parameters
    ----------
    lon : float  経度 (-180 ~ 180)
    lat : float  緯度 (-85.05 ~ 85.05)
    z   : int    ズームレベル

    Returns
    -------
    (x, y) : tuple[int, int]
    """
    lat_rad = math.radians(lat)
    n = 2 ** z
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    # クランプ
    x = max(0, min(n - 1, x))
    y = max(0, min(n - 1, y))
    return x, y


def tile_to_lonlat_nw(x: int, y: int, z: int) -> tuple[float, float]:
    """
    タイルインデックス → タイル左上隅（北西）の経緯度へ変換する。

    Returns
    -------
    (lon, lat) : tuple[float, float]
    """
    n = 2 ** z
    lon = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat = math.degrees(lat_rad)
    return lon, lat


# --------------------------------------------------------------------------
# 日本全国タイル範囲
# --------------------------------------------------------------------------

def japan_tile_range(z: int) -> tuple[int, int, int, int]:
    """
    日本全国を囲む XYZ タイルの範囲 (x_min, x_max, y_min, y_max) を返す。

    Note: Web Mercator では緯度が高い（北）ほど y が小さい。
    """
    # 北東隅（緯度最大=y最小, 経度最大=x最大）
    x_max, y_min = lonlat_to_tile_indices(JAPAN_LON_MAX, JAPAN_LAT_MAX, z)
    # 南西隅（緯度最小=y最大, 経度最小=x最小）
    x_min, y_max = lonlat_to_tile_indices(JAPAN_LON_MIN, JAPAN_LAT_MIN, z)
    logger.debug(
        "z=%d: x=%d..%d, y=%d..%d (総タイル数=%d)",
        z, x_min, x_max, y_min, y_max,
        (x_max - x_min + 1) * (y_max - y_min + 1),
    )
    return x_min, x_max, y_min, y_max


def iter_japan_tiles(z: int) -> Iterator[tuple[int, int, int]]:
    """
    日本全国を囲む全タイルを (z, x, y) のタプルで yield する。

    z=13 の場合、約 4 万〜5 万タイルを走査する（大部分は海や空タイル）。
    データ無しタイルは API が HTTP 200 + 空 features で返すため、
    呼び出し側でスキップする。
    """
    x_min, x_max, y_min, y_max = japan_tile_range(z)
    total = (x_max - x_min + 1) * (y_max - y_min + 1)
    logger.info(
        "タイル走査開始: z=%d, 走査対象 %d タイル (x=%d..%d, y=%d..%d)",
        z, total, x_min, x_max, y_min, y_max,
    )
    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            yield z, x, y


# --------------------------------------------------------------------------
# 都道府県タイル範囲（将来拡張用）
# --------------------------------------------------------------------------

# 各都道府県の大まかな bounding box (lon_min, lon_max, lat_min, lat_max)
PREFECTURE_BBOX: dict[str, tuple[float, float, float, float]] = {
    "01": (141.0, 145.9, 41.3, 45.6),  # 北海道
    "02": (140.1, 141.7, 40.2, 41.6),  # 青森
    "03": (140.7, 142.1, 38.7, 40.5),  # 岩手
    "04": (140.2, 141.7, 37.7, 39.0),  # 宮城
    "05": (139.7, 141.0, 39.0, 40.5),  # 秋田
    "06": (139.8, 140.9, 37.7, 39.0),  # 山形
    "07": (139.2, 141.1, 36.7, 37.9),  # 福島
    "08": (139.7, 140.9, 35.7, 36.9),  # 茨城
    "09": (139.3, 140.4, 36.2, 37.2),  # 栃木
    "10": (138.7, 139.8, 36.0, 37.0),  # 群馬
    "11": (138.7, 139.9, 35.7, 36.3),  # 埼玉
    "12": (139.7, 140.9, 35.0, 35.9),  # 千葉
    "13": (138.9, 139.9, 35.5, 35.9),  # 東京
    "14": (138.9, 139.8, 35.1, 35.7),  # 神奈川
    "15": (137.5, 139.3, 36.7, 38.6),  # 新潟
    "16": (136.7, 137.8, 36.3, 37.0),  # 富山
    "17": (136.3, 137.1, 36.1, 37.0),  # 石川
    "18": (135.6, 136.8, 35.3, 36.4),  # 福井
    "19": (138.2, 139.2, 35.2, 35.9),  # 山梨
    "20": (137.3, 138.6, 35.7, 36.9),  # 長野
    "21": (136.2, 137.7, 35.2, 36.4),  # 岐阜
    "22": (137.5, 138.9, 34.6, 35.6),  # 静岡
    "23": (136.7, 137.7, 34.6, 35.4),  # 愛知
    "24": (135.8, 136.9, 33.9, 35.0),  # 三重
    "25": (135.7, 136.4, 34.8, 35.7),  # 滋賀
    "26": (135.0, 135.9, 34.7, 35.8),  # 京都
    "27": (135.1, 135.7, 34.3, 34.9),  # 大阪
    "28": (134.3, 135.4, 34.2, 35.3),  # 兵庫
    "29": (135.6, 136.1, 34.2, 34.9),  # 奈良
    "30": (135.1, 135.7, 33.4, 34.4),  # 和歌山
    "31": (133.1, 134.3, 35.1, 35.6),  # 鳥取
    "32": (132.1, 133.4, 34.5, 35.6),  # 島根
    "33": (133.3, 134.3, 34.4, 35.3),  # 岡山
    "34": (131.7, 133.4, 34.0, 35.2),  # 広島
    "35": (130.8, 132.2, 33.8, 34.7),  # 山口
    "36": (133.5, 134.8, 33.6, 34.4),  # 徳島
    "37": (133.5, 134.4, 34.0, 34.5),  # 香川
    "38": (132.3, 133.7, 33.2, 34.0),  # 愛媛
    "39": (132.5, 133.9, 32.7, 33.9),  # 高知
    "40": (129.9, 131.3, 33.0, 34.3),  # 福岡
    "41": (129.3, 130.5, 33.1, 33.8),  # 佐賀
    "42": (128.6, 130.4, 32.5, 33.6),  # 長崎
    "43": (130.1, 131.3, 32.2, 33.2),  # 熊本
    "44": (130.7, 132.1, 32.7, 33.6),  # 大分
    "45": (130.6, 131.9, 31.4, 32.8),  # 宮崎
    "46": (129.3, 131.4, 30.2, 32.1),  # 鹿児島
    "47": (122.9, 128.3, 24.0, 26.9),  # 沖縄
}


def prefecture_tile_range(
    prefecture_code: str, z: int
) -> tuple[int, int, int, int]:
    """
    都道府県コードに対応する XYZ タイル範囲を返す。
    未登録コードの場合は日本全国範囲を返す。
    """
    bbox = PREFECTURE_BBOX.get(prefecture_code.zfill(2))
    if bbox is None:
        logger.warning("都道府県コード %s が未登録。全国範囲を使用します。", prefecture_code)
        return japan_tile_range(z)
    lon_min, lon_max, lat_min, lat_max = bbox
    x_min, y_max = lonlat_to_tile_indices(lon_min, lat_min, z)
    x_max, y_min = lonlat_to_tile_indices(lon_max, lat_max, z)
    return x_min, x_max, y_min, y_max


def iter_prefecture_tiles(prefecture_code: str, z: int) -> Iterator[tuple[int, int, int]]:
    """都道府県内のタイルを (z, x, y) で yield する。"""
    x_min, x_max, y_min, y_max = prefecture_tile_range(prefecture_code, z)
    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            yield z, x, y
