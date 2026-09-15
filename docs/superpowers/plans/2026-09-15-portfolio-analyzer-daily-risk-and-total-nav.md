# Daily risk monitor + total NAV — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The daily P&L report and mail show NAV / cumulative P&L / attribution for all three accounts together, and gain a daily risk section (look-through exposures by asset class, currency, country and sector; concentration vs policy limits; volatility, VaR/ES, betas, risk contributions; factor scenarios and replayed episodes).

**Architecture:** Each account's daily path becomes a `timeseries.AccountSeries` (IBKR from the existing replay, the domestic account from its trade CSV, the DC plan from its anchor + contributions) and `timeseries.combine` sums them with `None` where any account is undefined. A new pure-Python module `risk.py` turns today's holdings + the analysis reference + the already-downloaded price history into a `risk` payload block that `dashboard.py` and `mailer.py` render. The reference JSON gains country / currency / asset mixes, three draft limits and replay episodes.

**Tech Stack:** Python 3.12, Decimal for money paths, float for statistics, pandas only inside `scripts/daily_pl_report.py`, pytest; run everything from `/home/kazumasa/projects` with `uv run --no-sync`.

**Spec:** `docs/superpowers/specs/2026-09-15-portfolio-analyzer-daily-risk-and-total-nav-design.md`

## Global Constraints

- Run tests as `uv run --no-sync pytest portfolio-analyzer/tests -q` from `/home/kazumasa/projects`; lint/format only the files touched (`uv run --no-sync ruff check <files>`, `uv run --no-sync ruff format <files>`) — never `ruff format` the whole project.
- No new production dependencies: `src/portfolio_analyzer/*.py` stays stdlib-only (Decimal, math, statistics); pandas/yfinance are used only in `scripts/`.
- Money paths are `Decimal`; an undefined date is `None`, never 0.
- Labels: Japanese for the user-facing text, English identifiers; the mail draws with table cells and inline styles only (no CSS `background`, no `<script>`, no SVG).
- `data/*.private.json` are the user's own files (gitignored); edit them with a script that preserves 2-space indent and `ensure_ascii=False`.
- Commit messages end with the attribution lines the session provides (Co-Authored-By: Claude Fable 5.1 + Claude-Session).

---

## Part A — total NAV and P&L

### Task 1: `timeseries.AccountSeries`, `from_ledger`, `combine`, `first_defined`, `daily_changes`

**Files:**
- Modify: `portfolio-analyzer/src/portfolio_analyzer/timeseries.py` (append after `value_paths`)
- Test: `portfolio-analyzer/tests/test_timeseries.py`

**Interfaces:**
- Produces: `AccountSeries(account_id, nav, deposits_cum, unrealized, realized_cum, dividends_cum, fees_cum, fx_translation_cum, forex_cum, xirr_flows=None)` with property `pnl`; `BUCKETS` tuple; `from_ledger(account_id, paths, values, flows)`; `combine(series, account_id="total")`; `first_defined(values) -> int | None`; `daily_changes(values) -> list[Decimal | None]` (first element `None`).

- [ ] **Step 1: Write the failing tests** (append to `tests/test_timeseries.py`)

```python
def _series(account_id, nav, deposits, unrealized=None, flows=None):
    n = len(nav)
    zeros = [None if v is None else D(0) for v in nav]
    return ts.AccountSeries(
        account_id=account_id,
        nav=nav,
        deposits_cum=deposits,
        unrealized=unrealized if unrealized is not None else [None if v is None or d is None else v - d for v, d in zip(nav, deposits, strict=True)],
        realized_cum=list(zeros),
        dividends_cum=list(zeros),
        fees_cum=list(zeros),
        fx_translation_cum=list(zeros),
        forex_cum=list(zeros),
        xirr_flows=flows,
    )


def test_account_series_pnl_is_nav_minus_deposits_and_none_where_undefined() -> None:
    s = _series("a", [None, D(110), D(120)], [None, D(100), D(100)])
    assert s.pnl == [None, D(10), D(20)]


def test_combine_sums_accounts_and_propagates_none() -> None:
    a = _series("a", [D(100), D(110), D(120)], [D(100), D(100), D(100)])
    b = _series("b", [None, D(50), D(55)], [None, D(40), D(40)])
    total = ts.combine([a, b])
    assert total.account_id == "total"
    assert total.nav == [None, D(160), D(175)]
    assert total.deposits_cum == [None, D(140), D(140)]
    assert total.pnl == [None, D(20), D(35)]
    assert total.unrealized == [None, D(20), D(35)]
    assert total.xirr_flows is None


def test_from_ledger_reads_the_replayed_ibkr_paths() -> None:
    paths = ts.replay(transactions(), DATES)
    prices = {"XLE": [D(50), D(50), D(60), D(60)]}
    fx = [D(150)] * 4
    values = ts.value_paths(paths, prices, fx)
    s = ts.from_ledger("global_broker", paths, values, [("2026-01-05", D(1000000))])
    assert s.nav == values.nav and s.deposits_cum == paths.deposits_cum
    assert s.pnl == values.pnl_total
    assert s.realized_cum == paths.realized_cum and s.dividends_cum == paths.dividends_cum
    assert s.xirr_flows == [("2026-01-05", D(1000000))]
    # the buckets add up to NAV − deposits on every date
    for i in range(len(DATES)):
        parts = sum((getattr(s, b)[i] for b in ts.BUCKETS), D(0))
        assert parts == s.pnl[i]


def test_first_defined_and_daily_changes() -> None:
    values = [None, None, D(5), D(7), D(6)]
    assert ts.first_defined(values) == 2
    assert ts.first_defined([None, None]) is None
    assert ts.daily_changes(values) == [None, None, None, D(2), D(-1)]
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run --no-sync pytest portfolio-analyzer/tests/test_timeseries.py -q`
Expected: FAIL with `AttributeError: module ... has no attribute 'AccountSeries'`

- [ ] **Step 3: Implement** (append to `timeseries.py`; add `from collections.abc import Sequence` at the top)

```python
BUCKETS = (
    "unrealized",
    "realized_cum",
    "dividends_cum",
    "fees_cum",
    "fx_translation_cum",
    "forex_cum",
)


@dataclass
class AccountSeries:
    """One account's daily path in JPY. ``None`` on a date the history cannot reconstruct.

    On every defined date ``nav - deposits_cum`` equals the sum of the six buckets
    in ``BUCKETS`` — each source keeps that identity by construction.
    """

    account_id: str
    nav: list[Decimal | None]
    deposits_cum: list[Decimal | None]
    unrealized: list[Decimal | None]
    realized_cum: list[Decimal | None]
    dividends_cum: list[Decimal | None]
    fees_cum: list[Decimal | None]
    fx_translation_cum: list[Decimal | None]
    forex_cum: list[Decimal | None]
    # dated deposits for a money-weighted return; None when the history does not have them
    xirr_flows: list[tuple[str, Decimal]] | None = None

    @property
    def pnl(self) -> list[Decimal | None]:
        return [
            None if n is None or d is None else n - d
            for n, d in zip(self.nav, self.deposits_cum, strict=True)
        ]


def from_ledger(
    account_id: str, paths: Paths, values: ValuePaths, flows: list[tuple[str, Decimal]]
) -> AccountSeries:
    """The IBKR account's series from its replayed paths and their marks."""
    n = len(paths.dates)
    unrealized = [sum((values.unrealized[s][i] for s in values.unrealized), ZERO) for i in range(n)]
    return AccountSeries(
        account_id=account_id,
        nav=list(values.nav),
        deposits_cum=list(paths.deposits_cum),
        unrealized=unrealized,
        realized_cum=list(paths.realized_cum),
        dividends_cum=list(paths.dividends_cum),
        fees_cum=list(paths.fees_cum),
        fx_translation_cum=list(paths.fx_translation_cum),
        forex_cum=list(paths.forex_cum),
        xirr_flows=list(flows),
    )


def _add(columns: Sequence[Sequence[Decimal | None]]) -> list[Decimal | None]:
    out: list[Decimal | None] = []
    for values in zip(*columns, strict=True):
        out.append(None if any(v is None for v in values) else sum(values, ZERO))
    return out


def combine(series: Sequence[AccountSeries], account_id: str = "total") -> AccountSeries:
    """The accounts added together; a date any of them cannot reconstruct is None."""
    summed = {f: _add([getattr(s, f) for s in series]) for f in ("nav", "deposits_cum", *BUCKETS)}
    return AccountSeries(account_id=account_id, xirr_flows=None, **summed)


def first_defined(values: Sequence[Decimal | None]) -> int | None:
    return next((i for i, v in enumerate(values) if v is not None), None)


def daily_changes(values: Sequence[Decimal | None]) -> list[Decimal | None]:
    """Day-over-day differences; None on the first date and wherever either side is None."""
    out: list[Decimal | None] = [None]
    for prev, cur in zip(values, values[1:], strict=False):
        out.append(None if prev is None or cur is None else cur - prev)
    return out
```

- [ ] **Step 4: Run tests** — `uv run --no-sync pytest portfolio-analyzer/tests/test_timeseries.py -q` → PASS
- [ ] **Step 5: Commit** — `git add portfolio-analyzer/src/portfolio_analyzer/timeseries.py portfolio-analyzer/tests/test_timeseries.py && git commit -m "feat(portfolio-analyzer): per-account daily series and their sum"`

### Task 2: `jpbroker.account_paths` (domestic account: cash, deposits, dividends, realized, unrealized)

**Files:**
- Modify: `portfolio-analyzer/src/portfolio_analyzer/jpbroker.py` (`replay` gains `realized_cum` per symbol; new `account_paths`)
- Test: `portfolio-analyzer/tests/test_jpbroker.py`

**Interfaces:**
- Consumes: `timeseries.AccountSeries`
- Produces: `account_paths(rows, dates, prices, account_id="securities") -> AccountSeries` where `prices: dict[symbol, list[Decimal | None]]` is aligned to `dates`; `replay(...)[symbol]["realized_cum"]`.

- [ ] **Step 1: Failing tests** (append to `tests/test_jpbroker.py`)

```python
DATES = ["2024-11-01", "2024-11-25", "2025-01-28", "2025-06-04", "2025-10-01", "2026-03-09", "2026-08-14"]


def _prices():
    # 9023 until it is sold, 7532 (post-split shares), 1329
    return {
        "9023": [None, D("1754"), D("1800"), D("1727"), D("1727"), D("1727"), D("1727")],
        "7532": [None, None, D("4219"), D("4000"), D("1000"), D("900"), D("726")],
        "1329": [None, None, None, None, None, D("5360"), D("6636")],
        "8976": [None] * 7,
    }


def test_account_paths_replays_cash_from_the_settled_amounts() -> None:
    rows = jpbroker.parse_transactions(SAMPLE)
    s = jpbroker.account_paths(rows, DATES, _prices())
    assert s.account_id == "securities"
    # deposit only
    assert s.nav[0] == D(600000) and s.deposits_cum[0] == D(600000) and s.pnl[0] == D(0)
    # after buying 9023: cash 600000 − 528424, position 300 × 1754
    assert s.nav[1] == D(600000) - D(528424) + D(300) * D(1754)
    # the sale realises 515902 − 528424 and the dividend later lands in cash
    assert s.realized_cum[3] == D(515902) - D(528424)
    assert s.dividends_cum[-1] == D(15260) and s.dividends_cum[3] == D(0)


def test_account_paths_keeps_the_bucket_identity_on_every_date() -> None:
    rows = jpbroker.parse_transactions(SAMPLE)
    s = jpbroker.account_paths(rows, DATES, _prices())
    for i, date in enumerate(DATES):
        if s.nav[i] is None:
            continue
        parts = sum((getattr(s, b)[i] for b in ts.BUCKETS), D(0))
        assert parts == s.pnl[i], date
    assert s.fees_cum == [D(0)] * len(DATES)  # commissions sit inside the cost basis


def test_account_paths_is_undefined_while_a_held_symbol_has_no_price() -> None:
    rows = jpbroker.parse_transactions(SAMPLE)
    prices = _prices()
    prices["1329"][-1] = None
    s = jpbroker.account_paths(rows, DATES, prices)
    assert s.nav[-1] is None and s.pnl[-1] is None and s.unrealized[-1] is None
    assert s.deposits_cum[-1] == D(600000)  # cash-side paths never depend on a price


def test_replay_carries_realised_pnl_per_symbol() -> None:
    rows = jpbroker.parse_transactions(SAMPLE)
    path = jpbroker.replay(rows, DATES)["9023"]
    assert path["realized_cum"][2] == D(0) and path["realized_cum"][3] == D(515902) - D(528424)
```

Add `from portfolio_analyzer import timeseries as ts` and `D = Decimal` (with `from decimal import Decimal`) at the top of the test file if not present.

- [ ] **Step 2: Run** — expected FAIL (`account_paths` missing).
- [ ] **Step 3: Implement**

In `replay`: add `"realized_cum": []` to each `paths[s]`, `"realized": ZERO` to each `book[s]`; in `apply` for SELL compute `removed = state["cost_basis_jpy"] * share` and `state["realized"] += txn.amount - removed` before subtracting; in the per-date loop append `state["realized"]` to `paths[symbol]["realized_cum"]`. (Splits leave realised P&L alone.)

Append:

```python
def account_paths(
    rows: list[Txn],
    dates: Sequence[str],
    prices: dict[str, list[Decimal | None]],
    account_id: str = "securities",
) -> AccountSeries:
    """The account's NAV, deposits and P&L buckets on each date.

    Cash moves on the trade date (``_event_date``), the same day the quantity does,
    so NAV never counts a purchase twice between trade and settlement. With cost at
    the settled amount, ``NAV − deposits = unrealised + realised + dividends`` on every
    date; commissions are inside the cost basis, so ``fees_cum`` stays zero. A date on
    which a held symbol has no price is None.
    """
    ordered = sorted(rows, key=lambda t: (_event_date(t), t.settle_date or ""))
    paths = replay(rows, dates)
    n = len(dates)
    cash, deposits, dividends = [], [], []
    running_cash = running_dep = running_div = ZERO
    cursor = 0
    for date in dates:
        while cursor < len(ordered) and _event_date(ordered[cursor]) <= date:
            txn = ordered[cursor]
            cursor += 1
            if txn.amount is None:
                continue
            running_cash += txn.amount
            if txn.kind.startswith("入金(振込)"):
                running_dep += txn.amount
            elif txn.kind in DIVIDEND_KINDS:
                running_div += txn.amount
        cash.append(running_cash)
        deposits.append(running_dep)
        dividends.append(running_div)
    nav: list[Decimal | None] = []
    unrealized: list[Decimal | None] = []
    realized: list[Decimal | None] = []
    for i in range(n):
        value = unreal = ZERO
        defined = True
        for symbol, path in paths.items():
            q = path["quantity"][i]
            if q <= ZERO:
                continue
            price = (prices.get(symbol) or [None] * n)[i]
            if price is None:
                defined = False
                break
            value += q * price
            unreal += q * price - path["cost_basis_jpy"][i]
        realized.append(sum((p["realized_cum"][i] for p in paths.values()), ZERO))
        nav.append(cash[i] + value if defined else None)
        unrealized.append(unreal if defined else None)
    zeros: list[Decimal | None] = [ZERO] * n
    return AccountSeries(
        account_id=account_id,
        nav=nav,
        deposits_cum=list(deposits),
        unrealized=unrealized,
        realized_cum=realized,
        dividends_cum=list(dividends),
        fees_cum=list(zeros),
        fx_translation_cum=list(zeros),
        forex_cum=list(zeros),
        xirr_flows=[
            (_event_date(t), t.amount)
            for t in ordered
            if t.kind.startswith("入金(振込)") and t.amount is not None
        ],
    )
```

Import at top: `from portfolio_analyzer.timeseries import AccountSeries`.

- [ ] **Step 4: Run** the whole jpbroker test file → PASS (existing replay tests still pass).
- [ ] **Step 5: Commit** — `feat(portfolio-analyzer): replay the domestic account's NAV and P&L buckets`

### Task 3: `dcplan.account_paths`

**Files:**
- Modify: `portfolio-analyzer/src/portfolio_analyzer/dcplan.py`
- Test: `portfolio-analyzer/tests/test_dcplan.py`

**Interfaces:** `account_paths(holding, trades, dates, nav_path: list[Decimal | None]) -> AccountSeries` — `nav_path` is the fund price per 10,000 units aligned to `dates`.

- [ ] **Step 1: Failing test**

```python
def test_account_paths_values_the_units_and_treats_contributions_as_deposits() -> None:
    dates = ["2025-08-25", "2025-08-26", "2026-08-26", "2026-09-11"]
    nav_path = [D("22000"), D("22470"), D("26502"), D("25885")]
    s = dcplan.account_paths(HOLDING, dcplan.parse_trades(TRADES_PASTE), dates, nav_path)
    assert s.account_id == "dc"
    assert s.nav[0] is None and s.pnl[0] is None and s.deposits_cum[0] is None
    assert s.deposits_cum[-1] == D("5184000")
    assert s.nav[-1] == D("290.1109") * D("25885")
    assert s.pnl[-1] == s.nav[-1] - D("5184000") == s.unrealized[-1]
    assert s.realized_cum[-1] == D(0) and s.xirr_flows is None
    # a date with a price but no anchor path stays undefined; the reverse too
    s2 = dcplan.account_paths(HOLDING, dcplan.parse_trades(TRADES_PASTE), dates, [None, *nav_path[1:]])
    assert s2.nav[1] is not None and s2.nav[0] is None
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** (append to `dcplan.py`; import `from portfolio_analyzer.timeseries import AccountSeries`)

```python
def account_paths(
    holding: dict[str, Any],
    trades: Sequence[Trade],
    dates: Sequence[str],
    nav_path: Sequence[Decimal | None],
) -> AccountSeries:
    """Units × price as NAV, the contributions as deposits, so P&L is the unrealised gain.

    Undefined (None) before the first contribution the history lists, and on a
    date without a price. Dated flows for a money-weighted return are not known
    (the contributions before the history are folded into the anchor), so
    ``xirr_flows`` is None.
    """
    path = replay(holding, trades, dates)[holding["symbol"]]
    nav: list[Decimal | None] = []
    deposits: list[Decimal | None] = []
    for q, cost, price in zip(path["quantity"], path["cost_basis_jpy"], nav_path, strict=True):
        if q is None or cost is None or price is None:
            nav.append(None)
            deposits.append(None)
        else:
            nav.append(q * price)
            deposits.append(cost)
    pnl = [None if n is None or d is None else n - d for n, d in zip(nav, deposits, strict=True)]
    zeros = [None if n is None else ZERO for n in nav]
    return AccountSeries(
        account_id=str(holding["account_id"]),
        nav=nav,
        deposits_cum=deposits,
        unrealized=pnl,
        realized_cum=list(zeros),
        dividends_cum=list(zeros),
        fees_cum=list(zeros),
        fx_translation_cum=list(zeros),
        forex_cum=list(zeros),
        xirr_flows=None,
    )
```

- [ ] **Step 4: Run** → PASS. **Step 5: Commit** — `feat(portfolio-analyzer): the DC plan as a daily account series`

### Task 4: script integration — total series, headline, attribution, notes, history

**Files:**
- Modify: `portfolio-analyzer/scripts/daily_pl_report.py` (`build_payload`: tickers, series, headline, attribution, daily, notes, payload; new helper `attribution_of`)
- Test: `portfolio-analyzer/tests/test_daily_pl_report.py`

**Interfaces:**
- Produces payload keys: `headline.pnl_window / pnl_incept / realized_cum / dividends_net / max_dd_window / max_dd_window_jpy / xirr / xirr_scope`; `series.nav / pnl / deposits / daily_pnl` (totals, `null` allowed) and `series.accounts = {account_id: {"nav": [...], "pnl": [...]}}`; `attribution = {"window": {...}, "incept": {...}, "accounts": {account_id: {"window": {...}, "incept": {...}}}}` with keys `unrealized, realized, dividends, fees, fx_translation, forex, total`.
- Helper: `attribution_of(series: ts.AccountSeries, wi: int) -> dict[str, dict[str, float | None]]`.

- [ ] **Step 1: Failing test** (append to `tests/test_daily_pl_report.py`)

```python
def test_attribution_of_buckets_the_window_and_inception() -> None:
    from portfolio_analyzer import timeseries as ts

    s = ts.AccountSeries(
        account_id="a",
        nav=[None, Decimal(110), Decimal(130)],
        deposits_cum=[None, Decimal(100), Decimal(100)],
        unrealized=[None, Decimal(6), Decimal(20)],
        realized_cum=[None, Decimal(1), Decimal(4)],
        dividends_cum=[None, Decimal(3), Decimal(6)],
        fees_cum=[None, Decimal(0), Decimal(0)],
        fx_translation_cum=[None, Decimal(0), Decimal(0)],
        forex_cum=[None, Decimal(0), Decimal(0)],
    )
    out = daily_pl_report.attribution_of(s, wi=1)
    assert out["window"] == {"unrealized": 14.0, "realized": 3.0, "dividends": 3.0, "fees": 0.0, "fx_translation": 0.0, "forex": 0.0, "total": 20.0}
    assert out["incept"]["total"] == 30.0 and out["incept"]["unrealized"] == 20.0
    # a window that starts before the series is defined measures from its first defined date
    assert daily_pl_report.attribution_of(s, wi=0)["window"]["total"] == 20.0
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** in `daily_pl_report.py`:

Add the helper (module level, near `_downsample`):

```python
def attribution_of(series: ts.AccountSeries, wi: int) -> dict[str, dict[str, float | None]]:
    """Each P&L bucket over the window (from its first defined date on or after ``wi``) and since inception."""
    keys = {
        "unrealized": series.unrealized,
        "realized": series.realized_cum,
        "dividends": series.dividends_cum,
        "fees": series.fees_cum,
        "fx_translation": series.fx_translation_cum,
        "forex": series.forex_cum,
        "total": series.pnl,
    }
    start = ts.first_defined(series.pnl[wi:])
    i0 = None if start is None else wi + start

    def bucket(values, i0_):
        a, b = values[i0_], values[-1]
        return None if a is None or b is None else float(b - a)

    return {
        "window": {k: (None if i0 is None else bucket(v, i0)) for k, v in keys.items()},
        "incept": {k: (None if v[-1] is None else float(v[-1])) for k, v in keys.items()},
    }
```

In `build_payload`:

1. Tickers: after `ledger_symbols`, add the domestic symbols so closed ones are priced while they were held:
```python
    jp_tickers = {mtm.market_symbol(s, "JPY") for s in {t.symbol for t in jp_rows if t.symbol}}
    tickers = sorted((set(open_tickers) | set(ledger_symbols) | jp_tickers) - {dc_ticker, None})
```
2. After `values = ts.value_paths(...)` build the account series:
```python
    cash = ibkr.summarize_cash(transactions) if transactions else None
    account_series = [
        ts.from_ledger(ledger_account, paths, values, cash.deposit_flows if cash else [])
    ]
    if jp_rows:
        jp_prices = {
            s: price_path.get(mtm.market_symbol(s, "JPY"), [None] * n_all)
            for s in {t.symbol for t in jp_rows if t.symbol}
        }
        account_series.append(jpbroker.account_paths(jp_rows, dates, jp_prices, args.jp_account))
    if dc_ledger:
        account_series.append(
            dcplan.account_paths(dc_holding, dc_trades, dates, price_path[dc_ticker])
        )
    total = ts.combine(account_series)
```
(`n_all = len(dates)`; compute before use. Remove the later duplicate `cash = ...` line.)
3. Headline: replace the IBKR-only figures:
```python
    pnl = total.pnl
    start = ts.first_defined(pnl[wi:])
    i0 = None if start is None else wi + start
    pnl_window = None if i0 is None or pnl[-1] is None else pnl[-1] - pnl[i0]
    xirr_series = [s for s in account_series if s.xirr_flows]
    xirr = None
    if xirr_series and all(s.nav[-1] is not None for s in xirr_series):
        flows = [(d, -a) for s in xirr_series for d, a in s.xirr_flows] + [
            (as_of, sum((s.nav[-1] for s in xirr_series), ZERO))
        ]
        xirr = ibkr.money_weighted_return(flows)
    xirr_scope = "・".join(account_names.get(s.account_id, s.account_id) for s in xirr_series)
    peak, dd_jpy, dd_pct = None, ZERO, None
    for i in range(wi, n):
        v, nav_i = pnl[i], total.nav[i]
        if v is None or nav_i is None:
            continue
        if peak is None or v > peak[0]:
            peak = (v, nav_i)
        if peak[1] and v - peak[0] < dd_jpy:
            dd_jpy, dd_pct = v - peak[0], (v - peak[0]) / peak[1]
```
and in the dict: `"pnl_window": _f(pnl_window)`, `"pnl_incept": _f(pnl[-1])`, `"realized_cum": _f(total.realized_cum[-1])`, `"dividends_net": _f(total.dividends_cum[-1])`, `"xirr": _f(xirr)`, `"xirr_scope": xirr_scope`.
4. Attribution: replace the `unreal_total` / `bucket` block with
```python
    attribution = attribution_of(total, wi)
    attribution["accounts"] = {s.account_id: attribution_of(s, wi) for s in account_series}
```
5. Daily: `daily = [_f(v) for v in ts.daily_changes(pnl)[wi:]]`.
6. Series payload: `"nav": window(total.nav)`, `"pnl": window(pnl)`, `"deposits": window(total.deposits_cum)`, plus `"accounts": {s.account_id: {"nav": window(s.nav), "pnl": window(s.pnl)} for s in account_series}`.
7. Notes: change the sentence starting "海外証券口座の NAV・損益は取引履歴を日次で再生した値で" to "NAV・累計損益は 3 口座の合計（NAV − 累計入金）。海外は取引履歴、国内は取引 CSV（手数料は取得原価に含む）、DC は掛金履歴（{first DC date} から。それ以前の掛金は拠出金累計に含む）を日次で再生した値で、" keeping the tail about the CSV's last day. Get the DC first date from `dc_trades[0].trade_date` when present.
8. History record: after `total` exists, `record["total_pnl_incept_jpy"] = _f(pnl[-1])` and `record["deposits_cum_jpy"] = _f(total.deposits_cum[-1])`.

Keep `_f` returning `None` for `None` (it already does). `window()` already maps through `_f`.

- [ ] **Step 4: Run** the unit test, then a real run `uv run --no-sync python portfolio-analyzer/scripts/daily_pl_report.py --edition tokyo` from `/home/kazumasa/projects` and check the printed totals: `inception` must now be roughly 海外 P&L + 国内 (≈ +5.0M) + DC (≈ +2.3M).
- [ ] **Step 5: Commit** — `feat(portfolio-analyzer): NAV, cumulative and daily P&L across all three accounts`

### Task 5: rendering the totals (dashboard + mail) and updating the tests

**Files:**
- Modify: `portfolio-analyzer/src/portfolio_analyzer/dashboard.py` (`_attribution`, captions, KPI subs), `portfolio-analyzer/src/portfolio_analyzer/mailer.py` (`_attribution`, `_charts` captions, KPI subs, `text_body`)
- Test: `portfolio-analyzer/tests/test_dashboard.py`, `portfolio-analyzer/tests/test_mailer.py`

- [ ] **Step 1: Failing tests**

test_dashboard.py — extend `sample()`'s attribution with `"accounts": {"global_broker": {"window": {...same keys..., "total": -135387}, "incept": {..., "total": 405724}}}` and `"xirr_scope": "海外証券口座・国内証券口座"` in headline; add:
```python
def test_render_labels_the_series_as_all_accounts_and_lists_each_account_s_attribution() -> None:
    html = dashboard.render(sample(), ":root{--ink:#000}")
    assert "全口座 NAV と損益" in html and "海外証券口座 NAV と損益" not in html
    assert "日次損益 <small>全口座" in html
    assert "海外証券口座</td>" in html.split("損益の内訳")[0] or "口座別" in html
    assert "海外証券口座・国内証券口座" in html  # the xirr scope
    assert "<td>海外証券口座</td><td class='n dn'>−135,387</td><td class='n up'>+405,724</td>" in html
```
test_mailer.py — extend `payload()` similarly (`attribution.accounts` for `"gb"` using the account name `海外証券口座`; account names come from `data["accounts"]` by id) and add:
```python
def test_html_body_shows_the_totals_across_accounts_with_a_row_per_account() -> None:
    body = mailer.html_body(payload())
    assert "全口座" in body and "海外証券口座 · 2025-09-11 → 2026-09-11" not in body
    assert "資金加重リターン" in body and "海外証券口座・国内証券口座" in body
    assert "海外証券口座" in body.split("損益の内訳")[1].split("保有")[0]
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement**
  - dashboard `_attribution(att, names)`: after the total row append one row per `att.get("accounts", {})` item: `<tr><td>{name}</td><td class='n {cls(w)}'>{jpy(w, True)}</td><td class='n {cls(i)}'>{jpy(i, True)}</td></tr>` using each account's `window.total` / `incept.total`; `names` = `{a["id"]: a["name"] for a in data["accounts"]}`; heading `<th>内訳</th>` unchanged, sub-heading 「合計＝NAV−入金」 row keeps `tr.tot`.
  - dashboard captions: `海外証券口座 NAV と損益` → `全口座 NAV と損益 <small>3 口座の合計 · 入金は段差、損益 ＝ NAV − 累計入金</small>`, `日次損益 <small>海外証券口座 · …` → `全口座 · 入金を除いた NAV の日次変化`, KPI `期間損益` sub `海外証券口座 {start} 以降・入金控除後` → `全口座 {start} 以降・入金控除後`, KPI `資金加重リターン` sub → `f"{h.get('xirr_scope') or '—'} · 最大DD（期間内） …"`.
  - mailer: same wording changes in `_charts` (`"海外証券口座 · …"` → `"全口座 · …"`), the KPI subs, `_attribution(att, table_style, names)` gains the per-account rows, section sub `"海外証券口座"` → `"全口座 · 下段は口座別"`; `text_body`: `期間損益 … (海外証券口座・入金控除後)` → `(全口座・入金控除後)`.
- [ ] **Step 4: Run** the two test files → PASS; then `uv run --no-sync pytest portfolio-analyzer/tests -q` → all green.
- [ ] **Step 5: Commit** — `feat(portfolio-analyzer): show the all-account totals in the report and mail`

---

## Part B — daily risk monitor

### Task 6: reference data — countries, mixes, limits, episodes

**Files:**
- Modify (private, gitignored): `portfolio-analyzer/data/analysis_reference.private.json` via a one-off script run from `/home/kazumasa/projects/portfolio-analyzer`
- Verify: a Python assertion run, no repo test (the file is private)

- [ ] **Step 1: Run the edit script**

```python
import json
from pathlib import Path

p = Path("data/analysis_reference.private.json")
ref = json.loads(p.read_text(encoding="utf-8"))
JP = "日本"; US = "米国"
COUNTRY = {
    "ASML": "オランダ", "Taiwan Semiconductor Manufacturing": "台湾",
    **{n: JP for n in ("Advantest", "Daiwa Office Investment", "Fanuc", "Fast Retailing", "Hitachi", "Ibiden", "KDDI", "Kioxia Holdings", "Mitsubishi Corporation", "Mitsubishi UFJ Financial Group", "Mizuho Financial Group", "Pan Pacific International Holdings", "Recruit Holdings", "SoftBank Group", "Sony Group", "Sumitomo Mitsui Financial Group", "TDK", "Tokyo Electron", "Toyota Motor")},
}
DEFAULT_COUNTRY = {"SMH": US, "QQQ": US, "XLE": US, "1329": JP, "1475": JP, "2561": JP, "6857": JP, "7532": JP, "8976": JP}
for inst in ref["instruments"]:
    for e in inst["exposures"]:
        if e["group"] == "issuer":
            e["country"] = COUNTRY.get(e["category"], US)
    if inst["symbol"] in DEFAULT_COUNTRY:
        inst["country_default"] = DEFAULT_COUNTRY[inst["symbol"]]
    if inst["symbol"] == "HAPPY_AGING_40":
        inst["asset_mix"] = {"日本株": 0.3124, "海外株": 0.1895, "日本債券": 0.3283, "外国債券": 0.1498, "現金等": 0.0200}
        inst["currency_mix"] = {"JPY": 0.6607, "USD": 0.1652, "その他外貨": 0.1741}
        inst["country_mix"] = {"日本": 0.6607, "米国": 0.1652, "欧州": 0.0879, "新興国": 0.0498, "その他先進国": 0.0364}
        inst["mix_note"] = "2026-08-31 月次レポートの構成比（国内債券32.83・大型バリュー15.64・小型15.60・外国債券(ヘッジなし)14.98・TCW外国株式13.97・MSCI Emerging4.98・コール等2.00）。国・通貨は外国株式を米70/欧20/他10、外国債券を米45/欧40/他15 で按分した推定"
ref["policy"]["limits"] += [
    {"id": "foreign_currency_max", "label": "外貨エクスポージャーは総資産の40%以下", "metric": "foreign_currency_ratio", "operator": "<=", "threshold": 0.4, "note": "暫定値。ルックスルー後（DC の外貨部分を含む）"},
    {"id": "foreign_country_max", "label": "海外の単一国は総資産の30%以下", "metric": "largest_foreign_country_ratio", "operator": "<=", "threshold": 0.3, "note": "暫定値。ルックスルー後"},
    {"id": "lookthrough_issuer_max", "label": "ルックスルー後の単一銘柄は総資産の15%以下", "metric": "largest_issuer_lookthrough_ratio", "operator": "<=", "threshold": 0.15, "note": "暫定値。直接保有と ETF 経由の合算"},
]
ref["episodes"] = [
    {"id": "yen_carry_unwind_2024", "label": "2024-08 円キャリー巻き戻し", "start": "2024-07-31", "end": "2024-08-05"},
    {"id": "ai_capex_digestion_2024", "label": "2024 AI capex 消化局面", "start": "2024-07-10", "end": "2024-10-31"},
    {"id": "tariff_shock_2025", "label": "2025-04 関税ショック", "start": "2025-04-02", "end": "2025-04-08"},
]
p.write_text(json.dumps(ref, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
```

- [ ] **Step 2: Verify** — `python3 -c "import json;d=json.load(open('data/analysis_reference.private.json'));assert all('country' in e for i in d['instruments'] for e in i['exposures'] if e['group']=='issuer');assert len(d['policy']['limits'])==9 and len(d['episodes'])==3;print('ok')"`
- [ ] **Step 3:** nothing to commit (private data). Note the edit in the final report.

### Task 7: `risk.py` — holdings, look-through, concentration

**Files:**
- Create: `portfolio-analyzer/src/portfolio_analyzer/risk.py`
- Test: `portfolio-analyzer/tests/test_risk.py`

**Interfaces:**
- `Holding(symbol, account_id, value_jpy: float, currency, asset_class, ticker=None)` with `.is_cash`
- `lookthrough(holdings, reference) -> dict` with keys `total, asset_class, currency, country, sector, issuers, coverage, mix` (`mix[symbol] = {"currency": {...}, "country": {...}, "sector": {...}}` as fractions, used later to allocate risk contributions)
- `concentration(holdings, exposures) -> dict` with `largest_position_ratio, top5_ratio, effective_positions, effective_sectors, effective_currencies, effective_countries, max_sector_ratio, max_sector, largest_issuer_lookthrough_ratio, largest_issuer, foreign_currency_ratio, largest_foreign_country_ratio, largest_foreign_country, cash_ratio`
- Constants: `HOME_CURRENCY="JPY"`, `HOME_COUNTRY="日本"`, `CASH_CLASS="現金"`, `NON_EQUITY_SECTOR="債券・現金等"`, `UNMAPPED_SECTOR="その他・未分類株式"`

- [ ] **Step 1: Failing tests** (`tests/test_risk.py`)

```python
"""Offline tests for the daily risk monitor."""

from __future__ import annotations

import math

import pytest

from portfolio_analyzer import risk

REFERENCE = {
    "instruments": [
        {
            "symbol": "SMH",
            "country_default": "米国",
            "factor_loadings": {"株式全体": 1.9, "海外株": 1, "情報技術": 1.0, "外貨対円": 1},
            "exposures": [
                {"group": "sector", "category": "情報技術", "weight": 1.0},
                {"group": "issuer", "category": "Nvidia", "weight": 0.2, "country": "米国"},
                {"group": "issuer", "category": "Taiwan Semiconductor Manufacturing", "weight": 0.1, "country": "台湾"},
            ],
        },
        {
            "symbol": "1329",
            "country_default": "日本",
            "factor_loadings": {"株式全体": 1.0, "日本株": 1, "情報技術": 0.35},
            "exposures": [
                {"group": "sector", "category": "情報技術", "weight": 0.35},
                {"group": "sector", "category": "その他・未分類株式", "weight": 0.65},
                {"group": "issuer", "category": "Advantest", "weight": 0.12, "country": "日本"},
            ],
        },
        {
            "symbol": "6857",
            "country_default": "日本",
            "factor_loadings": {"株式全体": 1.5, "日本株": 1, "情報技術": 1.0},
            "exposures": [
                {"group": "sector", "category": "情報技術", "weight": 1.0},
                {"group": "issuer", "category": "Advantest", "weight": 1.0, "country": "日本"},
            ],
        },
        {
            "symbol": "FUND",
            "asset_mix": {"日本株": 0.3, "海外株": 0.2, "日本債券": 0.5},
            "currency_mix": {"JPY": 0.8, "USD": 0.2},
            "country_mix": {"日本": 0.8, "米国": 0.2},
            "factor_loadings": {"株式全体": 0.5, "日本金利": -2.0, "外貨対円": 0.2},
            "exposures": [
                {"group": "sector", "category": "情報技術", "weight": 0.1},
                {"group": "sector", "category": "その他・未分類株式", "weight": 0.4},
                {"group": "asset", "category": "日本債券", "weight": 0.5},
            ],
        },
    ],
    "scenarios": [
        {"id": "global_equity_down_10", "label": "株式全体 -10%", "shocks": {"株式全体": -0.1}},
        {"id": "compound_x", "label": "複合", "kind": "compound", "shocks": {"株式全体": -0.1, "外貨対円": -0.1}},
    ],
    "policy": {"limits": [
        {"id": "single_position_max", "label": "単一10%", "metric": "largest_position_ratio", "operator": "<=", "threshold": 0.1},
        {"id": "cash_min", "label": "現金15%", "metric": "cash_ratio", "operator": ">=", "threshold": 0.15},
        {"id": "na_metric", "label": "無い指標", "metric": "does_not_exist", "operator": "<=", "threshold": 1},
    ]},
    "episodes": [{"id": "ep", "label": "局面", "start": "2026-01-03", "end": "2026-01-05"}],
}


def holdings():
    return [
        risk.Holding("SMH", "gb", 600.0, "USD", "米国株", "SMH"),
        risk.Holding("1329", "sec", 200.0, "JPY", "日本株", "1329.T"),
        risk.Holding("6857", "sec", 100.0, "JPY", "日本株", "6857.T"),
        risk.Holding("FUND", "dc", 100.0, "JPY", "バランス型", "F:1"),
        risk.Holding("CASH_JPY", "sec", 1000.0, "JPY", "現金"),
    ]


def _value(rows, label):
    return next(r["value"] for r in rows if r["label"] == label)


def test_lookthrough_sums_back_to_the_total_in_every_dimension() -> None:
    x = risk.lookthrough(holdings(), REFERENCE)
    assert x["total"] == 2000.0
    for key in ("asset_class", "currency", "country", "sector"):
        assert math.isclose(sum(r["value"] for r in x[key]), 2000.0), key


def test_lookthrough_currency_and_country_use_the_mixes_and_the_issuers() -> None:
    x = risk.lookthrough(holdings(), REFERENCE)
    assert _value(x["currency"], "USD") == 600.0 + 20.0  # SMH plus the fund's dollar part
    assert _value(x["currency"], "JPY") == 2000.0 - 620.0
    assert _value(x["country"], "台湾") == 60.0  # TSMC through SMH
    assert _value(x["country"], "米国") == 600.0 * 0.9 + 20.0  # the rest of SMH plus the fund
    assert _value(x["country"], "日本") == 200.0 + 100.0 + 80.0 + 1000.0


def test_lookthrough_sector_puts_bonds_and_cash_in_their_own_bucket() -> None:
    x = risk.lookthrough(holdings(), REFERENCE)
    assert _value(x["sector"], risk.NON_EQUITY_SECTOR) == 1000.0 + 50.0
    assert _value(x["sector"], "情報技術") == 600.0 + 70.0 + 100.0 + 10.0


def test_lookthrough_asset_class_uses_the_fund_s_mix_and_the_snapshot_class_otherwise() -> None:
    x = risk.lookthrough(holdings(), REFERENCE)
    assert _value(x["asset_class"], "日本債券") == 50.0
    assert _value(x["asset_class"], "日本株") == 300.0 + 30.0
    assert _value(x["asset_class"], "現金") == 1000.0


def test_lookthrough_merges_an_issuer_held_directly_and_through_a_fund() -> None:
    x = risk.lookthrough(holdings(), REFERENCE)
    adv = next(r for r in x["issuers"] if r["label"] == "Advantest")
    assert adv["value"] == 100.0 + 24.0 and adv["via"] == ["6857", "1329"]
    assert x["issuers"][0]["label"] == "Advantest"  # the largest look-through name
    assert x["mix"]["SMH"]["country"] == {"米国": 0.9, "台湾": 0.1}


def test_concentration_metrics() -> None:
    x = risk.lookthrough(holdings(), REFERENCE)
    c = risk.concentration(holdings(), x)
    assert c["largest_position_ratio"] == 0.3 and c["top5_ratio"] == 0.5
    assert c["cash_ratio"] == 0.5
    assert math.isclose(c["foreign_currency_ratio"], 620.0 / 2000.0)
    assert c["largest_foreign_country"] == "米国" and math.isclose(c["largest_foreign_country_ratio"], 560.0 / 2000.0)
    assert c["largest_issuer"] == "Advantest" and math.isclose(c["largest_issuer_lookthrough_ratio"], 124.0 / 2000.0)
    assert c["max_sector"] == "情報技術" and math.isclose(c["max_sector_ratio"], 780.0 / 2000.0)
    # effective sectors: 1 / HHI over the equity sectors only
    tech, other = 780.0, 150.0 + 20.0
    equity = tech + other
    assert math.isclose(c["effective_sectors"], 1 / ((tech / equity) ** 2 + (other / equity) ** 2))
```

- [ ] **Step 2: Run** → FAIL (`ModuleNotFoundError`).
- [ ] **Step 3: Implement `risk.py`** (first half)

```python
"""Daily risk monitor: what the book is exposed to, how much it moves, what would hurt.

Exposures look through funds with the analysis reference — each instrument's
sector, issuer and asset rows, the country of each issuer, and an asset /
currency / country mix for a balanced fund. Statistics come from the daily JPY
returns of the holdings at today's weights: annualised volatility, historical-
simulation VaR and expected shortfall, single-regression betas, and each
holding's share of the portfolio variance (w_i (Σw)_i / wᵀΣw), allocated to
currency, sector and country with the same look-through weights. Stress comes
two ways: the reference's factor scenarios (Σ value × loading × shock, as the
main dashboard computes them) and past episodes replayed with the actual
returns of what is held now.

Float arithmetic on already-computed values; nothing here reads the network.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

HOME_CURRENCY = "JPY"
HOME_COUNTRY = "日本"
CASH_CLASS = "現金"
NON_EQUITY_SECTOR = "債券・現金等"
UNMAPPED_SECTOR = "その他・未分類株式"
TRADING_DAYS = 252
COUNTRY_BY_CURRENCY = {"JPY": HOME_COUNTRY, "USD": "米国"}


@dataclass(frozen=True)
class Holding:
    symbol: str
    account_id: str
    value_jpy: float
    currency: str
    asset_class: str
    ticker: str | None = None

    @property
    def is_cash(self) -> bool:
        return self.asset_class == CASH_CLASS


def _instruments(reference: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(i["symbol"]): i for i in reference.get("instruments", [])}


def _rows(instrument: dict[str, Any], group: str) -> list[dict[str, Any]]:
    return [e for e in instrument.get("exposures", []) if e.get("group") == group]


def _bump(bucket: dict[str, float], key: str, value: float) -> None:
    if value:
        bucket[key] = bucket.get(key, 0.0) + value


def _mixes(holding: Holding, instrument: dict[str, Any]) -> dict[str, dict[str, float]]:
    """The holding's currency / country / sector split as fractions summing to 1."""
    currency = {str(k): float(v) for k, v in (instrument.get("currency_mix") or {holding.currency: 1.0}).items()}
    if instrument.get("country_mix"):
        country = {str(k): float(v) for k, v in instrument["country_mix"].items()}
    else:
        default = str(
            instrument.get("country_default") or COUNTRY_BY_CURRENCY.get(holding.currency, "その他")
        )
        country: dict[str, float] = {}
        covered = 0.0
        for e in _rows(instrument, "issuer"):
            w = float(e["weight"])
            covered += w
            _bump(country, str(e.get("country") or default), w)
        _bump(country, default, max(1.0 - covered, 0.0))
    sector: dict[str, float] = {}
    if holding.is_cash:
        sector[NON_EQUITY_SECTOR] = 1.0
    else:
        covered = 0.0
        for e in _rows(instrument, "sector"):
            w = float(e["weight"])
            covered += w
            _bump(sector, str(e["category"]), w)
        non_equity = min(sum(float(e["weight"]) for e in _rows(instrument, "asset")), 1.0)
        rest = max(1.0 - covered, 0.0)
        _bump(sector, NON_EQUITY_SECTOR, min(rest, non_equity))
        _bump(sector, UNMAPPED_SECTOR, max(rest - non_equity, 0.0))
    return {"currency": currency, "country": country, "sector": sector}


def lookthrough(holdings: Sequence[Holding], reference: dict[str, Any]) -> dict[str, Any]:
    """Value by asset class, currency, country, sector and issuer after looking through funds."""
    instruments = _instruments(reference)
    by: dict[str, dict[str, float]] = {k: {} for k in ("asset_class", "currency", "country", "sector")}
    issuers: dict[str, dict[str, Any]] = {}
    mix: dict[str, dict[str, dict[str, float]]] = {}
    equity_value = mapped_value = 0.0
    total = sum(float(h.value_jpy) for h in holdings)
    for h in holdings:
        v = float(h.value_jpy)
        inst = instruments.get(h.symbol, {})
        m = _mixes(h, inst)
        mix.setdefault(h.symbol, m)
        for key in ("currency", "country", "sector"):
            for label, w in m[key].items():
                _bump(by[key], label, v * w)
        asset_mix = inst.get("asset_mix")
        if asset_mix:
            for label, w in asset_mix.items():
                _bump(by["asset_class"], str(label), v * float(w))
        else:
            _bump(by["asset_class"], h.asset_class, v)
        if not h.is_cash:
            equity_value += v * (1.0 - m["sector"].get(NON_EQUITY_SECTOR, 0.0))
        for e in _rows(inst, "issuer"):
            name, w = str(e["category"]), float(e["weight"])
            row = issuers.setdefault(name, {"label": name, "value": 0.0, "country": e.get("country"), "via": {}})
            row["value"] += v * w
            row["via"][h.symbol] = row["via"].get(h.symbol, 0.0) + v * w
            mapped_value += v * w

    def table(bucket: dict[str, float]) -> list[dict[str, Any]]:
        return [
            {"label": k, "value": val, "pct": (val / total if total else None)}
            for k, val in sorted(bucket.items(), key=lambda kv: -kv[1])
        ]

    issuer_rows = sorted(
        (
            {
                "label": r["label"],
                "value": r["value"],
                "pct": (r["value"] / total if total else None),
                "country": r["country"],
                "via": sorted(r["via"], key=lambda s: -r["via"][s]),
            }
            for r in issuers.values()
        ),
        key=lambda r: -r["value"],
    )
    return {
        "total": total,
        **{k: table(b) for k, b in by.items()},
        "issuers": issuer_rows,
        "coverage": {"issuer": (mapped_value / equity_value if equity_value else None)},
        "mix": mix,
    }


def _hhi(values: Sequence[float]) -> float:
    s = sum(values)
    return sum((v / s) ** 2 for v in values) if s else 0.0


def concentration(holdings: Sequence[Holding], exposures: dict[str, Any]) -> dict[str, Any]:
    """Concentration figures as ratios of total assets (sector effective count over the equity part)."""
    total = float(exposures["total"])
    invested = sorted((float(h.value_jpy) for h in holdings if not h.is_cash), reverse=True)
    sectors = [r for r in exposures["sector"] if r["label"] != NON_EQUITY_SECTOR]
    foreign = [r for r in exposures["country"] if r["label"] != HOME_COUNTRY]
    jpy = next((r["value"] for r in exposures["currency"] if r["label"] == HOME_CURRENCY), 0.0)
    issuers = exposures["issuers"]
    cash = sum(float(h.value_jpy) for h in holdings if h.is_cash)

    def effective(rows: list[dict[str, Any]]) -> float | None:
        h = _hhi([r["value"] for r in rows])
        return 1.0 / h if h else None

    ratio = (lambda v: v / total) if total else (lambda v: None)
    return {
        "largest_position_ratio": ratio(invested[0]) if invested else None,
        "top5_ratio": ratio(sum(invested[:5])) if invested else None,
        "effective_positions": (1.0 / _hhi(invested)) if invested else None,
        "effective_sectors": effective(sectors),
        "effective_currencies": effective(exposures["currency"]),
        "effective_countries": effective(exposures["country"]),
        "max_sector_ratio": ratio(sectors[0]["value"]) if sectors else None,
        "max_sector": sectors[0]["label"] if sectors else None,
        "largest_issuer_lookthrough_ratio": ratio(issuers[0]["value"]) if issuers else None,
        "largest_issuer": issuers[0]["label"] if issuers else None,
        "foreign_currency_ratio": (1.0 - jpy / total) if total else None,
        "largest_foreign_country_ratio": ratio(foreign[0]["value"]) if foreign else 0.0,
        "largest_foreign_country": foreign[0]["label"] if foreign else None,
        "cash_ratio": ratio(cash),
    }
```

- [ ] **Step 4: Run** `uv run --no-sync pytest portfolio-analyzer/tests/test_risk.py -q` → PASS.
- [ ] **Step 5: Commit** — `feat(portfolio-analyzer): look-through exposures and concentration for the daily risk monitor`

### Task 8: `risk.py` — statistics, contributions, scenarios, episodes, limits, `assemble`

**Files:**
- Modify: `portfolio-analyzer/src/portfolio_analyzer/risk.py` (append)
- Test: `portfolio-analyzer/tests/test_risk.py` (append)

**Interfaces:**
- `portfolio_returns(weights: dict[str, float], returns: dict[str, list[float]]) -> list[float]`
- `volatility(rs) -> float | None`, `value_at_risk(rs, level) -> float | None`, `expected_shortfall(rs, level) -> float | None`, `beta(rs, bench) -> float | None`, `quantile(sorted_values, q) -> float`
- `risk_contributions(weights, returns) -> dict[str, float]` (shares summing to 1)
- `scenario_impacts(holdings, reference) -> list[dict]` (`id, label, kind, impact_jpy, impact_pct`, ascending impact)
- `episode_impacts(values_by_ticker, episodes, dates, prices_jpy) -> list[dict]` (`id, label, start, end, impact_jpy, impact_pct, coverage`)
- `evaluate_limits(limits, metrics) -> list[dict]` (`id, label, metric, operator, threshold, value, status, note`)
- `assemble(holdings, reference, returns, benchmarks, dates, prices_jpy, as_of, previous=None) -> dict` — the payload block (shape in Step 3)

- [ ] **Step 1: Failing tests** (append)

```python
def test_portfolio_returns_weight_each_day_and_skip_tickers_without_returns() -> None:
    rs = risk.portfolio_returns({"A": 0.5, "B": 0.25, "CASH": 0.25}, {"A": [0.02, -0.01], "B": [0.0, 0.04]})
    assert rs == pytest.approx([0.01, 0.005])


def test_volatility_var_and_es_on_a_known_sample() -> None:
    rs = [0.01, -0.02, 0.015, -0.03, 0.005, 0.0, -0.01, 0.02, -0.005, 0.025]
    assert risk.volatility(rs) == pytest.approx(math.sqrt(252) * 0.017638, rel=1e-3)
    assert risk.quantile(sorted(rs), 0.5) == pytest.approx(0.0025)
    # the worst tenth of these days: between the worst two, interpolated
    assert risk.value_at_risk(rs, 0.95) == pytest.approx(0.0255, rel=1e-3)
    assert risk.expected_shortfall(rs, 0.90) == pytest.approx(0.025, rel=1e-3)
    assert risk.volatility([0.01]) is None and risk.value_at_risk([], 0.95) is None


def test_beta_recovers_a_known_slope() -> None:
    bench = [0.01, -0.02, 0.03, 0.0, -0.01]
    port = [2 * b + 0.001 for b in bench]
    assert risk.beta(port, bench) == pytest.approx(2.0)
    assert risk.beta(port, [0.0] * 5) is None


def test_risk_contributions_sum_to_one_and_follow_the_covariance() -> None:
    returns = {"A": [0.01, -0.01, 0.02, -0.02], "B": [0.01, -0.01, 0.02, -0.02], "C": [0.0, 0.0, 0.0, 0.0]}
    rc = risk.risk_contributions({"A": 0.5, "B": 0.25, "C": 0.25}, returns)
    assert sum(rc.values()) == pytest.approx(1.0)
    assert rc["A"] == pytest.approx(2 / 3) and rc["B"] == pytest.approx(1 / 3) and rc["C"] == 0.0


def test_scenario_impacts_apply_the_factor_loadings() -> None:
    out = risk.scenario_impacts(holdings(), REFERENCE)
    by_id = {r["id"]: r for r in out}
    # 株式全体 −10%: SMH 600×1.9 + 1329 200×1.0 + 6857 100×1.5 + FUND 100×0.5 = 1540 → −154
    assert by_id["global_equity_down_10"]["impact_jpy"] == pytest.approx(-154.0)
    assert by_id["global_equity_down_10"]["impact_pct"] == pytest.approx(-154.0 / 2000.0)
    assert by_id["compound_x"]["kind"] == "compound"
    assert by_id["compound_x"]["impact_jpy"] == pytest.approx(-154.0 - 0.1 * (600 * 1 + 100 * 0.2))
    assert out[0]["impact_jpy"] <= out[-1]["impact_jpy"]


def test_episode_impacts_replay_the_move_from_the_close_before_the_start() -> None:
    dates = ["2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05", "2026-01-06"]
    prices = {"SMH": [100.0, 90.0, 85.0, 80.0, 95.0], "1329.T": [10.0, 10.0, 9.0, 9.5, 9.0], "F:1": [None] * 5}
    out = risk.episode_impacts({"SMH": 600.0, "1329.T": 200.0, "F:1": 100.0}, REFERENCE["episodes"], dates, prices)
    (ep,) = out
    assert ep["impact_jpy"] == pytest.approx(600.0 * (80 / 100 - 1) + 200.0 * (9.5 / 10 - 1))
    assert ep["coverage"] == pytest.approx(800.0 / 900.0)
    # an episode the history does not reach is left out
    assert risk.episode_impacts({"SMH": 1.0}, [{"id": "old", "label": "x", "start": "2025-01-01", "end": "2025-01-05"}], dates, prices) == []


def test_evaluate_limits_reports_ok_breach_and_na() -> None:
    rows = risk.evaluate_limits(REFERENCE["policy"]["limits"], {"largest_position_ratio": 0.3, "cash_ratio": 0.5})
    status = {r["id"]: r["status"] for r in rows}
    assert status == {"single_position_max": "breach", "cash_min": "ok", "na_metric": "na"}
    assert rows[0]["value"] == 0.3 and rows[0]["threshold"] == 0.1


def test_assemble_builds_the_payload_block() -> None:
    dates = [f"2026-01-{d:02d}" for d in range(1, 11)]
    returns = {"SMH": [0.01, -0.02, 0.015, -0.03, 0.005, 0.0, -0.01, 0.02, -0.005, 0.025], "1329.T": [0.0] * 10, "6857.T": [0.02, -0.01, 0.0, -0.02, 0.01, 0.0, 0.0, 0.01, -0.01, 0.0], "F:1": [0.0] * 10}
    bench = {"topix": [0.0] * 10, "sp500": [0.005, -0.01, 0.0075, -0.015, 0.0025, 0.0, -0.005, 0.01, -0.0025, 0.0125], "usdjpy": [0.0] * 10}
    prices = {t: [100.0] * 10 for t in returns}
    out = risk.assemble(holdings(), REFERENCE, returns, bench, dates, prices, "2026-01-10", previous={"vol_annual": 0.10})
    assert out["as_of"] == "2026-01-10" and out["total"] == 2000.0
    assert out["exposures"]["currency"][0]["label"] in ("JPY", "USD")
    assert out["stats"]["beta"]["sp500"] == pytest.approx(2.0 * 0.3, rel=1e-6)  # SMH is 30% of assets and moves 2× the index
    assert out["stats"]["vol_annual"] > 0 and out["stats"]["var_1d_95_jpy"] > 0
    assert out["stats"]["prev"]["vol_annual"] == 0.10
    assert sum(r["risk_share"] for r in out["contributions"]["positions"]) == pytest.approx(1.0)
    assert sum(r["risk_share"] for r in out["contributions"]["currency"]) == pytest.approx(1.0)
    assert {r["id"] for r in out["policy"]} == {"single_position_max", "cash_min", "na_metric"}
    assert out["policy_breaches"] == 1
    assert out["stress"]["scenarios"][0]["id"] in ("global_equity_down_10", "compound_x")
    assert out["history"]["vol_annual"] == out["stats"]["vol_annual"]
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** (append to `risk.py`)

```python
# ---- statistics on daily JPY returns at today's weights ----


def portfolio_returns(weights: dict[str, float], returns: dict[str, list[float]]) -> list[float]:
    """Σ w_i r_i per day. A ticker with no return series (cash) contributes nothing."""
    n = max((len(r) for t, r in returns.items() if t in weights), default=0)
    out = []
    for i in range(n):
        day = 0.0
        for t, w in weights.items():
            series = returns.get(t)
            if series is not None and i < len(series) and series[i] is not None:
                day += w * series[i]
        out.append(day)
    return out


def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs)


def _variance(xs: Sequence[float]) -> float:
    m = _mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def volatility(rs: Sequence[float]) -> float | None:
    """Annualised standard deviation of daily returns (√252)."""
    return math.sqrt(_variance(rs) * TRADING_DAYS) if len(rs) > 1 else None


def quantile(sorted_values: Sequence[float], q: float) -> float:
    """Linear-interpolated quantile of an ascending sequence (numpy's default)."""
    pos = (len(sorted_values) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


def value_at_risk(rs: Sequence[float], level: float) -> float | None:
    """Historical-simulation VaR as a positive loss fraction of assets."""
    if not rs:
        return None
    return max(-quantile(sorted(rs), 1.0 - level), 0.0)


def expected_shortfall(rs: Sequence[float], level: float) -> float | None:
    """Mean loss beyond the VaR quantile, as a positive fraction."""
    if not rs:
        return None
    ordered = sorted(rs)
    cut = quantile(ordered, 1.0 - level)
    tail = [x for x in ordered if x <= cut]
    return max(-_mean(tail), 0.0) if tail else None


def beta(rs: Sequence[float], bench: Sequence[float]) -> float | None:
    """Slope of the portfolio's daily return on the benchmark's (single regression)."""
    n = min(len(rs), len(bench))
    if n < 3:
        return None
    a, b = list(rs[-n:]), list(bench[-n:])
    ma, mb = _mean(a), _mean(b)
    var_b = sum((x - mb) ** 2 for x in b)
    if var_b == 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(a, b, strict=True)) / var_b


def risk_contributions(weights: dict[str, float], returns: dict[str, list[float]]) -> dict[str, float]:
    """Each ticker's share of the portfolio variance: w_i (Σw)_i / wᵀΣw. Sums to 1."""
    tickers = [t for t, w in weights.items() if t in returns and w]
    if not tickers:
        return {}
    n = min(len(returns[t]) for t in tickers)
    series = {t: [x if x is not None else 0.0 for x in returns[t][-n:]] for t in tickers}
    means = {t: _mean(series[t]) for t in tickers}

    def cov(a: str, b: str) -> float:
        return sum((x - means[a]) * (y - means[b]) for x, y in zip(series[a], series[b], strict=True)) / (n - 1)

    sigma_w = {a: sum(cov(a, b) * weights[b] for b in tickers) for a in tickers}
    var_p = sum(weights[a] * sigma_w[a] for a in tickers)
    if var_p <= 0:
        return dict.fromkeys(tickers, 0.0)
    return {a: weights[a] * sigma_w[a] / var_p for a in tickers}


# ---- stress ----


def scenario_impacts(holdings: Sequence[Holding], reference: dict[str, Any]) -> list[dict[str, Any]]:
    """Σ value × factor loading × shock for every scenario in the reference (worst first)."""
    instruments = _instruments(reference)
    total = sum(float(h.value_jpy) for h in holdings)
    out = []
    for sc in reference.get("scenarios", []):
        impact = 0.0
        for h in holdings:
            loadings = instruments.get(h.symbol, {}).get("factor_loadings", {})
            impact += float(h.value_jpy) * sum(
                float(loadings.get(f, 0.0)) * float(shock) for f, shock in sc.get("shocks", {}).items()
            )
        out.append(
            {
                "id": str(sc["id"]),
                "label": str(sc.get("label", sc["id"])),
                "kind": str(sc.get("kind", "hypothetical")),
                "impact_jpy": impact,
                "impact_pct": (impact / total if total else None),
            }
        )
    return sorted(out, key=lambda r: r["impact_jpy"])


def episode_impacts(
    values_by_ticker: dict[str, float],
    episodes: Sequence[dict[str, Any]],
    dates: Sequence[str],
    prices_jpy: dict[str, Sequence[float | None]],
) -> list[dict[str, Any]]:
    """Each episode's move replayed on today's holdings: last close before ``start`` → close at ``end``."""
    total = sum(values_by_ticker.values())
    out = []
    for ep in episodes:
        before = [i for i, d in enumerate(dates) if d < str(ep["start"])]
        upto = [i for i, d in enumerate(dates) if d <= str(ep["end"])]
        if not before or not upto or upto[-1] <= before[-1]:
            continue
        i0, i1 = before[-1], upto[-1]
        impact = covered = 0.0
        for t, v in values_by_ticker.items():
            series = prices_jpy.get(t)
            if not series or series[i0] in (None, 0) or series[i1] is None:
                continue
            impact += v * (float(series[i1]) / float(series[i0]) - 1.0)
            covered += v
        out.append(
            {
                "id": str(ep["id"]),
                "label": str(ep.get("label", ep["id"])),
                "start": str(ep["start"]),
                "end": str(ep["end"]),
                "impact_jpy": impact,
                "impact_pct": (impact / total if total else None),
                "coverage": (covered / total if total else None),
            }
        )
    return sorted(out, key=lambda r: r["impact_jpy"])


# ---- limits ----


def evaluate_limits(limits: Sequence[dict[str, Any]], metrics: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for limit in limits:
        value = metrics.get(str(limit["metric"]))
        op, threshold = str(limit["operator"]), float(limit["threshold"])
        if value is None or op not in ("<=", ">="):
            status = "na"
        elif op == "<=":
            status = "ok" if value <= threshold else "breach"
        else:
            status = "ok" if value >= threshold else "breach"
        out.append(
            {
                "id": str(limit["id"]),
                "label": str(limit.get("label", limit["id"])),
                "metric": str(limit["metric"]),
                "operator": op,
                "threshold": threshold,
                "value": value,
                "status": status,
                "note": str(limit.get("note", "")),
            }
        )
    return out


# ---- the payload block ----

HISTORY_KEYS = (
    "vol_annual",
    "var_1d_95",
    "es_1d_975",
    "foreign_currency_ratio",
    "largest_issuer_lookthrough_ratio",
    "max_sector_ratio",
    "beta_topix",
    "beta_sp500",
    "beta_usdjpy",
    "policy_breaches",
)


def assemble(
    holdings: Sequence[Holding],
    reference: dict[str, Any],
    returns: dict[str, list[float]],
    benchmarks: dict[str, list[float]],
    dates: Sequence[str],
    prices_jpy: dict[str, Sequence[float | None]],
    as_of: str,
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Everything the report shows, from today's holdings and the price history.

    ``returns`` / ``prices_jpy`` are per ticker, in JPY, aligned to ``dates``;
    ``benchmarks`` holds ``topix`` / ``sp500`` (local currency) and ``usdjpy``
    daily returns over the same window as ``returns``; ``previous`` is the
    ``history`` block of the last report, for day-over-day comparison.
    """
    exposures = lookthrough(holdings, reference)
    total = float(exposures["total"])
    conc = concentration(holdings, exposures)
    weights: dict[str, float] = {}
    values: dict[str, float] = {}
    symbol_of: dict[str, str] = {}
    for h in holdings:
        if h.ticker and not h.is_cash and total:
            weights[h.ticker] = weights.get(h.ticker, 0.0) + float(h.value_jpy) / total
            values[h.ticker] = values.get(h.ticker, 0.0) + float(h.value_jpy)
            symbol_of[h.ticker] = h.symbol
    port = portfolio_returns(weights, returns)
    var95, var99 = value_at_risk(port, 0.95), value_at_risk(port, 0.99)
    es = expected_shortfall(port, 0.975)
    worst_i = min(range(len(port)), key=lambda i: port[i]) if port else None
    offset = len(dates) - len(port)
    stats = {
        "window_days": len(port),
        "vol_annual": volatility(port),
        "var_1d_95": var95,
        "var_1d_99": var99,
        "es_1d_975": es,
        "var_20d_95": (None if var95 is None else var95 * math.sqrt(20)),
        "var_1d_95_jpy": (None if var95 is None else var95 * total),
        "var_1d_99_jpy": (None if var99 is None else var99 * total),
        "es_1d_975_jpy": (None if es is None else es * total),
        "var_20d_95_jpy": (None if var95 is None else var95 * math.sqrt(20) * total),
        "worst_day": (
            None
            if worst_i is None
            else {"date": dates[offset + worst_i] if 0 <= offset + worst_i < len(dates) else None, "pnl_jpy": port[worst_i] * total, "pct": port[worst_i]}
        ),
        "beta": {name: beta(port, series) for name, series in benchmarks.items()},
        "prev": previous or {},
    }
    shares = risk_contributions(weights, returns)
    standalone = {
        t: volatility([x if x is not None else 0.0 for x in returns[t][-len(port):]])
        for t in weights
        if t in returns and len(returns[t]) > 1
    }
    positions = sorted(
        (
            {
                "ticker": t,
                "sym": symbol_of[t],
                "weight": weights[t],
                "risk_share": shares.get(t, 0.0),
                "vol_annual": standalone.get(t),
            }
            for t in weights
        ),
        key=lambda r: -r["risk_share"],
    )
    buckets: dict[str, dict[str, float]] = {"currency": {}, "sector": {}, "country": {}}
    for t, share in shares.items():
        mixes = exposures["mix"].get(symbol_of[t], {})
        for key in buckets:
            for label, w in mixes.get(key, {}).items():
                _bump(buckets[key], label, share * w)
    contributions = {
        "positions": positions,
        **{
            key: [
                {"label": label, "risk_share": share, "weight": next((r["pct"] for r in exposures[key] if r["label"] == label), None)}
                for label, share in sorted(b.items(), key=lambda kv: -kv[1])
            ]
            for key, b in buckets.items()
        },
    }
    scenarios = scenario_impacts(holdings, reference)
    compound = [r["impact_pct"] for r in scenarios if r["kind"] == "compound" and r["impact_pct"] is not None]
    metrics = {
        **conc,
        "worst_compound_drawdown": (max(-min(compound), 0.0) if compound else None),
    }
    policy = evaluate_limits((reference.get("policy") or {}).get("limits", []), metrics)
    breaches = sum(1 for r in policy if r["status"] == "breach")
    history = {
        "vol_annual": stats["vol_annual"],
        "var_1d_95": var95,
        "es_1d_975": es,
        "foreign_currency_ratio": conc["foreign_currency_ratio"],
        "largest_issuer_lookthrough_ratio": conc["largest_issuer_lookthrough_ratio"],
        "max_sector_ratio": conc["max_sector_ratio"],
        "beta_topix": stats["beta"].get("topix"),
        "beta_sp500": stats["beta"].get("sp500"),
        "beta_usdjpy": stats["beta"].get("usdjpy"),
        "policy_breaches": breaches,
    }
    return {
        "as_of": as_of,
        "total": total,
        "exposures": {k: exposures[k] for k in ("asset_class", "currency", "country", "sector", "issuers", "coverage")},
        "concentration": conc,
        "stats": stats,
        "contributions": contributions,
        "stress": {
            "scenarios": scenarios,
            "episodes": episode_impacts(values, reference.get("episodes", []), dates, prices_jpy),
        },
        "policy": policy,
        "policy_breaches": breaches,
        "history": history,
    }
```

- [ ] **Step 4: Run** → PASS; `ruff check` / `ruff format` the two files.
- [ ] **Step 5: Commit** — `feat(portfolio-analyzer): risk statistics, contributions, stress and limits`

### Task 9: script integration — benchmarks, episode-aware start, returns, `risk` payload, history

**Files:**
- Modify: `portfolio-analyzer/scripts/daily_pl_report.py`
- Test: `portfolio-analyzer/tests/test_daily_pl_report.py`

**Interfaces:**
- New arg `--reference` (default `data/analysis_reference.private.json`); `BENCHMARKS = {"topix": "1306.T", "sp500": "SPY", "usdjpy": "JPY=X"}`.
- Helpers: `history_start(today, history_days, episodes) -> str`, `jpy_price_paths(filled, tickers, fx_symbol, usd_tickers) -> dict[str, list[float | None]]`, `daily_returns(path) -> list[float]` (0.0 where the previous close is missing).
- Payload: `payload["risk"]` = `risk.assemble(...)`; `record["risk"] = payload["risk"]["history"]`; `previous = mtm.previous_record(records_before, as_of)["risk"]` (read the history file before upsert).

- [ ] **Step 1: Failing tests**

```python
def test_history_start_reaches_back_to_the_oldest_episode() -> None:
    from datetime import date

    episodes = [{"start": "2024-07-31", "end": "2024-08-05"}, {"start": "2025-04-02", "end": "2025-04-08"}]
    assert daily_pl_report.history_start(date(2026, 9, 15), 760, episodes) == "2024-07-24"
    assert daily_pl_report.history_start(date(2026, 9, 15), 760, []) == "2024-08-16"


def test_jpy_price_paths_convert_dollar_tickers_and_daily_returns_skip_gaps() -> None:
    idx = pd.to_datetime(["2026-09-10", "2026-09-11", "2026-09-14"])
    filled = pd.DataFrame({"SMH": [560.0, 568.0, 568.0], "6857.T": [float("nan"), 31720.0, 31080.0], "JPY=X": [153.0, 154.0, 155.0]}, index=idx)
    paths = daily_pl_report.jpy_price_paths(filled, ["SMH", "6857.T"], "JPY=X", {"SMH"})
    assert paths["SMH"] == [560.0 * 153.0, 568.0 * 154.0, 568.0 * 155.0]
    assert paths["6857.T"][0] is None and paths["6857.T"][1] == 31720.0
    assert daily_pl_report.daily_returns(paths["6857.T"]) == [0.0, 0.0, pytest.approx(31080.0 / 31720.0 - 1)]
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement**

```python
BENCHMARKS = {"topix": "1306.T", "sp500": "SPY", "usdjpy": mtm.FX_SYMBOL}
RISK_WINDOW = 252


def history_start(today: date, history_days: int, episodes: list[dict]) -> str:
    """Far enough back for the P&L window and for the oldest episode to be replayed."""
    floor = today - timedelta(days=history_days)
    for ep in episodes:
        first = date.fromisoformat(str(ep["start"])) - timedelta(days=7)
        floor = min(floor, first)
    return floor.isoformat()


def jpy_price_paths(filled, tickers, fx_symbol, usd_tickers) -> dict[str, list[float | None]]:
    """Forward-filled closes in JPY per ticker (None before the first bar)."""
    fx = [float(v) for v in filled[fx_symbol].tolist()]
    out = {}
    for t in tickers:
        if t not in filled.columns:
            continue
        raw = filled[t].tolist()
        rate = fx if t in usd_tickers else [1.0] * len(raw)
        out[t] = [None if v != v else float(v) * r for v, r in zip(raw, rate, strict=True)]
    return out


def daily_returns(path: list[float | None]) -> list[float]:
    out = [0.0]
    for prev, cur in zip(path, path[1:], strict=False):
        out.append(0.0 if prev in (None, 0.0) or cur is None else cur / prev - 1.0)
    return out
```

In `parse_args`: `parser.add_argument("--reference", default=str(PROJECT_ROOT / "data" / "analysis_reference.private.json"), help="look-through, factor loadings, scenarios, limits and episodes for the risk section")`.

In `build_payload`:
- Load `reference = json.loads(Path(args.reference).read_text(encoding="utf-8")) if Path(args.reference).exists() else {}`.
- `start = history_start(today, args.history_days, reference.get("episodes", []))` replaces the `start = ...` line; download `[*tickers, *sorted(set(BENCHMARKS.values()) - {mtm.FX_SYMBOL}), mtm.FX_SYMBOL]` (benchmarks are not open tickers: keep `tickers` for the quotes/positions and add the benchmark columns only to the download list).
- After the total series, compute the risk block:
```python
    usd_tickers = {t for t, (sym, acct) in open_tickers.items() if next(p["currency"] for p in snapshot["positions"] if p["symbol"] == sym and p["account_id"] == acct) == "USD"}
    price_jpy = jpy_price_paths(filled, [*open_tickers, *([dc_ticker] if dc_ticker else [])], mtm.FX_SYMBOL, usd_tickers)
    returns = {t: daily_returns(p)[-RISK_WINDOW:] for t, p in price_jpy.items()}
    bench_paths = jpy_price_paths(filled, list(BENCHMARKS.values()), mtm.FX_SYMBOL, set())
    benchmarks = {name: daily_returns(bench_paths[t])[-RISK_WINDOW:] for name, t in BENCHMARKS.items() if t in bench_paths}
    holdings = [
        risk.Holding(r.symbol, r.account_id, float(r.market_value_jpy), r.currency, r.asset_class, r.ticker if r.quoted else None)
        for r in rows
    ]
    earlier = mtm.load_history(Path(args.history))  # see below
    prev_record = mtm.previous_record(earlier, as_of)
    risk_block = risk.assemble(holdings, reference, returns, benchmarks, dates, price_jpy, as_of, previous=(prev_record or {}).get("risk")) if reference else None
```
  `mtm.load_history(path) -> list[dict]` is the read half of `upsert_history` — extract it (upsert calls it). RECONCILIATION rows (`asset_class` 未分類) count as non-cash, non-quoted holdings; they carry no ticker so they only enter the exposure totals — acceptable (29k).
- `payload["risk"] = risk_block`; `record["risk"] = risk_block["history"] if risk_block else None`.
- Import `risk` from `portfolio_analyzer` at the top.

- [ ] **Step 4: Run** unit tests, then the real script; print `payload["risk"]["stats"]` and `policy` once by hand (`python - <<EOF` reading `dist/pl-daily/latest.html`'s JSON) to sanity-check: vol in a 10–25% range, VaR 1d 95% ≈ 1–2% of assets, foreign currency ratio ≈ 0.30, Advantest look-through ≈ 0.15.
- [ ] **Step 5: Commit** — `feat(portfolio-analyzer): compute the daily risk block in the report script`

### Task 10: dashboard risk section

**Files:**
- Modify: `portfolio-analyzer/src/portfolio_analyzer/dashboard.py` (new `_risk(risk)` and CSS; insert between the general grid and the positions table)
- Test: `portfolio-analyzer/tests/test_dashboard.py`

- [ ] **Step 1: Failing test** — add a `risk` block to `sample()` (copy the shape from `risk.assemble`: two exposure rows per dimension, one issuer, stats with `vol_annual 0.18, var_1d_95 0.015, var_1d_95_jpy 690000, es_1d_975 0.02, es_1d_975_jpy 920000, var_20d_95 0.067, beta {topix 0.6, sp500 0.5, usdjpy 0.3}, prev {vol_annual 0.17}`, contributions, stress with one scenario and one episode, policy with one ok and one breach) and assert:
```python
def test_render_shows_the_risk_section() -> None:
    html = dashboard.render(sample(), ":root{--ink:#000}")
    for text in ("リスク", "限度", "外貨エクスポージャー", "超過", "年率ボラティリティ", "18.0%", "VaR 1日 95%", "690,000", "リスク寄与", "ストレス", "株式全体 -10%", "2024-08 円キャリー巻き戻し", "Advantest", "6857 · 1329"):
        assert text in html, text
    data = sample(); data["risk"] = None
    assert "年率ボラティリティ" not in dashboard.render(data, ":root{--ink:#000}")
```
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** `_risk(risk: dict | None) -> str` returning `""` when None, else a `<h2 class="sec">リスク …</h2>` plus a `.grid` with: (1) panel 「限度」: one `<span class='lim ok|breach|na'>` per limit with label, value and threshold (`超過` prefix on breach); (2) panel 「エクスポージャー」: four `.mini` tables (資産クラス/通貨/国/セクター) with a bar cell `<td><div class='bar' style='width:{pct*100:.0f}%'></div></td>`; (3) panel 「ルックスルー上位」: issuers with `via` joined by ` · `; (4) panel 「リスク量」: rows for 年率ボラティリティ, VaR 1日 95% / 99%, ES 97.5%, VaR 20日 95%, ベータ TOPIX / S&P500 / USD/JPY, 最悪日, each with 前日比 from `stats.prev` when present; (5) panel 「リスク寄与」: positions top 8 (weight vs risk_share) and the three bucket tables; (6) panel 「ストレス」: scenarios (worst 8 + all `historical`) and episodes with coverage. CSS: `.lim{display:inline-block;border-radius:999px;padding:2px 9px;margin:2px 4px 2px 0;font-size:11px;border:1px solid var(--rule)}.lim.breach{border-color:var(--series-2);color:var(--series-2);font-weight:700}.lim.ok{color:var(--ink-2)}.bar{height:8px;background:var(--accent);border-radius:2px}.mini td.b{width:38%}`.
- [ ] **Step 4: Run** → PASS. **Step 5: Commit** — `feat(portfolio-analyzer): risk section on the daily dashboard`

### Task 11: mail risk section

**Files:**
- Modify: `portfolio-analyzer/src/portfolio_analyzer/mailer.py` (`_risk(data)` inserted after the allocation card; `text_body` lines)
- Test: `portfolio-analyzer/tests/test_mailer.py`

- [ ] **Step 1: Failing test** — add the same `risk` block to `payload()` and:
```python
def test_html_and_text_body_carry_the_risk_section() -> None:
    body = mailer.html_body(payload())
    for text in ("リスク", "超過", "外貨エクスポージャー", "年率ボラティリティ", "18.0%", "VaR 1日 95%", "690,000", "リスク寄与", "ストレス", "株式全体 -10%", "Advantest"):
        assert text in body, text
    assert "background:" not in body
    text = mailer.text_body(payload())
    assert "リスク" in text and "ボラ 18.0%" in text and "VaR(1日95%) 690,000" in text and "超過 1" in text
```
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** with the existing helpers: `_section("リスク", "ルックスルー · 直近 252 営業日")`, a `_card` per block; limits as inline `<span>` chips with `border:1px solid` (red text `DN` for breach); exposures via `emailchart.shares([(label, pct, f"{pct:.1%} · {jpy(value)}")], width=200)` four times with a small heading each; issuers as a `_td` table (label, via, pct); stats as a two-column table with 前日比 in `_under`; contributions as a table (銘柄 / 比率 / リスク寄与); stress via `emailchart.hbars([(label, impact_pct*100, jpy(impact_jpy, True))])` for scenarios (worst 8 + historical) and episodes (with coverage in the note). `text_body`: append after the account lines: `リスク: ボラ {pct}, VaR(1日95%) {jpy}, ES {jpy}, 外貨 {pct}, 最大ルックスルー銘柄 {label} {pct}, 超過 {n}`.
- [ ] **Step 4: Run** → PASS; full suite green; `ruff` on touched files.
- [ ] **Step 5: Commit** — `feat(portfolio-analyzer): risk section in the daily mail`

### Task 12: docs, real run, memory

**Files:**
- Modify: `portfolio-analyzer/README.md` (definitions: 合計化、リスクの各指標の窓・方法・限界; the new `--reference`; the three draft limits), memory file `project_portfolio_analyzer.md`

- [ ] **Step 1:** README — under 定義 add: 累計損益＝3 口座の NAV − 累計入金（口座ごとの再生方法と DC の開始日）; 資金加重リターンの範囲; リスク: ルックスルーの元データ（参照ファイル、発行体の国、DC の按分は推定）、ボラ／VaR／ES（過去シミュレーション、252 営業日、現在ウェイト固定、休場日は 0 リターン扱いで相関が薄まる）、20 日 VaR は √20 換算、ベータは単回帰、リスク寄与の式と按分、シナリオはファクター係数×ショック、エピソードは実測リプレイ（開始日直前の終値→終了日終値、価格の無い保有は 0 でカバレッジを表示）、限度は draft。
- [ ] **Step 2:** Real run with `--edition tokyo --email $PL_MAIL_TO` after the user says so (sending is external — ask first unless already approved), else run without `--email` and inspect `dist/pl-daily/latest.html`.
- [ ] **Step 3:** Update memory `project_portfolio_analyzer.md` and `MEMORY.md` line; commit README: `docs(portfolio-analyzer): totals across accounts and the daily risk monitor`.
- [ ] **Step 4:** Push to `main` after `git fetch` and a rebase if other sessions pushed.

---

## Self-review

- Spec coverage: A §2.1 → Tasks 1–3; §2.2 → Task 4; §2.3 → Task 5; B §3.2 → Task 6; §3.3 → Tasks 7–9; §3.4 → Tasks 10–11 (+ history in 9); §3.5 tests inside each task; README → Task 12. Not covered by design: per-account lines on the NAV chart (data shipped in `series.accounts`, drawing deferred, as the spec says).
- Placeholders: none — every code step has the code; Task 10/11 describe markup in prose but name the exact helpers, classes and texts the tests assert.
- Type consistency: `AccountSeries` fields are used with the same names in Tasks 1–5; `risk.assemble` returns `history` consumed as `record["risk"]` in Task 9 and read back as `previous` → `stats.prev` (Task 8 test asserts `stats.prev`); `jpy_price_paths` / `daily_returns` signatures match between Task 9's tests and code.
