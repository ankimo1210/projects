#!/usr/bin/env python3
"""Refresh a Japanese iShares ETF's look-through from the fund's holdings CSV.

The reference used to carry 1329 / 1475 from the monthly fact sheet, which lists
only the largest industries (15-26% of each fund stayed unclassified) and goes
stale by a month. The holdings CSV lists every name with its TSE 33 industry and
market value, so this rebuilds the instrument's rows from it:

- sector: every equity's market value, TSE 33 industry mapped to the broad
  sectors the reference uses (``TSE33_TO_SECTOR``), over the fund's total market
  value; cash rows become the ``現金等`` asset row, futures carry no value
- issuer: the ``--top`` largest names plus every issuer the reference already
  tracks (so a name held directly or through the other fund adds up), keeping
  each issuer's tags (theme, chain role, business mix, country)
- loadings: ``情報技術`` is the mapped IT sector weight and ``IT装置`` the weight
  of issuers tagged as chip equipment, as they were derived before

Weights come from market value, not the CSV's two-decimal weight column, where
a thousand small names print as 0.00. Network (unless ``--csv``), run by hand;
``--write`` saves a dated backup next to the reference first.

    uv run --package portfolio-analyzer python \\
      portfolio-analyzer/scripts/ishares_lookthrough.py 1329 1475 --write
"""

from __future__ import annotations

import argparse
import copy
import csv
import io
import json
import re
import shutil
import unicodedata
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UNMAPPED = "その他・未分類株式"
CHIP_EQUIPMENT = "半導体製造・検査装置"
ROUND = 4

# TSE 33 industries -> the broad sectors of the reference. 電気機器 goes to IT as a whole,
# as it always has here (it also holds Hitachi, Sony, Fanuc); 精密機器 is mostly medical
# devices by weight (Terumo, Olympus against HOYA).
TSE33_TO_SECTOR = {
    "電気機器": "情報技術",
    "情報・通信業": "コミュニケーション",
    "小売業": "一般消費財",
    "輸送用機器": "一般消費財",
    "ゴム製品": "一般消費財",
    "繊維製品": "一般消費財",
    "その他製品": "一般消費財",
    "サービス業": "資本財・サービス",
    "機械": "資本財・サービス",
    "卸売業": "資本財・サービス",
    "建設業": "資本財・サービス",
    "金属製品": "資本財・サービス",
    "陸運業": "資本財・サービス",
    "海運業": "資本財・サービス",
    "空運業": "資本財・サービス",
    "倉庫・運輸関連": "資本財・サービス",
    "化学": "素材",
    "非鉄金属": "素材",
    "鉄鋼": "素材",
    "ガラス・土石製品": "素材",
    "パルプ・紙": "素材",
    "医薬品": "ヘルスケア",
    "精密機器": "ヘルスケア",
    "食料品": "生活必需品",
    "水産・農林業": "生活必需品",
    "銀行業": "金融",
    "保険業": "金融",
    "証券、商品先物取引業": "金融",
    "その他金融業": "金融",
    "不動産業": "不動産",
    "電気・ガス業": "公益事業",
    "石油・石炭製品": "エネルギー",
    "鉱業": "エネルギー",
}

# Issuers the reference tracks, by TSE code, under the names it already uses.
TRACKED_ISSUERS = {
    "6857": "Advantest",
    "9983": "Fast Retailing",
    "8035": "Tokyo Electron",
    "9984": "SoftBank Group",
    "6762": "TDK",
    "6098": "Recruit Holdings",
    "6954": "Fanuc",
    "9433": "KDDI",
    "4062": "Ibiden",
    "285A": "Kioxia Holdings",
    "8306": "Mitsubishi UFJ Financial Group",
    "7203": "Toyota Motor",
    "8316": "Sumitomo Mitsui Financial Group",
    "6501": "Hitachi",
    "6758": "Sony Group",
    "8411": "Mizuho Financial Group",
    "8058": "Mitsubishi Corporation",
    "7532": "Pan Pacific International Holdings",
}
METHOD_NOTE = (
    "iShares 保有銘柄CSV（全銘柄の時価）から東証33業種を広義セクターへ集約し、発行体は上位10銘柄と"
    "他の商品で追っている銘柄（scripts/ishares_lookthrough.py）。"
)
OLD_METHOD = ("東証33業種を広義セクターへ集約。", "公式値の丸め誤差は計算時に正規化。")


@dataclass(frozen=True)
class Row:
    ticker: str
    name: str
    sector: str
    asset_class: str
    market_value: float
    location: str


def _number(text: str) -> float:
    return float(text.replace(",", "") or 0)


def parse_holdings(text: str) -> tuple[str, list[Row]]:
    """(as-of date, every row) from the holdings CSV as iShares Japan serves it."""
    lines = text.lstrip("﻿").splitlines()
    match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", lines[0])
    if match is None:
        raise ValueError(f"no date in the first line: {lines[0]!r}")
    as_of = f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    start = next(i for i, line in enumerate(lines) if line.startswith("Ticker,"))
    rows = [
        Row(
            ticker=r["Ticker"],
            name=r["Name"],
            sector=r["Sector"],
            asset_class=r["Asset Class"],
            market_value=_number(r["Market Value"]),
            location=r["Location"],
        )
        for r in csv.DictReader(io.StringIO("\n".join(lines[start:])))
        if r.get("Ticker") and r["Ticker"].strip()
    ]
    return as_of, rows


def lookthrough(rows: list[Row], top: int = 10) -> dict[str, Any]:
    """Sector and cash weights over the fund's market value, and the issuer rows."""
    total = sum(r.market_value for r in rows)
    sector: dict[str, float] = {}
    cash = 0.0
    equities = [r for r in rows if r.asset_class == "株式"]
    for r in rows:
        if r.asset_class == "株式":
            key = TSE33_TO_SECTOR.get(r.sector, UNMAPPED)
            sector[key] = sector.get(key, 0.0) + r.market_value
        else:
            cash += r.market_value
    ranked = sorted(equities, key=lambda r: -r.market_value)
    chosen = {r.ticker for r in ranked[:top]} | {
        r.ticker for r in equities if r.ticker in TRACKED_ISSUERS
    }
    issuers = [
        (
            TRACKED_ISSUERS.get(r.ticker) or unicodedata.normalize("NFKC", r.name),
            round(r.market_value / total, ROUND),
        )
        for r in ranked
        if r.ticker in chosen
    ]
    return {
        "sector": {
            k: round(v / total, ROUND) for k, v in sorted(sector.items(), key=lambda kv: -kv[1])
        },
        "asset": {"現金等": round(cash / total, ROUND)} if cash else {},
        "issuers": issuers,
        "countries": {
            TRACKED_ISSUERS.get(r.ticker) or unicodedata.normalize("NFKC", r.name): r.location
            for r in equities
            if r.ticker in chosen
        },
    }


def _issuer_tags(reference: dict[str, Any], symbol: str) -> dict[str, dict[str, Any]]:
    """Tags per issuer name: this instrument's own first, then any other instrument's."""
    tags: dict[str, dict[str, Any]] = {}
    ordered = sorted(reference["instruments"], key=lambda i: i["symbol"] != symbol)
    for inst in ordered:
        for e in inst.get("exposures", []):
            if e.get("group") == "issuer" and e["category"] not in tags:
                tags[e["category"]] = {
                    k: v for k, v in e.items() if k not in ("group", "category", "weight")
                }
    return tags


def apply(
    reference: dict[str, Any], symbol: str, as_of: str, look: dict[str, Any]
) -> dict[str, Any]:
    """A copy of the reference with ``symbol``'s look-through rebuilt from ``look``."""
    out = copy.deepcopy(reference)
    inst = next((i for i in out["instruments"] if i["symbol"] == symbol), None)
    if inst is None:
        raise KeyError(f"instrument {symbol} is not in the reference")
    tags = _issuer_tags(reference, symbol)
    exposures: list[dict[str, Any]] = []
    for category, weight in look["sector"].items():
        row: dict[str, Any] = {"group": "sector", "category": category, "weight": weight}
        if category == UNMAPPED:
            row["mapped"] = False
        exposures.append(row)
    exposures += [
        {"group": "asset", "category": category, "weight": weight}
        for category, weight in look["asset"].items()
    ]
    for name, weight in look["issuers"]:
        row = {"group": "issuer", "category": name, "weight": weight, **tags.get(name, {})}
        row.setdefault("country", look["countries"].get(name) or inst.get("country_default"))
        exposures.append(row)
    inst["exposures"] = exposures
    inst["as_of"] = as_of
    loadings = inst.get("factor_loadings")
    if loadings is not None:
        if "情報技術" in loadings:
            loadings["情報技術"] = look["sector"].get("情報技術", 0.0)
        if "IT装置" in loadings:
            loadings["IT装置"] = round(
                sum(
                    e["weight"]
                    for e in exposures
                    if e["group"] == "issuer" and e.get("chain_role") == CHIP_EQUIPMENT
                ),
                ROUND,
            )
    note = str(inst.get("note", ""))
    for sentence in OLD_METHOD:
        note = note.replace(sentence, "")
    inst["note"] = METHOD_NOTE + note.replace(METHOD_NOTE, "")
    for source in out.get("sources", []):
        if source.get("id") == f"ishares_{symbol}_holdings":
            source["label"] = re.sub(r"（\d{4}-\d{2}-\d{2}）", f"（{as_of}）", source["label"])
    return out


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8-sig")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("symbols", nargs="+", help="e.g. 1329 1475")
    parser.add_argument(
        "--reference", default=str(PROJECT_ROOT / "data/analysis_reference.private.json")
    )
    parser.add_argument("--csv", nargs="*", help="read these files instead, in symbol order")
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--write", action="store_true", help="save (after a dated backup)")
    args = parser.parse_args()

    path = Path(args.reference)
    reference = json.loads(path.read_text(encoding="utf-8"))
    updated = reference
    for n, symbol in enumerate(args.symbols):
        if args.csv:
            text = Path(args.csv[n]).read_text(encoding="utf-8-sig")
        else:
            source = next(
                s for s in reference["sources"] if s["id"] == f"ishares_{symbol}_holdings"
            )
            text = fetch(source["href"])
        as_of, rows = parse_holdings(text)
        look = lookthrough(rows, top=args.top)
        old = next(i for i in updated["instruments"] if i["symbol"] == symbol)
        before = {e["category"]: e["weight"] for e in old["exposures"]}
        updated = apply(updated, symbol, as_of, look)
        new = next(i for i in updated["instruments"] if i["symbol"] == symbol)
        print(f"{symbol}: {old['as_of']} -> {as_of}, {len(rows)} rows")
        for e in new["exposures"]:
            was = before.get(e["category"])
            print(
                f"  {e['group']:6s} {e['category']:34s} {e['weight']:.4f}"
                + ("" if was is None else f"  (was {float(was):.4f})")
            )
        print(f"  loadings {old.get('factor_loadings')} -> {new.get('factor_loadings')}")
    if args.write:
        backup = path.with_name(
            path.name.replace(".private.json", f".backup-{date.today().isoformat()}.private.json")
        )
        shutil.copyfile(path, backup)
        path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path} (backup {backup.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
