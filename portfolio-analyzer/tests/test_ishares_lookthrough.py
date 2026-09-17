"""Offline tests for refreshing a Japanese iShares ETF's look-through from its holdings CSV."""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "ishares_lookthrough", PROJECT_ROOT / "scripts/ishares_lookthrough.py"
)
lt = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules[_spec.name] = lt  # dataclasses look their module up while the script loads
_spec.loader.exec_module(lt)

HEADER = "Ticker,Name,Sector,Asset Class,Market Value,Weight (%),Notional Value,Shares,Price,Location,Exchange,Currency,FX Rate,Market Currency\n"
CSV = (
    '﻿基準日,"2026年9月16日"\n \n'
    + HEADER
    + '"6857","ｱﾄﾞﾊﾞﾝﾃｽﾄ","電気機器","株式","400.00","40.00","400.00","1","1","日本","東証","JPY","1.00","JPY"\n'
    '"9983","ﾌｧｰｽﾄﾘﾃｲﾘﾝｸﾞ","小売業","株式","300.00","30.00","300.00","1","1","日本","東証","JPY","1.00","JPY"\n'
    '"8306","三菱UFJﾌｨﾅﾝｼｬﾙG","銀行業","株式","200.00","20.00","200.00","1","1","日本","東証","JPY","1.00","JPY"\n'
    '"9999","謎の会社","新しい業種","株式","60.00","6.00","60.00","1","1","日本","東証","JPY","1.00","JPY"\n'
    '"7532","ﾊﾟﾝ･ﾊﾟｼﾌｨｯｸ","小売業","株式","0.40","0.00","0.40","1","1","日本","東証","JPY","1.00","JPY"\n'
    '"JPY","円","その他","キャッシュ","39.60","3.96","39.60","1","1","日本","-","JPY","1.00","JPY"\n'
    '"NKZ6","NIKKEI 225 (OSE) DEC 26","その他","Futures","0.00","0.00","5,681,760.00","1","1","-","OSE","JPY","1.00","JPY"\n'
    "\xa0\n"
)


def test_parse_holdings_reads_the_date_and_every_row() -> None:
    as_of, rows = lt.parse_holdings(CSV)
    assert as_of == "2026-09-16"
    assert [r.ticker for r in rows] == ["6857", "9983", "8306", "9999", "7532", "JPY", "NKZ6"]
    assert rows[0].market_value == 400.0 and rows[0].sector == "電気機器"


def test_weights_come_from_market_value_so_rows_printed_as_zero_still_count() -> None:
    _, rows = lt.parse_holdings(CSV)
    look = lt.lookthrough(rows, top=2)
    # 1,000 of market value in all: futures carry none
    assert look["sector"] == {
        "情報技術": 0.4,
        "一般消費財": 0.3004,
        "金融": 0.2,
        "その他・未分類株式": 0.06,
    }
    assert look["asset"] == {"現金等": 0.0396}


def test_issuers_are_the_top_names_plus_every_issuer_the_reference_tracks() -> None:
    _, rows = lt.parse_holdings(CSV)
    look = lt.lookthrough(rows, top=2)
    assert look["issuers"] == [
        ("Advantest", 0.4),
        ("Fast Retailing", 0.3),
        ("Mitsubishi UFJ Financial Group", 0.2),
        ("Pan Pacific International Holdings", 0.0004),
    ]
    assert "謎の会社" not in [name for name, _ in look["issuers"]]


def test_apply_replaces_the_look_through_and_keeps_issuer_tags_and_other_loadings() -> None:
    instrument = {
        "symbol": "1329",
        "as_of": "2026-07-31",
        "note": "old",
        "exposures": [
            {"group": "sector", "category": "情報技術", "weight": 0.5},
            {"group": "sector", "category": "その他・未分類株式", "weight": 0.5, "mapped": False},
            {
                "group": "issuer",
                "category": "Advantest",
                "weight": 0.12,
                "chain_role": "半導体製造・検査装置",
                "country": "日本",
            },
            {"group": "issuer", "category": "Fanuc", "weight": 0.02, "country": "日本"},
        ],
        "factor_loadings": {"株式全体": 1.1, "情報技術": 0.5, "IT装置": 0.12},
        "country_default": "日本",
    }
    reference = {
        "instruments": [instrument],
        "sources": [
            {"id": "ishares_1329_holdings", "label": "iShares 1329 保有銘柄CSV（2026-09-10）"}
        ],
    }
    before = copy.deepcopy(reference)
    _, rows = lt.parse_holdings(CSV)
    out = lt.apply(reference, "1329", "2026-09-16", lt.lookthrough(rows, top=2))
    assert reference == before

    (inst,) = out["instruments"]
    assert inst["as_of"] == "2026-09-16"
    sectors = {e["category"]: e for e in inst["exposures"] if e["group"] == "sector"}
    assert sectors["情報技術"]["weight"] == 0.4
    assert sectors["その他・未分類株式"]["mapped"] is False
    issuers = {e["category"]: e for e in inst["exposures"] if e["group"] == "issuer"}
    assert issuers["Advantest"] == {
        "group": "issuer",
        "category": "Advantest",
        "weight": 0.4,
        "chain_role": "半導体製造・検査装置",
        "country": "日本",
    }
    assert issuers["Fast Retailing"]["country"] == "日本"
    assert "Fanuc" not in issuers  # no longer in the holdings
    assets = [e for e in inst["exposures"] if e["group"] == "asset"]
    assert assets == [{"group": "asset", "category": "現金等", "weight": 0.0396}]
    assert inst["factor_loadings"] == {"株式全体": 1.1, "情報技術": 0.4, "IT装置": 0.4}
    assert out["sources"][0]["label"] == "iShares 1329 保有銘柄CSV（2026-09-16）"


def test_apply_refuses_an_instrument_the_reference_does_not_have() -> None:
    _, rows = lt.parse_holdings(CSV)
    with pytest.raises(KeyError):
        lt.apply({"instruments": [], "sources": []}, "1475", "2026-09-16", lt.lookthrough(rows))


def test_a_newly_listed_issuer_takes_its_tags_from_the_other_fund() -> None:
    reference = {
        "instruments": [
            {"symbol": "1329", "exposures": [], "country_default": "日本"},
            {
                "symbol": "1475",
                "exposures": [
                    {
                        "group": "issuer",
                        "category": "Mitsubishi UFJ Financial Group",
                        "weight": 0.04,
                        "theme": "金利上昇の受益",
                        "country": "日本",
                    }
                ],
            },
        ],
        "sources": [],
    }
    _, rows = lt.parse_holdings(CSV)
    out = lt.apply(reference, "1329", "2026-09-16", lt.lookthrough(rows, top=2))
    mufg = next(
        e
        for e in out["instruments"][0]["exposures"]
        if e["category"] == "Mitsubishi UFJ Financial Group"
    )
    assert mufg == {
        "group": "issuer",
        "category": "Mitsubishi UFJ Financial Group",
        "weight": 0.2,
        "theme": "金利上昇の受益",
        "country": "日本",
    }
