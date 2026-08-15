#!/usr/bin/env python3
"""Estimate factor series, betas, covariance, and historical episode moves.

Network tool, run by hand. The dashboard build stays offline: this script writes
a dated snapshot to ``data/factor_estimates.json`` and nothing else reads the
network. Re-run it when the calibration window should move.

    uv run --package portfolio-analyzer python \
      portfolio-analyzer/scripts/estimate_factors.py
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Proxy series. The factor model names on the left are the ones used in
# data/analysis_reference*.json; the right side is how each is measured.
PRICE_PROXIES = {
    "1306.T": "TOPIX ETF — Japanese market leg",
    "SPY": "S&P 500 ETF — US market leg",
    "SMH": "semiconductor ETF — information-technology excess",
    "XLE": "energy ETF — energy excess",
    "1343.T": "J-REIT index ETF — real-estate excess",
    "JPY=X": "USD/JPY — a positive return means a weaker yen",
}
YIELD_PROXIES = {"^TNX": "US 10-year Treasury yield (percent)"}
MOF_JGB_CSV = "https://www.mof.go.jp/jgbs/reference/interest_rate/data/jgbcm_all.csv"
JGB_TENOR = "10年"

# Instruments whose market beta the reference data carries, and the market leg
# each one is measured against.
BETA_TARGETS = {
    "6857.T": "1306.T",
    "7532.T": "1306.T",
    "8976.T": "1306.T",
    "1329.T": "1306.T",
    "1475.T": "1306.T",
    "SMH": "SPY",
    "QQQ": "SPY",
    "XLE": "SPY",
}

# Windows replayed to calibrate the hand-set shock sizes. Each pair is the last
# quiet session before the move and the trough session of the move.
EPISODES = [
    {
        "id": "yen_carry_unwind_2024",
        "label": "2024-08 円キャリー巻き戻し",
        "start": "2024-07-31",
        "end": "2024-08-05",
        "note": "日銀利上げと米雇用統計を挟んだ数営業日の急落",
    },
    {
        "id": "inflation_rate_shock_2022",
        "label": "2022 インフレ・金利ショック",
        "start": "2022-01-03",
        "end": "2022-10-14",
        "note": "株債同時安。株債相関が正転した局面",
    },
    {
        "id": "covid_crash_2020",
        "label": "2020-03 コロナ・ショック",
        "start": "2020-02-19",
        "end": "2020-03-23",
        "note": "流動性危機を含む広範なリスクオフ",
    },
    {
        "id": "risk_off_2018q4",
        "label": "2018Q4 リスクオフ",
        "start": "2018-10-01",
        "end": "2018-12-25",
        "note": "利上げ終盤の成長株調整",
    },
]

ERA_OFFSETS = {"S": 1925, "H": 1988, "R": 2018, "M": 1867, "T": 1911}


def parse_wareki(value: str) -> date | None:
    """Parse a MoF Japanese-era date such as ``R8.8.3`` into a date."""
    text = str(value).strip()
    if not text or text[0] not in ERA_OFFSETS:
        return None
    try:
        year_text, month_text, day_text = text[1:].split(".")
        year = ERA_OFFSETS[text[0]] + int(year_text)
        return date(year, int(month_text), int(day_text))
    except (ValueError, KeyError):
        return None


def parse_jgb_csv(text: str, tenor: str = JGB_TENOR):
    """Return a dated Series of JGB par yields in percent for one tenor."""
    import pandas as pd

    frame = pd.read_csv(io.StringIO(text), skiprows=1, na_values=["-"])
    date_column = frame.columns[0]
    if tenor not in frame.columns:
        raise KeyError(f"tenor {tenor!r} not in {list(frame.columns)[1:]}")
    parsed = frame[date_column].map(parse_wareki)
    series = pd.Series(
        pd.to_numeric(frame[tenor], errors="coerce").values,
        index=pd.to_datetime(pd.Series(parsed)),
        name="jgb_10y",
    )
    return series[series.index.notna()].dropna().sort_index()


def build_factor_frame(prices, yields):
    """Map proxy levels to the model's factor returns.

    Equity legs stay in local currency so that the currency factor is not
    double counted against instruments that already carry a 外貨対円 loading.
    Sector and real-estate factors are excess returns over their market leg,
    matching how the reference data treats them as additional shocks.
    """
    import pandas as pd

    returns = prices.pct_change()
    frame = pd.DataFrame(index=prices.index)
    frame["株式全体"] = 0.5 * returns["1306.T"] + 0.5 * returns["SPY"]
    frame["情報技術"] = returns["SMH"] - returns["SPY"]
    frame["エネルギー"] = returns["XLE"] - returns["SPY"]
    frame["不動産"] = returns["1343.T"] - returns["1306.T"]
    frame["外貨対円"] = returns["JPY=X"]
    frame["日本金利"] = yields["jgb_10y"].diff() / 100
    frame["海外金利"] = yields["^TNX"].diff() / 100
    return frame


def download_prices(symbols: list[str], start: str, end: str):
    import warnings

    import pandas as pd
    import yfinance as yf

    frames = {}
    for symbol in symbols:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            raw = yf.download(
                symbol, start=start, end=end, auto_adjust=False, progress=False
            )
        if raw is None or raw.empty:
            raise RuntimeError(f"empty price response for {symbol}")
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        column = "Adj Close" if "Adj Close" in raw.columns else "Close"
        frames[symbol] = pd.to_numeric(raw[column], errors="coerce")
    out = pd.DataFrame(frames)
    out.index = pd.to_datetime(out.index).tz_localize(None)
    return out.sort_index()


def download_jgb():
    import requests

    response = requests.get(MOF_JGB_CSV, timeout=120)
    response.raise_for_status()
    return parse_jgb_csv(response.content.decode("shift_jis", errors="replace"))


def weekly(frame, how: str = "last"):
    resampled = frame.resample("W-FRI")
    return resampled.last() if how == "last" else resampled.sum()


def find_price_spikes(series, threshold: float = 0.4, window: int = 11) -> list:
    """Return index labels whose price is far from its local median.

    A bad print — including a run of them, as happens when a feed drops a
    decimal place — sits far from the surrounding level. A genuine crash moves
    the whole neighbourhood, so the local median follows it and nothing is
    flagged. Distances are measured in log space so both directions are
    treated symmetrically.
    """
    import numpy as np

    clean = series.dropna()
    clean = clean[clean > 0]
    if len(clean) < window:
        return []
    local = clean.rolling(window, center=True, min_periods=window // 2 + 1).median()
    deviation = np.log(clean / local).abs()
    return list(deviation[deviation > threshold].index)


def screen_prices(prices, threshold: float = 0.4, *, skip: tuple[str, ...] = ()) -> tuple[Any, dict[str, Any]]:
    """Blank out spike prints and report every value that was removed.

    ``skip`` exempts series whose level can legitimately halve or double — a
    yield at 0.5% is a real observation, not a dropped decimal place.
    """
    screened = prices.copy()
    report: dict[str, Any] = {}
    for symbol in prices.columns:
        if symbol in skip:
            continue
        spikes = find_price_spikes(prices[symbol], threshold)
        if not spikes:
            continue
        report[symbol] = [
            {
                "date": stamp.date().isoformat(),
                "price": round(float(prices[symbol].loc[stamp]), 4),
                "reason": "前後11営業日の中央値から大きく外れる価格（データ欠陥と判断）",
            }
            for stamp in spikes
        ]
        screened.loc[spikes, symbol] = float("nan")
    return screened, report


def robust_outlier_mask(returns, z_max: float = 8.0):
    """Flag returns that are absurd relative to the series' own dispersion.

    Screening prices catches bad prints, but not the adjustment discontinuity
    they leave behind in an adjusted-close series. A median-absolute-deviation
    score is not dragged around by the very observation being judged, and
    z > 8 is far outside anything a market move produces.
    """
    median = returns.median()
    scale = 1.4826 * (returns - median).abs().median()
    if not scale or scale != scale:
        return returns != returns  # all False
    return ((returns - median).abs() / scale) > z_max


def estimate_betas(weekly_prices, targets: dict[str, str]) -> dict[str, Any]:
    returns = weekly_prices.pct_change().dropna(how="all")
    out: dict[str, Any] = {}
    for symbol, market in targets.items():
        pair = returns[[symbol, market]].dropna()
        dropped = robust_outlier_mask(pair[symbol]) | robust_outlier_mask(pair[market])
        dropped_dates = [stamp.date().isoformat() for stamp in pair.index[dropped]]
        pair = pair[~dropped]
        if len(pair) < 52:
            out[symbol] = {
                "market_proxy": market,
                "observations": len(pair),
                "beta": None,
                "note": "観測数が52週未満のため推定しない",
            }
            continue
        market_returns = pair[market]
        beta = pair[symbol].cov(market_returns) / market_returns.var()
        out[symbol] = {
            "market_proxy": market,
            "observations": len(pair),
            "beta": round(float(beta), 4),
            "correlation": round(float(pair[symbol].corr(market_returns)), 4),
            "dropped_outliers": dropped_dates,
        }
    return out


def estimate_covariance(weekly_factors) -> dict[str, Any]:
    clean = weekly_factors.dropna()
    dropped = None
    for factor in clean.columns:
        flags = robust_outlier_mask(clean[factor])
        dropped = flags if dropped is None else (dropped | flags)
    dropped_dates = [stamp.date().isoformat() for stamp in clean.index[dropped]]
    clean = clean[~dropped]
    covariance = clean.cov()
    correlation = clean.corr()
    factors = list(covariance.columns)
    return {
        "factors": factors,
        "observations": len(clean),
        "dropped_outliers": dropped_dates,
        "frequency": "weekly",
        "covariance": [[round(float(covariance.loc[a, b]), 12) for b in factors] for a in factors],
        "correlation": [[round(float(correlation.loc[a, b]), 4) for b in factors] for a in factors],
        "annualized_volatility": {
            factor: round(float(clean[factor].std() * (52**0.5)), 6) for factor in factors
        },
    }


def measure_episodes(daily_prices, daily_yields) -> list[dict[str, Any]]:
    import pandas as pd

    out: list[dict[str, Any]] = []
    for episode in EPISODES:
        start = pd.Timestamp(episode["start"])
        end = pd.Timestamp(episode["end"])
        price_window = daily_prices.loc[:end].ffill()
        yield_window = daily_yields.loc[:end].ffill()
        if price_window.empty or price_window.index[-1] < start:
            continue
        first_prices = price_window.loc[:start].iloc[-1]
        last_prices = price_window.iloc[-1]
        first_yields = yield_window.loc[:start].iloc[-1]
        last_yields = yield_window.iloc[-1]
        moves = (last_prices / first_prices - 1).to_dict()
        shocks = {
            "株式全体": 0.5 * moves["1306.T"] + 0.5 * moves["SPY"],
            "情報技術": moves["SMH"] - moves["SPY"],
            "エネルギー": moves["XLE"] - moves["SPY"],
            "不動産": moves["1343.T"] - moves["1306.T"],
            "外貨対円": moves["JPY=X"],
            "日本金利": float(last_yields["jgb_10y"] - first_yields["jgb_10y"]) / 100,
            "海外金利": float(last_yields["^TNX"] - first_yields["^TNX"]) / 100,
        }
        out.append(
            {
                "id": episode["id"],
                "label": episode["label"],
                "start": episode["start"],
                "end": episode["end"],
                "note": episode["note"],
                "shocks": {
                    factor: round(float(value), 6)
                    for factor, value in shocks.items()
                    if value == value  # drop NaN when a proxy has no history yet
                },
                "raw_moves": {
                    symbol: round(float(value), 6) for symbol, value in moves.items() if value == value
                },
            }
        )
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2018-01-01", help="history start for episode replay")
    parser.add_argument("--end", default=date.today().isoformat(), help="history end")
    parser.add_argument(
        "--beta-window-years", type=int, default=3, help="trailing years used for beta and covariance"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data/factor_estimates.json",
        help="where to write the estimate snapshot",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    import pandas as pd

    symbols = [*PRICE_PROXIES, *BETA_TARGETS, *YIELD_PROXIES]
    symbols = list(dict.fromkeys(symbols))
    print(f"downloading {len(symbols)} series from yfinance ...", file=sys.stderr)
    levels = download_prices(symbols, args.start, args.end)
    print("downloading JGB par yields from MoF ...", file=sys.stderr)
    jgb = download_jgb()

    levels, quality_report = screen_prices(levels, skip=tuple(YIELD_PROXIES))
    for symbol, rows in quality_report.items():
        for row in rows:
            print(f"  data quality: dropped {symbol} {row['date']} ({row['price']})", file=sys.stderr)

    daily_prices = levels[list(PRICE_PROXIES)]
    daily_yields = pd.DataFrame({"^TNX": levels["^TNX"]})
    daily_yields["jgb_10y"] = jgb.reindex(daily_yields.index, method="ffill")
    daily_yields = daily_yields.dropna()

    window_start = pd.Timestamp(args.end) - pd.DateOffset(years=args.beta_window_years)
    weekly_prices = weekly(levels.loc[window_start:])
    weekly_factors = weekly(daily_prices.loc[window_start:]).pipe(
        lambda frame: build_factor_frame(frame, weekly(daily_yields.loc[window_start:]))
    )

    payload = {
        "manifest": {
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "history_start": args.start,
            "history_end": args.end,
            "estimation_window_start": window_start.date().isoformat(),
            "estimation_window_years": args.beta_window_years,
            "price_source": "yfinance (adjusted close)",
            "jgb_source": MOF_JGB_CSV,
            "jgb_tenor": JGB_TENOR,
            "price_proxies": PRICE_PROXIES,
            "yield_proxies": YIELD_PROXIES,
            "factor_construction": {
                "株式全体": "0.5 * r(1306.T) + 0.5 * r(SPY)、現地通貨ベース",
                "情報技術": "r(SMH) - r(SPY)、市場に対する超過",
                "エネルギー": "r(XLE) - r(SPY)、市場に対する超過",
                "不動産": "r(1343.T) - r(1306.T)、日本株に対する超過",
                "外貨対円": "r(USD/JPY)、正なら円安",
                "日本金利": "JGB10年 par yield の差分（小数）",
                "海外金利": "米10年利回り（^TNX）の差分（小数）",
            },
            "caveats": [
                "yfinanceの調整済み終値を使用。配当・分割の扱いは提供元依存",
                "エピソードは開始日直前の終値から終了日終値までの累積変化",
                "共分散は週次（W-FRI）で、相関の時間変化は捉えない",
            ],
        },
        "data_quality": {
            "screen": (
                "前後11営業日の中央値から対数で0.4超離れた価格を欠陥プリントとして除外。"
                "利回り系列（^TNX・JGB）は水準が正当に倍半分動くため検査対象外"
            ),
            "removed": quality_report,
        },
        "betas": estimate_betas(weekly_prices, BETA_TARGETS),
        "factor_risk": estimate_covariance(weekly_factors),
        "episodes": measure_episodes(daily_prices, daily_yields),
        "latest_levels": {
            "usdjpy": round(float(levels["JPY=X"].dropna().iloc[-1]), 4),
            "jgb_10y_percent": round(float(jgb.iloc[-1]), 4),
            "ust_10y_percent": round(float(levels["^TNX"].dropna().iloc[-1]), 4),
            "as_of": levels.index[-1].date().isoformat(),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"factor estimates: {args.output}")
    print(f"factor observations: {payload['factor_risk']['observations']} weeks")
    for episode in payload["episodes"]:
        print(f"  {episode['label']}: {episode['shocks']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
