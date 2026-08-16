"""J-Quants loader for the full TSE-listed universe (optional, needs network).

The curated ``universe_jp.toml`` covers the major names so that the framework
runs entirely offline. When credentials and outbound network are available,
this module replaces it with the authoritative list — every listed company, or
exactly TOPIX 500 / TOPIX 1000 via J-Quants' ``ScaleCat``.

This targets **API v2**. v1 was retired: every ``api.jquants.com/v1`` endpoint
answers HTTP 410 Gone, and the two-step ``token/auth_user`` →
``token/auth_refresh`` dance no longer exists. v2 authenticates with a single
long-lived API key in the ``x-api-key`` header::

    JQUANTS_API_KEY        (JQUANTS_REFRESH_TOKEN is accepted as an alias —
                            the v1 refresh token doubles as the v2 API key)

Only the standard library is used, so this adds no production dependency.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import pandas as pd

API_ROOT = "https://api.jquants.com/v2"

#: ScaleCat の組み合わせでインデックスを再現する。
#: TOPIX 500 = Core30 + Large70 + Mid400（JPXの定義どおり）。
#: 値の文字列は v1 の ScaleCategory から変わっていない（2026-08-16 実測）。
SCALE_SETS: dict[str, tuple[str, ...]] = {
    "topix100": ("TOPIX Core30", "TOPIX Large70"),
    "topix500": ("TOPIX Core30", "TOPIX Large70", "TOPIX Mid400"),
    "topix1000": ("TOPIX Core30", "TOPIX Large70", "TOPIX Mid400", "TOPIX Small 1"),
    "all": (),  # no filter
}


class JQuantsError(RuntimeError):
    """Raised when authentication or a data call fails."""


def _api_key(explicit: str | None = None) -> str:
    """The v2 subscription key.

    ``JQUANTS_REFRESH_TOKEN`` is accepted because the v1 refresh token is the
    same string v2 wants in ``x-api-key``; existing ``.env`` files carry it
    under the old name.
    """
    key = explicit or os.environ.get("JQUANTS_API_KEY") or os.environ.get("JQUANTS_REFRESH_TOKEN")
    if not key:
        raise JQuantsError(
            "JQUANTS_API_KEY が未設定です。"
            "オフラインで動かす場合は --universe curated を使ってください。"
        )
    return key


def _fail(url: str, exc: urllib.error.URLError) -> JQuantsError:
    """Carry the API's own error body into the exception.

    A bare ``HTTP Error 403: Forbidden`` cannot distinguish a bad key from an
    endpoint the subscription does not cover; J-Quants explains itself in the
    response body.
    """
    if isinstance(exc, urllib.error.HTTPError):
        try:
            body = exc.read().decode("utf-8", errors="replace").strip()
        except Exception:  # body already consumed, or not readable
            body = ""
        detail = f"HTTP {exc.code} {exc.reason}"
        if body:
            detail = f"{detail}: {body[:500]}"
    else:
        detail = str(getattr(exc, "reason", exc))
    return JQuantsError(f"GET {url} failed: {detail}")


#: HTTP 429 に当たったときの待ち時間（秒）。J-Quants の制限はトークンバケット的で、
#: 数十件の連続呼び出しは通るがその後じわじわ絞られる（2026-08-17 実測）。TOPIX 500 の
#: 493 銘柄を1件ずつ引くと途中で必ず当たるので、諦めずに待って続ける。
RATE_LIMIT_BACKOFF_SECONDS = (5, 15, 45, 120)


def _get_json(path: str, api_key: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    query = urllib.parse.urlencode(params or {})
    url = f"{API_ROOT}/{path}" + (f"?{query}" if query else "")
    req = urllib.request.Request(url, headers={"x-api-key": api_key})
    for wait in (*RATE_LIMIT_BACKOFF_SECONDS, None):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or wait is None:
                raise _fail(url, exc) from exc
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            time.sleep(float(retry_after) if retry_after and retry_after.isdigit() else wait)
        except urllib.error.URLError as exc:
            raise _fail(url, exc) from exc
    raise AssertionError("unreachable")  # pragma: no cover


def _get_rows(path: str, api_key: str, params: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """Every row of a v2 endpoint, following ``pagination_key`` to the end.

    v2 caps a response and hands back a ``pagination_key`` when more remains.
    Ignoring it silently truncates the universe, which looks like a shrinking
    index rather than a bug.
    """
    params = dict(params or {})
    rows: list[dict[str, Any]] = []
    while True:
        payload = _get_json(path, api_key, params)
        rows.extend(payload.get("data") or [])
        key = payload.get("pagination_key")
        if not key:
            return rows
        params["pagination_key"] = key


def normalise_code(code: str) -> str:
    """J-Quants uses 5-character codes ('72030'); the framework uses 4 ('7203')."""
    code = str(code)
    if len(code) == 5 and code.endswith("0"):
        return code[:4]
    return code


def fetch_listed_universe(scale: str = "topix500", api_key: str | None = None) -> pd.DataFrame:
    """Fetch the listed universe as a frame matching ``ReferenceData.universe``.

    Returns columns ``name``, ``sector33``, ``labor_intensity``, ``knowledge_tilt``
    indexed by 4-character code. Tilts default to ``"mid"`` because J-Quants
    carries no company-level labour attributes — the curated file is the place
    where those judgements live.
    """
    if scale not in SCALE_SETS:
        raise ValueError(f"unknown scale {scale!r}; expected one of {sorted(SCALE_SETS)}")

    rows = _get_rows("equities/master", _api_key(api_key))
    if not rows:
        raise JQuantsError("equities/master returned no rows")

    df = pd.DataFrame(rows)
    wanted = SCALE_SETS[scale]
    if wanted:
        df = df[df["ScaleCat"].isin(wanted)]
        if df.empty:
            raise JQuantsError(
                f"scale={scale!r} に該当する銘柄がありません。"
                f"ScaleCat の実値: {sorted(set(pd.DataFrame(rows)['ScaleCat']))}"
            )

    out = pd.DataFrame(
        {
            "code": df["Code"].map(normalise_code),
            "name": df["CoName"],
            "sector33": df["S33Nm"].str.strip(),
            # 業種名の表記は J-Quants 側で揺れる（半角中黒 '･' と全角 '・' が混在し、
            # 「証券、商品先物取引業」は読点が中黒になる）。参照テーブルとの結合は
            # 表記が安定しているこのコードで行う。
            "sector33_code": df["S33"].astype(str).str.strip(),
            "scale_category": df["ScaleCat"],
        }
    )
    out["labor_intensity"] = "mid"
    out["knowledge_tilt"] = "mid"
    return out.drop_duplicates(subset=["code"]).set_index("code")


#: /fins/summary の項目名 → こちらの列名。v2 は短縮名になっている
#: （v1 の NetSales / OperatingProfit に相当）。
SUMMARY_FIELDS = {
    "Sales": "revenue",
    "OP": "operating_profit",
}


def fetch_summaries(codes: list[str], api_key: str | None = None, progress: bool = True) -> pd.DataFrame:
    """Latest annual revenue / operating profit per code, from ``/fins/summary``.

    These are the figures in the 決算短信, i.e. **consolidated** for any filer
    that consolidates. J-Quants carries no headcount or personnel-cost field, so
    this covers only the denominator of the uplift ratio. Pair it with
    :mod:`labor_ai_quadrant.providers.edinet` for employees and average salary.
    """
    key = _api_key(api_key)
    records: dict[str, dict[str, float]] = {}

    for i, code in enumerate(codes, 1):
        try:
            rows = _get_rows("fins/summary", key, {"code": code})
        except JQuantsError as exc:
            if progress:
                print(f"  {code}: skipped ({exc})")
            continue

        annual = [r for r in rows if r.get("CurPerType") == "FY"]
        if not annual:
            continue
        latest = max(annual, key=lambda r: r.get("DiscDate", ""))

        parsed: dict[str, float] = {}
        for field, column in SUMMARY_FIELDS.items():
            raw = latest.get(field)
            if raw not in (None, ""):
                try:
                    parsed[column] = float(raw)
                except (TypeError, ValueError):
                    pass
        if parsed:
            records[code] = parsed

        if progress and i % 50 == 0:
            print(f"  {i}/{len(codes)} 銘柄を処理（取得 {len(records)} 件）")

    df = pd.DataFrame.from_dict(records, orient="index")
    df.index.name = "code"
    return df
