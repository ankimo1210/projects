"""Download the daily OHLCV cache the financial datasets are built from."""

from timesfm_lab.finance import CACHE, fetch

if __name__ == "__main__":
    df = fetch()
    print(f"\n{len(df)} rows, {df.ticker.nunique()} tickers -> {CACHE}")
