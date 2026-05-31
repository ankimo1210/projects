"""国交省 不動産情報ライブラリ XIT001 (取引価格) による実市場データ。

公式APIで取得できるのは取引価格・面積。¥/㎡ = TradePrice / Area。
賃料・Cap rate は公式APIに無いため別ソース (Web リサーチ) で後続対応。

設計: docs/design/2026-05-30-market-grounding-v1-design.md（甘さスコア向けに再構成）。
- 純粋関数 (`trade_price_stats` 等) は I/O を持たずテスト可能。
- HTTP は `get_fn` で注入可能（テストは fixture でネットワーク非依存）。
"""

from __future__ import annotations

import datetime as _dt
import gzip
import json
import math
import os
import urllib.parse
import urllib.request
from collections.abc import Callable

from pydantic import BaseModel, ConfigDict

REINFOLIB_BASE_URL = "https://www.reinfolib.mlit.go.jp/ex-api/external"
DEFAULT_TRADE_TYPE = "中古マンション等"

# (path, params) -> list[record dict]
GetFn = Callable[[str, dict], list[dict]]


class TradePriceStat(BaseModel):
    median_yen_per_sqm: float | None
    p25_yen_per_sqm: float | None
    p75_yen_per_sqm: float | None
    sample_count: int
    type_filter: str
    model_config = ConfigDict(extra="forbid")


class MarketSnapshot(BaseModel):
    """エリアの実取引に基づく市場スナップショット（出所・取得時刻つき）。"""

    pref_code: str
    city_code: str | None
    period: str | None  # "2025Q1" 等
    trade: TradePriceStat | None
    source: str
    source_url: str
    fetched_at: str  # ISO8601 (UTC)
    model_config = ConfigDict(extra="forbid")


def _price_per_sqm(rec: dict) -> float | None:
    """XIT001 レコードから ¥/㎡ を算出。マンションは UnitPrice 空なので TradePrice/Area。"""
    try:
        price = float(str(rec.get("TradePrice")))
        area = float(str(rec.get("Area")))
    except (TypeError, ValueError):
        return None
    if price <= 0 or area <= 0:
        return None
    return price / area


def _quantile(sorted_vals: list[float], p: float) -> float:
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = p * (len(sorted_vals) - 1)
    lo, hi = math.floor(idx), math.ceil(idx)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (idx - lo)


def trade_price_stats(
    records: list[dict], type_filter: str = DEFAULT_TRADE_TYPE
) -> TradePriceStat:
    """XIT001 レコード群から ¥/㎡ の中央値・四分位・件数を算出（純粋関数）。"""
    vals: list[float] = []
    for r in records:
        if type_filter and r.get("Type") != type_filter:
            continue
        v = _price_per_sqm(r)
        if v is not None:
            vals.append(v)
    if not vals:
        return TradePriceStat(
            median_yen_per_sqm=None, p25_yen_per_sqm=None, p75_yen_per_sqm=None,
            sample_count=0, type_filter=type_filter,
        )
    vals.sort()
    return TradePriceStat(
        median_yen_per_sqm=round(_quantile(vals, 0.5), 1),
        p25_yen_per_sqm=round(_quantile(vals, 0.25), 1),
        p75_yen_per_sqm=round(_quantile(vals, 0.75), 1),
        sample_count=len(vals),
        type_filter=type_filter,
    )


def recent_quarters(now: _dt.date | None = None, back: int = 8) -> list[tuple[int, int]]:
    """公表ラグ(約2四半期)を見込み、新しい順に (year, quarter) 候補を返す。"""
    now = now or _dt.date.today()
    cy, cq = now.year, (now.month - 1) // 3 + 1
    for _ in range(2):  # 2四半期戻して公表済みの想定開始点に
        cq -= 1
        if cq == 0:
            cq, cy = 4, cy - 1
    out: list[tuple[int, int]] = []
    for _ in range(back):
        out.append((cy, cq))
        cq -= 1
        if cq == 0:
            cq, cy = 4, cy - 1
    return out


def resolve_city_code(
    pref_code: str, city_name: str | None, *, get_fn: GetFn | None = None
) -> str | None:
    """XIT002 の市区町村一覧から名称→コードを解決。見つからなければ None。"""
    if not city_name:
        return None
    get_fn = get_fn or _default_get
    try:
        cities = get_fn("/XIT002", {"area": pref_code.zfill(2)})
    except Exception:
        return None
    for c in cities:  # 完全一致
        if str(c.get("name", "")) == city_name:
            return str(c.get("id"))
    for c in cities:  # 部分一致 (「新宿区」⊆「東京都新宿区」等の揺れ吸収)
        name = str(c.get("name", ""))
        if name and (name in city_name or city_name in name):
            return str(c.get("id"))
    return None


def get_property_market(
    pref_code: str,
    city_name: str | None = None,
    city_code: str | None = None,
    *,
    get_fn: GetFn | None = None,
    now: _dt.date | None = None,
) -> MarketSnapshot | None:
    """物件の都道府県+市区町村(名 or コード)から市場スナップショットを取得。"""
    code = city_code or resolve_city_code(pref_code, city_name, get_fn=get_fn)
    return get_area_market(pref_code, code, get_fn=get_fn, now=now)


def _default_get(path: str, params: dict) -> list[dict]:
    key = os.environ.get("REINFOLIB_API_KEY")
    if not key:
        raise RuntimeError("REINFOLIB_API_KEY not set")
    url = f"{REINFOLIB_BASE_URL}{path}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={
            "Ocp-Apim-Subscription-Key": key,
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = resp.read()
    if content[:2] == b"\x1f\x8b":  # gzip マジックバイト
        content = gzip.decompress(content)
    data = json.loads(content.decode("utf-8"))
    if isinstance(data, dict):
        return data.get("data", [])
    return data or []


def get_area_market(
    pref_code: str,
    city_code: str | None = None,
    *,
    get_fn: GetFn | None = None,
    now: _dt.date | None = None,
    type_filter: str = DEFAULT_TRADE_TYPE,
) -> MarketSnapshot | None:
    """エリアの最新の実取引から MarketSnapshot を返す。データ/キー無しなら None（degrade）。"""
    get_fn = get_fn or _default_get
    base = {"city": str(city_code)} if city_code else {"area": pref_code.zfill(2)}
    for year, quarter in recent_quarters(now):
        params = {**base, "year": str(year), "quarter": str(quarter)}
        try:
            recs = get_fn("/XIT001", params)
        except Exception:
            recs = []
        if not recs:
            continue
        stats = trade_price_stats(recs, type_filter)
        if stats.sample_count > 0:
            return MarketSnapshot(
                pref_code=pref_code,
                city_code=str(city_code) if city_code else None,
                period=f"{year}Q{quarter}",
                trade=stats,
                source="国交省 不動産情報ライブラリ XIT001 (取引価格)",
                source_url="https://www.reinfolib.mlit.go.jp/",
                fetched_at=_dt.datetime.now(_dt.UTC).isoformat(),
            )
    return None
