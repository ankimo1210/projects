# ruff: noqa  -- archived working script, kept as run on 2026-09-11
"""US ETF historical P/E reconstruction from N-PORT holdings + SEC XBRL point-in-time EPS.

usage: python us_hist.py <nport_dir> <figi_map.json> <sec_eps.json> <splits.json> <out.csv> [anchors.json]
"""

import json
import os
import sys

import numpy as np
import pandas as pd

S = os.environ.get("ETF_PE_WORKDIR", "./work/")
nport_dir, figi_f, eps_f, splits_f, out_f = sys.argv[1:6]
anchors = json.load(open(sys.argv[6])) if len(sys.argv) > 6 else {}
H = json.load(open(nport_dir + "/holdings.json"))
FIGI = json.load(open(figi_f))
EPS = json.load(open(eps_f))
SPL = json.load(open(splits_f))
PE_ERR = 1.0  # implied P/E below this = data error -> treat as missing
FX = pd.read_pickle(S + "fx.pkl")  # yfinance quotes: 'XXX=X' = USD->XXX, 'XXXUSD=X' = XXX->USD
ADR = {
    "TSM": 5,
    "PDD": 4,
    "JD": 2,
    "BIDU": 8,
    "NTES": 5,
    "AZN": 0.5,
    "TCOM": 1,
    "ASML": 1,
    "STM": 1,
    "CHKP": 1,
    "CCEP": 1,
    "FER": 1,
    "NBIS": 1,
    "ARM": 1,
}
MAX_STALE_DAYS = 400


def to_usd(val, unit, asof):
    cur = (unit or "USD/shares").split("/")[0].upper()
    if cur == "USD":
        return val
    ts = pd.Timestamp(asof)
    row = FX.loc[:ts].iloc[-1]
    if f"{cur}USD=X" in FX.columns and np.isfinite(row[f"{cur}USD=X"]):
        return val * row[f"{cur}USD=X"]
    if f"{cur}=X" in FX.columns and np.isfinite(row[f"{cur}=X"]) and row[f"{cur}=X"]:
        return val / row[f"{cur}=X"]
    return None


def split_factor(tkr, after, upto):
    f = 1.0
    for d, r in (SPL.get(tkr) or {}).items():
        if not d.startswith("_") and after < d <= upto and r:
            f *= r
    return f


def key_of(h):
    return (
        h["cusip"]
        if h["cusip"] and h["cusip"] not in ("N/A", "000000000")
        else ("ISIN:" + h["isin"] if h["isin"] else "NAME:" + h["name"])
    )


def quarterly_series(points, asof):
    """Point-in-time quarterly diluted EPS as known at `asof` (filed <= asof).
    Returns dict period_end -> (val, filed). Q4 derived as FY - (Q1+Q2+Q3) from the 10-K when needed."""
    q = {}
    fy = {}
    for p in points:
        if not p.get("start") or not p.get("end") or p.get("val") is None or not p.get("filed"):
            continue
        if p["filed"] > asof:
            continue
        s, e = pd.Timestamp(p["start"]), pd.Timestamp(p["end"])
        dur = (e - s).days
        if 80 <= dur <= 100:
            # keep the latest filing for each period end (restated / split-adjusted values win)
            if e not in q or p["filed"] >= q[e][1]:
                q[e] = (float(p["val"]), p["filed"], p.get("unit"))
        elif 350 <= dur <= 380:
            if e not in fy or p["filed"] >= fy[e][1]:
                fy[e] = (float(p["val"]), p["filed"], s, p.get("unit"))
    # derive missing Q4s = FY - (Q1+Q2+Q3), with the three quarters restated onto the 10-K's share basis
    for e, (v, filed, s, unit) in fy.items():
        if e in q:
            continue
        prior = [pe for pe in q if s < pe < e]
        if len(prior) == 3:
            q[e] = (
                v - sum(q[pe][0] / split_factor(TKR, q[pe][1], filed) for pe in prior),
                filed,
                unit,
            )
    return q, fy


TKR = None


def ttm_eps(tkr, asof):
    global TKR
    TKR = tkr
    rec = EPS.get(tkr)
    if not rec or not rec.get("points"):
        return None, "no_data"
    q, fy = quarterly_series(rec["points"], asof)
    asof_ts = pd.Timestamp(asof)
    ends = sorted(e for e in q if e <= asof_ts)
    if len(ends) >= 4 and (asof_ts - ends[-1]).days <= MAX_STALE_DAYS:
        last4 = ends[-4:]
        if (last4[-1] - last4[0]).days <= 400:
            # restate each quarter onto the asof share basis: divide by splits dated after ITS filing
            val = 0.0
            unit = q[last4[-1]][2]
            for e in last4:
                v, filed, _ = q[e]
                val += v / split_factor(tkr, filed, asof)
            usd = to_usd(val, unit, asof)
            if usd is None:
                return None, f"fx:{unit}"
            return usd * ADR.get(tkr, 1), f"q4:{last4[-1].date()}"
    # fallback: latest annual (20-F filers etc.), if not stale
    fys = sorted(e for e in fy if e <= asof_ts and (asof_ts - e).days <= 500)
    if fys:
        e = fys[-1]
        v, filed, _, unit = fy[e]
        val = v / split_factor(tkr, filed, asof)
        usd = to_usd(val, unit, asof)
        if usd is None:
            return None, f"fx:{unit}"
        return usd * ADR.get(tkr, 1), f"fy:{e.date()}"
    return None, "stale_or_insufficient"


def harmonic(rows, neg, missing):
    valid = [(w, pe) for w, pe in rows if pe is not None]
    pos = [(w, pe) for w, pe in valid if pe > 0]
    negw = sum(w for w, pe in valid if pe <= 0)
    missw = sum(w for w, pe in rows if pe is None)
    if missing == "median" and pos:
        med = float(np.median([pe for _, pe in pos]))
        pos = pos + [(w, med) for w, pe in rows if pe is None]
    num = sum(w for w, _ in pos)
    den = sum(w / pe for w, pe in pos)
    if neg == "keep":
        num += negw
    return (num / den if den else None), negw, missw


out = []
detail = {}
for rd in sorted(H):
    p = H[rd]
    rows = []
    miss_names = []
    neg_names = []
    tot = sum(h["valUSD"] for h in p["holdings"])
    for h in p["holdings"]:
        if h["valUSD"] <= 0 or h["balance"] <= 0:
            continue
        w = h["valUSD"] / tot
        price = h["valUSD"] / h["balance"]
        tkr = (FIGI.get(key_of(h)) or {}).get("ticker")
        eps, how = ttm_eps(tkr, rd) if tkr else (None, "no_ticker")
        pe = None
        if eps is not None and eps != 0:
            pe = price / eps
            if 0 < pe < PE_ERR:
                pe = None
                how += ":pe_err"
        if pe is None:
            miss_names.append((tkr or h["name"], round(100 * w, 2), how))
        elif pe <= 0:
            neg_names.append((tkr, round(100 * w, 2)))
        rows.append((w, pe))
        detail.setdefault(rd, []).append(
            dict(tkr=tkr, name=h["name"], w=w, price=price, eps=eps, pe=pe, how=how)
        )
    res = {}
    for neg in ("exclude", "keep"):
        for mis in ("exclude", "median"):
            v, negw, missw = harmonic(rows, neg, mis)
            res[f"{neg}/{mis}"] = v
    out.append(
        dict(
            date=rd,
            n=len(rows),
            **{k: (round(v, 2) if v else None) for k, v in res.items()},
            neg_w=round(100 * negw, 2),
            miss_w=round(100 * missw, 2),
            anchor=anchors.get(rd),
            miss=";".join(f"{a}:{b}" for a, b, c in sorted(miss_names, key=lambda x: -x[1])[:6]),
        )
    )
df = pd.DataFrame(out)
for col in ("exclude/median", "keep/median"):
    df["err_" + col.split("/")[0]] = df.apply(
        lambda r: (100 * (r[col] / r["anchor"] - 1)) if r["anchor"] and r[col] else np.nan, axis=1
    ).round(1)
pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 60)
print(df.drop(columns=["exclude/exclude", "keep/exclude"]).to_string(index=False))
df.to_csv(out_f, index=False)
json.dump(detail, open(out_f.replace(".csv", "_detail.json"), "w"))
a = df.dropna(subset=["anchor"])
if len(a):
    print(
        "\nanchored points",
        len(a),
        " MAE exclude",
        a["err_exclude"].abs().mean().round(2),
        " MAE keep",
        a["err_keep"].abs().mean().round(2),
        " mean err exclude",
        a["err_exclude"].mean().round(2),
        " keep",
        a["err_keep"].mean().round(2),
    )
