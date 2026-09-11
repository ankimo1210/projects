# ruff: noqa  -- archived working script, kept as run on 2026-09-11
"""JP historical tie-out v2: quarterly reported EPS (Yahoo earnings_dates, split-adjusted, with announcement dates)
-> point-in-time TTM and FY EPS; JPX-definition (full shares, negatives included) vs JPX monthly; ETF-style series for 1329/1475."""

import json
import os

import numpy as np
import pandas as pd

S = os.environ.get("ETF_PE_WORKDIR", "./work/")
H = json.load(open(S + "jp_holdings.json"))
C = json.load(open(S + "jp_cache.json"))
C2 = json.load(open(S + "jp_cache2.json"))
SP = json.load(open(S + "jp_splits.json"))
QE = json.load(open(S + "jp_qeps.json"))
px = pd.read_pickle(S + "jp_px5y.pkl")
px.index = pd.to_datetime(px.index)
me = px.resample("ME").last()
jpx = json.load(open(S + "jpx_per_series.json"))
seg = pd.read_excel(S + "jpx_data_j.xls")
seg["code"] = seg["コード"].astype(str)
prime = {
    c + ".T" for c, m in zip(seg["code"], seg["市場・商品区分"]) if m == "プライム（内国株式）"
}
syms = sorted(set(H["h1475"]) | set(H["h1329"]))


def fye_month(s):
    ann = (C.get(s) or {}).get("annual") or {}
    ks = sorted(ann)
    return pd.Timestamp(ks[-1]).month if ks else 3


def qeps(s):
    d = QE.get(s) or {}
    return sorted((pd.Timestamp(k), v) for k, v in d.items() if not k.startswith("_"))


def ttm(s, m):
    """Sum of the last 4 quarterly reported EPS announced on or before m."""
    e = [(d, v) for d, v in qeps(s) if d <= m]
    if len(e) < 4:
        return None
    last = e[-4:]
    if (last[-1][0] - last[0][0]).days > 400 or (m - last[-1][0]).days > 400:
        return None  # stale coverage (Yahoo stops for many small caps)
    return sum(v for _, v in last)


def fy_eps(s, m, lag_days=45):
    """Annual EPS of the last fiscal year whose results were announced by m (JPX: confirmed annual figures).
    The FY's 4 quarterly announcements are the 4 announcements ending with the one made ~lag days after FYE."""
    fm = fye_month(s)
    e = qeps(s)
    if len(e) < 4:
        return None
    # candidate FYEs: month-ends with month==fm, FYE <= m - lag
    cands = []
    for d, _ in e:
        pass
    y0 = m.year
    out = None
    for y in range(y0, y0 - 3, -1):
        fye = pd.Timestamp(year=y, month=fm, day=1) + pd.offsets.MonthEnd(0)
        if fye > m - pd.Timedelta(days=lag_days):
            continue
        if fye < m - pd.DateOffset(months=15):
            return None  # only the most recent completed FY counts
        # the Q4 announcement is the first announcement after FYE (within 100 days)
        q4 = [(d, v) for d, v in e if fye < d <= fye + pd.Timedelta(days=100)]
        if not q4 or q4[0][0] > m:
            continue
        idx = [i for i, (d, v) in enumerate(e) if d == q4[0][0]][0]
        if idx < 3:
            return None
        last4 = e[idx - 3 : idx + 1]
        if (last4[-1][0] - last4[0][0]).days > 400:
            return None
        return sum(v for _, v in last4)
    return None


def split_factor_after(s, t):
    f = 1.0
    for d, r in (SP.get(s) or {}).items():
        if not d.startswith("_") and pd.Timestamp(d) > t and r:
            f *= r
    return f


def shares_asof(s, m):
    c = C2.get(s) or {}
    sh = c.get("shares_hist") or {}
    cands = [
        (pd.Timestamp(k), v) for k, v in sh.items() if pd.Timestamp(k) <= m + pd.Timedelta(days=3)
    ]
    if cands:
        t, v = max(cands)
        return v * split_factor_after(s, t)
    d = c.get("Diluted Average Shares") or c.get("Basic Average Shares") or {}
    cands = [(pd.Timestamp(k), v) for k, v in d.items() if v is not None]
    return max(cands)[1] if cands else None


rows = []
for m in me.index:
    if m < pd.Timestamp("2020-06-30"):
        continue
    ym = m.strftime("%Y%m")
    if ym not in jpx:
        continue
    key = [k for k in jpx[ym]["rows"] if k.endswith("|総合") and ("プライム" in k or "一部" in k)]
    if not key:
        continue
    j = jpx[ym]["rows"][key[0]]
    mcap = ni = 0
    n = 0
    etf = {}
    for code in ("1475", "1329"):
        etf[code] = dict(num=0.0, den=0.0, neg=0, miss=0, nummed=[], w_all=0.0)
    for s in syms:
        p = me.at[m, s] if s in me.columns else np.nan
        if not np.isfinite(p):
            continue
        sh = shares_asof(s, m)
        e_fy = fy_eps(s, m)
        e_ttm = ttm(s, m)
        if s in prime and e_fy is not None and sh:
            v = e_fy * sh
            pe_i = p / e_fy if e_fy else None
            if pe_i is not None and (0 < pe_i < 1 or abs(pe_i) > 2000):
                pass
            else:
                mcap += p * sh
                ni += v
                n += 1
        for code in ("1475", "1329"):
            if s in H["h" + code]:
                w = H["h" + code][s]["sh"] * p
                d = etf[code]
                d["w_all"] += w
                if e_ttm is None:
                    d["miss"] += 1
                    continue
                pe = p / e_ttm if e_ttm else None
                if pe is None or 0 < pe < 2:
                    d["miss"] += 1
                    continue
                if pe <= 0:
                    d["neg"] += 1
                    continue
                d["num"] += w
                d["den"] += w / pe
    rows.append(
        dict(
            month=m.date(),
            jpx_n=j["n"],
            jpx_w_per=j["w_per"],
            recon_jpx=mcap / ni if ni else None,
            n=n,
            etf1475=etf["1475"]["num"] / etf["1475"]["den"] if etf["1475"]["den"] else None,
            miss1475=etf["1475"]["miss"],
            neg1475=etf["1475"]["neg"],
            etf1329=etf["1329"]["num"] / etf["1329"]["den"] if etf["1329"]["den"] else None,
            miss1329=etf["1329"]["miss"],
            neg1329=etf["1329"]["neg"],
        )
    )
df = pd.DataFrame(rows)
df["err_%"] = (100 * (df.recon_jpx / df.jpx_w_per - 1)).round(1)
for c in ("recon_jpx", "etf1475", "etf1329"):
    df[c] = df[c].round(2)
pd.set_option("display.width", 220)
print(df.to_string(index=False))
df.to_csv(S + "jp_hist2_tieout.csv", index=False)
print(
    "\nJPX-def: MAE %",
    df["err_%"].abs().mean().round(2),
    " mean",
    df["err_%"].mean().round(2),
    " months",
    len(df),
    " months with n>1000",
    int((df.n > 1000).sum()),
)
