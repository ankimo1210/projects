# ruff: noqa  -- archived working script, kept as run on 2026-09-11
"""SEC XBRL diluted EPS points (with filed dates) for a list of tickers."""

import json
import os
import sys
import time
import urllib.request

S = os.environ.get("ETF_PE_WORKDIR", "./work/")
UA = "Kazumasa Research kikeuchi1210@gmail.com"
tickers = json.load(open(sys.argv[1]))
out_f = sys.argv[2]
ct = json.load(open(S + "tickers.json"))
cik = {v["ticker"]: v["cik_str"] for v in ct.values()}
manual_cik = json.load(open(S + "manual_cik.json")) if os.path.exists(S + "manual_cik.json") else {}
out = json.load(open(out_f)) if os.path.exists(out_f) else {}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return json.load(urllib.request.urlopen(req, timeout=60))


for t in tickers:
    if t in out:
        continue
    c = cik.get(t) or manual_cik.get(t)
    if not c:
        out[t] = {"cik": None, "points": []}
        continue
    pts = []
    tags_used = []
    for ns, tag in (
        ("us-gaap", "EarningsPerShareDiluted"),
        ("us-gaap", "EarningsPerShareBasicAndDiluted"),
        ("ifrs-full", "DilutedEarningsLossPerShare"),
        ("us-gaap", "EarningsPerShareBasic"),
        ("ifrs-full", "BasicEarningsLossPerShare"),
    ):
        try:
            d = get(
                f"https://data.sec.gov/api/xbrl/companyconcept/CIK{int(c):010d}/{ns}/{tag}.json"
            )
        except Exception:
            time.sleep(0.3)
            continue
        for unit, arr in d.get("units", {}).items():
            for p in arr:
                pts.append(
                    dict(
                        tag=tag,
                        unit=unit,
                        start=p.get("start"),
                        end=p.get("end"),
                        val=p.get("val"),
                        fy=p.get("fy"),
                        fp=p.get("fp"),
                        form=p.get("form"),
                        filed=p.get("filed"),
                        frame=p.get("frame"),
                    )
                )
        tags_used.append(tag)
        time.sleep(0.3)
        if tag == "EarningsPerShareDiluted" and len(pts) >= 8:
            break
    out[t] = {"cik": c, "points": pts, "tags": tags_used}
    json.dump(out, open(out_f, "w"))
print(
    "SEC-EPS-DONE",
    len(out),
    "no cik",
    [t for t, v in out.items() if not v["cik"]],
    "no points",
    [t for t, v in out.items() if v["cik"] and not v["points"]],
)
