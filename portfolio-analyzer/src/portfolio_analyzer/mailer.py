"""Compose and send the daily P&L email.

The dashboard's charts are drawn by JavaScript, and every mail client strips
scripts and inline SVG, so the email redraws them with coloured table cells (see
``emailchart``) — that keeps the figures in the body itself, where a ``cid:``
image cannot be relied on: Gmail rewrites the Content-ID of an attached picture,
which turns a hand-written reference into a plain attachment. A rendered PNG of
the full dashboard section can still ride along as an opt-in inline image.

Credentials never live in this file: ``send`` takes them from the caller, which
reads them from the environment (see ``scripts/daily_pl_report.py``).
"""

from __future__ import annotations

import html
import smtplib
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


def _tone(value: float | None) -> str:
    if value is None or float(value) == 0:
        return MUTED
    return UP if float(value) > 0 else DN


def split(stock: float | None, fx: float | None, sep: str = " · ") -> str:
    """Stock and FX parts of a JPY P&L, e.g. ``株 +12,000 · FX −3,506``; empty when unknown."""
    if stock is None and fx is None:
        return ""
    return f"株 {jpy(stock, True)}{sep}FX {jpy(fx, True)}"


def after_tax(value: float | None, label: str = "税引後") -> str:
    return "" if value is None else f"{label} {jpy(value, True)}"


def _joined(*parts: str, sep: str = " · ") -> str:
    return sep.join(p for p in parts if p)


def _split_cell(row: dict[str, Any], stock: str, fx: str, taxed: str) -> str:
    """The split and the after-tax figure under a table cell's value, one per line."""
    text = _joined(
        split(row.get(stock), row.get(fx), "<br>"), after_tax(row.get(taxed), "税後"), sep="<br>"
    )
    if not text:
        return ""
    return (
        f'<div style="font-size:10px;line-height:1.4;color:{MUTED};white-space:nowrap">{text}</div>'
    )


def decode_header_text(raw: str | None) -> str:
    """Decode an RFC 2047 header back to text (used by the tests and by log output)."""
    return "" if raw is None else str(make_header(decode_header(raw)))


def subject(data: dict[str, Any]) -> str:
    h = data["headline"]
    return f"日次損益 {data['as_of']} · {jpy(h['nav_total'])} 円（{jpy(h['day_pnl'], True)}）"


def _nav_after_tax(h: dict[str, Any]) -> str:
    """Total assets after the estimated tax on unrealised gains (unsigned: it is a balance)."""
    return "" if h.get("nav_after_tax") is None else f"税引後 {jpy(h['nav_after_tax'])}"


def text_body(data: dict[str, Any]) -> str:
    h, w = data["headline"], data["window"]
    lines = [
        f"日次損益 {data['as_of']}  (USD/JPY {float(data['fx']['last']):.2f})",
        "",
        f"総資産          {jpy(h['nav_total']):>14} 円  (時価評価 {int(h['quoted_share'] * 100)}%)",
        f"                {_nav_after_tax(h)}",
        f"日次損益        {jpy(h['day_pnl'], True):>14} 円  ({pct(h['day_pnl_pct'])})",
        f"                {_joined(split(h.get('day_stock'), h.get('day_fx')), after_tax(h.get('day_after_tax')))}",
        f"期間損益 {w['days']}日  {jpy(h['pnl_window'], True):>14} 円  (海外証券口座・入金控除後)",
        f"含み損益        {jpy(h['unrealized_known'], True):>14} 円  (原価が台帳にある保有)",
        f"                {_joined(split(h.get('unreal_stock'), h.get('unreal_fx')), after_tax(h.get('unreal_after_tax')))}",
        "",
        "口座別",
    ]
    for a in data["accounts"]:
        lines.append(f"  {a['name']:<12} {jpy(a['total']):>12} / {jpy(a['day_pnl'], True):>10}")
        day_split = _joined(
            split(a.get("day_stock"), a.get("day_fx")), after_tax(a.get("day_after_tax"), "税後")
        )
        unreal_split = _joined(
            split(a.get("unreal_stock"), a.get("unreal_fx")),
            after_tax(a.get("unreal_after_tax"), "税後"),
        )
        if day_split or unreal_split:
            lines.append(f"      日次 {day_split or '—'}  /  含み {unreal_split or '—'}")
    lines += ["", "保有 (数量 / 1D / 1Y / 評価額 / 日次 / 含み)"]
    for p in data["positions"]:
        unreal = jpy(p["unreal"], True) if p.get("unreal") is not None else "原価なし"
        lines.append(
            f"  {p['sym']:<5} {p['acct'][:4]:<4} {jpy(p['qty']):>7} / {pct(p['chg1d']):>7} / "
            f"{pct(p['chg1y'], 1):>8} / {jpy(p['value']):>11} / {jpy(p['day_pnl'], True):>10} / {unreal:>11}"
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
        *([data["tax_note"], ""] if data.get("tax_note") else []),
        f"生成 {data['generated_at']}",
        "ダッシュボード本体: Documents\\pl-daily\\latest.html",
    ]
    return "\n".join(lines)


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
    recent = daily[-40:]
    if daily:
        points, idx = _sample(recent, 40)
        labels = [dates[len(dates) - len(recent) + i] for i in idx] if dates else None
        known = [v for v in recent if v is not None]
        wins = sum(1 for v in known if v > 0)
        out += _section("日次損益", f"直近 {len(recent)} 営業日")
        out += _card(
            emailchart.columns(points, labels, total_px=96, col_w=9, gap=4, fmt=man, months=None)
            + _caption(f"上げた日 {wins} 日 / 下げた日 {len(known) - wins} 日。")
        )
    return out


def _spark(values: list[Any]) -> str:
    """A year of prices in 100px: 20 points, no axis — the shape, beside the numbers."""
    points, _ = _sample([v for v in values], 20)
    if len([v for v in points if v is not None]) < 2:
        return ""
    return emailchart.line(points, total_px=22, col_w=5, thickness=2, zero=False)


def _kpi_cell(label: str, value: str, sub: str, tone: str, sub2: str = "") -> str:
    second = (
        f'<div style="font:400 11px {SANS};color:{MUTED};margin-top:1px">{html.escape(sub2)}</div>'
        if sub2
        else ""
    )
    return (
        f'<td width="50%" bgcolor="{CARD}" style="padding:11px 13px;border:1px solid {RULE};'
        f'border-radius:8px;vertical-align:top">'
        f'<div style="font:500 10px {MONO};letter-spacing:.1em;color:{MUTED}">{html.escape(label)}</div>'
        f'<div style="font:600 21px {MONO};color:{tone};margin-top:5px">{value}</div>'
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


def html_body(data: dict[str, Any], image_cid: str | None = None) -> str:
    h, w = data["headline"], data["window"]
    kpis = (
        '<table role="presentation" cellspacing="6" cellpadding="0" style="border-collapse:separate;width:100%"><tr>'
        + _kpi_cell(
            "総資産 ¥",
            jpy(h["nav_total"]),
            f"時価評価 {int(h['quoted_share'] * 100)}%・残りは残高据え置き",
            INK,
            _nav_after_tax(h),
        )
        + _kpi_cell(
            "日次損益 ¥",
            jpy(h["day_pnl"], True),
            _joined(pct(h["day_pnl_pct"]), split(h.get("day_stock"), h.get("day_fx"))),
            _tone(h["day_pnl"]),
            after_tax(h.get("day_after_tax")),
        )
        + "</tr><tr>"
        + _kpi_cell(
            f"期間損益 ¥ · {w['days']}日",
            jpy(h["pnl_window"], True),
            f"{w['start']} 以降・入金控除後",
            _tone(h["pnl_window"]),
        )
        + _kpi_cell(
            "含み損益 ¥",
            jpy(h["unrealized_known"], True),
            split(h.get("unreal_stock"), h.get("unreal_fx")) or "取得原価が分かる保有の合計",
            _tone(h["unrealized_known"]),
            after_tax(h.get("unreal_after_tax")),
        )
        + "</tr></table>"
    )
    acc_rows = ""
    for i, a in enumerate(data["accounts"]):
        last = i == len(data["accounts"]) - 1
        acc_rows += (
            "<tr>"
            + _td(html.escape(a["name"]), "left", INK, SANS, last)
            + _td(jpy(a["total"]), "right", INK, None, last)
            + _td(
                jpy(a["day_pnl"], True) + _split_cell(a, "day_stock", "day_fx", "day_after_tax"),
                "right",
                _tone(a["day_pnl"]),
                None,
                last,
            )
            + _td(
                jpy(a["unrealized"], True)
                + _split_cell(a, "unreal_stock", "unreal_fx", "unreal_after_tax")
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
            jpy(p["unreal"], True) + _split_cell(p, "unreal_stock", "unreal_fx", "unreal_after_tax")
            if p.get("unreal") is not None
            else "原価なし"
        )
        pos_rows += (
            "<tr>"
            + _td(name, "left", INK, SANS, last)
            + _td(pct(p["chg1d"]), "right", _tone(p["chg1d"]), None, last)
            + _td(_spark(p.get("spark") or []), "left", INK, None, last)
            + _td(pct(p["chg1y"], 1), "right", _tone(p["chg1y"]), None, last)
            + _td(jpy(p["value"]), "right", INK, None, last)
            + _td(
                jpy(p["day_pnl"], True) + _split_cell(p, "day_stock", "day_fx", "day_after_tax"),
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
    # The dashboard's own figures, rendered to an image, are the real thing; the
    # table-cell charts stand in only when no browser was available to draw them.
    if image_cid:
        charts = _section("時系列", f"{w['start']} → {w['end']}") + _card(
            f'<img src="cid:{image_cid}" width="572" alt="NAV・累計損益・日次損益と銘柄ごとの株価チャート" '
            f'style="display:block;width:100%;max-width:572px;height:auto;border-radius:4px">',
            pad="6px",
        )
    else:
        charts = _charts(data)
    quoted = int(h["quoted_share"] * 100)
    return f"""<table width="100%" cellspacing="0" cellpadding="0" bgcolor="{GROUND}"><tr>
<td style="padding:18px 12px;font-family:{SANS};color:{INK}">
<div style="max-width:600px;margin:0 auto">
<div style="font:400 11px {MONO};letter-spacing:.12em;color:{MUTED}">DAILY MARK-TO-MARKET</div>
<div style="font:700 20px/1.3 Georgia,serif;margin:6px 0 2px">日次損益 {html.escape(data["as_of"])}</div>
<div style="font:400 12px {SANS};color:{MUTED};margin-bottom:14px">USD/JPY {float(data["fx"]["last"]):.2f}（{pct(data["fx"]["chg_pct"])}）· 生成 {html.escape(str(data["generated_at"])[:16].replace("T", " "))}</div>
{kpis}
{charts}
{_section("口座別")}
<table role="presentation" cellspacing="0" cellpadding="0" {table_style}>
<tr>{_th("口座", "left")}{_th("評価額 ¥")}{_th("日次損益 ¥")}{_th("含み損益 ¥")}</tr>{acc_rows}</table>
{_section("保有", "評価額の大きい順 · 1Y は直近 1 年の株価")}
<table role="presentation" cellspacing="0" cellpadding="0" {table_style}>
<tr>{_th("銘柄", "left")}{_th("1D")}{_th("値動き 1Y", "left")}{_th("1Y")}{_th("評価額 ¥")}{_th("日次 ¥")}{_th("含み ¥")}</tr>{pos_rows}</table>
<div style="font:400 11px/1.7 {SANS};color:{MUTED};margin-top:16px">
日次損益は各銘柄の直近 2 終値の差（価格と為替の両方）。株＝価格の変化（今日のレート換算）、FX＝残り（レートの変化分）で、円建ては FX 0。含み損益の FX は取得原価（外貨）×（現在レート − 取得時レート）。総資産の {100 - quoted}% は時価が取れない残高（現金など）で据え置き。海外証券口座の累計損益は取引履歴を日次で再生した値で、入金は差し引いています。{html.escape(data.get("tax_note", ""))}<br>
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
