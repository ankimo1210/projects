"""AIラリー開始以降、4象限のどれが実際に上がったのかを測る。

象限は供給制約への感応度の地図であって株価の予測ではない。だからこそ
「市場はもう織り込んだのか」を別に測る必要がある。ここでは 2022-11-30 の
ChatGPT 公開を起点に、象限ごとの等ウェイト指数を作る。

読むときの前提（結果と一緒に必ず出すこと）:

* 象限は 2025-26 年のデータで付けた区分を 2022-11 に遡って当てている。
  当時これが分かっていたわけではない（リバランスもしていない）。
* ユニバースは現在の TOPIX 構成銘柄。期間中に上場廃止された銘柄が居ないので
  生存バイアスで上振れする。
* 起点に株価が無い銘柄（期間中の新規上場）は指数から外している。

    uv run python labor_ai_quadrant/tools/quadrant_performance.py
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

PKG = Path(__file__).resolve().parents[1]
DATA = PKG / "_data"
CACHE = DATA / "prices_monthly.json"

#: ChatGPT 公開 = 2022-11-30。その月末を 100 とする。
BASE = pd.Period("2022-11", freq="M")
#: 起点の1か月前から取る（起点の月末値が欠けている銘柄を見分けるため）。
CHART = ("https://query1.finance.yahoo.com/v8/finance/chart/{code}.T"
         "?period1=1664582400&period2=1893456000&interval=1mo")


def _one(code: str) -> tuple[str, dict[str, float] | None]:
    for attempt in range(3):
        try:
            req = urllib.request.Request(CHART.format(code=code), headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=25) as fh:
                payload = json.load(fh)
            result = payload["chart"]["result"][0]
            stamps = result["timestamp"]
            adjusted = result["indicators"].get("adjclose", [{}])[0].get("adjclose")
            if adjusted is None:
                adjusted = result["indicators"]["quote"][0]["close"]
            series = {
                pd.Timestamp(s, unit="s", tz="Asia/Tokyo").strftime("%Y-%m"): v
                for s, v in zip(stamps, adjusted, strict=False)
                if v is not None
            }
            return code, series or None
        except urllib.error.HTTPError as exc:
            if exc.code in (400, 404):
                return code, None
            time.sleep(1.5 * (attempt + 1))
        except Exception:
            time.sleep(1.0 * (attempt + 1))
    return code, None


def fetch_prices(codes: list[str]) -> pd.DataFrame:
    """Monthly adjusted closes, cached on disk so a rerun costs nothing."""
    cached: dict[str, dict[str, float]] = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    todo = [c for c in codes if c not in cached]
    if todo:
        print(f"fetching {len(todo)} tickers from Yahoo Finance ...", flush=True)
        with ThreadPoolExecutor(max_workers=6) as pool:
            for code, series in pool.map(_one, todo):
                if series:
                    cached[code] = series
        CACHE.write_text(json.dumps(cached))
    frame = pd.DataFrame({c: cached[c] for c in codes if c in cached}).sort_index()
    frame.index = pd.PeriodIndex(frame.index, freq="M")
    return frame


#: 月次調整後終値として成立しない変化率。これを超えたら配信側の壊れたデータと判断する。
MAX_MONTHLY_RATIO = 4.0


def sanitize(prices: pd.DataFrame) -> pd.DataFrame:
    """壊れた配信データを落とす。

    実測で 8303 SBI新生銀行 が負の調整後終値（-2.3億）と 5.4e10 のスパイクを返し、
    等ウェイト指数に月次で -40% の穴を空けた。1銘柄で 459銘柄の平均が壊れるので、
    黙って混ぜずに落として件数を出す。
    """
    ratio = prices / prices.shift(1)
    broken = prices.columns[
        (prices <= 0).any()
        | (ratio > MAX_MONTHLY_RATIO).any()
        | (ratio < 1.0 / MAX_MONTHLY_RATIO).any()
    ]
    if len(broken):
        print(f"dropped {len(broken)} tickers with unusable price series: {list(broken)}")
    return prices.drop(columns=broken)


def performance(scored: pd.DataFrame, prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Equal-weight index per quadrant, and per-stock total returns."""
    started = prices.loc[BASE].dropna()
    codes = [c for c in started.index if c in scored.index]
    relative = prices[codes].div(prices.loc[BASE, codes], axis=1) * 100.0
    quadrant = scored.loc[codes, "quadrant"]

    index = pd.DataFrame({name: relative[grp.index].mean(axis=1) for name, grp in quadrant.groupby(quadrant)})
    index["ユニバース全体"] = relative.mean(axis=1)
    index = index.dropna(how="all")
    index.index = index.index.astype(str)

    returns = (relative.loc[prices.index.max()] - 100.0).rename("total_return_pct").to_frame()
    returns = returns.join(scored[["name", "sector33", "quadrant", "escape_potential", "op_margin_uplift_pp"]])
    return index, returns


def main() -> None:
    scored = pd.read_csv(DATA / "topix_scored.csv", dtype={"code": str}).set_index("code")
    prices = sanitize(fetch_prices(scored.index.tolist()))
    index, returns = performance(scored, prices)

    index.to_csv(DATA / "quadrant_index.csv")
    returns.to_csv(DATA / "quadrant_returns.csv")

    asof = index.index[-1]
    print(f"universe {len(scored)}  priced {prices.shape[1]}  in the index {len(returns)}")
    print(f"\n=== 等ウェイト指数 (2022-11 = 100, {asof} 時点) ===")
    summary = pd.DataFrame(
        {
            "n": returns.groupby("quadrant").size(),
            "等ウェイト%": index.iloc[-1] - 100,
            "中央値%": returns.groupby("quadrant")["total_return_pct"].median(),
        }
    )
    summary.loc["ユニバース全体", "n"] = len(returns)
    summary.loc["ユニバース全体", "中央値%"] = returns["total_return_pct"].median()
    print(summary.round(1).to_string())

    by_sector = returns.groupby("sector33").agg(
        n=("total_return_pct", "size"),
        median=("total_return_pct", "median"),
        mean=("total_return_pct", "mean"),
    )
    print(f"\n=== 業種別 中央値リターン ({asof} 時点) ===")
    print(by_sector.sort_values("median", ascending=False).round(1).to_string())


if __name__ == "__main__":
    main()
