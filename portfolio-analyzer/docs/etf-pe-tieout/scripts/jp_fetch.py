# ruff: noqa  -- archived working script, kept as run on 2026-09-11
"""Collect holdings + EPS inputs for 1329/1475 reconstruction. Caches to JSON."""

import csv
import io
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import yfinance as yf
from yfinance.data import YfData

S = os.environ.get("ETF_PE_WORKDIR", "./work/")


def load_holdings(code):
    raw = open(S + f"h{code}.csv", encoding="utf-8-sig").read().splitlines()
    hdr = [i for i, l in enumerate(raw) if l.startswith("Ticker,")][0]
    rd = csv.DictReader(io.StringIO("\n".join(raw[hdr:])))
    hold = {}
    for r in rd:
        t = (r.get("Ticker") or "").strip()
        if not t or (r.get("Asset Class") or "") != "株式":
            continue
        f = lambda k: float(r[k].replace(",", ""))
        hold[t + ".T"] = dict(
            w=f("Weight (%)"), sh=f("Shares"), px=f("Price"), name=r["Name"], sector=r["Sector"]
        )
    return raw[0], hold


asof1329, h1329 = load_holdings("1329")
asof1475, h1475 = load_holdings("1475")
syms = sorted(set(h1329) | set(h1475))
print("1329", asof1329, len(h1329), round(sum(v["w"] for v in h1329.values()), 2))
print("1475", asof1475, len(h1475), round(sum(v["w"] for v in h1475.values()), 2))
print("union", len(syms), flush=True)
json.dump(
    dict(asof1329=asof1329, asof1475=asof1475, h1329=h1329, h1475=h1475),
    open(S + "jp_holdings.json", "w"),
    ensure_ascii=False,
)

# 1) bulk quote: TTM EPS + price
qf = S + "jp_quote.json"
quote = json.load(open(qf)) if os.path.exists(qf) else {}
if len(quote) < len(syms) - 20:
    d = YfData()
    fields = "symbol,regularMarketPrice,regularMarketTime,epsTrailingTwelveMonths,epsForward,trailingPE,forwardPE,marketCap,sharesOutstanding,earningsTimestamp"
    for i in range(0, len(syms), 100):
        chunk = syms[i : i + 100]
        for attempt in range(3):
            try:
                r = d.get(
                    "https://query2.finance.yahoo.com/v7/finance/quote",
                    params={"symbols": ",".join(chunk), "fields": fields},
                )
                for q in r.json()["quoteResponse"]["result"]:
                    quote[q["symbol"]] = q
                break
            except Exception as e:
                print("quote chunk err", i, repr(e)[:120])
                time.sleep(5)
        time.sleep(0.5)
    json.dump(quote, open(qf, "w"))
print(
    "quotes",
    len(quote),
    "with TTM eps",
    sum(1 for q in quote.values() if q.get("epsTrailingTwelveMonths") is not None),
    flush=True,
)

# 2) prices 7/24..now for 7/31 weights
pf = S + "jp_px.pkl"
if not os.path.exists(pf):
    px = yf.download(
        syms, start="2026-07-24", end="2026-09-12", auto_adjust=False, progress=False, threads=True
    )["Close"].ffill()
    px.to_pickle(pf)
else:
    px = pd.read_pickle(pf)
print("px", px.shape, "last", px.index[-1].date(), flush=True)

# 3) per-ticker: annual EPS, quarterly EPS, FY1 estimate
cf = S + "jp_cache.json"
cache = json.load(open(cf)) if os.path.exists(cf) else {}
lock = threading.Lock()
todo = [s for s in syms if s not in cache]
print("per-ticker todo", len(todo), flush=True)


def fetch(s):
    out = {}
    tk = yf.Ticker(s)
    for attempt in range(3):
        try:
            a = tk.income_stmt
            out["annual"] = (
                {
                    str(k.date()): (None if pd.isna(v) else float(v))
                    for k, v in a.loc["Diluted EPS"].items()
                }
                if a is not None and "Diluted EPS" in a.index
                else {}
            )
            q = tk.quarterly_income_stmt
            out["quarterly"] = (
                {
                    str(k.date()): (None if pd.isna(v) else float(v))
                    for k, v in q.loc["Diluted EPS"].items()
                }
                if q is not None and "Diluted EPS" in q.index
                else {}
            )
            try:
                e = tk.earnings_estimate
                if e is not None and not e.empty and "0y" in e.index:
                    out["fy1"] = None if pd.isna(e.loc["0y", "avg"]) else float(e.loc["0y", "avg"])
                    out["fy1_n"] = (
                        None
                        if pd.isna(e.loc["0y", "numberOfAnalysts"])
                        else int(e.loc["0y", "numberOfAnalysts"])
                    )
                    if "+1y" in e.index:
                        out["fy2"] = (
                            None if pd.isna(e.loc["+1y", "avg"]) else float(e.loc["+1y", "avg"])
                        )
            except Exception as ex:
                out["fy1_err"] = repr(ex)[:80]
            out["ok"] = True
            return s, out
        except Exception as ex:
            out["err"] = repr(ex)[:120]
            time.sleep(2 + 3 * attempt)
    return s, out


done = 0
with ThreadPoolExecutor(max_workers=4) as ex:
    for s, out in ex.map(fetch, todo):
        with lock:
            cache[s] = out
            done += 1
            if done % 50 == 0:
                json.dump(cache, open(cf, "w"))
                print("fetched", done, "/", len(todo), time.strftime("%H:%M:%S"), flush=True)
json.dump(cache, open(cf, "w"))
print(
    "DONE per-ticker",
    len(cache),
    "ok",
    sum(1 for v in cache.values() if v.get("ok")),
    "fy1",
    sum(1 for v in cache.values() if v.get("fy1")),
    flush=True,
)
