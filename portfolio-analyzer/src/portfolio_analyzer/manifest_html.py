"""Render the main dashboard artifact (``core.build_artifact``) as one self-contained page.

The manifest lists blocks (markdown, metric strips, charts, tables) over the snapshot's
datasets. Everything is laid out here: bars are HTML so long Japanese labels wrap, the line
chart is inline SVG, and every mark carries a native tooltip. The account filter is
pre-rendered, one copy of each filtered block per scope, switched by a select. Colours come
from the claude-report tokens (dark by default, toggle), as on the daily dashboard.

This replaced the Codex data-analytics plugin's portable builder, which plugin 1.0.8 dropped.
"""

from __future__ import annotations

import html
import math
import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Tokyo")
MINUS = "−"
# palette names in the manifest -> the validated token pair
HUES = {"orange": "var(--series-1)", "blue": "var(--series-2)"}
CATEGORICAL = ("var(--series-1)", "var(--series-2)", "var(--s5)", "var(--s3)")
# the TeX commands the artifact's notes use; anything else is shown by name
TEX_SYMBOLS = {
    "Sigma": "Σ",
    "sigma": "σ",
    "mu": "μ",
    "beta": "β",
    "rho": "ρ",
    "Delta": "Δ",
    "top": "⊤",
    "cdot": "·",
    "times": "×",
    "le": "≤",
    "ge": "≥",
    "approx": "≈",
    "min": "min",
    "max": "max",
    "qquad": "\u2003\u2003",
    "quad": "\u2003",
    ",": "\u2009",
}
MATH = re.compile(r"(?<![\w$])\$(?![\s\d])([^$\n]+?)(?<!\s)\$(?!\d)")
LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
BOLD = re.compile(r"\*\*(.+?)\*\*")
CODE = re.compile(r"`([^`]+)`")


def _esc(text: Any) -> str:
    return html.escape(str(text), quote=True)


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return None if math.isnan(float(value)) else float(value)
    return None


def fmt(value: Any, format: str | None) -> str:
    """A cell or label value in the manifest's format (``currency`` / ``percent`` / ``number``)."""
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "はい" if value else "いいえ"
    v = _num(value)
    if v is None:
        return str(value)
    if format == "currency":
        text = f"{round(v):,} 円"
    elif format == "percent":
        text = f"{v * 100:.1f}%"
    elif v.is_integer():
        text = f"{int(v):,}"
    else:
        text = f"{v:,.0f}" if abs(v) >= 1000 else f"{v:,.2f}"
    return text.replace("-", MINUS)


def compact_yen(value: float) -> str:
    """Yen for bar labels and axes: ``4,591万`` / ``2.5億``."""
    v = float(value)
    if abs(v) >= 1e8:
        text = f"{v / 1e8:,.1f}億"
    elif abs(v) >= 1e4:
        text = f"{round(v / 1e4):,}万"
    else:
        text = f"{round(v):,}"
    return text.replace("-", MINUS)


def _short(value: float, format: str | None) -> str:
    return compact_yen(value) if format == "currency" else fmt(value, format)


# ---------------------------------------------------------------- markdown


def _tex(src: str) -> str:
    """A small TeX subset as HTML: symbols, ``^``/``_``, ``\\frac`` and ``\\sqrt``."""
    out: list[str] = []
    i = 0

    def group(i: int) -> tuple[str, int]:
        while i < len(src) and src[i] == " ":
            i += 1
        if i >= len(src):
            return "", i
        if src[i] == "{":
            depth, j = 0, i
            while j < len(src):
                depth += {"{": 1, "}": -1}.get(src[j], 0)
                if depth == 0:
                    break
                j += 1
            return _tex(src[i + 1 : j]), j + 1
        if src[i] == "\\":
            name = re.match(r"\\([A-Za-z]+|.)", src[i:])
            assert name is not None
            return TEX_SYMBOLS.get(name.group(1), _esc(name.group(1))), i + len(name.group(0))
        return _esc(src[i]), i + 1

    while i < len(src):
        c = src[i]
        if c == "\\":
            match = re.match(r"\\([A-Za-z]+|.)", src[i:])
            assert match is not None
            name = match.group(1)
            i += len(match.group(0))
            if name == "frac":
                num, i = group(i)
                den, i = group(i)
                out.append(f"<span class='fr'><span>{num}</span><span>{den}</span></span>")
            elif name == "sqrt":
                body, i = group(i)
                out.append(f"√<span class='sq'>{body}</span>")
            else:
                out.append(TEX_SYMBOLS.get(name, _esc(name)))
        elif c in "^_":
            body, i = group(i + 1)
            tag = "sup" if c == "^" else "sub"
            out.append(f"<{tag}>{body}</{tag}>")
        elif c in "{}":
            i += 1
        else:
            out.append(_esc(c))
            i += 1
    return "".join(out)


def _inline(text: str) -> str:
    kept: list[str] = []

    def keep(html_text: str) -> str:
        kept.append(html_text)
        return f"\x00{len(kept) - 1}\x00"

    out = CODE.sub(lambda m: keep(f"<code>{_esc(m.group(1))}</code>"), text)
    out = MATH.sub(lambda m: keep(f"<i class='m'>{_tex(m.group(1))}</i>"), out)
    out = _esc(out)

    def link(match: re.Match[str]) -> str:
        label, href = match.group(1), match.group(2)
        if href.startswith(("https://", "http://")):
            return f'<a href="{href}">{label}</a>'
        return label

    out = LINK.sub(link, out)
    out = BOLD.sub(r"<strong>\1</strong>", out)
    return re.sub(r"\x00(\d+)\x00", lambda m: kept[int(m.group(1))], out)


def markdown(body: str) -> str:
    """The subset the artifact uses: ``##`` headings, paragraphs, ``-`` lists, bold, code,
    links (http/https only), inline ``$...$`` and display ``$$...$$`` math. Raw HTML is
    escaped."""
    parts: list[str] = []
    for chunk in re.split(r"\n\s*\n", body.strip()):
        if chunk.startswith("$$") and chunk.endswith("$$") and len(chunk) > 4:
            parts.append(f"<div class='eq'><i class='m'>{_tex(chunk[2:-2].strip())}</i></div>")
            continue
        para: list[str] = []
        items: list[str] = []
        for line in chunk.splitlines():
            if line.startswith("## "):
                _flush(parts, para, items)
                parts.append(f"<h2>{_inline(line[3:])}</h2>")
            elif line.startswith("- "):
                if para:
                    _flush(parts, para, items)
                items.append(line[2:])
            elif items and line.startswith("  "):
                items[-1] += " " + line.strip()
            else:
                if items:
                    _flush(parts, para, items)
                para.append(line)
        _flush(parts, para, items)
    return "\n".join(parts)


def _flush(parts: list[str], para: list[str], items: list[str]) -> None:
    """Close the open paragraph and list of ``markdown`` into ``parts``."""
    if para:
        parts.append(f"<p>{' '.join(_inline(x) for x in para)}</p>")
        para.clear()
    if items:
        parts.append("<ul>" + "".join(f"<li>{_inline(x)}</li>" for x in items) + "</ul>")
        items.clear()


# ---------------------------------------------------------------- charts


def _tooltip(chart: dict[str, Any], row: dict[str, Any], label: str) -> str:
    y = chart["encodings"]["y"]
    parts = [f"{label}: {fmt(row.get(y['field']), y.get('format') or chart.get('valueFormat'))}"]
    for tip in chart["encodings"].get("tooltip", []):
        value = row.get(tip["field"])
        if value is None or value == "":
            continue
        parts.append(f"{tip['label']} {fmt(value, tip.get('format'))}")
    return " · ".join(parts)


def horizontal_bar(chart: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    """One bar per row from a shared zero, sorted as the chart asks, value at the bar's end."""
    enc = chart["encodings"]
    label_field, value_field = enc["x"]["field"], enc["y"]["field"]
    value_format = enc["y"].get("format") or chart.get("valueFormat")
    points = [(r, _num(r.get(value_field))) for r in rows]
    points = [(r, v) for r, v in points if v is not None]
    if not points:
        return "<p class='empty'>この範囲にはデータがありません</p>"
    order = (chart.get("settings") or {}).get("sort")
    if order in ("descending", "ascending"):
        points.sort(key=lambda p: p[1], reverse=order == "descending")
    refs = [r for r in chart.get("referenceLines", []) if r.get("axis") == "x"]
    values = [v for _, v in points] + [float(r["value"]) for r in refs]
    lo, hi = min(0.0, *values), max(0.0, *values)
    span = (hi - lo) or 1.0
    # room for the value label beyond the longest bar on each side
    lo -= span * 0.22 if lo < 0 else 0
    hi += span * 0.22 if hi > 0 else 0
    span = hi - lo

    def at(v: float) -> float:
        return (v - lo) / span * 100

    zero = at(0.0)
    hue = HUES.get((chart.get("palette") or {}).get("name", ""), "var(--series-2)")
    show = (chart.get("settings") or {}).get("showValues", True)
    out = []
    for row, v in points:
        label = str(row.get(label_field, ""))
        left, width = (at(v), zero - at(v)) if v < 0 else (zero, at(v) - zero)
        side = "neg" if v < 0 else "pos"
        value = ""
        if show:
            pos = f"right:{100 - left:.2f}%" if v < 0 else f"left:{left + width:.2f}%"
            value = f"<span class='val {side}' style='{pos}'>{_esc(_short(v, value_format))}</span>"
        out.append(
            f"<div class='hr' title='{_esc(_tooltip(chart, row, label))}'>"
            f"<span class='lb'>{_esc(label)}</span>"
            f"<span class='tr'><span class='bar {side}' style='left:{left:.2f}%;width:{max(width, 0.3):.2f}%;background:{hue}'></span>{value}</span>"
            "</div>"
        )
    lines = f"<span class='zero' style='left:{zero:.2f}%'></span>" + "".join(
        f"<span class='ref{' end' if at(float(r['value'])) > 80 else ''}' style='left:{at(float(r['value'])):.2f}%'>"
        f"<em>{_esc(r.get('label', ''))}</em></span>"
        for r in refs
        if float(r["value"]) != 0 or r.get("label")
    )
    return f"<div class='hbars'><div class='rules'>{lines}</div>{''.join(out)}</div>"


def stacked_bar_100(chart: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    """One 100% bar per x value, segments in first-seen category order, direct labels + legend."""
    enc = chart["encodings"]
    group_field, value_field, color_field = (
        enc["x"]["field"],
        enc["y"]["field"],
        enc["color"]["field"],
    )
    categories: list[str] = []
    groups: dict[str, list[tuple[str, float]]] = {}
    for row in rows:
        v = _num(row.get(value_field))
        if v is None or v <= 0:
            continue
        cat = str(row.get(color_field))
        if cat not in categories:
            categories.append(cat)
        groups.setdefault(str(row.get(group_field)), []).append((cat, v))
    if not groups:
        return "<p class='empty'>この範囲にはデータがありません</p>"
    colour = {c: CATEGORICAL[min(i, len(CATEGORICAL) - 1)] for i, c in enumerate(categories)}
    bars = []
    for group, segs in groups.items():
        total = sum(v for _, v in segs)
        cells = []
        for cat, v in sorted(segs, key=lambda s: categories.index(s[0])):
            share = v / total
            text = f"{cat} {share * 100:.1f}%"
            tip = f"{group} · {text} · {fmt(v, enc['y'].get('format') or 'currency')}"
            cells.append(
                f"<span class='seg' style='flex:{share:.6f};background:{colour[cat]}' title='{_esc(tip)}'>"
                + (f"<b>{_esc(text)}</b>" if share >= 0.12 else "")
                + "</span>"
            )
        small = [f"{cat} {v / total * 100:.1f}%" for cat, v in segs if v / total < 0.12]
        bars.append(
            f"<div class='sb'><span class='lb'>{_esc(group)}</span><span class='stack'>{''.join(cells)}</span>"
            + (f"<small>{_esc(' · '.join(small))}</small>" if small else "")
            + "</div>"
        )
    legend = "".join(
        f"<span><i style='background:{colour[c]}'></i>{_esc(c)}</span>" for c in categories
    )
    return f"<div class='sbars'>{''.join(bars)}</div><div class='legend'>{legend}</div>"


def line_chart(chart: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    """A single series over time, gaps kept as gaps, a zero rule when the range spans it,
    and a hover target per point."""
    enc = chart["encodings"]
    x_field, y_field = enc["x"]["field"], enc["y"]["field"]
    value_format = enc["y"].get("format") or chart.get("valueFormat")
    pts = sorted(rows, key=lambda r: str(r.get(x_field)))
    values = [_num(r.get(y_field)) for r in pts]
    known = [v for v in values if v is not None]
    if not known:
        return "<p class='empty'>この範囲にはデータがありません</p>"
    width, height, left, right, top, bottom = 720, 220, 44, 8, 10, 22
    lo, hi = min(known), max(known)
    pad = (hi - lo) * 0.08 or abs(hi) * 0.1 or 1.0
    lo, hi = lo - pad, hi + pad
    n = len(pts)

    def x(i: int) -> float:
        return left + (width - left - right) * (i / (n - 1) if n > 1 else 0.5)

    def y(v: float) -> float:
        return top + (height - top - bottom) * (hi - v) / (hi - lo)

    path, pen_down = [], False
    for i, v in enumerate(values):
        if v is None:
            pen_down = False
            continue
        path.append(f"{'L' if pen_down else 'M'}{x(i):.1f},{y(v):.1f}")
        pen_down = True
    step = (width - left - right) / max(n - 1, 1)
    hits = []
    for i, (row, v) in enumerate(zip(pts, values, strict=True)):
        if v is None:
            continue
        tip = _tooltip(chart, row, str(row.get(x_field)))
        hits.append(
            f"<g class='pt'><rect class='hit' x='{x(i) - step / 2:.1f}' y='{top}' width='{step:.1f}' height='{height - top - bottom}'/>"
            f"<circle class='dot' cx='{x(i):.1f}' cy='{y(v):.1f}' r='4'/><title>{_esc(tip)}</title></g>"
        )
    axis = "".join(
        f"<text x='{left - 6}' y='{y(t) + 3:.1f}' text-anchor='end'>{_esc(fmt(t, value_format))}</text>"
        for t in (hi - pad, lo + pad)
    )
    zero = ""
    if lo < 0 < hi:
        zero = (
            f"<line class='zero' x1='{left}' x2='{width - right}' y1='{y(0):.1f}' y2='{y(0):.1f}'/>"
        )
        axis += f"<text x='{left - 6}' y='{y(0) + 3:.1f}' text-anchor='end'>0</text>"
    ticks = sorted(
        {0, n - 1}
        | {
            i
            for i in range(1, n)
            if str(pts[i].get(x_field))[:4] != str(pts[i - 1].get(x_field))[:4]
        }
    )
    labels = "".join(
        f"<text x='{x(i):.1f}' y='{height - 6}' text-anchor='{'start' if i == 0 else 'end' if i == n - 1 else 'middle'}'>{_esc(str(pts[i].get(x_field))[:7])}</text>"
        for i in ticks
    )
    return (
        f"<svg class='line' viewBox='0 0 {width} {height}' role='img' aria-label='{_esc(chart.get('title', ''))}'>"
        f"{zero}<path class='line' d='{' '.join(path)}'/>{axis}{labels}{''.join(hits)}</svg>"
    )


CHARTS = {"horizontalBar": horizontal_bar, "stackedBar100": stacked_bar_100, "line": line_chart}


# ---------------------------------------------------------------- tables and cards


def table(spec: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    """All rows, sorted by ``defaultSort`` (blanks last), numbers right-aligned; long tables scroll."""
    rows = list(rows)
    sort = spec.get("defaultSort")
    if sort:
        field, desc = sort["field"], sort.get("direction") == "desc"
        filled = [r for r in rows if r.get(field) is not None]
        blank = [r for r in rows if r.get(field) is None]
        numbers = [r for r in filled if _num(r[field]) is not None]
        texts = [r for r in filled if _num(r[field]) is None]
        numbers.sort(key=lambda r: _num(r[field]) or 0.0, reverse=desc)
        texts.sort(key=lambda r: str(r[field]), reverse=desc)
        filled = numbers + texts
        rows = filled + blank
    cols = spec["columns"]
    numeric = [c.get("format") is not None for c in cols]
    head = "".join(
        f"<th class='{'n' if isnum else 't'}'>{_esc(c['label'])}</th>"
        for c, isnum in zip(cols, numeric, strict=True)
    )
    body = "".join(
        "<tr>"
        + "".join(
            f"<td class='{'n' if isnum else 't'}'>{_esc(fmt(r.get(c['field']), c.get('format')))}</td>"
            for c, isnum in zip(cols, numeric, strict=True)
        )
        + "</tr>"
        for r in rows
    )
    tall = " tall" if len(rows) > 16 else ""
    if not rows:
        body = (
            f"<tr><td colspan='{len(cols)}' class='empty'>この範囲にはデータがありません</td></tr>"
        )
    return (
        f"<h3>{_esc(spec.get('title', ''))}</h3>"
        + (f"<p class='sub'>{_esc(spec['subtitle'])}</p>" if spec.get("subtitle") else "")
        + f"<div class='tw{tall}'><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"
        + f"<p class='cnt'>{len(rows)} 行</p>"
    )


def metric_strip(cards: list[dict[str, Any]], row: dict[str, Any] | None) -> str:
    tiles = []
    for card in cards:
        for n, metric in enumerate(card["metrics"]):
            value = None if row is None else row.get(metric["field"])
            unit = (
                f"<small>{_esc(metric['unit'])}</small>"
                if metric.get("unit") and value is not None
                else ""
            )
            tiles.append(
                f"<div class='kpi' title='{_esc(card.get('description', ''))}'>"
                f"<span class='k'>{_esc(metric['label'])}</span>"
                f"<span class='v'>{_esc(fmt(value, metric.get('format')))}{unit}</span>"
                + (f"<span class='s'>{_esc(card.get('description', ''))}</span>" if n == 0 else "")
                + "</div>"
            )
    return f"<div class='kpis'>{''.join(tiles)}</div>"


def chart_panel(chart: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    draw = CHARTS.get(chart["type"])
    body = (
        draw(chart, rows)
        if draw
        else f"<p class='empty'>未対応のグラフ種類: {_esc(chart['type'])}</p>"
    )
    return (
        f"<h3>{_esc(chart.get('title', ''))}</h3>"
        + (f"<p class='sub'>{_esc(chart['subtitle'])}</p>" if chart.get("subtitle") else "")
        + body
    )


# ---------------------------------------------------------------- page


def render(artifact: dict[str, Any], tokens_css: str) -> str:
    manifest = artifact["manifest"]
    datasets: dict[str, list[dict[str, Any]]] = artifact["snapshot"]["datasets"]
    charts = {c["id"]: c for c in manifest.get("charts", [])}
    tables = {t["id"]: t for t in manifest.get("tables", [])}
    cards = {c["id"]: c for c in manifest.get("cards", [])}
    filt = (manifest.get("filters") or [None])[0]
    scope_field = filt["field"] if filt else None
    targets = {t["dataset"]: t["field"] for t in filt["targets"]} if filt else {}
    if filt:
        targets[filt["dataset"]] = filt["field"]
        scopes = list(dict.fromkeys(str(r[scope_field]) for r in datasets[filt["dataset"]]))
        default = str(filt.get("defaultValue", scopes[0]))
    else:
        scopes, default = [""], ""

    def rows_for(dataset: str, scope: str) -> list[dict[str, Any]]:
        rows = datasets.get(dataset, [])
        field = targets.get(dataset)
        return [r for r in rows if str(r.get(field)) == scope] if field else rows

    def body(block: dict[str, Any], scope: str) -> str:
        kind = block["type"]
        if kind == "markdown":
            return f"<div class='md'>{markdown(block['body'])}</div>"
        if kind == "metric-strip":
            strip = [cards[i] for i in block["cardIds"] if i in cards]
            dataset = strip[0]["dataset"] if strip else ""
            rows = rows_for(dataset, scope)
            return metric_strip(strip, rows[0] if rows else None)
        if kind == "chart":
            chart = charts[block["chartId"]]
            return chart_panel(chart, rows_for(chart["dataset"], scope))
        if kind == "table":
            spec = tables[block["tableId"]]
            return table(spec, rows_for(spec["dataset"], scope))
        return f"<p class='empty'>未対応のブロック: {_esc(kind)}</p>"

    def dataset_of(block: dict[str, Any]) -> str | None:
        if block["type"] == "chart":
            return charts[block["chartId"]]["dataset"]
        if block["type"] == "table":
            return tables[block["tableId"]]["dataset"]
        if block["type"] == "metric-strip":
            ids = [i for i in block["cardIds"] if i in cards]
            return cards[ids[0]]["dataset"] if ids else None
        return None

    sections = []
    for block in manifest["blocks"]:
        layout = "half" if block.get("layout") == "half" else "full"
        kind = block["type"]
        bid = _esc(block["id"])
        if dataset_of(block) in targets:
            inner = "".join(
                f"<div class='sc' data-scope='{_esc(s)}' data-block='{bid}'{'' if s == default else ' hidden'}>{body(block, s)}</div>"
                for s in scopes
            )
        else:
            inner = f"<div data-block='{bid}'>{body(block, default)}</div>"
        # a div, not <section>: the report tokens pad every section for long-form pages
        sections.append(f"<div class='blk {layout} {kind}'>{inner}</div>")

    options = "".join(
        f"<option value='{_esc(s)}'{' selected' if s == default else ''}>{_esc(s)}</option>"
        for s in scopes
    )
    picker = (
        f"<label class='pick'>{_esc(filt['label'])} <select id='scope'>{options}</select></label>"
        if filt
        else ""
    )
    sources = "".join(
        "<li>"
        + (
            f"<a href='{_esc(s['href'])}'>{_esc(s['label'])}</a>"
            if str(s.get("href", "")).startswith(("https://", "http://"))
            else f"{_esc(s['label'])} <code>{_esc(s.get('path', ''))}</code>"
        )
        + "</li>"
        for s in manifest.get("sources", [])
    )
    generated = manifest.get("generatedAt", "")
    try:
        generated = datetime.fromisoformat(generated).astimezone(TZ).strftime("%Y-%m-%d %H:%M JST")
    except ValueError:
        pass

    return f"""<!doctype html>
<html lang="ja" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(manifest.get("title", ""))}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&family=Zen+Kaku+Gothic+New:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
{tokens_css}
{CSS}
</style>
</head>
<body>
<header class="top"><div class="wrap">
<h1>{_esc(manifest.get("title", ""))}</h1>
<span class="meta">生成 {_esc(generated)}</span>
{picker}
<button id="theme" type="button">ライト / ダーク</button>
<p class="desc">{_esc(manifest.get("description", ""))}</p>
</div></header>
<main class="wrap grid">
{"".join(sections)}
</main>
<footer class="wrap"><h2>出典</h2><ul>{sources}</ul></footer>
<script>
(function () {{
  var sel = document.getElementById('scope');
  function apply(v) {{
    document.querySelectorAll('.sc').forEach(function (el) {{ el.hidden = el.dataset.scope !== v; }});
  }}
  if (sel) {{
    var saved = decodeURIComponent(location.hash.slice(1));
    if (saved && Array.prototype.some.call(sel.options, function (o) {{ return o.value === saved; }})) {{ sel.value = saved; apply(saved); }}
    sel.addEventListener('change', function () {{ apply(sel.value); history.replaceState(null, '', '#' + encodeURIComponent(sel.value)); }});
  }}
  var root = document.documentElement, key = 'portfolio-dashboard-theme';
  try {{ var t = localStorage.getItem(key); if (t) root.dataset.theme = t; }} catch (e) {{}}
  document.getElementById('theme').addEventListener('click', function () {{
    root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    try {{ localStorage.setItem(key, root.dataset.theme); }} catch (e) {{}}
  }});
}})();
</script>
</body>
</html>
"""


CSS = """
*{box-sizing:border-box}
body{background:var(--ground);color:var(--ink);font-family:var(--sans);font-size:14px;line-height:1.7;margin:0;padding:0 18px 80px;-webkit-font-smoothing:antialiased;font-feature-settings:"palt" 1}
.wrap{max-width:1180px;margin:0 auto}
.top{position:sticky;top:0;z-index:5;background:var(--ground);border-bottom:1px solid var(--rule);padding:10px 0 6px}
.top .wrap{display:flex;gap:6px 18px;align-items:baseline;flex-wrap:wrap}
.top h1{font-family:var(--serif);font-weight:700;font-size:21px;margin:0;line-height:1.3}
.top .meta{font-family:var(--mono);font-size:11px;color:var(--ink-3)}
.pick{font-size:12px;color:var(--ink-2)}
.pick select{font:inherit;background:var(--surface);color:var(--ink);border:1px solid var(--rule-2);border-radius:6px;padding:2px 6px;margin-left:4px}
.top button{margin-left:auto;background:var(--surface);color:var(--ink-2);border:1px solid var(--rule);border-radius:999px;padding:3px 11px;font:inherit;font-size:11px;cursor:pointer}
.desc{flex-basis:100%;margin:0;font-size:12px;color:var(--ink-3)}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:14px}
.blk{min-width:0}.blk.full{grid-column:1/-1}
@media (max-width:860px){.grid{grid-template-columns:1fr}}
.blk.chart>div,.blk.table>div{background:var(--surface);border:1px solid var(--rule);border-radius:10px;padding:12px 14px 10px}
.md{max-width:880px}
.md h2{font-family:var(--serif);font-weight:700;font-size:22px;line-height:1.4;margin:26px 0 4px}
.md p{margin:8px 0;color:var(--ink-2)}
.md ul{margin:6px 0 8px;padding-left:1.2em;color:var(--ink-2)}
.md li{margin:3px 0}
.md strong{color:var(--ink)}
a{color:var(--accent);text-underline-offset:3px;word-break:break-all}
code{font-family:var(--mono);font-size:.86em;background:var(--surface-2);padding:1px 6px;border-radius:3px;color:var(--ink-2)}
i.m{font-family:var(--serif);font-style:italic;color:var(--ink)}
.eq{margin:10px 0;font-size:17px;overflow-x:auto}
.fr{display:inline-flex;flex-direction:column;vertical-align:middle;text-align:center;margin:0 .15em}
.fr>span:first-child{border-bottom:1px solid var(--ink-2);padding:0 .2em}
.sq{border-top:1px solid var(--ink-2);padding:0 .1em}
h3{font-size:13.5px;font-weight:700;margin:0;letter-spacing:.02em}
p.sub{margin:2px 0 8px;font-size:11.5px;color:var(--ink-3);line-height:1.5}
p.cnt{margin:4px 0 0;font-family:var(--mono);font-size:10px;color:var(--ink-3);text-align:right}
.empty{color:var(--ink-3);font-size:12px}
.kpis{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:8px}
.kpi{background:var(--surface);border:1px solid var(--rule);border-radius:10px;padding:10px 13px 11px;min-width:0}
.kpi .k{display:block;font-size:11px;color:var(--ink-3);font-weight:500}
.kpi .v{display:block;font-family:var(--mono);font-variant-numeric:tabular-nums;font-size:21px;font-weight:600;line-height:1.25;margin-top:4px}
.kpi .v small{font-family:var(--sans);font-size:11px;color:var(--ink-3);margin-left:3px;font-weight:400}
.kpi .s{display:block;font-size:10.5px;color:var(--ink-3);margin-top:3px;line-height:1.45}
.hbars{position:relative;margin-top:4px}
.rules{position:absolute;inset:0 0 0 calc(34% + 10px);pointer-events:none}
.rules span{position:absolute;top:0;bottom:0;border-left:1px solid var(--rule-2)}
.rules .ref{border-left:1px dashed var(--ink-3)}
.rules .ref em{position:absolute;top:-2px;left:4px;font-style:normal;font-family:var(--mono);font-size:9.5px;color:var(--ink-3);white-space:nowrap}
.rules .ref.end em{left:auto;right:4px}
.hr{display:grid;grid-template-columns:34% 1fr;gap:10px;align-items:center;padding:3px 0;border-radius:4px}
.hr:hover{background:var(--surface-2)}
.hr .lb{font-size:12px;line-height:1.35;color:var(--ink-2);text-align:right}
.tr{position:relative;height:16px}
.bar{position:absolute;top:1px;bottom:1px;border-radius:0 4px 4px 0}
.bar.neg{border-radius:4px 0 0 4px}
.val{position:absolute;top:-1px;font-family:var(--mono);font-size:10.5px;color:var(--ink-2);white-space:nowrap;padding:0 5px}
.sbars{display:flex;flex-direction:column;gap:8px;margin-top:6px}
.sb .lb{display:block;font-size:12px;color:var(--ink-2)}
.stack{display:flex;gap:2px;height:30px}
.seg{border-radius:4px;min-width:3px;overflow:hidden;display:flex;align-items:center;padding:0 7px}
.seg b{font-family:var(--mono);font-size:11px;font-weight:600;color:#fff;white-space:nowrap}
.sb small{display:block;font-family:var(--mono);font-size:10.5px;color:var(--ink-3)}
.legend{display:flex;gap:14px;margin-top:8px;font-size:11px;color:var(--ink-3)}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}
svg.line{display:block;width:100%;height:auto;overflow:visible;margin-top:4px}
svg text{font-family:var(--mono);fill:var(--ink-3);font-size:10px}
svg .zero{stroke:var(--rule-2);stroke-width:1}
svg path.line{fill:none;stroke:var(--series-2);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
svg .hit{fill:transparent}
svg .dot{fill:var(--series-2);stroke:var(--surface);stroke-width:2;opacity:0}
svg .pt:hover .dot{opacity:1}
.tw{overflow:auto;margin-top:6px;border:1px solid var(--rule);border-radius:8px}
.tw.tall{max-height:560px}
table{border-collapse:collapse;width:100%;font-size:12px}
th{position:sticky;top:0;background:var(--surface-3);font-size:10.5px;font-weight:500;color:var(--ink-3);text-align:left;padding:6px 8px;border-bottom:1px solid var(--rule);white-space:nowrap}
td{padding:5px 8px;border-bottom:1px solid var(--rule);vertical-align:top}
tbody tr:last-child td{border-bottom:none}
tbody tr:hover td{background:var(--surface-2)}
th.n,td.n{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}
th.t,td.t{text-align:left}
td.t{white-space:normal;min-width:6em;max-width:36em}
footer{margin-top:36px;font-size:12px;color:var(--ink-3)}
footer h2{font-family:var(--serif);font-size:18px;color:var(--ink);margin:0 0 6px}
footer ul{padding-left:1.2em;margin:0}
"""
