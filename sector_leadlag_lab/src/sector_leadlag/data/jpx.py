"""The TSE listed-issues file (JPX ``data_j.xlsx``): 17-sector and size classes (design §4)."""

from __future__ import annotations

import io
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd

URL = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xlsx"
COLUMNS = (
    "日付",
    "コード",
    "銘柄名",
    "市場・商品区分",
    "33業種コード",
    "33業種区分",
    "17業種コード",
    "17業種区分",
    "規模コード",
    "規模区分",
)
# JPX 17-sector code k (1-17) is SECTORS[k - 1]; its NEXT FUNDS ETF is 1616 + k.
SECTORS = (
    "食品",
    "エネルギー資源",
    "建設・資材",
    "素材・化学",
    "医薬品",
    "自動車・輸送機",
    "鉄鋼・非鉄",
    "機械",
    "電機・精密",
    "情報通信・サービスその他",
    "電力・ガス",
    "運輸・物流",
    "商社・卸売",
    "小売",
    "銀行",
    "金融（除く銀行）",
    "不動産",
)
ETF_TICKERS = tuple(f"{1616 + k}.T" for k in range(1, 18))
TOPIX500 = ("TOPIX Core30", "TOPIX Large70", "TOPIX Mid400")


def _norm(text: str) -> str:
    return unicodedata.normalize("NFKC", str(text)).strip()


@dataclass(frozen=True)
class Listing:
    as_of: date
    stocks: pd.DataFrame  # index: code (str); columns: name, sector (1-17), size


def parse_listing(content: bytes) -> Listing:
    frame = pd.read_excel(io.BytesIO(content), dtype=str)
    missing = [column for column in COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"the listed-issues file lacks columns {missing}")
    as_of = datetime.strptime(frame["日付"].dropna().iloc[0].strip(), "%Y%m%d").date()
    rows = frame[frame["17業種コード"].fillna("").str.strip().str.fullmatch(r"\d{1,2}")]
    sector = rows["17業種コード"].str.strip().astype(int).to_numpy()
    expected = {k + 1: _norm(name) for k, name in enumerate(SECTORS)}
    for k, name in zip(sector, rows["17業種区分"], strict=True):
        if expected.get(int(k)) != _norm(name):
            raise ValueError(f"17-sector code {k} is {name!r}, expected {expected.get(int(k))!r}")
    stocks = pd.DataFrame(
        {
            "name": rows["銘柄名"].str.strip().to_numpy(),
            "sector": sector,
            "size": rows["規模区分"].fillna("").str.strip().to_numpy(),
        },
        index=pd.Index(rows["コード"].str.strip().to_numpy(), name="code"),
    )
    return Listing(as_of, stocks)


def topix500(listing: Listing) -> pd.DataFrame:
    return listing.stocks[listing.stocks["size"].isin(TOPIX500)]


def stock_ticker(code: str) -> str:
    return f"{code}.T"
