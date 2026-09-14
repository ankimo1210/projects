"""Compose and send the daily P&L email.

The mail carries what the dashboard shows: the headline, accounts, allocation,
the P&L attribution, holdings, closed positions, the time series, a card per
position and the notes. The dashboard's charts are drawn by JavaScript, and every
mail client strips scripts and inline SVG, so the email redraws them with
coloured table cells (see ``emailchart``), which keeps the figures in the body
itself. A rendered PNG of the dashboard's chart section can still ride along as
an opt-in inline image in place of the drawn charts and cards.

Credentials never live in this file: ``send`` takes them from the caller, which
reads them from the environment (see ``scripts/daily_pl_report.py``).
"""

from __future__ import annotations

import html
import smtplib
from bisect import bisect_left
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from typing import Any

from portfolio_analyzer import emailchart

UP, DN, INK, MUTED, RULE, GROUND, CARD = (
    "#C05C33",
    "#2A6DA6",
    "#141413",
    "#85817A",
    "#DFDBCF",
    "#F0EEE6",
    "#FAF9F5",
)
MONO = "ui-monospace,monospace"
SANS = "system-ui,sans-serif"


def jpy(value: float | None, sign: bool = False) -> str:
    if value is None:
        return "—"
    v = round(float(value))
    text = f"{abs(v):,}"
    if sign:
        return ("+" if v > 0 else "−" if v < 0 else "±") + text
    return ("−" if v < 0 else "") + text


def pct(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "—"
    return f"{float(value):+.{digits}f}%".replace("-", "−")


def price(value: float | None, cur: str) -> str:
    if value is None:
        return "—"
    v = float(value)
    return f"{v:,.2f}" if cur == "USD" or v < 100 else f"{v:,.1f}"


def _tone(value: float | None) -> str:
    if value is None or float(value) == 0:
        return MUTED
    return UP if float(value) > 0 else DN


def split(stock: float | None, fx: float | None, sep: str = " · ") -> str:
    """Stock and FX parts of a JPY P&L, e.g. ``株 +12,000 · FX −3,506``; empty when unknown."""
    if stock is None and fx is None:
        return ""
    return f"株 {jpy(stock, True)}{sep}FX {jpy(fx, True)}"


def usd(value: float | None, rate: float | None, sign: bool = False) -> str:
    """A yen amount in dollars at the day's USD/JPY, e.g. ``$301,257`` / ``−$2,934``."""
    if value is None or not rate:
        return ""
    v = round(float(value) / float(rate))
    text = f"${abs(v):,}"
    if sign:
        return ("+" if v > 0 else "−" if v < 0 else "±") + text
    return ("−" if v < 0 else "") + text


def after_tax(value: float | None, label: str = "税引後") -> str:
    return "" if value is None else f"{label} {jpy(value, True)}"


def _joined(*parts: str, sep: str = " · ") -> str:
    return sep.join(p for p in parts if p)


def _under(text: str) -> str:
    """Small muted lines under a table cell's value."""
    if not text:
        return ""
    return (
        f'<div style="font-size:10px;line-height:1.4;color:{MUTED};white-space:nowrap">{text}</div>'
    )


def _split_cell(row: dict[str, Any], stock: str, fx: str, taxed: str, dollars: str = "") -> str:
    """The dollar figure, the split and the after-tax figure under a cell's value, one per line."""
    return _under(
        _joined(
            dollars,
            split(row.get(stock), row.get(fx), "<br>"),
            after_tax(row.get(taxed), "税後"),
            sep="<br>",
        )
    )


def decode_header_text(raw: str | None) -> str:
    """Decode an RFC 2047 header back to text (used by the tests and by log output)."""
    return "" if raw is None else str(make_header(decode_header(raw)))


def _edition(data: dict[str, Any]) -> str:
    """Which run this is, e.g. ``東京引け`` or ``NY引け``, with a leading separator; empty when unset."""
    return f" · {data['edition']}" if data.get("edition") else ""


def subject(data: dict[str, Any]) -> str:
    h = data["headline"]
    return (
        f"日次損益 {data['as_of']}{_edition(data)} · "
        f"{jpy(h['nav_total'])} 円（{jpy(h['day_pnl'], True)}）"
    )


def _nav_after_tax(h: dict[str, Any]) -> str:
    """Total assets after the estimated tax on unrealised gains (unsigned: it is a balance)."""
    return "" if h.get("nav_after_tax") is None else f"税引後 {jpy(h['nav_after_tax'])}"


def text_body(data: dict[str, Any]) -> str:
    h, w = data["headline"], data["window"]
    rate = data["fx"]["last"]
    lines = [
        f"日次損益 {data['as_of']}{_edition(data)}  (USD/JPY {float(data['fx']['last']):.2f})",
        "",
        f"総資産          {jpy(h['nav_total']):>14} 円  {usd(h['nav_total'], rate):>10}  (時価評価 {int(h['quoted_share'] * 100)}%)",
        f"                {_nav_after_tax(h)}",
        f"日次損益        {jpy(h['day_pnl'], True):>14} 円  {usd(h['day_pnl'], rate, True):>10}  ({pct(h['day_pnl_pct'])})",
        f"                {_joined(split(h.get('day_stock'), h.get('day_fx')), after_tax(h.get('day_after_tax')))}",
        f"期間損益 {w['days']}日  {jpy(h['pnl_window'], True):>14} 円  {usd(h['pnl_window'], rate, True):>10}  (海外証券口座・入金控除後)",
        f"含み損益        {jpy(h['unrealized_known'], True):>14} 円  {usd(h['unrealized_known'], rate, True):>10}  (原価が台帳にある保有)",
        f"                {_joined(split(h.get('unreal_stock'), h.get('unreal_fx')), after_tax(h.get('unreal_after_tax')))}",
        f"開設来損益      {jpy(h.get('pnl_incept'), True):>14} 円  {usd(h.get('pnl_incept'), rate, True):>10}  (実現 {jpy(h.get('realized_cum'), True)} · 配当 {jpy(h.get('dividends_net'), True)})",
        f"資金加重リターン {_xirr(h):>13}     最大DD（期間内） {_max_dd(h)}",
        "",
        "口座別",
    ]
    for a in data["accounts"]:
        lines.append(
            f"  {a['name']:<12} {jpy(a['total']):>12} / {jpy(a['day_pnl'], True):>10}"
            f"  ({usd(a['total'], rate) or '—'} / {usd(a['day_pnl'], rate, True) or '—'})"
        )
        day_split = _joined(
            split(a.get("day_stock"), a.get("day_fx")), after_tax(a.get("day_after_tax"), "税後")
        )
        unreal_split = _joined(
            split(a.get("unreal_stock"), a.get("unreal_fx")),
            after_tax(a.get("unreal_after_tax"), "税後"),
        )
        if day_split or unreal_split:
            lines.append(f"      日次 {day_split or '—'}  /  含み {unreal_split or '—'}")
    lines += ["", "保有 (数量 / 1D / 1Y / 評価額 / 日次 / 含み  (USD: 評価額 / 日次 / 含み))"]
    for p in data["positions"]:
        unreal = jpy(p["unreal"], True) if p.get("unreal") is not None else "原価なし"
        lines.append(
            f"  {p['sym']:<5} {p['acct'][:4]:<4} {jpy(p['qty']):>7} / {pct(p['chg1d']):>7} / "
            f"{pct(p['chg1y'], 1):>8} / {jpy(p['value']):>11} / {jpy(p['day_pnl'], True):>10} / {unreal:>11}"
            f"  ({usd(p['value'], rate)} / {usd(p['day_pnl'], rate, True) or '—'} / {usd(p.get('unreal'), rate, True) or '—'})"
        )
        day_split = _joined(
            split(p.get("day_stock"), p.get("day_fx")), after_tax(p.get("day_after_tax"), "税後")
        )
        unreal_split = _joined(
            split(p.get("unreal_stock"), p.get("unreal_fx")),
            after_tax(p.get("unreal_after_tax"), "税後"),
        )
        if day_split or unreal_split:
            lines.append(f"        日次 {day_split or '—'}  /  含み {unreal_split or '—'}")
    lines += [
        "",
        *[f"* {n}" for n in _notes(data)],
        "",
        f"生成 {data['generated_at']}",
        "ダッシュボード本体: Documents\\pl-daily\\latest.html",
    ]
    return "\n".join(lines)


def _xirr(h: dict[str, Any]) -> str:
    return pct(None if h.get("xirr") is None else h["xirr"] * 100)


def _max_dd(h: dict[str, Any]) -> str:
    return pct(None if h.get("max_dd_window") is None else h["max_dd_window"] * 100, 1)


def _notes(data: dict[str, Any]) -> list[str]:
    """The dashboard's notes, with the tax note appended unless they already carry it."""
    notes = [str(n) for n in data.get("notes") or []]
    tax = data.get("tax_note")
    return notes + ([tax] if tax and tax not in notes else [])


def _sample(values: list[Any], count: int) -> tuple[list[float | None], list[int]]:
    """Evenly spaced points (the last one always kept), with their source indices."""
    if not values:
        return [], []
    if len(values) <= count:
        idx = list(range(len(values)))
    else:
        step = (len(values) - 1) / (count - 1)
        idx = sorted({round(i * step) for i in range(count)} | {len(values) - 1})
    return [values[i] for i in idx], idx


def man(value: float) -> str:
    """An axis label in 万円: the dashboard's unit, short enough for a 40px gutter."""
    v = float(value)
    if v == 0:
        return "0"
    if abs(v) >= 1e4:
        return f"{v / 1e4:+.0f}万".replace("-", "−")
    return f"{v:+.0f}".replace("-", "−")


def man_level(value: float) -> str:
    """An unsigned axis label in 万円, for a balance such as NAV."""
    return f"{float(value) / 1e4:,.0f}万".replace("-", "−")


def _price_axis(value: float, cur: str) -> str:
    v = float(value)
    if v >= 100:
        return f"{v:,.0f}"
    return f"{v:.0f}" if cur == "USD" else f"{v:.1f}"


def _nearest(idx: list[int], i: int) -> int:
    """Position, among sampled source indices, of the one closest to ``i``."""
    k = bisect_left(idx, i)
    if k >= len(idx):
        return len(idx) - 1
    if k and i - idx[k - 1] < idx[k] - i:
        return k - 1
    return k


def _section(title: str, sub: str = "") -> str:
    right = (
        f'<td align="right" style="font:400 11px {MONO};color:{MUTED};white-space:nowrap">{html.escape(sub)}</td>'
        if sub
        else ""
    )
    return (
        f'<table width="100%" cellspacing="0" cellpadding="0" style="margin:22px 0 6px"><tr>'
        f'<td style="font:700 13px {SANS};color:{INK}">{html.escape(title)}</td>{right}</tr></table>'
    )


def _card(inner: str, pad: str = "12px 14px") -> str:
    """A bordered panel. The fill is an attribute — Gmail strips a CSS background."""
    return (
        f'<table width="100%" cellspacing="0" cellpadding="0" bgcolor="{CARD}" '
        f'style="border:1px solid {RULE};border-radius:8px"><tr>'
        f'<td style="padding:{pad}">{inner}</td></tr></table>'
    )


def _caption(text: str) -> str:
    return f'<div style="font:400 11px/1.5 {SANS};color:{MUTED};margin-top:8px">{text}</div>'


def _charts(data: dict[str, Any]) -> str:
    """The figures, drawn with table cells so they render in the body of the mail."""
    out = ""
    series = data.get("series") or {}
    dates = series.get("dates") or []
    w = data.get("window") or {}
    nav = list(series.get("nav") or [])
    if nav:
        points, idx = _sample(nav, 52)
        deposits = list(series.get("deposits") or [])
        overlay = [deposits[i] for i in idx] if len(deposits) == len(nav) else None
        labels = [dates[i] for i in idx] if len(dates) == len(nav) else None
        out += _section(
            "NAV と累計入金", f"海外証券口座 · {w.get('start', '')} → {w.get('end', '')}"
        )
        out += _card(
            emailchart.line(
                points, labels, total_px=120, col_w=10, zero=False, fmt=man_level, overlay=overlay
            )
            + _caption(
                f'<span style="color:{UP}">━</span> NAV <b>{jpy(nav[-1])}</b> 円 · '
                f'<span style="color:{DN}">━</span> 累計入金 {jpy(deposits[-1] if deposits else None)} 円。'
                "入金は段差になります。"
            )
        )
    pnl = list(series.get("pnl") or [])
    if pnl:
        points, idx = _sample(pnl, 52)
        labels = [dates[i] for i in idx] if dates else None
        known = [v for v in pnl if v is not None]
        last = next((v for v in reversed(points) if v is not None), None)
        out += _section("累計損益", f"海外証券口座 · {w.get('start', '')} → {w.get('end', '')}")
        out += _card(
            emailchart.line(points, labels, total_px=120, col_w=10, fmt=man)
            + _caption(
                f"NAV − 累計入金。直近 <b>{jpy(last, True)}</b> 円・"
                f"期間の高値 {jpy(max(known, default=None), True)} 円 / "
                f"安値 {jpy(min(known, default=None), True)} 円。"
            )
        )
    daily = list(series.get("daily_pnl") or [])
    if daily:
        labels = dates[-len(daily) :] if len(dates) >= len(daily) else None
        known = [v for v in daily if v is not None]
        wins = sum(1 for v in known if v > 0)
        losses = sum(1 for v in known if v < 0)
        step = min(13, max(2, 520 // len(daily)))
        gap = 1 if step < 6 else 3
        out += _section("日次損益", f"海外証券口座 · 期間 {len(daily)} 営業日")
        out += _card(
            emailchart.columns(
                daily,
                labels,
                total_px=110,
                col_w=step - gap,
                gap=gap,
                fmt=man,
                months=None if len(daily) < 60 else emailchart.QUARTERS,
            )
            + _caption(
                f"入金を除いた NAV の日次変化。上げた日 {wins} 日 / 下げた日 {losses} 日"
                f"（変化なし {len(known) - wins - losses} 日）。"
            )
        )
    return out


def _stat(label: str, value: str, tone: str | None = None) -> str:
    style = f' style="color:{tone}"' if tone else ""
    return f'<span style="white-space:nowrap">{label} <b{style}>{value}</b></span>'


def _label(left: str, right: str = "") -> str:
    return (
        f'<table width="100%" cellspacing="0" cellpadding="0" style="margin-top:8px"><tr>'
        f'<td style="font:400 10px {MONO};color:{MUTED}">{left}</td>'
        f'<td align="right" style="font:400 10px {MONO};color:{MUTED}">{right}</td></tr></table>'
    )


def _cards(data: dict[str, Any]) -> str:
    """One card per charted position: its numbers, a year of prices and its P&L."""
    series = data.get("series") or {}
    dates = series.get("dates") or []
    w = data["window"]
    out = ""
    for key, s in (series.get("symbols") or {}).items():
        p = next((r for r in data["positions"] if r.get("key", r["sym"]) == key), None)
        prices = list(s.get("price") or [])
        if p is None or not prices:
            continue
        cur = p["cur"]
        points, idx = _sample(prices, 52)
        labels = [dates[i] for i in idx] if len(dates) == len(prices) else None
        marks = [
            (_nearest(idx, int(t["i"])), 1 if float(t["qty"]) > 0 else -1)
            for t in s.get("trades") or []
            if t.get("qty")
        ]
        price_chart = emailchart.line(
            points,
            labels,
            total_px=84,
            col_w=9,
            zero=False,
            fmt=lambda v, c=cur: _price_axis(v, c),
            level=s.get("avg_cost"),
            marks=marks,
        )
        pnl = list(s.get("pnl") or [])
        pnl_points, _ = _sample(pnl, 52)
        pnl_now = next((v for v in reversed(pnl) if v is not None), None)
        pnl_chart = emailchart.line(pnl_points, total_px=64, col_w=9, fmt=man)
        stats = " · ".join(
            t
            for t in (
                _stat("数量", jpy(p["qty"])),
                _stat("評価", jpy(p["value"])),
                _stat("比率", f"{float(p['weight']):.1f}%"),
                _stat("平均", price(p["avg_cost"], cur)) if p.get("avg_cost") is not None else "",
                _stat("1W", pct(p.get("chg1w"), 1), _tone(p.get("chg1w"))),
                _stat("1M", pct(p.get("chg1m"), 1), _tone(p.get("chg1m"))),
                _stat("1Y", pct(p.get("chg1y"), 1), _tone(p.get("chg1y"))),
                _stat("含み", pct(p.get("unreal_pct"), 1), _tone(p.get("unreal_pct")))
                if p.get("unreal_pct") is not None
                else "",
            )
            if t
        )
        legend = "下の帯 橙 買 · 青 売" if marks else ""
        if s.get("avg_cost") is not None:
            legend = _joined(legend, "青線 平均取得")
        inner = (
            f'<table width="100%" cellspacing="0" cellpadding="0"><tr>'
            f'<td style="font:700 14px {SANS};color:{INK}">{html.escape(p["sym"])}</td>'
            f'<td align="right" style="font:400 12px {MONO};color:{INK};white-space:nowrap">'
            f'{price(p["last"], cur)} <span style="color:{MUTED};font-size:10px">{html.escape(cur)}</span> '
            f'<span style="color:{_tone(p["chg1d"])}">{pct(p["chg1d"])}</span></td></tr></table>'
            f'<div style="font:400 11px {SANS};color:{MUTED}">{html.escape(str(p.get("name", "")))} · {html.escape(p["acct"])}</div>'
            f'<div style="font:400 11px/1.7 {SANS};color:{MUTED};margin-top:4px">{stats}</div>'
            + _label(f"株価 · {w['start'][:7]} → {data['as_of'][:7]}", legend)
            + price_chart
            + _label(
                f"{html.escape(str(s.get('label', '損益')))} ¥ "
                f'<span style="color:{_tone(pnl_now)}">{jpy(pnl_now, True)}</span>'
            )
            + pnl_chart
        )
        out += f'<div style="padding-top:8px">{_card(inner, pad="11px 12px 10px")}</div>'
    if not out:
        return ""
    return _section("銘柄ごとの推移", "株価 1 年 · 損益") + out


def _spark(values: list[Any]) -> str:
    """A year of prices in 100px: 20 points, no axis — the shape, beside the numbers."""
    points, _ = _sample([v for v in values], 20)
    if len([v for v in points if v is not None]) < 2:
        return ""
    return emailchart.line(points, total_px=22, col_w=5, thickness=2, zero=False)


def _kpi_cell(
    label: str, value: str, sub: str, tone: str, sub2: str = "", dollars: str = ""
) -> str:
    in_usd = (
        f'<div style="font:400 12px {MONO};color:{MUTED};margin-top:1px">{html.escape(dollars)}</div>'
        if dollars
        else ""
    )
    second = (
        f'<div style="font:400 11px {SANS};color:{MUTED};margin-top:1px">{html.escape(sub2)}</div>'
        if sub2
        else ""
    )
    return (
        f'<td width="50%" bgcolor="{CARD}" style="padding:11px 13px;border:1px solid {RULE};'
        f'border-radius:8px;vertical-align:top">'
        f'<div style="font:500 10px {MONO};letter-spacing:.1em;color:{MUTED}">{html.escape(label)}</div>'
        f'<div style="font:600 21px {MONO};color:{tone};margin-top:5px">{value}</div>{in_usd}'
        f'<div style="font:400 11px {SANS};color:{MUTED};margin-top:3px">{html.escape(sub)}</div>{second}</td>'
    )


def _th(text: str, align: str = "right") -> str:
    return (
        f'<th align="{align}" style="padding:6px 8px;border-bottom:1px solid {RULE};'
        f'font:500 10px {MONO};letter-spacing:.06em;color:{MUTED};white-space:nowrap">{html.escape(text)}</th>'
    )


def _td(
    inner: str, align: str = "right", tone: str = INK, font: str | None = None, last: bool = False
) -> str:
    border = "" if last else f"border-bottom:1px solid {RULE};"
    return (
        f'<td align="{align}" style="padding:7px 8px;{border}'
        f"{f'font:400 12px {font};' if font else ''}"
        f'{f"color:{tone};" if tone != INK else ""}">{inner}</td>'
    )


ATTRIBUTION = (
    ("unrealized", "含み（保有中）"),
    ("realized", "実現（売却済）"),
    ("dividends", "配当 税引後"),
    ("fees", "費用"),
    ("fx_translation", "為替換算 現金"),
    ("forex", "為替取引"),
)


def _attribution(att: dict[str, Any] | None, table_style: str) -> str:
    """Where the overseas account's P&L came from, over the window and since inception."""
    if not att:
        return ""
    keys = [*ATTRIBUTION, ("total", "合計＝NAV−入金")]
    rows = ""
    for i, (key, label) in enumerate(keys):
        last = i == len(keys) - 1
        win, inc = att["window"].get(key), att["incept"].get(key)
        weight = "font-weight:700;" if key == "total" else ""
        rows += (
            f'<tr style="{weight}">'
            + _td(html.escape(label), "left", INK, SANS, last)
            + _td(jpy(win, True), "right", _tone(win), None, last)
            + _td(jpy(inc, True), "right", _tone(inc), None, last)
            + "</tr>"
        )
    return (
        _section("損益の内訳", "海外証券口座")
        + f'<table role="presentation" cellspacing="0" cellpadding="0" {table_style}>'
        + f"<tr>{_th('内訳', 'left')}{_th('期間内 ¥')}{_th('開設来 ¥')}</tr>{rows}</table>"
    )


def _closed(rows: list[dict[str, Any]] | None, table_style: str) -> str:
    """Positions sold out, with what each one realised."""
    if not rows:
        return ""
    total = sum(float(r["realized"]) for r in rows)
    body = ""
    for r in rows:
        body += (
            "<tr>"
            + _td(f"<b>{html.escape(r['sym'])}</b>", "left", INK, SANS)
            + _td(f"{r['first']} → {r['last']}", "left", MUTED)
            + _td(str(r["trades"]), "right", MUTED)
            + _td(jpy(r["realized"], True), "right", _tone(r["realized"]))
            + "</tr>"
        )
    body += (
        '<tr style="font-weight:700">'
        + _td("合計", "left", INK, SANS, True)
        + _td("", "left", INK, None, True)
        + _td("", "right", INK, None, True)
        + _td(jpy(total, True), "right", _tone(total), None, True)
        + "</tr>"
    )
    return (
        _section("決済済み", "海外証券口座 · 実現損益")
        + f'<table role="presentation" cellspacing="0" cellpadding="0" {table_style}>'
        + f"<tr>{_th('銘柄', 'left')}{_th('保有期間', 'left')}{_th('約定')}{_th('実現損益 ¥')}</tr>{body}</table>"
    )


def html_body(data: dict[str, Any], image_cid: str | None = None) -> str:
    h, w = data["headline"], data["window"]
    rate = data["fx"]["last"]
    kpis = (
        '<table role="presentation" cellspacing="6" cellpadding="0" style="border-collapse:separate;width:100%"><tr>'
        + _kpi_cell(
            "総資産 ¥",
            jpy(h["nav_total"]),
            f"時価評価 {int(h['quoted_share'] * 100)}%・残りは残高据え置き",
            INK,
            _joined(_nav_after_tax(h), usd(h.get("nav_after_tax"), rate)),
            usd(h["nav_total"], rate),
        )
        + _kpi_cell(
            "日次損益 ¥",
            jpy(h["day_pnl"], True),
            _joined(pct(h["day_pnl_pct"]), split(h.get("day_stock"), h.get("day_fx"))),
            _tone(h["day_pnl"]),
            _joined(after_tax(h.get("day_after_tax")), usd(h.get("day_after_tax"), rate, True)),
            usd(h["day_pnl"], rate, True),
        )
        + "</tr><tr>"
        + _kpi_cell(
            "含み損益 ¥",
            jpy(h["unrealized_known"], True),
            split(h.get("unreal_stock"), h.get("unreal_fx")) or "取得原価が分かる保有の合計",
            _tone(h["unrealized_known"]),
            _joined(
                after_tax(h.get("unreal_after_tax")), usd(h.get("unreal_after_tax"), rate, True)
            ),
            usd(h["unrealized_known"], rate, True),
        )
        + _kpi_cell(
            f"期間損益 ¥ · {w['days']}日",
            jpy(h["pnl_window"], True),
            f"海外証券口座 {w['start']} 以降・入金控除後",
            _tone(h["pnl_window"]),
            dollars=usd(h["pnl_window"], rate, True),
        )
        + "</tr><tr>"
        + _kpi_cell(
            "開設来損益 ¥",
            jpy(h.get("pnl_incept"), True),
            f"実現 {jpy(h.get('realized_cum'), True)} · 配当 {jpy(h.get('dividends_net'), True)}",
            _tone(h.get("pnl_incept")),
            dollars=usd(h.get("pnl_incept"), rate, True),
        )
        + _kpi_cell(
            "資金加重リターン",
            _xirr(h),
            f"最大DD（期間内） {_max_dd(h)}",
            _tone(h.get("xirr")),
        )
        + "</tr></table>"
    )
    acc_rows = ""
    for i, a in enumerate(data["accounts"]):
        last = i == len(data["accounts"]) - 1
        acc_rows += (
            "<tr>"
            + _td(html.escape(a["name"]), "left", INK, SANS, last)
            + _td(jpy(a["total"]) + _under(usd(a["total"], rate)), "right", INK, None, last)
            + _td(
                jpy(a["day_pnl"], True)
                + _split_cell(
                    a, "day_stock", "day_fx", "day_after_tax", usd(a["day_pnl"], rate, True)
                ),
                "right",
                _tone(a["day_pnl"]),
                None,
                last,
            )
            + _td(
                jpy(a["unrealized"], True)
                + _split_cell(
                    a,
                    "unreal_stock",
                    "unreal_fx",
                    "unreal_after_tax",
                    usd(a.get("unrealized"), rate, True),
                )
                if a.get("unrealized") is not None
                else "原価なし",
                "right",
                _tone(a.get("unrealized")),
                None if a.get("unrealized") is not None else SANS,
                last,
            )
            + "</tr>"
        )
    pos_rows = ""
    for i, p in enumerate(data["positions"]):
        last = i == len(data["positions"]) - 1
        name = (
            f'<div style="font:600 12px {SANS};color:{INK}">{html.escape(p["sym"])}</div>'
            f'<div style="font:400 10.5px {SANS};color:{MUTED};white-space:nowrap">{html.escape(p["acct"])}</div>'
        )
        unreal = (
            jpy(p["unreal"], True)
            + _split_cell(
                p, "unreal_stock", "unreal_fx", "unreal_after_tax", usd(p["unreal"], rate, True)
            )
            if p.get("unreal") is not None
            else "原価なし"
        )
        pos_rows += (
            "<tr>"
            + _td(name, "left", INK, SANS, last)
            + _td(pct(p["chg1d"]), "right", _tone(p["chg1d"]), None, last)
            + _td(_spark(p.get("spark") or []), "left", INK, None, last)
            + _td(pct(p["chg1y"], 1), "right", _tone(p["chg1y"]), None, last)
            + _td(jpy(p["value"]) + _under(usd(p["value"], rate)), "right", INK, None, last)
            + _td(
                jpy(p["day_pnl"], True)
                + _split_cell(
                    p, "day_stock", "day_fx", "day_after_tax", usd(p["day_pnl"], rate, True)
                ),
                "right",
                _tone(p["day_pnl"]),
                None,
                last,
            )
            + _td(
                unreal,
                "right",
                _tone(p.get("unreal")),
                None if p.get("unreal") is not None else SANS,
                last,
            )
            + "</tr>"
        )
    table_style = (
        f'bgcolor="{CARD}" style="border-collapse:collapse;width:100%;color:{INK};'
        f'font:400 12px {MONO};border:1px solid {RULE};border-radius:8px"'
    )
    # A rendered image of the dashboard's figures, when one is attached, stands in
    # for the drawn charts and cards (it holds the same figures).
    if image_cid:
        charts = _section("時系列", f"{w['start']} → {w['end']}") + _card(
            f'<img src="cid:{image_cid}" width="572" alt="NAV・累計損益・日次損益と銘柄ごとの株価チャート" '
            f'style="display:block;width:100%;max-width:572px;height:auto;border-radius:4px">',
            pad="6px",
        )
    else:
        charts = _charts(data) + _cards(data)
    quoted = int(h["quoted_share"] * 100)
    tape = " &nbsp; ".join(
        f'<span style="white-space:nowrap"><b style="color:{INK}">{html.escape(t["sym"])}</b> '
        f'{price(t["last"], t.get("cur", "USD"))} <span style="color:{_tone(t["chg_pct"])}">{pct(t["chg_pct"])}</span></span>'
        for t in data.get("tape") or []
    )
    allocation = ""
    if data.get("allocation"):
        allocation = _section("資産配分", "総資産比") + _card(
            emailchart.shares(
                [
                    (a["label"], a["pct"], f"{float(a['pct']):.1f}% · {jpy(a['value'])}")
                    for a in data["allocation"]
                ],
                width=260,
            )
        )
    notes = "".join(f'<li style="margin:0 0 4px">{html.escape(n)}</li>' for n in _notes(data))
    return f"""<table width="100%" cellspacing="0" cellpadding="0" bgcolor="{GROUND}"><tr>
<td style="padding:18px 12px;font-family:{SANS};color:{INK}">
<div style="max-width:600px;margin:0 auto">
<div style="font:400 11px {MONO};letter-spacing:.12em;color:{MUTED}">DAILY MARK-TO-MARKET</div>
<div style="font:700 20px/1.3 Georgia,serif;margin:6px 0 2px">日次損益 {html.escape(data["as_of"] + _edition(data))}</div>
<div style="font:400 12px {SANS};color:{MUTED};margin-bottom:14px">USD/JPY {float(data["fx"]["last"]):.2f}（{pct(data["fx"]["chg_pct"])}）· 生成 {html.escape(str(data["generated_at"])[:16].replace("T", " "))}</div>
{f'<div style="font:400 11.5px/1.8 {MONO};color:{MUTED};margin-bottom:12px">{tape}</div>' if tape else ""}
{kpis}
{_section("口座別", "評価額 / 日次 / 含み")}
<table role="presentation" cellspacing="0" cellpadding="0" {table_style}>
<tr>{_th("口座", "left")}{_th("評価額 ¥")}{_th("日次損益 ¥")}{_th("含み損益 ¥")}</tr>{acc_rows}</table>
{allocation}
{_attribution(data.get("attribution"), table_style)}
{_section("保有", "評価額の大きい順 · 1Y は直近 1 年の株価")}
<table role="presentation" cellspacing="0" cellpadding="0" {table_style}>
<tr>{_th("銘柄", "left")}{_th("1D")}{_th("値動き 1Y", "left")}{_th("1Y")}{_th("評価額 ¥")}{_th("日次 ¥")}{_th("含み ¥")}</tr>{pos_rows}</table>
{_closed(data.get("closed"), table_style)}
{charts}
<div style="font:400 11px/1.7 {SANS};color:{MUTED};margin-top:16px">
日次損益は全銘柄に共通の直近 2 営業日で比べた差（価格と為替の両方）で、まだ開いていない市場の銘柄は株の変化 0。株＝価格の変化（今日のレート換算）、FX＝残り（レートの変化分）で、円建ては FX 0。含み損益の FX は取得原価（外貨）×（現在レート − 取得時レート）。総資産の {100 - quoted}% は時価が取れない残高（現金など）で据え置き。海外証券口座の累計損益は取引履歴を日次で再生した値で、入金は差し引いています。
<ul style="margin:8px 0 0;padding-left:18px">{notes}</ul>
ダッシュボード本体（ホバーで数値が出る図つき）: <span style="font-family:{MONO}">Documents\\pl-daily\\latest.html</span>
</div></div></td></tr></table>"""


def build_message(
    data: dict[str, Any],
    to: list[str],
    sender: str,
    png: bytes | None,
    cid: str | None = None,
) -> EmailMessage:
    """RFC 5322 message: plain text, HTML, and the chart PNG inline when given."""
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    msg["Subject"] = subject(data)
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    image_cid = None
    if png is not None:
        image_cid = cid or "charts"
    msg.set_content(text_body(data))
    msg.add_alternative(html_body(data, image_cid), subtype="html")
    if png is not None:
        html_part = msg.get_payload()[-1]
        html_part.add_related(
            png,
            maintype="image",
            subtype="png",
            cid=f"<{image_cid}>",
            filename=f"pl-{data['as_of']}.png",
            disposition="inline",
        )
    return msg


def send(
    msg: EmailMessage,
    host: str,
    port: int,
    user: str,
    password: str,
    timeout: int = 60,
) -> None:
    """Deliver over SMTP. Port 465 uses implicit TLS, anything else STARTTLS."""
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=timeout) as server:
            server.login(user, password)
            server.send_message(msg)
        return
    with smtplib.SMTP(host, port, timeout=timeout) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
