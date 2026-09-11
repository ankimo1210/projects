# ruff: noqa  -- archived working script, kept as run on 2026-09-11
"""Quarterly reported EPS with announcement dates (Yahoo earnings_dates) for all JP names -> point-in-time TTM."""

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import yfinance as yf

S = os.environ.get("ETF_PE_WORKDIR", "./work/")
H = json.load(open(S + "jp_holdings.json"))
syms = sorted(set(H["h1329"]) | set(H["h1475"]))
cf = S + "jp_qeps.json"
cache = json.load(open(cf)) if os.path.exists(cf) else {}
todo = [s for s in syms if s not in cache]
print("todo", len(todo), flush=True)


def fetch(s):
    for attempt in range(3):
        try:
            e = yf.Ticker(s).get_earnings_dates(limit=60)
            if e is None or e.empty:
                return s, {}
            e = e[e["Reported EPS"].notna()]
            return s, {k.strftime("%Y-%m-%d"): float(v) for k, v in e["Reported EPS"].items()}
        except Exception as ex:
            err = repr(ex)[:80]
            time.sleep(2 + 3 * attempt)
    return s, {"_err": err}


lock = threading.Lock()
done = 0
with ThreadPoolExecutor(max_workers=4) as ex:
    for s, out in ex.map(fetch, todo):
        with lock:
            cache[s] = out
            done += 1
            if done % 200 == 0:
                json.dump(cache, open(cf, "w"))
                print("fetched", done, time.strftime("%H:%M:%S"), flush=True)
json.dump(cache, open(cf, "w"))
print(
    "DONE4",
    len(cache),
    "with data",
    sum(1 for v in cache.values() if v and "_err" not in v),
    "median rows",
    sorted(len(v) for v in cache.values())[len(cache) // 2],
    flush=True,
)
