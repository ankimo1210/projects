# ruff: noqa  -- archived working script, kept as run on 2026-09-11
"""Split history per JP ticker (to align point-in-time share counts with split-adjusted prices)."""

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
cf = S + "jp_splits.json"
cache = json.load(open(cf)) if os.path.exists(cf) else {}
todo = [s for s in syms if s not in cache]
print("todo", len(todo), flush=True)


def fetch(s):
    for attempt in range(3):
        try:
            sp = yf.Ticker(s).splits
            return s, {
                str(k.date()): float(v)
                for k, v in sp.items()
                if k >= pd.Timestamp("2019-01-01", tz=k.tz)
            } if sp is not None and len(sp) else {}
        except Exception as e:
            time.sleep(2 + 3 * attempt)
            err = repr(e)[:80]
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
    "DONE3",
    len(cache),
    "with splits",
    sum(1 for v in cache.values() if v and "_err" not in v),
    flush=True,
)
# probe: quarterly reported EPS history availability for JP names
for s in ["7203.T", "8306.T", "6501.T", "9432.T", "2802.T"]:
    try:
        e = yf.Ticker(s).get_earnings_dates(limit=30)
        print(
            s,
            "earnings_dates rows",
            0 if e is None else len(e),
            "reported non-null",
            0 if e is None else int(e["Reported EPS"].notna().sum()),
            "range",
            None
            if e is None or e.empty
            else (str(e.index.min().date()), str(e.index.max().date())),
            flush=True,
        )
    except Exception as ex:
        print(s, "ERR", repr(ex)[:80], flush=True)
