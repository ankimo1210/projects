"""Daily mark-to-market P&L summary.

Positions come from the snapshot (what is held), closes and FX from the market,
cost basis from the IBKR ledger where it exists. Everything here is offline and
pure; ``scripts/daily_pl_report.py`` fetches the quotes and writes the files.

Day P&L is the yen change between the last two closes the market has for each
instrument (price and FX both move), so it is a mark-to-market number, not a
calendar-day number: on a Monday it spans the weekend, and a JP close and a US
close of the same report can carry different dates.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from portfolio_analyzer.ibkr import Holding, decompose_pnl

NON_MARKET_SYMBOLS = {"CASH_JPY", "RECONCILIATION"}
FX_SYMBOL = "JPY=X"
ZERO = Decimal(0)
ONE = Decimal(1)


@dataclass(frozen=True)
class Quote:
    """Last close and the close before it, with their dates."""

    close: Decimal
    prev_close: Decimal | None
    date: str
    prev_date: str | None


def market_symbol(symbol: str, currency: str) -> str | None:
    """Return the yfinance ticker for a holding, or None if it has no quote."""
    if symbol in NON_MARKET_SYMBOLS:
        return None
    if currency == "JPY" and symbol.isdigit():
        return f"{symbol}.T"
    if currency == "USD":
        return symbol
    return None


def _dec(value: Any) -> Decimal | None:
    return None if value is None else Decimal(str(value))


@dataclass
class Row:
    """One position, marked to market."""

    account_id: str
    symbol: str
    name: str
    asset_class: str
    currency: str
    quantity: Decimal | None
    quoted: bool
    ticker: str | None
    price: Decimal | None
    prev_price: Decimal | None
    price_date: str | None
    prev_price_date: str | None
    fx: Decimal
    prev_fx: Decimal | None
    market_value_jpy: Decimal
    prev_value_jpy: Decimal | None
    day_pnl_jpy: Decimal | None
    day_price_pnl_jpy: Decimal | None
    day_change_pct: Decimal | None
    cost_basis_jpy: Decimal | None
    average_cost: Decimal | None
    unrealized_jpy: Decimal | None
    unrealized_pct: Decimal | None
    price_pnl_jpy: Decimal | None
    fx_pnl_jpy: Decimal | None
    cross_pnl_jpy: Decimal | None
    commission_jpy: Decimal | None
    note: str


def _cost_index(ledger: dict[str, Any] | None) -> dict[tuple[str, str], dict[str, Any]]:
    if not ledger:
        return {}
    account = str(ledger.get("account_id", ""))
    return {(account, str(h["symbol"])): h for h in ledger.get("holdings", [])}


def mark_positions(
    snapshot: dict[str, Any],
    quotes: dict[str, Quote],
    fx: Quote,
    ledger: dict[str, Any] | None,
) -> list[Row]:
    """Mark every snapshot position; positions without a quote are carried at snapshot value."""
    cost = _cost_index(ledger)
    rows: list[Row] = []
    for pos in snapshot["positions"]:
        account_id = str(pos["account_id"])
        symbol = str(pos["symbol"])
        currency = str(pos["currency"])
        quantity = _dec(pos.get("quantity"))
        ticker = market_symbol(symbol, currency)
        quote = quotes.get(ticker) if ticker else None
        row = Row(
            account_id=account_id,
            symbol=symbol,
            name=str(pos.get("name", symbol)),
            asset_class=str(pos.get("asset_class", "")),
            currency=currency,
            quantity=quantity,
            quoted=False,
            ticker=ticker,
            price=_dec(pos.get("price")),
            prev_price=None,
            price_date=None,
            prev_price_date=None,
            fx=_dec(pos.get("fx_rate")) or ONE,
            prev_fx=None,
            market_value_jpy=_dec(pos["market_value_jpy"]) or ZERO,
            prev_value_jpy=None,
            day_pnl_jpy=None,
            day_price_pnl_jpy=None,
            day_change_pct=None,
            cost_basis_jpy=None,
            average_cost=None,
            unrealized_jpy=None,
            unrealized_pct=None,
            price_pnl_jpy=None,
            fx_pnl_jpy=None,
            cross_pnl_jpy=None,
            commission_jpy=None,
            note="時価が取れないためスナップショットの値を据え置き",
        )
        if quote is not None and quantity is not None:
            rate, prev_rate = (fx.close, fx.prev_close) if currency == "USD" else (ONE, ONE)
            row.quoted = True
            row.price, row.prev_price = quote.close, quote.prev_close
            row.price_date, row.prev_price_date = quote.date, quote.prev_date
            row.fx, row.prev_fx = rate, prev_rate
            row.market_value_jpy = quantity * quote.close * rate
            row.note = ""
            if quote.prev_close is not None and prev_rate is not None:
                row.prev_value_jpy = quantity * quote.prev_close * prev_rate
                row.day_pnl_jpy = row.market_value_jpy - row.prev_value_jpy
                row.day_price_pnl_jpy = quantity * (quote.close - quote.prev_close) * rate
                row.day_change_pct = quote.close / quote.prev_close - ONE
            _attach_cost(row, cost.get((account_id, symbol)))
        rows.append(row)
    return rows


def _attach_cost(row: Row, holding: dict[str, Any] | None) -> None:
    """Fill the unrealised P&L columns from a ledger holding (average cost, trade-date FX)."""
    if holding is None or row.quantity is None or row.price is None:
        return
    average_cost = _dec(holding.get("average_cost"))
    trade_fx = _dec(holding.get("average_trade_fx")) or ONE
    ledger_qty = _dec(holding.get("quantity"))
    if average_cost is None or ledger_qty in (None, ZERO):
        return
    scale = row.quantity / ledger_qty
    cost_basis_jpy = (_dec(holding.get("cost_basis_jpy")) or ZERO) * scale
    commission_jpy = (_dec(holding.get("commission_jpy")) or ZERO) * scale
    cost_native = row.quantity * average_cost
    holding_state = Holding(
        symbol=row.symbol,
        currency=row.currency,
        quantity=row.quantity,
        cost_basis_jpy=cost_basis_jpy,
        cost_basis_gross_jpy=cost_basis_jpy + commission_jpy,
        cost_basis_native=cost_native,
        average_trade_fx=trade_fx,
        realized_pnl_jpy=ZERO,
    )
    split = decompose_pnl(holding_state, row.price, row.fx)
    if split is None:
        return
    row.cost_basis_jpy = cost_basis_jpy
    row.average_cost = average_cost
    row.unrealized_jpy = split.total_jpy
    row.unrealized_pct = split.total_jpy / cost_basis_jpy if cost_basis_jpy else None
    row.price_pnl_jpy = split.price_jpy
    row.fx_pnl_jpy = split.fx_jpy
    row.cross_pnl_jpy = split.cross_jpy
    row.commission_jpy = split.commission_jpy
    if scale != ONE:
        row.note = f"台帳の数量 {ledger_qty} と異なるため平均取得単価を数量に掛けて按分"


@dataclass
class AccountSummary:
    id: str
    name: str
    snapshot_as_of: str
    total_jpy: Decimal
    quoted_value_jpy: Decimal
    day_pnl_jpy: Decimal | None
    unrealized_known_jpy: Decimal | None
    cost_known_value_jpy: Decimal
    snapshot_unrealized_jpy: Decimal | None


@dataclass
class Summary:
    accounts: dict[str, AccountSummary]
    total_jpy: Decimal
    quoted_value_jpy: Decimal
    day_pnl_jpy: Decimal | None
    unrealized_known_jpy: Decimal | None
    cost_known_value_jpy: Decimal


def _sum_optional(values: list[Decimal | None]) -> Decimal | None:
    present = [v for v in values if v is not None]
    return sum(present, ZERO) if present else None


def summarize(snapshot: dict[str, Any], rows: list[Row]) -> Summary:
    accounts: dict[str, AccountSummary] = {}
    for acc in snapshot["accounts"]:
        acc_id = str(acc["id"])
        mine = [r for r in rows if r.account_id == acc_id]
        accounts[acc_id] = AccountSummary(
            id=acc_id,
            name=str(acc.get("name", acc_id)),
            snapshot_as_of=str(acc.get("as_of", "")),
            total_jpy=sum((r.market_value_jpy for r in mine), ZERO),
            quoted_value_jpy=sum((r.market_value_jpy for r in mine if r.quoted), ZERO),
            day_pnl_jpy=_sum_optional([r.day_pnl_jpy for r in mine]),
            unrealized_known_jpy=_sum_optional([r.unrealized_jpy for r in mine]),
            cost_known_value_jpy=sum(
                (r.market_value_jpy for r in mine if r.unrealized_jpy is not None), ZERO
            ),
            snapshot_unrealized_jpy=_dec(acc.get("unrealized_pnl_jpy")),
        )
    return Summary(
        accounts=accounts,
        total_jpy=sum((a.total_jpy for a in accounts.values()), ZERO),
        quoted_value_jpy=sum((a.quoted_value_jpy for a in accounts.values()), ZERO),
        day_pnl_jpy=_sum_optional([a.day_pnl_jpy for a in accounts.values()]),
        unrealized_known_jpy=_sum_optional([a.unrealized_known_jpy for a in accounts.values()]),
        cost_known_value_jpy=sum((a.cost_known_value_jpy for a in accounts.values()), ZERO),
    )


# ---------------------------------------------------------------- history ---


def _f(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def history_record(summary: Summary, rows: list[Row], meta: dict[str, Any]) -> dict[str, Any]:
    """One JSON-serialisable line for the history file."""
    fx: Quote = meta["fx"]
    return {
        "as_of": meta["as_of"],
        "generated_at": meta["generated_at"],
        "fx_usdjpy": _f(fx.close),
        "total_jpy": _f(summary.total_jpy),
        "quoted_value_jpy": _f(summary.quoted_value_jpy),
        "day_pnl_jpy": _f(summary.day_pnl_jpy),
        "unrealized_known_jpy": _f(summary.unrealized_known_jpy),
        "accounts": {
            k: {"total_jpy": _f(a.total_jpy), "day_pnl_jpy": _f(a.day_pnl_jpy)}
            for k, a in summary.accounts.items()
        },
        "positions": {
            f"{r.account_id}:{r.symbol}": {
                "price": _f(r.price),
                "price_date": r.price_date,
                "value_jpy": _f(r.market_value_jpy),
                "day_pnl_jpy": _f(r.day_pnl_jpy),
                "unrealized_jpy": _f(r.unrealized_jpy),
            }
            for r in rows
            if r.quoted
        },
    }


def upsert_history(path: Path, record: dict[str, Any]) -> list[dict[str, Any]]:
    """Append ``record`` to the JSONL history, replacing any line with the same ``as_of``."""
    records: list[dict[str, Any]] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
    records = [r for r in records if r.get("as_of") != record["as_of"]]
    records.append(record)
    records.sort(key=lambda r: str(r.get("as_of", "")))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8"
    )
    return records


def previous_record(records: list[dict[str, Any]], as_of: str) -> dict[str, Any] | None:
    earlier = [r for r in records if str(r.get("as_of", "")) < as_of]
    return earlier[-1] if earlier else None


# ------------------------------------------------------------------- html ---


def fmt_jpy(value: Decimal | None, sign: bool = False) -> str:
    if value is None:
        return "—"
    rounded = int(value.to_integral_value())
    text = f"{abs(rounded):,}"
    if sign:
        return ("+" if rounded > 0 else "−" if rounded < 0 else "±") + text
    return ("−" if rounded < 0 else "") + text


def fmt_pct(value: Decimal | None, digits: int = 2) -> str:
    if value is None:
        return "—"
    v = float(value) * 100
    return f"{v:+.{digits}f}%".replace("-", "−")


def fmt_price(value: Decimal | None, currency: str) -> str:
    if value is None:
        return "—"
    v = float(value)
    return f"{v:,.2f}" if currency == "USD" or v < 100 else f"{v:,.1f}"


def _cls(value: Decimal | None) -> str:
    if value is None or value == 0:
        return ""
    return "pos" if value > 0 else "neg"


def _esc(text: str) -> str:
    return html.escape(text, quote=True)


def _history_svg(history: list[dict[str, Any]]) -> str:
    """Total value line and day P&L bars for the recorded history (needs 2+ points)."""
    pts = [h for h in history if h.get("total_jpy") is not None]
    if len(pts) < 2:
        return ""
    w, h = 760, 220
    ml, mr, mt, mb = 70, 16, 14, 26
    n = len(pts)
    xs = [ml + i * (w - ml - mr) / (n - 1) for i in range(n)]
    totals = [float(p["total_jpy"]) for p in pts]
    lo, hi = min(totals), max(totals)
    pad = max((hi - lo) * 0.15, hi * 0.002)
    lo, hi = lo - pad, hi + pad
    y = lambda v: mt + (hi - v) / (hi - lo) * (h - mt - mb)  # noqa: E731
    line = " ".join(f"{'M' if i == 0 else 'L'}{xs[i]:.1f} {y(t):.1f}" for i, t in enumerate(totals))
    ticks = ""
    step = (hi - lo) / 4
    for k in range(5):
        v = lo + k * step
        ticks += (
            f'<line x1="{ml}" x2="{w - mr}" y1="{y(v):.1f}" y2="{y(v):.1f}" class="gridline"/>'
            f'<text x="{ml - 8}" y="{y(v) + 3.5:.1f}" text-anchor="end" font-size="10.5">{v / 1e6:.2f}M</text>'
        )
    labels = ""
    seen = set()
    for i, p in enumerate(pts):
        month = str(p["as_of"])[:7]
        if month not in seen and (i == 0 or i % max(1, n // 8) == 0):
            seen.add(month)
            labels += f'<text x="{xs[i]:.1f}" y="{h - mb + 16}" text-anchor="middle" font-size="10.5">{str(p["as_of"])[5:]}</text>'
    dots = "".join(
        f'<circle cx="{xs[i]:.1f}" cy="{y(t):.1f}" r="2.4" class="dot"><title>{p["as_of"]}  {t:,.0f} 円</title></circle>'
        for i, (p, t) in enumerate(zip(pts, totals, strict=True))
    )
    total_chart = (
        f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="総資産の推移"><g>{ticks}{labels}'
        f'<path d="{line}" fill="none" class="line"/>{dots}</g></svg>'
    )
    pnl = [float(p["day_pnl_jpy"]) if p.get("day_pnl_jpy") is not None else 0.0 for p in pts]
    amax = max(abs(v) for v in pnl) or 1.0
    h2 = 160
    y2 = lambda v: mt + (amax - v) / (2 * amax) * (h2 - mt - mb)  # noqa: E731
    bw = max((w - ml - mr) / n * 0.6, 1.5)
    bars = "".join(
        f'<rect x="{xs[i] - bw / 2:.1f}" y="{min(y2(0), y2(v)):.1f}" width="{bw:.1f}" height="{abs(y2(v) - y2(0)):.1f}" class="{"bar-pos" if v >= 0 else "bar-neg"}"><title>{p["as_of"]}  {v:+,.0f} 円</title></rect>'
        for i, (p, v) in enumerate(zip(pts, pnl, strict=True))
    )
    pnl_chart = (
        f'<svg viewBox="0 0 {w} {h2}" role="img" aria-label="日次損益の推移"><g>'
        f'<line x1="{ml}" x2="{w - mr}" y1="{y2(0):.1f}" y2="{y2(0):.1f}" class="zero"/>'
        f'<text x="{ml - 8}" y="{y2(amax) + 4:.1f}" text-anchor="end" font-size="10.5">{amax / 1e4:+.0f}万</text>'
        f'<text x="{ml - 8}" y="{y2(-amax) + 4:.1f}" text-anchor="end" font-size="10.5">{-amax / 1e4:+.0f}万</text>'
        f"{bars}</g></svg>"
    )
    return (
        '<figure><p class="figtitle">総資産の推移</p><p class="figsub">レポートを出した日の評価額（円）。DC・現金は据え置き</p>'
        f'<div class="scroll">{total_chart}</div></figure>'
        '<figure><p class="figtitle">日次損益の推移</p><p class="figsub">時価が取れる保有の前回終値比（円）</p>'
        f'<div class="scroll">{pnl_chart}</div></figure>'
    )


def render_html(
    summary: Summary,
    rows: list[Row],
    history: list[dict[str, Any]],
    meta: dict[str, Any],
    tokens_css: str,
) -> str:
    """Self-contained report (doctype included) on the claude-report tokens."""
    as_of = str(meta["as_of"])
    fx: Quote = meta["fx"]
    stale: dict[str, str] = meta.get("stale", {})
    since_last = meta.get("since_last")
    quoted_share = summary.quoted_value_jpy / summary.total_jpy if summary.total_jpy else ZERO
    day_pct = (
        summary.day_pnl_jpy / (summary.quoted_value_jpy - summary.day_pnl_jpy)
        if summary.day_pnl_jpy is not None and summary.quoted_value_jpy != summary.day_pnl_jpy
        else None
    )

    def account_table(acc: AccountSummary) -> str:
        mine = [r for r in rows if r.account_id == acc.id]
        body = ""
        for r in mine:
            date_note = ""
            if r.quoted and r.price_date and r.price_date != as_of:
                date_note = f' <span class="stale">{r.price_date[5:]} 終値</span>'
            body += (
                "<tr>"
                f"<td><strong>{_esc(r.symbol)}</strong> <span class='muted'>{_esc(r.name)}</span>{date_note}</td>"
                f"<td class='num'>{fmt_jpy(r.quantity) if r.quantity is not None else '—'}</td>"
                f"<td class='num'>{fmt_price(r.price, r.currency)}{' <span class=muted>' + r.currency + '</span>' if r.quoted and r.currency != 'JPY' else ''}</td>"
                f"<td class='num {_cls(r.day_change_pct)}'>{fmt_pct(r.day_change_pct)}</td>"
                f"<td class='num'>{fmt_jpy(r.market_value_jpy)}</td>"
                f"<td class='num {_cls(r.day_pnl_jpy)}'>{fmt_jpy(r.day_pnl_jpy, sign=True)}</td>"
                f"<td class='num {_cls(r.unrealized_jpy)}'>{fmt_jpy(r.unrealized_jpy, sign=True)}"
                f"{' <span class=muted>' + fmt_pct(r.unrealized_pct, 1) + '</span>' if r.unrealized_pct is not None else ''}</td>"
                "</tr>"
            )
        unreal = acc.unrealized_known_jpy
        unreal_note = ""
        if unreal is None and acc.snapshot_unrealized_jpy is not None:
            unreal_note = f"<span class='muted'>口座表示 {fmt_jpy(acc.snapshot_unrealized_jpy, sign=True)}（{acc.snapshot_as_of}）</span>"
        body += (
            "<tr class='hl'><td>小計</td><td></td><td></td><td></td>"
            f"<td class='num'>{fmt_jpy(acc.total_jpy)}</td>"
            f"<td class='num {_cls(acc.day_pnl_jpy)}'>{fmt_jpy(acc.day_pnl_jpy, sign=True)}</td>"
            f"<td class='num {_cls(unreal)}'>{fmt_jpy(unreal, sign=True) if unreal is not None else unreal_note}</td></tr>"
        )
        return (
            f"<div class='tw'><table><caption>{_esc(acc.name)}</caption>"
            "<thead><tr><th>銘柄</th><th>数量</th><th>終値</th><th>前日比</th><th>評価額 (円)</th><th>日次損益 (円)</th><th>含み損益 (円)</th></tr></thead>"
            f"<tbody>{body}</tbody></table></div>"
        )

    decomposition = ""
    cost_rows = [r for r in rows if r.unrealized_jpy is not None]
    if cost_rows:
        body = "".join(
            "<tr>"
            f"<td><strong>{_esc(r.symbol)}</strong></td>"
            f"<td class='num'>{fmt_price(r.average_cost, r.currency)} <span class=muted>{r.currency}</span></td>"
            f"<td class='num'>{fmt_jpy(r.cost_basis_jpy)}</td>"
            f"<td class='num {_cls(r.price_pnl_jpy)}'>{fmt_jpy(r.price_pnl_jpy, sign=True)}</td>"
            f"<td class='num {_cls(r.fx_pnl_jpy)}'>{fmt_jpy(r.fx_pnl_jpy, sign=True)}</td>"
            f"<td class='num {_cls(r.cross_pnl_jpy)}'>{fmt_jpy(r.cross_pnl_jpy, sign=True)}</td>"
            f"<td class='num'>{fmt_jpy(r.commission_jpy, sign=True)}</td>"
            f"<td class='num {_cls(r.unrealized_jpy)}'><strong>{fmt_jpy(r.unrealized_jpy, sign=True)}</strong></td>"
            "</tr>"
            for r in cost_rows
        )
        tot = {
            k: sum((getattr(r, k) or ZERO for r in cost_rows), ZERO)
            for k in (
                "cost_basis_jpy",
                "price_pnl_jpy",
                "fx_pnl_jpy",
                "cross_pnl_jpy",
                "commission_jpy",
                "unrealized_jpy",
            )
        }
        body += (
            "<tr class='hl'><td>合計</td><td></td>"
            f"<td class='num'>{fmt_jpy(tot['cost_basis_jpy'])}</td>"
            f"<td class='num {_cls(tot['price_pnl_jpy'])}'>{fmt_jpy(tot['price_pnl_jpy'], sign=True)}</td>"
            f"<td class='num {_cls(tot['fx_pnl_jpy'])}'>{fmt_jpy(tot['fx_pnl_jpy'], sign=True)}</td>"
            f"<td class='num {_cls(tot['cross_pnl_jpy'])}'>{fmt_jpy(tot['cross_pnl_jpy'], sign=True)}</td>"
            f"<td class='num'>{fmt_jpy(tot['commission_jpy'], sign=True)}</td>"
            f"<td class='num {_cls(tot['unrealized_jpy'])}'><strong>{fmt_jpy(tot['unrealized_jpy'], sign=True)}</strong></td></tr>"
        )
        decomposition = (
            "<h3>含み損益の分解（取得原価が台帳にある保有）</h3>"
            "<div class='tw'><table><caption>取得原価は約定日レート換算・手数料込みの平均法。価格要因 ＋ 為替要因 ＋ 交差項 ＋ 手数料 ＝ 含み損益</caption>"
            "<thead><tr><th>銘柄</th><th>平均取得単価</th><th>取得原価 (円)</th><th>価格要因</th><th>為替要因</th><th>交差項</th><th>手数料</th><th>含み損益</th></tr></thead>"
            f"<tbody>{body}</tbody></table></div>"
        )

    notes = []
    if stale:
        notes.append(
            "基準日より前の終値を使った銘柄: "
            + "、".join(f"{k}（{v}）" for k, v in sorted(stale.items()))
        )
    carried = [r for r in rows if not r.quoted]
    if carried:
        notes.append(
            "時価が取れず据え置き: "
            + "、".join(f"{r.symbol}" for r in carried)
            + f"（合計 {fmt_jpy(sum((r.market_value_jpy for r in carried), ZERO))} 円）"
        )
    no_cost = [r for r in rows if r.quoted and r.unrealized_jpy is None]
    if no_cost:
        notes.append(
            "取得原価が無く含み損益を出せない保有: "
            + "、".join(f"{r.account_id}/{r.symbol}" for r in no_cost)
        )
    notes.append(
        "日次損益は各銘柄の直近 2 つの終値の差（価格と為替の両方を含む）。月曜は週末をまたぎ、日本株と米国株で日付が異なることがある"
    )
    notes_html = "".join(f"<li>{_esc(n)}</li>" for n in notes)

    since_html = ""
    if since_last:
        since_html = f"<div><span class='k'>前回レポート比</span><span class='v {_cls(_dec(since_last['diff']))}'>{fmt_jpy(_dec(since_last['diff']), sign=True)}</span><span class='n'>{since_last['as_of']} の総資産 {fmt_jpy(_dec(since_last['total']))} 円から</span></div>"

    accounts_html = "".join(account_table(a) for a in summary.accounts.values())
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>日次損益 {as_of}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&family=Public+Sans:wght@400;500;700&family=Zen+Old+Mincho:wght@700;900&family=Zen+Kaku+Gothic+New:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
{tokens_css}
*{{box-sizing:border-box}}
body{{background:var(--ground);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.8;margin:0;padding:0 24px 80px;-webkit-font-smoothing:antialiased;font-feature-settings:"palt" 1}}
.wrap{{max-width:var(--wide);margin:0 auto}}
.mast{{padding:44px 0 20px}}
.eyebrow{{font-family:var(--mono);font-size:11px;letter-spacing:.15em;text-transform:uppercase;color:var(--ink-3);display:flex;gap:8px 16px;flex-wrap:wrap}}
.eyebrow b{{color:var(--accent);font-weight:600}}
h1{{font-family:var(--serif);font-weight:700;font-size:clamp(30px,4.6vw,44px);line-height:1.2;margin:14px 0 0;text-wrap:balance}}
h1 small{{display:block;font-family:var(--sans);font-size:15px;font-weight:500;color:var(--ink-2);margin-top:10px}}
.strip{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:26px 0 0}}
.strip>div{{background:var(--surface);border:1px solid var(--rule);border-radius:var(--r-card);padding:16px 18px 18px}}
.strip .k{{font-family:var(--mono);font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--ink-3);display:block}}
.strip .v{{font-family:var(--serif);font-weight:700;font-size:30px;line-height:1.15;display:block;margin-top:10px;font-variant-numeric:tabular-nums;letter-spacing:-.01em}}
.strip .n{{font-size:12.5px;color:var(--ink-3);display:block;margin-top:6px;line-height:1.6}}
.pos{{color:var(--accent)}}.neg{{color:var(--series-2)}}
section{{padding:36px 0 0}}
h2{{font-family:var(--serif);font-weight:700;font-size:22px;margin:0 0 4px}}
h3{{font-weight:700;font-size:15px;margin:32px 0 6px}}
.tw{{overflow-x:auto;margin:16px 0 0;border:1px solid var(--rule);border-radius:var(--r-card);background:var(--surface)}}
table{{border-collapse:collapse;width:100%;font-size:13.5px;min-width:640px}}
th,td{{padding:9px 13px;text-align:right;border-bottom:1px solid var(--rule);font-variant-numeric:tabular-nums;white-space:nowrap}}
th{{font-family:var(--mono);font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3);font-weight:500;background:var(--surface-3)}}
th:first-child,td:first-child{{text-align:left}}
td.num{{font-family:var(--mono)}}
tbody tr:last-child td{{border-bottom:none}}
tr.hl td{{background:var(--accent-wash);font-weight:700}}
caption{{caption-side:top;text-align:left;padding:14px 13px 8px;font-size:13.5px;font-weight:700;color:var(--ink)}}
.muted{{color:var(--ink-3);font-weight:400;font-size:12px}}
.stale{{font-family:var(--mono);font-size:10px;color:var(--accent);margin-left:4px}}
figure{{margin:18px 0 0;background:var(--surface);border:1px solid var(--rule);border-radius:var(--r-card);padding:20px 22px 14px}}
.figtitle{{font-weight:700;font-size:14.5px;margin:0 0 2px}}
.figsub{{font-size:12.5px;color:var(--ink-3);margin:0 0 12px}}
.scroll{{overflow-x:auto}}
svg{{display:block;max-width:100%;height:auto}}
svg text{{font-family:var(--mono);fill:var(--ink-2)}}
.gridline{{stroke:var(--grid);stroke-width:1}}
.zero{{stroke:var(--rule-2);stroke-width:1}}
.line{{stroke:var(--series-1);stroke-width:2;stroke-linejoin:round}}
.dot{{fill:var(--series-1)}}
.bar-pos{{fill:var(--accent)}}.bar-neg{{fill:var(--series-2)}}
ul{{padding-left:0;list-style:none;margin:12px 0;max-width:var(--wide)}}
ul li{{position:relative;padding-left:22px;margin:8px 0;font-size:13.5px;color:var(--ink-2)}}
ul li::before{{content:"";position:absolute;left:3px;top:.8em;width:8px;height:2px;border-radius:1px;background:var(--accent-soft)}}
footer{{margin-top:48px;padding-top:18px;border-top:1px solid var(--rule);font-family:var(--mono);font-size:11px;color:var(--ink-3);line-height:2}}
@media (max-width:640px){{body{{padding:0 14px 60px}}.mast{{padding-top:28px}}}}
</style>
</head>
<body>
<div class="wrap">
<header class="mast">
  <div class="eyebrow"><span>daily mark-to-market</span><span>基準日 {as_of}</span><span>USD/JPY {float(fx.close):,.2f}（{fx.date}）</span><b>portfolio-analyzer</b></div>
  <h1>日次損益サマリー<small>生成 {_esc(str(meta["generated_at"]))} · 時価評価の対象は総資産の {float(quoted_share) * 100:.0f}%（残りは DC 残高・現金・調整額の据え置き）</small></h1>
  <div class="strip">
    <div><span class="k">総資産</span><span class="v">{fmt_jpy(summary.total_jpy)}</span><span class="n">円。時価評価分 {fmt_jpy(summary.quoted_value_jpy)} 円</span></div>
    <div><span class="k">日次損益</span><span class="v {_cls(summary.day_pnl_jpy)}">{fmt_jpy(summary.day_pnl_jpy, sign=True)}</span><span class="n">時価評価分の前回終値比 {fmt_pct(day_pct)}</span></div>
    <div><span class="k">含み損益（原価既知分）</span><span class="v {_cls(summary.unrealized_known_jpy)}">{fmt_jpy(summary.unrealized_known_jpy, sign=True)}</span><span class="n">評価額 {fmt_jpy(summary.cost_known_value_jpy)} 円に対して {fmt_pct((summary.unrealized_known_jpy / (summary.cost_known_value_jpy - summary.unrealized_known_jpy)) if summary.unrealized_known_jpy is not None and summary.cost_known_value_jpy != summary.unrealized_known_jpy else None, 1)}</span></div>
    {since_html}
  </div>
</header>

<section>
  <h2>口座別の保有</h2>
  {accounts_html}
  {decomposition}
</section>

<section>
  <h2>推移</h2>
  {_history_svg(history) or '<p class="muted">履歴は 2 回目のレポートから表示</p>'}
</section>

<section>
  <h2>注記</h2>
  <ul>{notes_html}</ul>
</section>

<footer>
  ポジション: data/portfolio.private.json · 取得原価: data/ibkr-ledger.private.json · 株価と為替: yfinance 終値<br>
  スクリプト: portfolio-analyzer/scripts/daily_pl_report.py
</footer>
</div>
</body>
</html>
"""
