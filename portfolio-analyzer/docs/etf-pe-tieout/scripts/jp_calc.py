# ruff: noqa  -- archived working script, kept as run on 2026-09-11
"""Reconstruct 1329/1475 P/E from holdings (harmonic weighted mean) under several conventions."""

import json
import os

import numpy as np
import pandas as pd

S = os.environ.get("ETF_PE_WORKDIR", "./work/")
H = json.load(open(S + "jp_holdings.json"))
Q = json.load(open(S + "jp_quote.json"))
C = json.load(open(S + "jp_cache.json"))
px = pd.read_pickle(S + "jp_px.pkl")
p731 = px.loc[:"2026-07-31"].iloc[-1]
p910 = px.loc[:"2026-09-10"].iloc[-1]
ANCHOR = {"1329": 21.00, "1475": 17.62}
PE_ERR = 2.0


def eps_vintage(s, asof, lag_days=45):
    """Latest annual diluted EPS whose FYE <= asof - lag (announced by asof)."""
    ann = (C.get(s) or {}).get("annual") or {}
    cutoff = pd.Timestamp(asof) - pd.Timedelta(days=lag_days)
    cands = [
        (pd.Timestamp(k), v) for k, v in ann.items() if v is not None and pd.Timestamp(k) <= cutoff
    ]
    if not cands:
        return None
    return max(cands)[1]


def eps_ttm_now(s):
    q = Q.get(s) or {}
    return q.get("epsTrailingTwelveMonths")


def eps_fy1(s):
    c = C.get(s) or {}
    return c.get("fy1") if c.get("fy1") and c.get("fy1_n", 0) >= 1 else None


def harmonic(rows, neg="exclude", missing="exclude"):
    """rows: list of (w, pe or None). pe<=0 means negative earnings."""
    valid = [(w, pe) for w, pe in rows if pe is not None]
    pos = [(w, pe) for w, pe in valid if pe > 0]
    negw = sum(w for w, pe in valid if pe <= 0)
    missw = sum(w for w, pe in rows if pe is None)
    if missing == "median" and pos:
        med = float(np.median([pe for _, pe in pos]))
        pos = pos + [(w, med) for w, pe in rows if pe is None]
        missw = 0
    num = sum(w for w, _ in pos)
    den = sum(w / pe for w, pe in pos)
    if neg == "keep":
        num += negw
    return num / den, dict(neg_w=negw, miss_w=missw, n=len(pos))


def build(code, asof):
    hold = H["h" + code]
    tot = sum(v["w"] for v in hold.values())
    rows = {}
    for s, h in hold.items():
        if asof == "2026-07-31":
            p = float(p731.get(s, np.nan))
            if not np.isfinite(p):
                p = h["px"]
            e_tr = eps_vintage(s, asof)
            if e_tr is None:  # fall back to Yahoo TTM if annual missing
                e_tr = eps_ttm_now(s)
        else:
            p = h["px"]
            e_tr = eps_ttm_now(s)
        w = h["sh"] * p
        pe_tr = (p / e_tr) if e_tr not in (None, 0) else None
        if pe_tr is not None and e_tr < 0:
            pe_tr = -abs(pe_tr)
        if (
            pe_tr is not None and 0 < pe_tr < PE_ERR
        ):  # EPS unit error (e.g. 7189 TTM 288,017 yen) -> treat as missing
            pe_tr = None
        f1 = eps_fy1(s)
        pe_f1 = (p / f1) if f1 not in (None, 0) else None
        if pe_f1 is not None and f1 < 0:
            pe_f1 = -abs(pe_f1)
        rows[s] = dict(w=w, pe_tr=pe_tr, pe_f1=pe_f1, name=h["name"])
    W = sum(r["w"] for r in rows.values())
    for r in rows.values():
        r["w"] /= W
    return rows


def report(code, asof):
    rows = build(code, asof)
    out = {}
    for kind in ("pe_tr", "pe_f1"):
        lst = [(r["w"], r[kind]) for r in rows.values()]
        for neg in ("exclude", "keep"):
            for miss in ("exclude", "median"):
                v, info = harmonic(lst, neg, miss)
                out[(kind, neg, miss)] = (v, info)
    return rows, out


if __name__ == "__main__":
    for code in ("1329", "1475"):
        for asof in ("2026-07-31", "2026-09-10"):
            rows, out = report(code, asof)
            anchor = ANCHOR[code] if asof == "2026-07-31" else None
            print(f"\n=== {code} as of {asof}  (BlackRock {anchor if anchor else 'n/a'})")
            for (kind, neg, miss), (v, info) in out.items():
                tag = f"{'実績' if kind == 'pe_tr' else 'FY1 '} 赤字={neg:7s} 欠測={miss:7s}"
                err = f"  err {100 * (v / anchor - 1):+5.1f}%" if anchor else ""
                print(
                    f"  {tag}: {v:6.2f}  (赤字w {100 * info['neg_w']:4.1f}%  欠測w {100 * info['miss_w']:4.1f}%  n={info['n']}){err}"
                )
        # top contributors to 1/PE (denominator) and largest weights
        rows, _ = report(code, "2026-09-10")
        df = pd.DataFrame(rows).T
        df["w"] = df["w"].astype(float)
        print(
            "  top10 by weight:",
            [
                (
                    s,
                    r["name"],
                    round(100 * r["w"], 2),
                    None if r["pe_tr"] is None else round(r["pe_tr"], 1),
                )
                for s, r in df.sort_values("w", ascending=False).head(10).iterrows()
            ],
        )
        neg = df[df["pe_tr"].apply(lambda x: x is not None and x <= 0)]
        print(
            "  赤字銘柄 上位:",
            [
                (s, r["name"], round(100 * r["w"], 2))
                for s, r in neg.sort_values("w", ascending=False).head(8).iterrows()
            ],
        )
        miss = df[df["pe_tr"].isna()]
        print(
            "  欠測銘柄:",
            len(miss),
            [
                (s, r["name"], round(100 * r["w"], 2))
                for s, r in miss.sort_values("w", ascending=False).head(8).iterrows()
            ],
        )
