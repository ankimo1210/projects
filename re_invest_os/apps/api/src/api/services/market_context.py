"""MarketContext: 公示地価・取引価格データを使った市場比較情報。

v1: stub 実装。Supabase + 公示地価 ETL 完了後に実データで置き換える。
本番では Score の market_cap_rate コンポーネントをこれで駆動する。
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class MarketContext:
    """近傍エリアの市場データ。Score に渡すための構造体。"""

    pref_code: str
    area_name: str | None
    # 近傍の公示地価 (円/㎡)
    nearby_land_price_per_sqm: float | None = None
    # 近傍取引の NOI Cap 中央値
    market_cap_rate_median: float | None = None
    # 近傍取引の表面利回り中央値
    market_gross_yield_median: float | None = None
    # サンプル件数
    sample_count: int = 0
    # データソース
    data_source: str = "none"


# DB 接続文字列 (Supabase postgres が設定されれば実データを使う)
_DATABASE_URL = os.getenv("DATABASE_URL", "")


def get_market_context(
    pref_code: str,
    city_code: str | None = None,
    radius_km: float = 2.0,
) -> MarketContext | None:
    """近傍エリアの MarketContext を返す。

    v1: DB 未接続または公示地価データ未投入の場合は None を返す。
    Score 側は None を受け取った場合 market_cap_rate を 0 点にする (既存挙動維持)。

    v2 以降: Supabase から public_notice_prices / trade_prices を
    PostGIS ST_DWithin で近傍検索する実装に差し替える。
    """
    if not _DATABASE_URL or _DATABASE_URL.startswith("sqlite"):
        # SQLite dev 環境ではデータなし
        return None

    # TODO: Supabase 接続後に実装
    # SELECT avg(price_per_sqm) FROM public_notice_prices
    # WHERE pref_code = :pref AND year = (SELECT max(year) FROM public_notice_prices)
    # AND ST_DWithin(geom, ST_MakePoint(:lng, :lat), :radius_m)
    return None
