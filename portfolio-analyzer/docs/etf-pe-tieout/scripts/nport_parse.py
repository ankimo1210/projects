# ruff: noqa  -- archived working script, kept as run on 2026-09-11
"""Parse N-PORT primary_doc.xml -> list of equity holdings."""

import glob
import json
import sys
import xml.etree.ElementTree as ET


def parse(path):
    root = ET.parse(path).getroot()
    for el in root.iter():  # strip namespaces
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    hdr = root.find(".//genInfo")
    rep = hdr.findtext("repPdDate") if hdr is not None else None
    series = root.findtext(".//seriesName")
    out = []
    for inv in root.iter("invstOrSec"):
        if (inv.findtext("assetCat") or "") != "EC":
            continue
        ids = inv.find("identifiers")
        isin = None
        other = None
        if ids is not None:
            e = ids.find("isin")
            isin = e.get("value") if e is not None else None
            o = ids.find("other")
            other = (o.get("otherDesc"), o.get("value")) if o is not None else None
        out.append(
            dict(
                name=inv.findtext("name"),
                title=inv.findtext("title"),
                cusip=inv.findtext("cusip"),
                isin=isin,
                other=other,
                balance=float(inv.findtext("balance") or 0),
                valUSD=float(inv.findtext("valUSD") or 0),
                pctVal=float(inv.findtext("pctVal") or 0),
                cur=inv.findtext("curCd")
                or (
                    inv.find("currencyConditional").get("curCd")
                    if inv.find("currencyConditional") is not None
                    else None
                ),
                exch=(
                    inv.find("currencyConditional").get("exchangeRt")
                    if inv.find("currencyConditional") is not None
                    else None
                ),
                issuerCat=inv.findtext("issuerCat"),
            )
        )
    return dict(report_date=rep, series=series, holdings=out)


if __name__ == "__main__":
    d = sys.argv[1]
    res = {}
    for f in sorted(glob.glob(d + "/*.xml")):
        p = parse(f)
        res[p["report_date"] or f.split("/")[-1][:10]] = p
        print(
            p["report_date"],
            p["series"],
            len(p["holdings"]),
            "sum pct",
            round(sum(h["pctVal"] for h in p["holdings"]), 2),
        )
    json.dump(res, open(d + "/holdings.json", "w"))
