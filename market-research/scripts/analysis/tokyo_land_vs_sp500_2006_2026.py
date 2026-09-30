"""Compare Tokyo 23-ward official land values with the S&P 500, 2006–2026.

Land observations are January 1; stock and FX observations are the preceding
calendar year's final available trading day. All series are nominal price
indices (2006 = 100), not investment total returns.
"""

from __future__ import annotations

import csv
import io
import math
from datetime import UTC, date, datetime
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import requests
from matplotlib.ticker import FixedLocator, FuncFormatter

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs" / "data" / "validation"
DATA_ROOT = ROOT.parent / "_data/market-research"
STEM = "tokyo_land_vs_sp500_2006_2026"
YEARS = range(2006, 2027)
CATEGORIES = {"住宅地": "residential", "商業地": "commercial"}
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "Mozilla/5.0 (research; annual price-index comparison)"


def land_changes() -> dict[int, dict[str, dict]]:
    result: dict[int, dict[str, dict]] = {}
    for year in YEARS:
        path = DATA_ROOT / "market" / "processed" / f"land_prices_y{year}_pref13_pc0.parquet"
        if not path.is_file():
            raise FileNotFoundError(path)
        rows = (
            duckdb.connect()
            .execute(
                """
            SELECT use_category_name,
                   COUNT(*) AS sites,
                   COUNT(yoy_change_pct) AS continuing_sites,
                   AVG(yoy_change_pct) AS mean_yoy,
                   COUNT(*) - COUNT(DISTINCT city_code || ':' || standard_land_number)
                       AS duplicate_keys
            FROM read_parquet(?)
            WHERE survey_source = '地価公示'
              AND city_code BETWEEN '13101' AND '13123'
              AND use_category_name IN ('住宅地', '商業地')
            GROUP BY use_category_name
            """,
                [str(path)],
            )
            .fetchall()
        )
        result[year] = {}
        for category, sites, continuing, mean_yoy, duplicates in rows:
            if duplicates or sites < 300 or continuing < 300 or mean_yoy is None:
                raise ValueError(f"Land data quality check failed: {year} {category}")
            result[year][CATEGORIES[category]] = {
                "sites": sites,
                "continuing_sites": continuing,
                "mean_yoy_pct": float(mean_yoy),
            }
        if set(result[year]) != set(CATEGORIES.values()):
            raise ValueError(f"Missing Tokyo land category in {year}")
    return result


def sp500_year_ends() -> dict[int, tuple[date, float]]:
    start = int(datetime(2005, 12, 1, tzinfo=UTC).timestamp())
    end = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp())
    url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC"
    response = SESSION.get(
        url,
        params={"period1": start, "period2": end, "interval": "1d"},
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()["chart"]
    if payload["error"]:
        raise ValueError(payload["error"])
    series = payload["result"][0]
    if series["meta"].get("symbol") != "^GSPC":
        raise ValueError("Unexpected stock ticker")
    closes = series["indicators"]["quote"][0]["close"]
    found: dict[int, tuple[date, float]] = {}
    for timestamp, close in zip(series["timestamp"], closes, strict=True):
        if close is None or not math.isfinite(close):
            continue
        day = datetime.fromtimestamp(timestamp, UTC).date()
        if day.month == 12 and 2005 <= day.year <= 2025:
            if day.year not in found or day > found[day.year][0]:
                found[day.year] = day, float(close)
    if set(found) != set(range(2005, 2026)):
        raise ValueError(f"Missing stock year ends: {set(range(2005, 2026)) - set(found)}")
    return found


def usd_jpy_for_stock_dates(stock: dict[int, tuple[date, float]]) -> dict[int, tuple[date, float]]:
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    response = SESSION.get(
        url,
        params={"id": "DEXJPUS", "cosd": "2005-12-01", "coed": "2025-12-31"},
        timeout=45,
    )
    response.raise_for_status()
    observations = []
    for row in csv.DictReader(io.StringIO(response.text)):
        value = row.get("DEXJPUS")
        if value and value != ".":
            observations.append((date.fromisoformat(row["observation_date"]), float(value)))
    if not observations:
        raise ValueError("No USD/JPY observations")
    found = {}
    for year, (stock_date, _) in stock.items():
        prior = [(day, rate) for day, rate in observations if day <= stock_date]
        fx_date, rate = prior[-1]
        if (stock_date - fx_date).days > 5:
            raise ValueError(f"Stale USD/JPY observation for {year}: {fx_date}")
        found[year] = fx_date, rate
    return found


def create_rows() -> list[dict]:
    land = land_changes()
    stock = sp500_year_ends()
    fx = usd_jpy_for_stock_dates(stock)
    base_stock = stock[2005][1]
    base_fx = fx[2005][1]
    residential = commercial = 100.0
    rows = []
    for year in YEARS:
        if year > 2006:
            residential *= 1 + land[year]["residential"]["mean_yoy_pct"] / 100
            commercial *= 1 + land[year]["commercial"]["mean_yoy_pct"] / 100
        stock_date, stock_close = stock[year - 1]
        fx_date, fx_rate = fx[year - 1]
        stock_usd = 100 * stock_close / base_stock
        rows.append(
            {
                "year": year,
                "land_date": f"{year}-01-01",
                "stock_date": stock_date.isoformat(),
                "fx_date": fx_date.isoformat(),
                "tokyo_residential_sites": land[year]["residential"]["sites"],
                "tokyo_residential_continuing_sites": land[year]["residential"]["continuing_sites"],
                "tokyo_residential_mean_yoy_pct": land[year]["residential"]["mean_yoy_pct"],
                "tokyo_commercial_sites": land[year]["commercial"]["sites"],
                "tokyo_commercial_continuing_sites": land[year]["commercial"]["continuing_sites"],
                "tokyo_commercial_mean_yoy_pct": land[year]["commercial"]["mean_yoy_pct"],
                "tokyo_residential_index": residential,
                "tokyo_commercial_index": commercial,
                "sp500_close_usd": stock_close,
                "usd_jpy": fx_rate,
                "sp500_usd_index": stock_usd,
                "sp500_jpy_index": stock_usd * fx_rate / base_fx,
            }
        )
    return rows


def write_csv(rows: list[dict]) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / f"{STEM}.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def plot(rows: list[dict]) -> Path:
    plt.rcParams.update(
        {
            "font.family": ["DejaVu Sans", "Droid Sans Fallback"],
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    fig, ax = plt.subplots(figsize=(13.6, 7.8), dpi=180)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")
    x = [row["year"] for row in rows]
    series = [
        ("sp500_jpy_index", "S&P 500（円換算）", "#0868ac", 3.0),
        ("sp500_usd_index", "S&P 500（米ドル）", "#43a2ca", 2.6),
        ("tokyo_commercial_index", "東京23区・商業地", "#d95f0e", 2.6),
        ("tokyo_residential_index", "東京23区・住宅地", "#238b45", 2.6),
    ]
    for key, label, color, width in series:
        values = [row[key] for row in rows]
        ax.plot(x, values, marker="o", markersize=3.0, lw=width, color=color, label=label)
        final = values[-1]
        annual_change = (final / 100) ** (1 / 20) - 1  # price index only, no dividends
        ax.annotate(
            f"{label}  {final:.0f}  (価格指数 {annual_change:+.1%}/年)",
            xy=(2026, final),
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
            color=color,
            fontsize=10,
            fontweight="bold",
        )
    ax.set_yscale("log", base=2)
    ax.set_xlim(2005.7, 2031.5)
    ax.set_ylim(45, 1000)
    ax.set_xticks([2006, 2010, 2014, 2018, 2022, 2026])
    ax.yaxis.set_major_locator(FixedLocator([50, 100, 200, 400, 800]))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:g}"))
    ax.grid(axis="y", alpha=0.25)
    ax.grid(axis="x", alpha=0.10)
    ax.set_ylabel("指数（2006年=100、対数目盛）", labelpad=10)
    fig.text(
        0.095, 0.93, "S&P 500と東京23区の地価：20年間の価格変化", fontsize=17, fontweight="bold"
    )
    fig.text(
        0.095,
        0.882,
        "地価公示は各年1月1日、株価と為替は直前年末の終値。名目価格指数、2006年=100。",
        fontsize=10,
        color="#4d4d4d",
    )
    fig.text(
        0.095,
        0.035,
        "地価：東京都・地価公示（継続地点の前年比を年次連鎖）／株価：S&P 500終値（Yahoo Finance）／為替：米FRB・DEXJPUS",
        fontsize=9,
        color="#555555",
    )
    fig.text(
        0.095,
        0.009,
        "配当・賃料収入、税・費用は含まない。公示地価は鑑定評価であり、実売買価格ではない。",
        fontsize=9,
        color="#555555",
    )
    fig.subplots_adjust(left=0.095, right=0.68, top=0.82, bottom=0.13)
    path = OUTPUT / f"{STEM}.png"
    fig.savefig(path, dpi=180, facecolor="white")
    plt.close(fig)
    return path


if __name__ == "__main__":
    annual_rows = create_rows()
    csv_path = write_csv(annual_rows)
    image_path = plot(annual_rows)
    print(f"CSV: {csv_path}")
    print(f"Chart: {image_path}")
    for key in (
        "tokyo_residential_index",
        "tokyo_commercial_index",
        "sp500_usd_index",
        "sp500_jpy_index",
    ):
        final = annual_rows[-1][key]
        print(
            f"{key}: {final:.2f}, total={final - 100:+.1f}%, "
            f"price-index annual change={(final / 100) ** (1 / 20) - 1:+.2%}"
        )
    print(
        f"Base: {annual_rows[0]['stock_date']} S&P={annual_rows[0]['sp500_close_usd']:.2f}, "
        f"USD/JPY={annual_rows[0]['usd_jpy']:.2f}"
    )
    print(
        f"End: {annual_rows[-1]['stock_date']} S&P={annual_rows[-1]['sp500_close_usd']:.2f}, "
        f"USD/JPY={annual_rows[-1]['usd_jpy']:.2f}"
    )
