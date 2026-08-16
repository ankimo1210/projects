"""J-Quants loader for the full TSE-listed universe (optional, needs network).

The curated ``universe_jp.toml`` covers the major names so that the framework
runs entirely offline. When credentials and outbound network are available,
this module replaces it with the authoritative list — every listed company, or
exactly TOPIX 500 / TOPIX 1000 via J-Quants' ``ScaleCategory``.

Credentials come from the environment:

    JQUANTS_MAIL_ADDRESS, JQUANTS_PASSWORD

Only the standard library is used, so this adds no production dependency.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import pandas as pd

API_ROOT = "https://api.jquants.com/v1"

#: ScaleCategory の組み合わせでインデックスを再現する。
#: TOPIX 500 = Core30 + Large70 + Mid400（JPXの定義どおり）。
SCALE_SETS: dict[str, tuple[str, ...]] = {
    "topix100": ("TOPIX Core30", "TOPIX Large70"),
    "topix500": ("TOPIX Core30", "TOPIX Large70", "TOPIX Mid400"),
    "topix1000": ("TOPIX Core30", "TOPIX Large70", "TOPIX Mid400", "TOPIX Small 1"),
    "all": (),  # no filter
}


class JQuantsError(RuntimeError):
    """Raised when authentication or the listed-info call fails."""


#: これらのクエリパラメータは資格情報そのもの。例外メッセージはログに残るので伏せる。
SECRET_QUERY_PARAMS = frozenset({"refreshtoken"})


def _redact(url: str) -> str:
    """Blank out credential query parameters, keeping the rest of the URL diagnosable."""
    split = urllib.parse.urlsplit(url)
    if not split.query:
        return url
    pairs = urllib.parse.parse_qsl(split.query, keep_blank_values=True)
    safe = [(k, "<redacted>" if k.lower() in SECRET_QUERY_PARAMS else v) for k, v in pairs]
    return urllib.parse.urlunsplit(split._replace(query=urllib.parse.urlencode(safe)))


def _fail(verb: str, url: str, exc: urllib.error.URLError) -> JQuantsError:
    """Carry the API's own error body into the exception.

    A bare ``HTTP Error 410: Gone`` says nothing about which of the many
    preconditions failed; J-Quants explains itself in the response body.
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
    return JQuantsError(f"{verb} {_redact(url)} failed: {detail}")


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.URLError as exc:  # network blocked, DNS, TLS, HTTP error
        raise _fail("POST", url, exc) from exc


def _get_json(url: str, token: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.URLError as exc:
        raise _fail("GET", url, exc) from exc


def get_id_token(mail: str | None = None, password: str | None = None) -> str:
    """Exchange credentials for an ID token (refresh token -> id token)."""
    mail = mail or os.environ.get("JQUANTS_MAIL_ADDRESS")
    password = password or os.environ.get("JQUANTS_PASSWORD")
    if not mail or not password:
        raise JQuantsError(
            "JQUANTS_MAIL_ADDRESS / JQUANTS_PASSWORD が未設定です。"
            "オフラインで動かす場合は --universe curated を使ってください。"
        )

    auth = _post_json(f"{API_ROOT}/token/auth_user", {"mailaddress": mail, "password": password})
    refresh = auth.get("refreshToken")
    if not refresh:
        raise JQuantsError(f"auth_user returned no refreshToken: {auth}")

    token_resp = _post_json(f"{API_ROOT}/token/auth_refresh?refreshtoken={refresh}", {})
    id_token = token_resp.get("idToken")
    if not id_token:
        raise JQuantsError(f"auth_refresh returned no idToken: {token_resp}")
    return id_token


def normalise_code(code: str) -> str:
    """J-Quants uses 5-character codes ('72030'); the framework uses 4 ('7203')."""
    code = str(code)
    if len(code) == 5 and code.endswith("0"):
        return code[:4]
    return code


def fetch_listed_universe(scale: str = "topix500", token: str | None = None) -> pd.DataFrame:
    """Fetch the listed universe as a frame matching ``ReferenceData.universe``.

    Returns columns ``name``, ``sector33``, ``labor_intensity``, ``knowledge_tilt``
    indexed by 4-character code. Tilts default to ``"mid"`` because J-Quants
    carries no company-level labour attributes — the curated file is the place
    where those judgements live.
    """
    if scale not in SCALE_SETS:
        raise ValueError(f"unknown scale {scale!r}; expected one of {sorted(SCALE_SETS)}")

    token = token or get_id_token()
    payload = _get_json(f"{API_ROOT}/listed/info", token)
    rows = payload.get("info", [])
    if not rows:
        raise JQuantsError("listed/info returned no rows")

    df = pd.DataFrame(rows)
    wanted = SCALE_SETS[scale]
    if wanted:
        df = df[df["ScaleCategory"].isin(wanted)]

    out = pd.DataFrame(
        {
            "code": df["Code"].map(normalise_code),
            "name": df["CompanyName"],
            "sector33": df["Sector33CodeName"].str.strip(),
            "scale_category": df["ScaleCategory"],
        }
    )
    out["labor_intensity"] = "mid"
    out["knowledge_tilt"] = "mid"
    return out.drop_duplicates(subset=["code"]).set_index("code")


#: /fins/statements の項目名 → こちらの列名。連結を優先し、単体しか無ければそちらを使う。
STATEMENT_FIELDS = {
    "NetSales": "revenue",
    "OperatingProfit": "operating_profit",
}


def fetch_statements(codes: list[str], token: str | None = None, progress: bool = True) -> pd.DataFrame:
    """Latest annual revenue / operating profit per code, from ``/fins/statements``.

    J-Quants carries no headcount or personnel-cost field, so this covers only
    the denominator of the uplift ratio. Pair it with
    :mod:`labor_ai_quadrant.providers.edinet` for employees and average salary.
    """
    token = token or get_id_token()
    records: dict[str, dict[str, float]] = {}

    for i, code in enumerate(codes, 1):
        try:
            payload = _get_json(f"{API_ROOT}/fins/statements?code={code}", token)
        except JQuantsError as exc:
            if progress:
                print(f"  {code}: skipped ({exc})")
            continue

        rows = [
            r for r in payload.get("statements", [])
            if r.get("TypeOfCurrentPeriod") == "FY"
        ]
        if not rows:
            continue
        latest = max(rows, key=lambda r: r.get("DisclosedDate", ""))

        parsed: dict[str, float] = {}
        for field, column in STATEMENT_FIELDS.items():
            raw = latest.get(field) or latest.get(f"NonConsolidated{field}")
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
