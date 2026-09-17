"""Compose and send the daily P&L email.

The mail carries what the dashboard shows: the headline, accounts, allocation,
the P&L attribution, holdings, closed positions, the time series, a card per
position and the notes. The dashboard's charts are drawn by JavaScript, and every
mail client strips scripts and inline SVG, so the email redraws them with
coloured table cells (see ``emailchart``) when no browser is at hand. Normally
each chart is instead the dashboard's own drawing, cut out of a headless
screenshot (``chartshot.render_pieces``) and attached inline: sent over SMTP,
Gmail shows ``cid:`` images in the body.

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


def preheader(data: dict[str, Any]) -> str:
    """The inbox preview line: the numbers, not the mail's heading repeated after the subject."""
    h = data["headline"]
    breaches = (data.get("risk") or {}).get("policy_breaches")
    return _joined(
        f"総資産 {jpy(h['nav_total'])} 円",
        f"日次 {jpy(h['day_pnl'], True)} 円（{pct(h['day_pnl_pct'])}）",
        f"含み {jpy(h['unrealized_known'], True)} 円",
        f"限度超過 {breaches} 件" if breaches else "",
    )


def _nav_after_tax(h: dict[str, Any]) -> str:
    """Total assets after the estimated tax on unrealised gains (unsigned: it is a balance)."""
    return "" if h.get("nav_after_tax") is None else f"税引後 {jpy(h['nav_after_tax'])}"


def _warning_box(data: dict[str, Any]) -> str:
    """Problems with this run itself (not the portfolio), at the top where they are seen.
    Colour by attribute and longhand CSS only: Gmail strips the ``background`` shorthand."""
    warnings = [str(w) for w in data.get("warnings") or []]
    if not warnings:
        return ""
    items = "<br>".join(html.escape(w) for w in warnings)
    return (
        f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" bgcolor="{CARD}" '
        f'style="border-left:3px solid {UP};margin:0 0 12px"><tr>'
        f'<td style="padding:8px 12px;font:400 12px/1.7 {SANS};color:{INK}"><b>このメールの注意</b><br>{items}</td>'
        "</tr></table>"
    )


def text_body(data: dict[str, Any]) -> str:
    h, w = data["headline"], data["window"]
    rate = data["fx"]["last"]
    lines = [
        f"日次損益 {data['as_of']}{_edition(data)}  (USD/JPY {float(data['fx']['last']):.2f})",
        *[f"! {warning}" for warning in data.get("warnings") or []],
        "",
        f"総資産          {jpy(h['nav_total']):>14} 円  {usd(h['nav_total'], rate):>10}  (時価評価 {int(h['quoted_share'] * 100)}%)",
        f"                {_nav_after_tax(h)}",
        f"日次損益        {jpy(h['day_pnl'], True):>14} 円  {usd(h['day_pnl'], rate, True):>10}  ({pct(h['day_pnl_pct'])})",
        f"                {_joined(split(h.get('day_stock'), h.get('day_fx')), after_tax(h.get('day_after_tax')))}",
        f"期間損益 {w['days']}日  {jpy(h['pnl_window'], True):>14} 円  {usd(h['pnl_window'], rate, True):>10}  (全口座・入金控除後)",
        f"含み損益        {jpy(h['unrealized_known'], True):>14} 円  {usd(h['unrealized_known'], rate, True):>10}  (原価が台帳にある保有)",
        f"                {_joined(split(h.get('unreal_stock'), h.get('unreal_fx')), after_tax(h.get('unreal_after_tax')))}",
        f"開設来損益      {jpy(h.get('pnl_incept'), True):>14} 円  {usd(h.get('pnl_incept'), rate, True):>10}  (実現 {jpy(h.get('realized_cum'), True)} · 配当 {jpy(h.get('dividends_net'), True)})",
        f"資金加重リターン {_xirr(h):>13}  ({h.get('xirr_scope') or '—'})  最大DD（期間内） {_max_dd(h)}",
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
    r = data.get("risk")
    if r:
        s, c = r["stats"], r["concentration"]
        lines += [
            "",
            f"リスク: ボラ {_ratio(s['vol_annual'])}, VaR(1日95%) {jpy(s['var_1d_95_jpy'])}, "
            f"ES(97.5%) {jpy(s['es_1d_975_jpy'])}, 外貨 {_ratio(c['foreign_currency_ratio'])}, "
            f"最大ルックスルー銘柄 {c.get('largest_issuer') or '—'} {_ratio(c['largest_issuer_lookthrough_ratio'])}, "
            f"超過 {r.get('policy_breaches') or 0}",
        ]
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
        f'<td align="right" style="font:400 11px {MONO};color:{MUTED}">{html.escape(sub)}</td>'
        if sub
        else ""
    )
    return (
        f'<table width="100%" cellspacing="0" cellpadding="0" style="margin:22px 0 6px"><tr>'
        f'<td style="font:700 13px {SANS};color:{INK};white-space:nowrap;padding-right:8px">'
        f"{html.escape(title)}</td>{right}</tr></table>"
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


Images = dict[str, tuple[str, int, int]]  # chart name -> (content id, width, height in CSS px)


def _img(
    images: Images | None, name: str, alt: str = "", fluid: bool = True, width: int | None = None
) -> str:
    """The dashboard's own drawing of a chart, attached inline; empty when there is none.

    ``fluid`` lets it shrink with a narrow screen; ``width`` shows it at that fixed width.
    """
    if not images or name not in images:
        return ""
    cid, w, h = images[name]
    if width:
        w, h = width, round(h * width / w)
    size = f"width:100%;max-width:{w}px;height:auto;" if fluid else ""
    return (
        f'<img src="cid:{html.escape(cid)}" width="{w}" height="{h}" alt="{html.escape(alt)}" '
        f'style="display:block;{size}border:0">'
    )


def _charts(data: dict[str, Any], images: Images | None = None) -> str:
    """The time series: the dashboard's drawings when attached, else table-cell charts."""
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
        out += _section("NAV と累計入金", f"全口座 · {w.get('start', '')} → {w.get('end', '')}")
        drawn = _img(images, "nav", "全口座の NAV と累計入金") or emailchart.line(
            points, labels, total_px=120, col_w=10, zero=False, fmt=man_level, overlay=overlay
        )
        out += _card(
            drawn
            + _caption(
                f'<span style="color:{UP}">━</span> NAV <b>{jpy(nav[-1])}</b> 円 · '
                f'<span style="color:{DN}">┅</span> 累計入金 {jpy(deposits[-1] if deposits else None)} 円。'
                "入金は段差になります。"
            )
        )
    pnl = list(series.get("pnl") or [])
    if pnl:
        points, idx = _sample(pnl, 52)
        labels = [dates[i] for i in idx] if dates else None
        known = [v for v in pnl if v is not None]
        last = next((v for v in reversed(points) if v is not None), None)
        out += _section("累計損益", f"全口座 · {w.get('start', '')} → {w.get('end', '')}")
        out += _card(
            (
                _img(images, "pnl", "全口座の累計損益")
                or emailchart.line(points, labels, total_px=120, col_w=10, fmt=man)
            )
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
        out += _section("日次損益", f"全口座 · 期間 {len(daily)} 営業日")
        out += _card(
            (
                _img(images, "daily", "日次損益の棒グラフ")
                or emailchart.columns(
                    daily,
                    labels,
                    total_px=110,
                    col_w=step - gap,
                    gap=gap,
                    fmt=man,
                    months=None if len(daily) < 60 else emailchart.QUARTERS,
                )
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


def _cards(data: dict[str, Any], images: Images | None = None) -> str:
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
        price_chart = _img(images, f"price:{key}", f"{p['sym']} の株価") or emailchart.line(
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
        pnl_chart = _img(images, f"pnlc:{key}", f"{p['sym']} の損益") or emailchart.line(
            pnl_points, total_px=64, col_w=9, fmt=man
        )
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
        drawn = bool(images and f"price:{key}" in images)
        legend = ("▲ 買 ▼ 売" if drawn else "下の帯 橙 買 · 青 売") if marks else ""
        if s.get("avg_cost") is not None:
            legend = _joined(legend, "点線 平均取得" if drawn else "青線 平均取得")
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
        f'<td width="50%" bgcolor="{CARD}" style="padding:10px 12px;border:1px solid {RULE};'
        f'border-radius:8px;vertical-align:top">'
        f'<div style="font:500 10px {MONO};letter-spacing:.1em;color:{MUTED}">{html.escape(label)}</div>'
        f'<div style="font:600 17px {MONO};color:{tone};margin-top:4px">{value}</div>{in_usd}'
        f'<div style="font:400 11px {SANS};color:{MUTED};margin-top:3px">{html.escape(sub)}</div>{second}</td>'
    )


# Holdings as fixed-width blocks instead of table columns: in a 600px column the four sit in
# one row; on a phone they wrap two by two, and every row (the head too) wraps the same way,
# so the figures still line up. A 7-column table needs ~594px and makes Gmail's app shrink
# the whole mail to fit.
HOLDING_WIDTHS = (150, 130, 150, 130)


def _holding_block(inner: str, width: int, align: str, color: str, pad: str = "7px 0") -> str:
    tone = f"color:{color};" if color != INK else ""
    return (
        f'<div style="display:inline-block;vertical-align:top;width:{width}px;'
        f'text-align:{align};padding:{pad};{tone}">{inner}</div>'
    )


def _holding_head() -> str:
    labels = ("銘柄 · 1D · 1Y", "評価額 ¥", "日次 ¥", "含み ¥")
    blocks = "".join(
        _holding_block(label, width, "left" if n == 0 else "right", MUTED, pad="6px 0 5px")
        for n, (label, width) in enumerate(zip(labels, HOLDING_WIDTHS, strict=True))
    )
    return (
        f'<div style="border-bottom:1px solid {RULE};font:500 10px {MONO};'
        f'letter-spacing:.06em">{blocks}</div>'
    )


def _holding_row(cells: tuple[tuple[str, str], ...], last: bool) -> str:
    blocks = "".join(
        _holding_block(inner, width, "left" if n == 0 else "right", color)
        for n, ((inner, color), width) in enumerate(zip(cells, HOLDING_WIDTHS, strict=True))
    )
    border = "" if last else f"border-bottom:1px solid {RULE};"
    return f'<div style="{border}font:400 12px {MONO}">{blocks}</div>'


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


def _attribution(
    att: dict[str, Any] | None, table_style: str, names: dict[str, str] | None = None
) -> str:
    """The P&L buckets over the window and since inception, then each account's total."""
    if not att:
        return ""
    names = names or {}
    entries = [
        (label, att["window"].get(key), att["incept"].get(key), key == "total")
        for key, label in [*ATTRIBUTION, ("total", "合計＝NAV−入金")]
    ]
    entries += [
        (f"　{names.get(acc, acc)}", a["window"].get("total"), a["incept"].get("total"), False)
        for acc, a in (att.get("accounts") or {}).items()
    ]
    rows = ""
    for i, (label, win, inc, bold) in enumerate(entries):
        last = i == len(entries) - 1
        weight = "font-weight:700;" if bold else ""
        rows += (
            f'<tr style="{weight}">'
            + _td(html.escape(label), "left", INK, SANS, last)
            + _td(jpy(win, True), "right", _tone(win), None, last)
            + _td(jpy(inc, True), "right", _tone(inc), None, last)
            + "</tr>"
        )
    return (
        _section("損益の内訳", "全口座 · 下段は口座別")
        + f'<table role="presentation" cellspacing="0" cellpadding="0" {table_style}>'
        + f"<tr>{_th('内訳', 'left')}{_th('期間内 ¥')}{_th('開設来 ¥')}</tr>{rows}</table>"
    )


def _ratio(value: float | None, digits: int = 1) -> str:
    """A fraction as an unsigned percentage: 0.323 → 32.3%."""
    return "—" if value is None else f"{float(value) * 100:.{digits}f}%"


def _delta(cur: float | None, prev: float | None, unit: str = "pt", digits: int = 1) -> str:
    """前日比 under a risk figure; empty when either side is unknown."""
    if cur is None or prev is None:
        return ""
    d = (float(cur) - float(prev)) * (100 if unit == "pt" else 1)
    text = f"{d:+.{digits}f}".replace("-", "−")
    return _under(f"前日比 {text}{unit if unit == 'pt' else ''}")


def _limit_value(metric: str, value: float | None) -> str:
    if value is None:
        return "—"
    # whole words: "largest_foreign_country_ratio" contains "count" but is a share
    words = set(metric.split("_"))
    return f"{float(value):.1f}" if words & {"effective", "count"} else _ratio(value)


def _heading(text: str) -> str:
    return (
        f'<div style="font:500 10px {MONO};letter-spacing:.08em;color:{MUTED};margin:10px 0 3px">'
        f"{html.escape(text)}</div>"
    )


def _risk(data: dict[str, Any], table_style: str) -> str:
    """The risk section: limits, look-through exposures, statistics, contributions and stress."""
    r = data.get("risk")
    if not r:
        return ""
    s, c, x, rc, st = (
        r["stats"],
        r["concentration"],
        r["exposures"],
        r["contributions"],
        r["stress"],
    )
    prev = s.get("prev") or {}
    beta = s.get("beta") or {}
    chips = ""
    for lim in r.get("policy") or []:
        breach = lim["status"] == "breach"
        color = DN if breach else MUTED
        chips += (
            f'<span style="display:inline-block;border:1px solid {DN if breach else RULE};color:{color};'
            f'border-radius:999px;padding:2px 9px;margin:0 4px 4px 0;font:{700 if breach else 400} 11px {SANS}">'
            f"{'超過 ' if breach else ''}{html.escape(lim['label'])} · {_limit_value(lim['metric'], lim['value'])}"
            f" / {html.escape(lim['operator'])} {_limit_value(lim['metric'], lim['threshold'])}</span>"
        )
    breaches = r.get("policy_breaches") or 0
    out = '<div id="risk"></div>' + _section(
        "リスク", f"ルックスルー · 直近 {int(s.get('window_days') or 0)} 営業日 · 現在ウェイト"
    )
    out += _card(
        f'<div style="font:600 12px {SANS};color:{DN if breaches else INK};margin-bottom:6px">'
        f"限度 · {'超過 ' + str(breaches) + ' 件' if breaches else '超過なし'}</div>{chips}"
        f'<div style="font:400 10.5px {SANS};color:{MUTED}">参照ファイルのポリシー（draft）· 値 / 限度</div>'
    )
    # the asset-class split is the 資産配分 card above; the mail adds the other three
    exposures = "".join(
        _heading(title)
        + emailchart.shares(
            [(e["label"], e["pct"], f"{_ratio(e['pct'])} · {jpy(e['value'])}") for e in x[key][:5]],
            width=170,
        )
        for key, title in (("currency", "通貨"), ("region", "国・地域"), ("sector", "セクター"))
    )
    out += _section(
        "エクスポージャー", "ルックスルー後 · 総資産比 · DC は構成比で按分（推定）"
    ) + _card(exposures)
    issuers = x["issuers"][:6]
    rows = ""
    for i, e in enumerate(issuers):
        last = i == len(issuers) - 1
        rows += (
            "<tr>"
            + _td(
                html.escape(e["label"]) + _under(html.escape(e.get("country") or "")),
                "left",
                INK,
                SANS,
                last,
            )
            + _td(html.escape(" · ".join(e["via"])), "left", MUTED, SANS, last)
            + _td(_ratio(e["pct"]), "right", INK, None, last)
            + "</tr>"
        )
    coverage = (x.get("coverage") or {}).get("issuer")
    out += _section(
        "ルックスルー上位銘柄", f"直接保有 ＋ ETF 経由 · 発行体カバー率 {_ratio(coverage, 0)}"
    )
    out += (
        f'<table role="presentation" cellspacing="0" cellpadding="0" {table_style}>'
        f"<tr>{_th('発行体', 'left')}{_th('経由', 'left')}{_th('比率')}</tr>{rows}</table>"
    )
    worst = s.get("worst_day") or {}

    def num(v: float | None) -> str:
        return "—" if v is None else f"{v:.2f}"

    stat_rows = [
        (
            "年率ボラティリティ",
            _ratio(s["vol_annual"]) + _delta(s["vol_annual"], prev.get("vol_annual")),
        ),
        (
            "VaR 1日 95%",
            f"{jpy(s['var_1d_95_jpy'])}"
            + _under(_ratio(s["var_1d_95"], 2))
            + _delta(s["var_1d_95"], prev.get("var_1d_95"), digits=2),
        ),
        ("VaR 1日 99%", f"{jpy(s['var_1d_99_jpy'])}" + _under(_ratio(s["var_1d_99"], 2))),
        (
            "ES 97.5%",
            f"{jpy(s['es_1d_975_jpy'])}"
            + _under(_ratio(s["es_1d_975"], 2))
            + _delta(s["es_1d_975"], prev.get("es_1d_975"), digits=2),
        ),
        (
            "VaR 20日 95%（√20 換算）",
            f"{jpy(s['var_20d_95_jpy'])}" + _under(_ratio(s["var_20d_95"])),
        ),
        (
            "最悪日（窓内）",
            jpy(worst.get("pnl_jpy"), True)
            + _under(
                f"{html.escape(str(worst.get('date') or '—'))} · {pct(None if worst.get('pct') is None else worst['pct'] * 100)}"
            ),
        ),
        (
            "ベータ TOPIX",
            num(beta.get("topix"))
            + _delta(beta.get("topix"), prev.get("beta_topix"), unit="", digits=2),
        ),
        (
            "ベータ S&P 500（現地通貨）",
            num(beta.get("sp500"))
            + _delta(beta.get("sp500"), prev.get("beta_sp500"), unit="", digits=2),
        ),
        (
            "ベータ USD/JPY",
            num(beta.get("usdjpy"))
            + _delta(beta.get("usdjpy"), prev.get("beta_usdjpy"), unit="", digits=2),
        ),
        (
            "外貨エクスポージャー",
            _ratio(c["foreign_currency_ratio"])
            + _delta(c["foreign_currency_ratio"], prev.get("foreign_currency_ratio")),
        ),
        (
            "最大ルックスルー銘柄",
            f"{html.escape(c.get('largest_issuer') or '—')} {_ratio(c['largest_issuer_lookthrough_ratio'])}"
            + _delta(
                c["largest_issuer_lookthrough_ratio"], prev.get("largest_issuer_lookthrough_ratio")
            ),
        ),
        (
            "最大セクター",
            f"{html.escape(c.get('max_sector') or '—')} {_ratio(c['max_sector_ratio'])}"
            + _delta(c["max_sector_ratio"], prev.get("max_sector_ratio")),
        ),
        (
            "実効数（銘柄 · セクター · 通貨 · 国・地域）",
            " · ".join(
                "—" if c.get(k) is None else f"{c[k]:.1f}"
                for k in (
                    "effective_positions",
                    "effective_sectors",
                    "effective_currencies",
                    "effective_countries",
                )
            ),
        ),
    ]
    rows = ""
    for i, (label, value) in enumerate(stat_rows):
        last = i == len(stat_rows) - 1
        rows += (
            "<tr>"
            + _td(html.escape(label), "left", INK, SANS, last)
            + _td(value, "right", INK, None, last)
            + "</tr>"
        )
    out += _section("リスク量", "過去シミュレーション · 前日比は前回レポート比")
    out += (
        f'<table role="presentation" cellspacing="0" cellpadding="0" {table_style}>{rows}</table>'
    )
    positions = rc["positions"][:6]
    rows = ""
    for i, p in enumerate(positions):
        last = i == len(positions) - 1
        rows += (
            "<tr>"
            + _td(html.escape(p["sym"]), "left", INK, SANS, last)
            + _td(_ratio(p["weight"]), "right", INK, None, last)
            + _td(f"<b>{_ratio(p['risk_share'])}</b>", "right", INK, None, last)
            + _td(_ratio(p.get("vol_annual")), "right", MUTED, None, last)
            + "</tr>"
        )
    buckets = "".join(
        _heading(title)
        + f'<div style="font:400 11.5px/1.7 {SANS};color:{INK}">'
        + " · ".join(
            f"{html.escape(b['label'])} <b>{_ratio(b['risk_share'])}</b>"
            f'<span style="color:{MUTED}">（比率 {_ratio(b.get("weight"))}）</span>'
            for b in rc[key][:3]
        )
        + "</div>"
        for key, title in (("currency", "通貨"), ("sector", "セクター"), ("region", "国・地域"))
    )
    out += _section("リスク寄与", "分散への寄与 w·Σw / σ² · 合計 100%")
    out += (
        f'<table role="presentation" cellspacing="0" cellpadding="0" {table_style}>'
        f"<tr>{_th('銘柄', 'left')}{_th('比率')}{_th('リスク寄与')}{_th('単独ボラ')}</tr>{rows}</table>"
        + _card(buckets, pad="4px 14px 10px")
    )
    scenarios = st["scenarios"]
    shown = scenarios[:5] + [e for e in scenarios[5:] if e["kind"] == "historical"]
    kinds = {"historical": "過去局面の換算", "compound": "複合", "hypothetical": "単一"}
    stress = emailchart.strips(
        [
            (
                f"{e['label']}（{kinds.get(e['kind'], e['kind'])}）",
                (e["impact_pct"] or 0) * 100,
                f"{pct((e['impact_pct'] or 0) * 100, 1)} · {jpy(e['impact_jpy'], True)}",
            )
            for e in shown
        ]
    )
    episodes = emailchart.strips(
        [
            (
                f"{e['label']} {e['start']} → {e['end']}",
                (e["impact_pct"] or 0) * 100,
                f"{pct((e['impact_pct'] or 0) * 100, 1)} · {jpy(e['impact_jpy'], True)} · カバー率 {_ratio(e.get('coverage'), 0)}",
            )
            for e in st["episodes"]
        ]
    )
    out += _section("ストレス", "ファクター換算のシナリオ · 実測リプレイの局面") + _card(
        _heading("シナリオ（参照ファイル）")
        + stress
        + _heading("過去局面のリプレイ · 開始前日の終値 → 終了日の終値 · 現在の保有で")
        + (episodes if st["episodes"] else _caption("価格履歴が届く局面はありません"))
    )
    return out


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


def html_body(data: dict[str, Any], images: Images | None = None) -> str:
    """The mail's HTML. ``images`` maps chart names to attached drawings of the dashboard."""
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
            f"全口座 {w['start']} 以降・入金控除後",
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
            f"{h.get('xirr_scope') or '—'} · 最大DD（期間内） {_max_dd(h)}",
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
            f'<div style="font:400 11px {MONO};color:{MUTED};white-space:nowrap;margin:2px 0">'
            f'1D <span style="color:{_tone(p["chg1d"])}">{pct(p["chg1d"])}</span> · '
            f'1Y <span style="color:{_tone(p["chg1y"])}">{pct(p["chg1y"], 1)}</span></div>'
            + (
                _img(images, f"spark:{p.get('key', p['sym'])}", fluid=False, width=64)
                or _spark(p.get("spark") or [])
            )
        )
        unreal = (
            jpy(p["unreal"], True)
            + _split_cell(
                p, "unreal_stock", "unreal_fx", "unreal_after_tax", usd(p["unreal"], rate, True)
            )
            if p.get("unreal") is not None
            else "原価なし"
        )
        pos_rows += _holding_row(
            (
                (name, INK),
                (jpy(p["value"]) + _under(usd(p["value"], rate)), INK),
                (
                    jpy(p["day_pnl"], True)
                    + _split_cell(
                        p, "day_stock", "day_fx", "day_after_tax", usd(p["day_pnl"], rate, True)
                    ),
                    _tone(p["day_pnl"]),
                ),
                (unreal, _tone(p.get("unreal"))),
            ),
            last,
        )
    table_style = (
        f'bgcolor="{CARD}" style="border-collapse:collapse;width:100%;color:{INK};'
        f'font:400 12px {MONO};border:1px solid {RULE};border-radius:8px"'
    )
    charts = _charts(data, images) + _cards(data, images)
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
<td style="padding:16px 12px;font-family:{SANS};color:{INK};-webkit-text-size-adjust:100%">
<div style="display:none;max-height:0;overflow:hidden;mso-hide:all">{html.escape(preheader(data))}</div>
<div style="max-width:600px;margin:0 auto">
<div style="font:400 10px {MONO};letter-spacing:.12em;color:{MUTED}">DAILY MARK-TO-MARKET</div>
<div style="font:700 15px/1.4 {SANS};margin:4px 0 1px">日次損益 {html.escape(data["as_of"] + _edition(data))}</div>
<div style="font:400 11.5px {SANS};color:{MUTED};margin-bottom:12px">USD/JPY {float(data["fx"]["last"]):.2f}（{pct(data["fx"]["chg_pct"])}）· 生成 {html.escape(str(data["generated_at"])[:16].replace("T", " "))}</div>
{_warning_box(data)}
{f'<div style="font:400 11.5px/1.8 {MONO};color:{MUTED};margin-bottom:12px">{tape}</div>' if tape else ""}
{kpis}
{_section("口座別", "評価額 / 日次 / 含み")}
<table role="presentation" cellspacing="0" cellpadding="0" {table_style}>
<tr>{_th("口座", "left")}{_th("評価額 ¥")}{_th("日次損益 ¥")}{_th("含み損益 ¥")}</tr>{acc_rows}</table>
{allocation}
{_risk(data, table_style)}
{_attribution(data.get("attribution"), table_style, {a["id"]: a["name"] for a in data.get("accounts") or []})}
{_section("保有", "評価額の大きい順 · 1Y は直近 1 年の株価")}
{_card(_holding_head() + pos_rows, pad="0 10px")}
{_closed(data.get("closed"), table_style)}
{charts}
<div style="font:400 11px/1.7 {SANS};color:{MUTED};margin-top:16px">
日次損益は全銘柄に共通の直近 2 営業日で比べた差（価格と為替の両方）で、まだ開いていない市場の銘柄は株の変化 0。株＝価格の変化（今日のレート換算）、FX＝残り（レートの変化分）で、円建ては FX 0。含み損益の FX は取得原価（外貨）×（現在レート − 取得時レート）。総資産の {100 - quoted}% は時価が取れない残高（現金など）で据え置き。累計損益は 3 口座の NAV − 累計入金（海外は取引履歴、国内は取引 CSV、DC は掛金履歴を日次で再生）。
<ul style="margin:8px 0 0;padding-left:18px">{notes}</ul>
ダッシュボード本体（ホバーで数値が出る図つき）: <span style="font-family:{MONO}">Documents\\pl-daily\\latest.html</span>
</div></div></td></tr></table>"""


def build_message(
    data: dict[str, Any],
    to: list[str],
    sender: str,
    pieces: dict[str, tuple[bytes, int, int]] | None = None,
) -> EmailMessage:
    """RFC 5322 message: plain text, HTML, and each chart's PNG inline when given.

    ``pieces`` maps a chart name to (png, width, height) as ``chartshot.render_pieces``
    returns them; any chart without one is drawn with table cells instead.
    """
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    msg["Subject"] = subject(data)
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    images: Images = {
        name: (f"chart{i}.{data['as_of']}@pl-daily", w, h)
        for i, (name, (_, w, h)) in enumerate((pieces or {}).items())
    }
    msg.set_content(text_body(data))
    msg.add_alternative(html_body(data, images), subtype="html")
    if pieces:
        html_part = msg.get_payload()[-1]
        for name, (png, _, _) in pieces.items():
            html_part.add_related(
                png,
                maintype="image",
                subtype="png",
                cid=f"<{images[name][0]}>",
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
