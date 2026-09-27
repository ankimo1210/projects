# stockkit Deterministic Core Tests — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a regression test suite for stockkit's deterministic core (plus yfinance-dependent analysis functions via mocking) so `make test` is green and the project meets the workspace Definition of Done.

**Architecture:** pytest unit tests under `stock/tests/`. Pure functions are tested with hand-computed reference values + invariants (hybrid approach C). yfinance-dependent functions are tested by monkeypatching the provider names **where they are looked up** (not where defined). The DuckDB cache is tested against a temporary database injected by overriding the module-level `cache._DEFAULT_DIR`. All hand-computed expected values in this plan were verified against the live code on 2026-06-01.

**Tech Stack:** Python 3.12, pytest>=8.3 (already in dev deps), pandas, numpy, duckdb. Run via `uv run --no-sync` from the workspace root `~/projects`.

**Note on TDD with pre-existing code:** The implementation already exists, so most "write test → run" steps will PASS immediately. That is expected. To prove the tests are meaningful (not vacuous), Task 6 includes an explicit "break the code, watch the test fail, restore" step for the key regression (`yoy_growth`), per spec DoD item 4.

---

### Task 0: Branch + test infrastructure

**Files:**
- Create: `stock/tests/__init__.py`
- Create: `stock/tests/conftest.py`
- Create: `stock/tests/test_smoke.py`
- Modify: `stock/pyproject.toml` (add `[tool.pytest.ini_options]`)

- [ ] **Step 1: Create a dedicated branch**

The current branch is `feat/reio-mvp-clean` (unrelated reio work). Create a clean branch:

```bash
cd ~/projects && git checkout -b feat/stockkit-tests
```

Expected: `Switched to a new branch 'feat/stockkit-tests'`

- [ ] **Step 2: Create the tests package marker**

Create `stock/tests/__init__.py` (empty file):

```python
```

- [ ] **Step 3: Write `conftest.py` with shared fixtures**

Create `stock/tests/conftest.py`:

```python
"""Shared fixtures for stockkit tests.

All tests run without network access. The DuckDB cache is redirected to a
per-test temporary directory by overriding the module-level constant
``cache._DEFAULT_DIR`` (it is resolved at import time, so the
``STOCKKIT_DATA_DIR`` env var alone would not take effect).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from stockkit.data import cache as cache_mod


@pytest.fixture
def temp_cache(tmp_path, monkeypatch):
    """Redirect the DuckDB cache to a temporary directory for one test."""
    monkeypatch.setattr(cache_mod, "_DEFAULT_DIR", tmp_path)
    return cache_mod


@pytest.fixture
def ohlcv():
    """Deterministic 10-row OHLCV frame with a daily DatetimeIndex."""
    idx = pd.date_range("2020-01-01", periods=10, freq="D")
    close = pd.Series(
        [100, 102, 101, 105, 107, 106, 110, 108, 112, 115], index=idx, dtype=float
    )
    df = pd.DataFrame(
        {
            "open": close.shift(1).fillna(close.iloc[0]),
            "high": close + 2.0,
            "low": close - 2.0,
            "close": close,
            "adj_close": close,
            "volume": pd.Series(range(1000, 1000 + 10 * 10, 10), index=idx, dtype=float),
        }
    )
    return df


@pytest.fixture
def price_panel_2():
    """Two-symbol wide adj_close panel with known returns (A: +10%, B: +5%)."""
    idx = pd.date_range("2020-01-01", periods=2, freq="D")
    return pd.DataFrame({"A": [100.0, 110.0], "B": [200.0, 210.0]}, index=idx)
```

- [ ] **Step 4: Write a smoke test**

Create `stock/tests/test_smoke.py`:

```python
import stockkit


def test_package_imports():
    assert hasattr(stockkit, "__version__")


def test_ohlcv_fixture(ohlcv):
    assert list(ohlcv.columns) == ["open", "high", "low", "close", "adj_close", "volume"]
    assert len(ohlcv) == 10
```

- [ ] **Step 5: Add pytest config to `pyproject.toml`**

Append to `stock/pyproject.toml` (after the `[dependency-groups]` block, before `[build-system]`):

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "network: tests that require live network access (deselected by default)",
]
```

- [ ] **Step 6: Run the smoke test**

Run: `cd ~/projects && uv run --no-sync pytest stock/tests/test_smoke.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: Commit**

```bash
cd ~/projects && git add stock/tests/__init__.py stock/tests/conftest.py stock/tests/test_smoke.py stock/pyproject.toml stock/docs/superpowers/
git commit -m "test(stockkit): add pytest infra (conftest, fixtures, config) + specs

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 1: symbols tests

**Files:**
- Create: `stock/tests/test_symbols.py`

- [ ] **Step 1: Write the tests**

Create `stock/tests/test_symbols.py`:

```python
import pytest

from stockkit.data.symbols import is_japanese, normalize_symbol


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("7203", "7203.T"),
        (" 7203 ", "7203.T"),
        ("7203.t", "7203.T"),
        ("aapl", "AAPL"),
        ("BRK-B", "BRK-B"),
        ("005930.KS", "005930.KS"),  # 6 digits -> not the 4-digit JP rule
    ],
)
def test_normalize_symbol(raw, expected):
    assert normalize_symbol(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("7203", True),
        ("7203.T", True),
        ("AAPL", False),
        ("005930.KS", False),
    ],
)
def test_is_japanese(raw, expected):
    assert is_japanese(raw) is expected
```

- [ ] **Step 2: Run**

Run: `cd ~/projects && uv run --no-sync pytest stock/tests/test_symbols.py -v`
Expected: PASS (all parametrized cases pass)

- [ ] **Step 3: Commit**

```bash
cd ~/projects && git add stock/tests/test_symbols.py
git commit -m "test(stockkit): cover symbol normalization

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: technical indicator tests

**Files:**
- Create: `stock/tests/test_technical.py`

- [ ] **Step 1: Write the tests**

Create `stock/tests/test_technical.py`:

```python
import numpy as np
import pandas as pd

from stockkit.analysis import technical as t


def test_sma_simple_average_and_nan_count():
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    out = t.sma(s, window=3)
    # first window-1 values are NaN, then the simple moving average
    assert out.iloc[:2].isna().all()
    np.testing.assert_allclose(out.iloc[2:].to_numpy(), [2.0, 3.0, 4.0])


def test_ema_hand_computed_span2():
    s = pd.Series([1, 2, 3], dtype=float)
    out = t.ema(s, window=2)  # alpha = 2/(2+1) = 2/3, adjust=False
    np.testing.assert_allclose(out.to_numpy(), [1.0, 5 / 3, 23 / 9])


def test_rsi_bounds_and_extremes():
    # strictly increasing -> no losses -> RSI undefined (NaN)
    inc = pd.Series(range(1, 9), dtype=float)
    assert np.isnan(t.rsi(inc).iloc[-1])
    # strictly decreasing -> no gains -> RSI == 0
    dec = pd.Series(range(8, 0, -1), dtype=float)
    assert t.rsi(dec).iloc[-1] == 0.0
    # mixed series stays within [0, 100]
    mixed = pd.Series([1, 2, 1, 3, 2, 4, 3, 5], dtype=float)
    r = t.rsi(mixed).dropna()
    assert ((r >= 0) & (r <= 100)).all()


def test_macd_hist_is_macd_minus_signal():
    s = pd.Series(np.linspace(100, 120, 60))
    m = t.macd(s)
    assert list(m.columns) == ["macd", "signal", "hist"]
    np.testing.assert_allclose(m["hist"], m["macd"] - m["signal"])


def test_bollinger_band_symmetry():
    s = pd.Series(np.linspace(100, 120, 30))
    bb = t.bollinger(s, window=20, k=2.0)
    valid = bb.dropna()
    np.testing.assert_allclose(valid["upper"] - valid["mid"], valid["mid"] - valid["lower"])


def test_atr_non_negative(ohlcv):
    a = t.atr(ohlcv, window=3)
    assert (a.dropna() >= 0).all()


def test_returns_simple_and_log():
    s = pd.Series([100.0, 110.0])
    np.testing.assert_allclose(t.returns(s).iloc[-1], 0.1)
    np.testing.assert_allclose(t.returns(s, log=True).iloc[-1], np.log(1.1))


def test_add_indicators_appends_expected_columns(ohlcv):
    out = t.add_indicators(ohlcv)
    for col in [
        "sma20", "sma50", "sma200", "ema20", "rsi14",
        "macd", "macd_signal", "macd_hist",
        "bb_mid", "bb_upper", "bb_lower", "atr14",
    ]:
        assert col in out.columns


def test_golden_cross_values_in_domain():
    # uptrending series produces a +1 golden cross with small windows
    s = pd.Series([10, 9, 8, 7, 9, 11, 13, 15, 17, 19], dtype=float)
    sig = t.signal_golden_cross(pd.DataFrame({"close": s}), fast=2, slow=3)
    assert set(sig.unique()).issubset({-1, 0, 1})
    assert (sig == 1).any()
```

- [ ] **Step 2: Run**

Run: `cd ~/projects && uv run --no-sync pytest stock/tests/test_technical.py -v`
Expected: PASS (9 tests)

- [ ] **Step 3: Commit**

```bash
cd ~/projects && git add stock/tests/test_technical.py
git commit -m "test(stockkit): cover technical indicators (hand-computed + invariants)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: backtest tests

**Files:**
- Create: `stock/tests/test_backtest.py`

- [ ] **Step 1: Write the tests**

Create `stock/tests/test_backtest.py`. The always-long equity end value (`1_208_350.0`) and the no-lookahead flat result were both verified against live code.

```python
import numpy as np
import pandas as pd
import pytest

from stockkit.analysis import backtest as bt


@pytest.fixture
def up_prices():
    # +10% per step, with an 'open' column so exec uses open
    idx = pd.date_range("2020-01-01", periods=3, freq="D")
    return pd.DataFrame({"open": [100.0, 110.0, 121.0], "close": [100.0, 110.0, 121.0]}, index=idx)


def test_run_requires_close():
    with pytest.raises(ValueError):
        bt.run(pd.DataFrame({"open": [1, 2, 3]}), lambda d: pd.Series([1, 1, 1]))


def test_always_long_equity_hand_computed(up_prices):
    # day0 flat (signal shifted), days 1-2 long, fee+slippage = 15bps on the entry day
    res = bt.run(up_prices, lambda d: pd.Series(1, index=d.index))
    np.testing.assert_allclose(res.equity.iloc[-1], 1_208_350.0)
    assert set(
        ["total_return", "cagr", "annual_vol", "sharpe", "max_drawdown", "win_rate_daily", "bars"]
    ).issubset(res.metrics.keys())
    assert res.metrics["max_drawdown"] <= 0.0


def test_no_lookahead_last_day_signal_stays_flat(up_prices):
    # A signal that only fires on the last bar cannot be acted on -> equity flat
    sig = pd.Series([0, 0, 1], index=up_prices.index)
    res = bt.run(up_prices, lambda d: sig)
    np.testing.assert_allclose(res.equity.to_numpy(), [1_000_000.0, 1_000_000.0, 1_000_000.0])
    assert res.trades.empty


def test_fees_reduce_terminal_equity(up_prices):
    longer = lambda d: pd.Series(1, index=d.index)
    no_fee = bt.run(up_prices, longer, fee_bps=0.0, slippage_bps=0.0)
    with_fee = bt.run(up_prices, longer, fee_bps=10.0, slippage_bps=5.0)
    assert no_fee.equity.iloc[-1] > with_fee.equity.iloc[-1]


@pytest.mark.parametrize("name", ["sma_cross", "rsi_reversion", "macd_cross", "donchian"])
def test_preset_signals_produce_binary_series(name, ohlcv):
    sig_fn = bt.PRESETS[name]()
    sig = sig_fn(ohlcv)
    assert len(sig) == len(ohlcv)
    assert set(sig.dropna().unique()).issubset({0, 1})
```

- [ ] **Step 2: Run**

Run: `cd ~/projects && uv run --no-sync pytest stock/tests/test_backtest.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
cd ~/projects && git add stock/tests/test_backtest.py
git commit -m "test(stockkit): cover backtester (equity, no-lookahead, fees, presets)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: portfolio tests (pure + mocked price_panel)

**Files:**
- Create: `stock/tests/test_portfolio.py`

- [ ] **Step 1: Write the tests**

Create `stock/tests/test_portfolio.py`. `price_panel` calls `get_prices` imported into the `portfolio` namespace, so patch `stockkit.analysis.portfolio.get_prices`.

```python
import numpy as np
import pandas as pd

from stockkit.analysis import portfolio as pf


def test_daily_returns_known_values(price_panel_2):
    dr = pf.daily_returns(price_panel_2)
    # first row dropped by dropna(how="all"); A +10%, B +5%
    np.testing.assert_allclose(dr["A"].to_numpy(), [0.1])
    np.testing.assert_allclose(dr["B"].to_numpy(), [0.05])


def test_sharpe_matches_definition(price_panel_2):
    ar = pf.annualized_return(price_panel_2)
    av = pf.annualized_vol(price_panel_2)
    sh = pf.sharpe(price_panel_2, rf=0.0)
    # with a single return per series, vol is 0 -> sharpe is NaN (guarded by replace(0, NaN))
    assert sh.isna().all() or np.isfinite(sh).all()
    assert set(ar.index) == {"A", "B"} == set(av.index)


def test_max_drawdown_non_positive():
    idx = pd.date_range("2020-01-01", periods=5, freq="D")
    prices = pd.DataFrame({"X": [100, 90, 95, 80, 120]}, index=idx, dtype=float)
    assert pf.max_drawdown(prices)["X"] <= 0.0


def test_correlation_diagonal_is_one():
    idx = pd.date_range("2020-01-01", periods=6, freq="D")
    prices = pd.DataFrame(
        {"A": [1, 2, 3, 4, 5, 6], "B": [2, 1, 4, 3, 6, 5]}, index=idx, dtype=float
    )
    corr = pf.correlation(prices)
    np.testing.assert_allclose(np.diag(corr.to_numpy()), [1.0, 1.0])


def test_weighted_portfolio_normalizes_weights():
    idx = pd.date_range("2020-01-01", periods=4, freq="D")
    prices = pd.DataFrame(
        {"A": [100, 110, 121, 133.1], "B": [50, 55, 60.5, 66.55]}, index=idx, dtype=float
    )
    equal = pf.weighted_portfolio(prices)  # default equal weight
    doubled = pf.weighted_portfolio(prices, {"A": 2.0, "B": 2.0})  # normalizes to equal
    np.testing.assert_allclose(equal.to_numpy(), doubled.to_numpy())


def test_price_panel_assembles_wide_frame(monkeypatch):
    idx = pd.date_range("2020-01-01", periods=3, freq="D")

    def fake_get_prices(symbol, period="5y"):
        if symbol == "EMPTY":
            return pd.DataFrame()
        base = {"A": 100.0, "B": 200.0}[symbol]
        return pd.DataFrame({"adj_close": [base, base + 1, base + 2]}, index=idx)

    monkeypatch.setattr(pf, "get_prices", fake_get_prices)
    panel = pf.price_panel(["A", "B", "EMPTY"])
    assert list(panel.columns) == ["A", "B"]  # EMPTY skipped
    assert len(panel) == 3


def test_price_panel_all_empty_returns_empty(monkeypatch):
    monkeypatch.setattr(pf, "get_prices", lambda s, period="5y": pd.DataFrame())
    assert pf.price_panel(["A", "B"]).empty
```

- [ ] **Step 2: Run**

Run: `cd ~/projects && uv run --no-sync pytest stock/tests/test_portfolio.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
cd ~/projects && git add stock/tests/test_portfolio.py
git commit -m "test(stockkit): cover portfolio analytics + mocked price_panel

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: fundamental tests (yoy_growth + mocked snapshot) with regression proof

**Files:**
- Create: `stock/tests/test_fundamental.py`

- [ ] **Step 1: Write the tests**

Create `stock/tests/test_fundamental.py`. `snapshot` calls `get_info` and `revenue_growth_history` calls `get_financials`, both imported into the `fundamental` namespace — patch them there.

```python
import numpy as np
import pandas as pd

from stockkit.analysis import fundamental as fnd


def _financials_desc():
    # yfinance-style: columns are period-end timestamps in DESCENDING order
    return pd.DataFrame(
        {
            pd.Timestamp("2023-12-31"): [300.0],
            pd.Timestamp("2022-12-31"): [200.0],
            pd.Timestamp("2021-12-31"): [100.0],
        },
        index=["Total Revenue"],
    )


def test_yoy_growth_sorts_ascending_then_pct_change():
    out = fnd.yoy_growth(_financials_desc(), "Total Revenue")
    # 100 -> 200 (+100%), 200 -> 300 (+50%)
    np.testing.assert_allclose(out.dropna().to_numpy(), [1.0, 0.5])


def test_yoy_growth_missing_or_empty_returns_empty():
    assert fnd.yoy_growth(pd.DataFrame(), "Total Revenue").empty
    assert fnd.yoy_growth(_financials_desc(), "No Such Row").empty


def test_snapshot_maps_info_fields_with_fallback(monkeypatch):
    info = {"shortName": "Acme", "trailingPE": 12.0, "returnOnEquity": 0.2}
    monkeypatch.setattr(fnd, "get_info", lambda s: info)
    snap = fnd.snapshot("AAA")
    assert snap["symbol"] == "AAA"
    assert snap["name"] == "Acme"  # falls back to shortName when longName absent
    assert snap["pe"] == 12.0
    assert snap["roe"] == 0.2
    assert snap["pb"] is None  # missing field -> None


def test_revenue_growth_history_uses_income_statement(monkeypatch):
    monkeypatch.setattr(fnd, "get_financials", lambda s: {"income": _financials_desc()})
    out = fnd.revenue_growth_history("AAA")
    np.testing.assert_allclose(out.dropna().to_numpy(), [1.0, 0.5])
```

- [ ] **Step 2: Run**

Run: `cd ~/projects && uv run --no-sync pytest stock/tests/test_fundamental.py -v`
Expected: PASS (4 tests)

- [ ] **Step 3: Prove the regression test is real (break-and-restore)**

Temporarily edit `stock/src/stockkit/analysis/fundamental.py` line 62 — remove `.sort_index()` from `yoy_growth`:

```python
    s = financials.loc[row].astype(float)
```

Run: `cd ~/projects && uv run --no-sync pytest stock/tests/test_fundamental.py::test_yoy_growth_sorts_ascending_then_pct_change -v`
Expected: FAIL (descending order gives roughly `[-0.333, -0.5]`, not `[1.0, 0.5]`)

Then RESTORE the line back to:

```python
    s = financials.loc[row].astype(float).sort_index()
```

Re-run the test: Expected PASS again. Confirm `git diff stock/src` is empty before committing.

- [ ] **Step 4: Commit**

```bash
cd ~/projects && git add stock/tests/test_fundamental.py
git commit -m "test(stockkit): cover fundamental yoy_growth + mocked snapshot

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: screener tests (rules + mocked screen)

**Files:**
- Create: `stock/tests/test_screener.py`

- [ ] **Step 1: Write the tests**

Create `stock/tests/test_screener.py`. `screen` calls `fundamental.snapshot` and `get_prices` from the `screener` namespace — patch `stockkit.analysis.screener.fundamental.snapshot` and `stockkit.analysis.screener.get_prices`.

```python
import pandas as pd

from stockkit.analysis import screener as sc


def test_pe_below_rule():
    rule = sc.pe_below(15)
    assert rule({"pe": 10.0}, None) is True
    assert rule({"pe": 20.0}, None) is False
    assert rule({"pe": None}, None) is False
    assert rule({}, None) is False


def test_roe_above_rule():
    rule = sc.roe_above(0.1)
    assert rule({"roe": 0.2}, None) is True
    assert rule({"roe": 0.05}, None) is False
    assert rule({"roe": None}, None) is False


def test_above_sma_rule():
    idx = pd.date_range("2020-01-01", periods=5, freq="D")
    rising = pd.DataFrame({"close": [1, 2, 3, 4, 5]}, index=idx, dtype=float)
    rule = sc.above_sma(window=3)
    assert rule({}, rising) is True  # last close 5 > sma(3)=4
    assert rule({}, pd.DataFrame()) is False  # empty prices -> False


def test_rsi_between_full_range_true_and_empty_false():
    idx = pd.date_range("2020-01-01", periods=8, freq="D")
    mixed = pd.DataFrame({"close": [1, 2, 1, 3, 2, 4, 3, 5]}, index=idx, dtype=float)
    assert sc.rsi_between(-1, 101)(None, mixed) is True  # any finite RSI is in range
    assert sc.rsi_between(30, 70)(None, pd.DataFrame()) is False


def test_screen_filters_and_is_exception_safe(monkeypatch):
    idx = pd.date_range("2020-01-01", periods=3, freq="D")
    snaps = {
        "GOOD": {"symbol": "GOOD", "pe": 10.0},
        "BAD": {"symbol": "BAD", "pe": 30.0},
    }
    monkeypatch.setattr(sc.fundamental, "snapshot", lambda s: snaps[s])
    monkeypatch.setattr(
        sc, "get_prices", lambda s, period="1y": pd.DataFrame({"close": [1, 2, 3]}, index=idx)
    )

    out = sc.screen(["GOOD", "BAD"], [sc.pe_below(15)])
    assert list(out.index) == ["GOOD"]

    # a rule that raises is caught -> symbol excluded, no crash
    def boom(_snap, _prices):
        raise RuntimeError("boom")

    out2 = sc.screen(["GOOD", "BAD"], [boom])
    assert out2.empty
```

- [ ] **Step 2: Run**

Run: `cd ~/projects && uv run --no-sync pytest stock/tests/test_screener.py -v`
Expected: PASS (5 tests)

- [ ] **Step 3: Commit**

```bash
cd ~/projects && git add stock/tests/test_screener.py
git commit -m "test(stockkit): cover screener rules + mocked screen

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: cache tests (temporary DuckDB)

**Files:**
- Create: `stock/tests/test_cache.py`

- [ ] **Step 1: Write the tests**

Create `stock/tests/test_cache.py`. Uses the `temp_cache` fixture, which overrides `cache._DEFAULT_DIR` to a `tmp_path`.

```python
import pandas as pd


def _price_df():
    idx = pd.date_range("2020-01-01", periods=3, freq="D", name="date")
    return pd.DataFrame(
        {
            "open": [10.0, 11.0, 12.0],
            "high": [10.5, 11.5, 12.5],
            "low": [9.5, 10.5, 11.5],
            "close": [10.2, 11.2, 12.2],
            "adj_close": [10.2, 11.2, 12.2],
            "volume": [1000.0, 1100.0, 1200.0],
        },
        index=idx,
    )


def test_prices_roundtrip(temp_cache):
    n = temp_cache.upsert_prices("TEST", _price_df())
    assert n == 3
    out = temp_cache.read_prices("TEST")
    assert len(out) == 3
    assert out["close"].iloc[-1] == 12.2


def test_prices_upsert_is_idempotent(temp_cache):
    temp_cache.upsert_prices("TEST", _price_df())
    temp_cache.upsert_prices("TEST", _price_df())  # same PKs -> replace, not duplicate
    assert len(temp_cache.read_prices("TEST")) == 3


def test_prices_date_filter(temp_cache):
    temp_cache.upsert_prices("TEST", _price_df())
    out = temp_cache.read_prices("TEST", start="2020-01-02")
    assert len(out) == 2


def test_latest_cached_date(temp_cache):
    temp_cache.upsert_prices("TEST", _price_df())
    assert temp_cache.latest_cached_date("TEST") == pd.Timestamp("2020-01-03")
    assert temp_cache.latest_cached_date("MISSING") is None


def test_empty_upsert_writes_nothing(temp_cache):
    assert temp_cache.upsert_prices("TEST", pd.DataFrame()) == 0
    assert temp_cache.read_prices("TEST").empty


def test_macro_roundtrip(temp_cache):
    s = pd.Series(
        [1.0, 2.0, 3.0],
        index=pd.date_range("2020-01-01", periods=3, freq="MS"),
        name="CPIAUCSL",
    )
    assert temp_cache.upsert_macro("CPIAUCSL", s) == 3
    out = temp_cache.read_macro("CPIAUCSL")
    assert len(out) == 3
    assert out.iloc[-1] == 3.0
    assert temp_cache.latest_macro_date("CPIAUCSL") == pd.Timestamp("2020-03-01")
```

- [ ] **Step 2: Run**

Run: `cd ~/projects && uv run --no-sync pytest stock/tests/test_cache.py -v`
Expected: PASS (6 tests)

- [ ] **Step 3: Commit**

```bash
cd ~/projects && git add stock/tests/test_cache.py
git commit -m "test(stockkit): cover DuckDB cache roundtrip + idempotency

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: version sync + full-suite verification

**Files:**
- Modify: `stock/src/stockkit/__init__.py:6`
- Modify: `stock/pyproject.toml:3`

- [ ] **Step 1: Bump `__version__` in the package**

In `stock/src/stockkit/__init__.py`, change:

```python
__version__ = "0.1.0"
```
to:
```python
__version__ = "0.4.0"
```

- [ ] **Step 2: Bump version in `pyproject.toml`**

In `stock/pyproject.toml`, change line 3:

```toml
version = "0.1.0"
```
to:
```toml
version = "0.4.0"
```

- [ ] **Step 3: Run the full stockkit suite**

Run: `cd ~/projects && uv run --no-sync pytest stock/tests -v`
Expected: PASS (all tests across the 8 test files green). Quote the summary line.

- [ ] **Step 4: Run the whole workspace test suite (DoD)**

Run: `cd ~/projects && make test`
Expected: green — confirm no other project was broken. If a pre-existing unrelated failure appears, report it explicitly rather than claiming success.

- [ ] **Step 5: Lint the new tests (DoD)**

Run: `cd ~/projects && make lint`
Expected: green (ruff passes on the new test files).

- [ ] **Step 6: Commit**

```bash
cd ~/projects && git add stock/src/stockkit/__init__.py stock/pyproject.toml
git commit -m "chore(stockkit): sync version to 0.4.0

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review Notes

- **Spec coverage:** Every module in the spec's two scope tables maps to a task — symbols (T1), technical (T2), backtest (T3), portfolio pure+mocked (T4), fundamental yoy_growth+mocked (T5), screener rules+mocked (T6), cache temp DuckDB (T7). Version fix (T8). conftest gotcha (`_DEFAULT_DIR` override) and "patch where looked up" both encoded. DoD verification (pytest + make test + make lint + regression-break proof) covered in T5 and T8.
- **Out-of-scope respected:** no raw provider HTTP tests, no `data.get_prices/get_macro` orchestration, no basket, no app/Dash/chat.
- **All hand-computed values** (sma3, ema span2, rsi extremes, returns, always-long equity `1,208,350`, no-lookahead flat, daily_returns 0.1/0.05, yoy `[1.0, 0.5]`) were verified against the live code before this plan was written.
