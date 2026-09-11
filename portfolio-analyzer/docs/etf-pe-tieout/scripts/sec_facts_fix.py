# ruff: noqa  -- archived working script, kept as run on 2026-09-11
"""Replace stale/empty companyconcept EPS with companyfacts EPS for tickers whose data ends too early."""

import json
import os
import sys
import time
import urllib.request

S = os.environ.get("ETF_PE_WORKDIR", "./work/")
UA = "Kazumasa Research kikeuchi1210@gmail.com"
TAGS = [
    ("us-gaap", "EarningsPerShareDiluted"),
    ("us-gaap", "EarningsPerShareBasicAndDiluted"),
    ("ifrs-full", "DilutedEarningsLossPerShare"),
    ("us-gaap", "IncomeLossFromContinuingOperationsPerDilutedShare"),
    ("us-gaap", "EarningsPerShareBasic"),
    ("ifrs-full", "BasicEarningsLossPerShare"),
]
for f in sys.argv[1:]:
    E = json.load(open(f))
    changed = 0
    for t, rec in E.items():
        pts = rec.get("points") or []
        ends = [p["end"] for p in pts if p.get("end")]
        if (
            rec.get("cik")
            and (not ends or max(ends) < "2025-06-30")
            and "companyfacts" not in (rec.get("tags") or [])
        ):
            c = rec["cik"]
            cf = S + f"facts/{t}.json"
            if not os.path.exists(cf):
                try:
                    req = urllib.request.Request(
                        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(c):010d}.json",
                        headers={"User-Agent": UA},
                    )
                    json.dump(json.load(urllib.request.urlopen(req, timeout=120)), open(cf, "w"))
                    time.sleep(0.4)
                except Exception as e:
                    print(t, "ERR", repr(e)[:80])
                    continue
            d = json.load(open(cf))
            new = []
            for ns, tag in TAGS:
                v = d.get("facts", {}).get(ns, {}).get(tag)
                if not v:
                    continue
                for unit, arr in v["units"].items():
                    for p in arr:
                        new.append(
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
                if len(new) >= 8:
                    break
            nends = [p["end"] for p in new if p.get("end")]
            print(
                t,
                "concept max end",
                max(ends) if ends else None,
                "-> facts n",
                len(new),
                "max end",
                max(nends) if nends else None,
            )
            if new:
                rec["points"] = new
                rec["tags"] = (rec.get("tags") or []) + ["companyfacts"]
                changed += 1
    json.dump(E, open(f, "w"))
    print(f.split("/")[-1], "updated", changed)
