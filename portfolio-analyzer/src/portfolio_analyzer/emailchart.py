"""Charts drawn with table cells, so they live in the email body itself.

Mail clients drop ``<script>`` and inline SVG, and Gmail rewrites the
``Content-ID`` of an attached image — a ``cid:`` reference written by hand does
not survive it, and the picture lands as an attachment instead of in the body.
Coloured table cells survive everything, so the daily mail draws its figures
that way: signed columns for a series over time, diverging bars for a ranking.

Every function returns a self-contained ``<table>`` with inline styles only.
"""

from __future__ import annotations

import html
from collections.abc import Sequence

UP, DN, INK, MUTED, RULE, CARD = "#C05C33", "#2A6DA6", "#141413", "#85817A", "#DFDBCF", "#FAF9F5"
SANS = "system-ui,sans-serif"
MONO = "ui-monospace,monospace"

Number = float | int | None


def scale(values: Sequence[Number], up_px: int, dn_px: int) -> list[int]:
    """Signed pixel heights. One factor for both signs, so the halves stay comparable."""
    clean = [0.0 if v is None else float(v) for v in values]
    top = max((v for v in clean if v > 0), default=0.0)
    bottom = -min((v for v in clean if v < 0), default=0.0)
    factors = []
    if top > 0:
        factors.append(up_px / top)
    if bottom > 0:
        factors.append(dn_px / bottom)
    if not factors:
        return [0 for _ in clean]
    factor = min(factors)
    return [round(v * factor) for v in clean]


def split(values: Sequence[Number], total: int) -> tuple[int, int]:
    """Divide a plot height between the two sides, so both extremes reach their edge."""
    clean = [0.0 if v is None else float(v) for v in values]
    top = max((v for v in clean if v > 0), default=0.0)
    bottom = -min((v for v in clean if v < 0), default=0.0)
    if bottom <= 0:
        return total, 0
    if top <= 0:
        return 0, total
    up = round(total * top / (top + bottom))
    return up, total - up


def _fill(color: str | None) -> str:
    """Colour as an attribute: Gmail's send path strips a CSS background, bgcolor survives."""
    return f' bgcolor="{color}"' if color else ""


def columns(
    values: Sequence[Number],
    labels: Sequence[str] | None = None,
    up_px: int = 62,
    dn_px: int = 30,
    total_px: int | None = None,
    col_w: int = 6,
    gap: int = 1,
    up: str = UP,
    dn: str = DN,
    ground: str = CARD,
) -> str:
    """A signed column chart: positives above a zero rule, negatives below it.

    Each bar is a one-cell table carrying its colour as ``bgcolor`` — Gmail's
    send path strips a CSS background, and a cell in a shared row cannot hold
    its own height. The gap between columns is a border in the panel's colour,
    because a cell's fill covers its padding and would merge the bars.
    Pass ``total_px`` to let the data divide the plot between the two sides.
    ``labels`` go under the plot at the left, middle and right.
    """
    if total_px is not None:
        up_px, dn_px = split(values, total_px)
    heights = scale(values, up_px, dn_px)
    edge = "font:0/0 a" + (f";border-right:{gap}px solid {ground}" if gap else "")

    def cell(height: int, color: str, align: str) -> str:
        bar = (
            f'<table width="{col_w}" height="{height}" bgcolor="{color}" cellspacing="0" '
            f'cellpadding="0" border="0"><tr><td style="font:0/0 a">&nbsp;</td></tr></table>'
            if height > 0
            else "&nbsp;"
        )
        return f'<td width="{col_w}" valign="{align}" style="{edge}">{bar}</td>'

    def half(px: int, color: str, above: bool) -> str:
        cells = [
            cell(max(h, 0) if above else max(-h, 0), color, "bottom" if above else "top")
            for h in heights
        ]
        return (
            f'<tr><td height="{px}" style="height:{px}px;padding:0">'
            f'<table cellspacing="0" cellpadding="0" border="0">'
            f"<tr>{''.join(cells)}</tr></table></td></tr>"
        )

    rows = []
    if up_px > 0:
        rows.append(half(up_px, up, above=True))
    rows.append(f'<tr><td height="1" bgcolor="{RULE}" style="font:0/0 a">&nbsp;</td></tr>')
    if dn_px > 0:
        rows.append(half(dn_px, dn, above=False))
    if labels:
        marks = [labels[0], labels[len(labels) // 2], labels[-1]] if len(labels) > 2 else labels
        cells = "".join(
            f'<td align="{a}" style="font:400 10px {MONO};color:{MUTED};padding:4px 0 0">'
            f"{html.escape(str(m))}</td>"
            for m, a in zip(marks, ("left", "center", "right"), strict=False)
        )
        rows.append(
            f'<tr><td><table width="100%" cellspacing="0" cellpadding="0" border="0">'
            f"<tr>{cells}</tr></table></td></tr>"
        )
    width = max(len(heights), 1) * (col_w + gap)
    return (
        f'<table cellspacing="0" cellpadding="0" border="0" '
        f'style="width:{width}px;max-width:100%">{"".join(rows)}</table>'
    )


def hbars(
    rows: Sequence[tuple[str, Number, str]],
    half: int = 96,
    bar_h: int = 11,
    up: str = UP,
    dn: str = DN,
) -> str:
    """Diverging horizontal bars: label, bar around a zero rule, and a note."""
    values = [0.0 if v is None else float(v) for _, v, _ in rows]
    peak = max((abs(v) for v in values), default=0.0)
    out = []
    for (label, _, note), value in zip(rows, values, strict=False):
        px = 0 if peak == 0 else round(abs(value) / peak * half)
        color = up if value > 0 else dn
        lead = half - px if value < 0 else 0
        bar = (
            f'<td width="{px}" height="{bar_h}"{_fill(color if px else None)} '
            f'style="font:0/0 a">&nbsp;</td>'
        )
        side = (
            f'<table cellspacing="0" cellpadding="0" border="0" width="{half}"><tr>'
            f'<td width="{lead}" style="font:0/0 a">&nbsp;</td>{bar}'
            f'<td style="font:0/0 a">&nbsp;</td></tr></table>'
        )
        empty = f'<td width="{half}">&nbsp;</td>'
        left = f'<td width="{half}" style="padding:2px 0">{side}</td>' if value < 0 else empty
        right = f'<td width="{half}" style="padding:2px 0">{side}</td>' if value > 0 else empty
        out.append(
            "<tr>"
            f'<td style="font:400 11.5px {SANS};color:{INK};padding:2px 8px 2px 0;'
            f'white-space:nowrap">{html.escape(label)}</td>'
            f"{left}"
            f'<td width="1" bgcolor="{RULE}" style="font:0/0 a">&nbsp;</td>'
            f"{right}"
            f'<td align="right" style="font:400 11px {MONO};color:{MUTED};'
            f'padding:2px 0 2px 8px;white-space:nowrap">{html.escape(note)}</td>'
            "</tr>"
        )
    return (
        f'<table cellspacing="0" cellpadding="0" border="0" style="width:100%">'
        f"{''.join(out)}</table>"
    )
