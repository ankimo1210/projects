# ruff: noqa  -- archived working script, kept as run on 2026-09-11
import json
import os
import sys
import time

import yfinance as yf

S = os.environ.get("ETF_PE_WORKDIR", "./work/")
tick = json.load(open(sys.argv[1]))
cf = S + sys.argv[2]
out = json.load(open(cf)) if os.path.exists(cf) else {}
for t in tick:
    if t in out:
        continue
    try:
        sp = yf.Ticker(t).splits
        out[t] = {str(k.date()): float(v) for k, v in sp.items() if k.year >= 2019}
    except Exception as e:
        out[t] = {"_err": repr(e)[:60]}
    time.sleep(0.3)
json.dump(out, open(cf, "w"))
print("SPLITS-DONE", len(out), {t: v for t, v in out.items() if v and "_err" not in v})
