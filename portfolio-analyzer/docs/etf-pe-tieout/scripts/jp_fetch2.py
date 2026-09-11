# ruff: noqa  -- archived working script, kept as run on 2026-09-11
"""Annual Net Income / diluted shares / total revenue per JP ticker (for JPX-definition tie-out)."""

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import yfinance as yf

S = os.environ.get("ETF_PE_WORKDIR", "./work/")
H = json.load(open(S + "jp_holdings.json"))
syms = sorted(set(H["h1329"]) | set(H["h1475"]))
cf = S + "jp_cache2.json"
cache = json.load(open(cf)) if os.path.exists(cf) else {}
todo = [s for s in syms if s not in cache]
print("todo", len(todo), flush=True)
ROWS = [
    "Net Income",
    "Net Income Common Stockholders",
    "Diluted Average Shares",
    "Basic Average Shares",
    "Diluted EPS",
    "Basic EPS",
]


def fetch(s):
    out = {}
    for attempt in range(3):
        try:
            a = yf.Ticker(s).income_stmt
            if a is not None and not a.empty:
                for r in ROWS:
                    if r in a.index:
                        out[r] = {
                            str(k.date()): (None if pd.isna(v) else float(v))
                            for k, v in a.loc[r].items()
                        }
            try:
                sh = yf.Ticker(s).get_shares_full(start="2020-06-01")
                if sh is not None and not sh.empty:
                    sh = sh[~sh.index.duplicated(keep="last")]
                    out["shares_hist"] = {
                        str(k.date()): float(v)
                        for k, v in sh.resample("QE").last().dropna().items()
                    }
            except Exception as e:
                out["shares_err"] = repr(e)[:80]
            out["ok"] = True
            return s, out
        except Exception as e:
            out["err"] = repr(e)[:100]
            time.sleep(2 + 3 * attempt)
    return s, out


lock = threading.Lock()
done = 0
with ThreadPoolExecutor(max_workers=4) as ex:
    for s, out in ex.map(fetch, todo):
        with lock:
            cache[s] = out
            done += 1
            if done % 100 == 0:
                json.dump(cache, open(cf, "w"))
                print("fetched", done, "/", len(todo), time.strftime("%H:%M:%S"), flush=True)
json.dump(cache, open(cf, "w"))
print(
    "DONE2",
    len(cache),
    "ok",
    sum(1 for v in cache.values() if v.get("ok")),
    "with NI",
    sum(1 for v in cache.values() if v.get("Net Income")),
    "with shares_hist",
    sum(1 for v in cache.values() if v.get("shares_hist")),
    flush=True,
)
