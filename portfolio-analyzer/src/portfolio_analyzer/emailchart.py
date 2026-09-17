"""Charts drawn with table cells, so they live in the email body itself.

Mail clients drop ``<script>`` and inline SVG, and Gmail rewrites the
``Content-ID`` of an attached image — a ``cid:`` reference written by hand does
not survive it, and the picture lands as an attachment instead of in the body.
Table cells survive everything, so the daily mail draws its figures that way:
a connected line for a series, signed columns for daily changes, diverging bars
for a ranking.

What a mark is made of was measured, not assumed: Gmail's send path strips the
CSS ``background`` shorthand and turns ``&nbsp;`` into a space, but keeps
``border-*``, ``padding-*``, the ``bgcolor`` attribute and ``height`` on a
cell. So a mark is a ``<div>`` whose only substance is a ``border-top`` of the
mark's height, placed by ``padding-top`` on its cell; a column of a chart is
one cell. (Gmail folds a body past roughly 104-106 KB of HTML behind "view entire
message"; measured, not documented, and not treated as a limit here.)

Every function returns a self-contained ``<table>`` with inline styles only.
"""

from __future__ import annotations

import html
from collections.abc import Callable, Sequence

UP, DN, INK, MUTED, RULE, CARD = "#C05C33", "#2A6DA6", "#141413", "#85817A", "#DFDBCF", "#FAF9F5"
UP_TINT, DN_TINT = "#F1DBD1", "#D7E2EC"
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


def _runs_of_zero(heights: list[int]) -> list[tuple[int, int]]:
    """Like ``_runs`` but only the empty columns merge — bars stay one per point."""
    out: list[tuple[int, int]] = []
    for h in heights:
        if h == 0 and out and out[-1][0] == 0:
            out[-1] = (0, out[-1][1] + 1)
        else:
            out.append((h, 1))
    return out


def _runs(heights: list[int]) -> list[tuple[int, int]]:
    """Consecutive equal heights collapsed into (height, count) — no seam in a flat run."""
    out: list[tuple[int, int]] = []
    for h in heights:
        if out and out[-1][0] == h:
            out[-1] = (h, out[-1][1] + 1)
        else:
            out.append((h, 1))
    return out


QUARTERS = ("01", "04", "07", "10")


def ticks(labels: Sequence[str], months: Sequence[str] | None = QUARTERS) -> list[tuple[int, str]]:
    """Month starts in a run of ISO dates, as (index, "YY/MM") — the x axis.

    ``months`` limits the ticks to those months (quarters by default, so a year
    gets four); ``None`` marks every month, for a window of a few weeks.
    """
    out: list[tuple[int, str]] = []
    prev = ""
    for i, label in enumerate(labels):
        month = str(label)[:7]
        if i and month != prev and (months is None or month[5:7] in months):
            out.append((i, f"{month[2:4]}/{month[5:7]}"))
        prev = month
    return out


NOTE = f'style="font:400 10px {MONO};color:{MUTED};padding:0 6px 0 0;white-space:nowrap"'


def _axis_top(fmt: Callable[[float], str], known: list[float], up_px: int) -> str:
    """The gutter beside the upper half: the high at its top, zero at its foot."""
    high = fmt(max(known)) if max(known) > 0 else "0"
    return (
        f'<td valign="top" align="right" {NOTE}><table height="{up_px}" cellspacing="0" '
        f'cellpadding="0"><tr><td valign="top" align="right" {NOTE}>{html.escape(high)}</td></tr>'
        f'<tr><td valign="bottom" align="right" {NOTE}>0</td></tr></table></td>'
    )


def _axis_bottom(fmt: Callable[[float], str], known: list[float]) -> str:
    return f'<td valign="bottom" align="right" {NOTE}>{html.escape(fmt(min(known)))}</td>'


def _axis_range(fmt: Callable[[float], str], high: float, low: float, px: int) -> str:
    """The gutter beside a plot with no zero rule: its high at the top, its low at the foot."""
    return (
        f'<td valign="top" align="right" {NOTE}><table height="{px}" cellspacing="0" '
        f'cellpadding="0"><tr><td valign="top" align="right" {NOTE}>{html.escape(fmt(high))}</td></tr>'
        f'<tr><td valign="bottom" align="right" {NOTE}>{html.escape(fmt(low))}</td></tr></table></td>'
    )


def _tick_row(labels: Sequence[str], step: int, months: Sequence[str] | None, gutter: bool) -> str:
    """Month labels under the plot, each at its column; empty when none fit."""
    cells, at = "", 0
    for i, text in ticks(labels, months):
        if i > len(labels) - 4:  # no room left for the text
            break
        cells += f'<td width="{(i - at) * step}"></td>'
        cells += (
            f'<td width="{step}" style="font:400 10px {MONO};color:{MUTED};'
            f'padding-top:4px;white-space:nowrap">{html.escape(text)}</td>'
        )
        at = i + 1
    if not cells:
        return ""
    return (
        f'<tr>{"<td></td>" if gutter else ""}<td><table cellspacing="0" '
        f'cellpadding="0"><tr>{cells}</tr></table></td></tr>'
    )


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
    fmt: Callable[[float], str] | None = None,
    months: Sequence[str] | None = QUARTERS,
) -> str:
    """A signed chart: an area when ``gap`` is 0, separate columns when it is not.

    Each bar is a one-cell table carrying its colour as ``bgcolor`` — Gmail's
    send path strips a CSS background, and a cell in a shared row cannot hold
    its own height. With a gap, the space between columns is a border in the
    panel's colour, because a cell's fill covers its padding and would merge the
    bars; without one, equal neighbours are merged so a flat run reads as one
    surface. ``fmt`` prints the high, zero and low in a gutter at the left, and
    ``labels`` puts month ticks below (see ``ticks``).
    """
    if total_px is not None:
        up_px, dn_px = split(values, total_px)
    heights = scale(values, up_px, dn_px)
    known = [float(v) for v in values if v is not None] or [0.0]
    edge = f' style="border-right:{gap}px solid {ground}"' if gap else ""

    def cell(height: int, span: int, color: str, align: str) -> str:
        width = col_w * span + gap * (span - 1)
        if height <= 0:
            return f'<td width="{width}"{edge}></td>'
        return f'<td width="{width}" valign="{align}"{edge}>{_mark(height, color)}</td>'

    def half(px: int, color: str, above: bool, axis: str) -> str:
        align = "bottom" if above else "top"
        mine = [max(h, 0) if above else max(-h, 0) for h in heights]
        # touching columns merge whenever equal; separated bars only merge the empty stretches
        runs = _runs(mine) if gap == 0 else _runs_of_zero(mine)
        cells = [cell(h, span, color, align) for h, span in runs]
        return (
            f'<tr>{axis}<td height="{px}" style="height:{px}px;padding:0">'
            f'<table height="{px}" cellspacing="0" cellpadding="0">'
            f"<tr>{''.join(cells)}</tr></table></td></tr>"
        )

    rows = []
    if up_px > 0:
        rows.append(half(up_px, up, True, _axis_top(fmt, known, up_px) if fmt else ""))
    rule = f'<td height="1" bgcolor="{RULE}" style="font:0/0 a">&nbsp;</td>'
    rows.append(f"<tr>{'<td></td>' if fmt else ''}{rule}</tr>")
    if dn_px > 0:
        rows.append(half(dn_px, dn, False, _axis_bottom(fmt, known) if fmt else ""))
    if labels:
        rows.append(_tick_row(labels, col_w + gap, months, bool(fmt)))
    return f'<table cellspacing="0" cellpadding="0">{"".join(rows)}</table>'


Stack = tuple[tuple[int, str | None], ...]


def _merged(stacks: list[tuple[Stack, int]]) -> list[tuple[Stack, int]]:
    """Consecutive identical columns collapsed into one, their widths summed."""
    out: list[tuple[Stack, int]] = []
    for s, w in stacks:
        if out and out[-1][0] == s:
            out[-1] = (s, out[-1][1] + w)
        else:
            out.append((s, w))
    return out


def _mark(height: int, color: str) -> str:
    """A block of colour that is nothing but a border — see the module docstring."""
    return f'<div style="border-top:{height}px solid {color}"></div>'


def _stack(rows: list[tuple[int, str | None]], width: int) -> str:
    """One column: a leading gap becomes padding, coloured rows become marks."""
    marks = ""
    pad = 0
    for h, c in rows:
        if h <= 0:
            continue
        if c is None:
            if marks:
                break  # nothing below the last mark matters
            pad += h
        else:
            marks += _mark(h, c)
    if not marks:
        return f'<td width="{width}"></td>'
    offset = f' style="padding-top:{pad}px"' if pad else ""
    return f'<td width="{width}" valign="top"{offset}>{marks}</td>'


def _paint(spans: list[tuple[int, int, str]], px: int, ground: str) -> Stack:
    """Coloured spans, measured from the foot, as one column's stack from the top.

    An earlier span is painted over a later one. The empty stretch between two
    marks is filled with the ground colour, since ``_stack`` stops at a gap.
    """
    rows: list[str | None] = [None] * px  # index 0 is the top pixel
    for lo, hi, c in reversed(spans):
        for y in range(max(lo, 0), min(hi, px)):
            rows[px - 1 - y] = c
    painted = [i for i, c in enumerate(rows) if c is not None]
    if not painted:
        return ()
    first, last = painted[0], painted[-1]
    out: list[tuple[int, str | None]] = []
    for i, c in enumerate(rows[: last + 1]):
        c = ground if c is None and i > first else c
        if out and out[-1][1] == c:
            out[-1] = (out[-1][0] + 1, c)
        else:
            out.append((1, c))
    return tuple(out)


def _marks_row(marks: Sequence[tuple[int, int]], count: int, col_w: int, gutter: bool) -> str:
    """A strip of small blocks under the plot, one at each marked point: buys up, sells down."""
    signs: dict[int, set[int]] = {}
    for i, sign in marks:
        if 0 <= i < count and sign:
            signs.setdefault(i, set()).add(1 if sign > 0 else -1)
    cells, run = "", 0
    for i in range(count):
        if i not in signs:
            run += 1
            continue
        if run:
            cells += f'<td width="{run * col_w}"></td>'
            run = 0
        color = UP if signs[i] == {1} else DN if signs[i] == {-1} else INK
        cells += f'<td width="{col_w}" valign="top" style="padding-top:3px">{_mark(4, color)}</td>'
    if not signs:
        return ""
    if run:
        cells += f'<td width="{run * col_w}"></td>'
    return (
        f'<tr>{"<td></td>" if gutter else ""}<td><table cellspacing="0" '
        f'cellpadding="0"><tr>{cells}</tr></table></td></tr>'
    )


def line(
    values: Sequence[Number],
    labels: Sequence[str] | None = None,
    total_px: int = 90,
    col_w: int = 12,
    thickness: int = 2,
    color: str = UP,
    fill: bool = True,
    zero: bool = True,
    up_tint: str = UP_TINT,
    dn_tint: str = DN_TINT,
    fmt: Callable[[float], str] | None = None,
    months: Sequence[str] | None = QUARTERS,
    overlay: Sequence[Number] | None = None,
    overlay_color: str = DN,
    level: float | None = None,
    level_color: str = DN,
    marks: Sequence[tuple[int, int]] | None = None,
    ground: str = CARD,
) -> str:
    """A connected line, drawn as one stacked column per point.

    Each column's stroke runs from the previous value to its own, so a step is a
    vertical connector rather than a floating dash and the line reads as one
    path. With ``zero`` the plot is split at a zero rule and the area between
    the line and the rule is tinted by sign; without it the range is the data's
    own, with no rule and no fill. ``fmt`` prints the high, zero and low (or,
    without ``zero``, the high and the low) at the left edge; ``labels`` puts
    quarter ticks below.

    Without ``zero`` the plot can carry more: an ``overlay`` series drawn 1px
    under the line, a constant ``level`` across it (an average cost), and
    ``marks`` — (point index, sign) pairs shown as a strip of blocks below.
    """
    clean = [None if v is None else float(v) for v in values]
    known = [v for v in clean if v is not None]
    if not known:
        return ""
    # Each point is two columns: a stroke-wide riser from the previous value and
    # the level itself — so a step reads as a thin line, not as a bar. A flat
    # run's riser equals its level and the two merge away.
    riser_w, level_w = (thickness, col_w - thickness) if col_w > thickness else (0, col_w)
    if not zero:
        second = [None if v is None else float(v) for v in (overlay or [])]
        extent = known + [v for v in second if v is not None]
        if level is not None:
            extent.append(float(level))
        lo_v, hi_v = min(extent), max(extent)
        factor = (total_px - thickness) / (hi_v - lo_v) if hi_v > lo_v else 0.0

        def lift(v: float | None) -> int | None:
            return None if v is None else round((v - lo_v) * factor)

        main = [lift(v) for v in clean]
        under = [lift(v) for v in second] + [None] * (len(main) - len(second))
        flat = lift(None if level is None else float(level))
        stacks: list[tuple[Stack, int]] = []
        prev_m: int | None = None
        prev_u: int | None = None
        for h, u in zip(main, under, strict=False):
            if h is None:
                stacks.append(((), col_w))
                continue
            pm = h if prev_m is None else prev_m
            pu = u if prev_u is None else prev_u
            prev_m = h
            prev_u = u if u is not None else prev_u
            for riser, w in ((True, riser_w), (False, level_w)):
                if not w:
                    continue
                spans = [
                    (min(pm, h), max(pm, h) + thickness, color)
                    if riser
                    else (h, h + thickness, color)
                ]
                if u is not None and pu is not None:
                    spans.append(
                        (min(pu, u), max(pu, u) + 1, overlay_color)
                        if riser
                        else (u, u + 1, overlay_color)
                    )
                if flat is not None:
                    spans.append((flat, flat + 1, level_color))
                stacks.append((_paint(spans, total_px, ground), w))
        cells = "".join(_stack(list(s), w) for s, w in _merged(stacks))
        axis = _axis_range(fmt, hi_v, lo_v, total_px) if fmt else ""
        rows = [
            f'<tr>{axis}<td height="{total_px}" style="height:{total_px}px;padding:0">'
            f'<table height="{total_px}" cellspacing="0" cellpadding="0"><tr>{cells}</tr></table></td></tr>'
        ]
        if marks:
            rows.append(_marks_row(marks, len(clean), col_w, bool(fmt)))
        if labels:
            rows.append(_tick_row(labels, col_w, months, bool(fmt)))
        return f'<table cellspacing="0" cellpadding="0">{"".join(rows)}</table>'
    # the stroke sits on top of its value, so the upper box is a stroke taller
    plot_u, dn_px = split(clean, total_px - thickness)
    scaled = scale([0.0 if v is None else v for v in clean], plot_u, dn_px)
    heights = [None if v is None else h for v, h in zip(clean, scaled, strict=False)]
    up_px = plot_u + thickness

    def above(lo: int, hi: int) -> Stack:
        # spacer down to the stroke, the stroke, tint from there to the rule
        top, bottom = min(hi, up_px), max(lo, 0)
        stroke = max(top - bottom, 0)
        tint = bottom if fill and stroke else 0
        return ((up_px - top, None), (stroke, color), (tint, up_tint))

    def below(lo: int, hi: int) -> Stack:
        # tint from the rule, stroke, spacer
        y1, y2 = max(lo, -dn_px), min(hi, 0)
        stroke = max(y2 - y1, 0)
        tint = -y2 if fill and stroke else 0
        return ((tint, dn_tint), (stroke, color), (dn_px - tint - stroke, None))

    upper: list[tuple[Stack, int]] = []
    lower: list[tuple[Stack, int]] = []
    prev: int | None = None
    for h in heights:
        if h is None:
            upper.append(((), col_w))
            lower.append(((), col_w))
            continue
        p = h if prev is None else prev
        prev = h
        for lo, hi, w in ((min(p, h), max(p, h) + thickness, riser_w), (h, h + thickness, level_w)):
            if w:
                upper.append((above(lo, hi), w))
                if dn_px:
                    lower.append((below(lo, hi), w))

    def row(stacks: list[tuple[Stack, int]], px: int, axis: str) -> str:
        # a flat run is one wide column, not a repeat of the same one
        cells = "".join(_stack(list(s), w) for s, w in _merged(stacks))
        return (
            f'<tr>{axis}<td height="{px}" style="height:{px}px;padding:0">'
            f'<table height="{px}" cellspacing="0" cellpadding="0"><tr>{cells}</tr></table></td></tr>'
        )

    gutter = bool(fmt)
    rows = [row(upper, up_px, _axis_top(fmt, known, up_px) if fmt else "")]
    rule = f'<td height="1" bgcolor="{RULE}" style="font:0/0 a">&nbsp;</td>'
    rows.append(f"<tr>{'<td></td>' if gutter else ''}{rule}</tr>")
    if dn_px:
        rows.append(row(lower, dn_px, _axis_bottom(fmt, known) if fmt else ""))
    if labels:
        rows.append(_tick_row(labels, col_w, months, gutter))
    return f'<table cellspacing="0" cellpadding="0">{"".join(rows)}</table>'


def shares(
    rows: Sequence[tuple[str, Number, str]],
    width: int = 240,
    bar_h: int = 10,
    color: str = UP,
) -> str:
    """Horizontal bars from a common left edge: label, bar in proportion to the largest, note."""
    values = [max(0.0, 0.0 if v is None else float(v)) for _, v, _ in rows]
    peak = max(values, default=0.0)
    out = []
    for (label, _, note), value in zip(rows, values, strict=False):
        px = 0 if peak == 0 else round(value / peak * width)
        rest = f'<td width="{width - px}" style="font:0/0 a">&nbsp;</td>' if px < width else ""
        bar = (
            f'<table cellspacing="0" cellpadding="0" border="0"><tr>'
            f'<td width="{px}" height="{bar_h}"{_fill(color if px else None)} style="font:0/0 a">&nbsp;</td>'
            f"{rest}</tr></table>"
        )
        out.append(
            "<tr>"
            f'<td style="font:400 11.5px {SANS};color:{INK};padding:2px 8px 2px 0;'
            f'white-space:nowrap">{html.escape(label)}</td>'
            f'<td width="{width}" style="padding:2px 0">{bar}</td>'
            f'<td align="right" style="font:400 11px {MONO};color:{MUTED};'
            f'padding:2px 0 2px 8px;white-space:nowrap">{html.escape(note)}</td>'
            "</tr>"
        )
    return (
        f'<table cellspacing="0" cellpadding="0" border="0" style="width:100%">'
        f"{''.join(out)}</table>"
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


def strips(
    rows: Sequence[tuple[str, Number, str]],
    width: int = 160,
    bar_h: int = 8,
    up: str = UP,
    dn: str = DN,
) -> str:
    """One-sided bars in proportion to the largest magnitude, coloured by sign: label, bar, note.

    Lighter than ``hbars`` (no zero rule, no empty half) for a long list where
    the sign is also in the note.
    """
    values = [0.0 if v is None else float(v) for _, v, _ in rows]
    peak = max((abs(v) for v in values), default=0.0)
    out = []
    for (label, _, note), value in zip(rows, values, strict=False):
        px = 0 if peak == 0 else round(abs(value) / peak * width)
        color = dn if value < 0 else up
        bar = (
            f'<table cellspacing="0" cellpadding="0" border="0"><tr>'
            f'<td width="{px}" height="{bar_h}"{_fill(color if px else None)} style="font:0/0 a">&nbsp;</td>'
            f'<td width="{width - px}" style="font:0/0 a">&nbsp;</td></tr></table>'
        )
        # the label has a line of its own: beside the bar and the note it had a few
        # characters per line on a phone
        out.append(
            "<tr>"
            f'<td colspan="2" style="font:400 11.5px {SANS};color:{INK};padding:5px 0 1px">'
            f"{html.escape(label)}</td></tr><tr>"
            f'<td width="{width}" style="padding:0 0 2px;vertical-align:middle">{bar}</td>'
            f'<td align="right" style="font:400 11px {MONO};color:{MUTED};'
            f'padding:0 0 2px 8px;white-space:nowrap">{html.escape(note)}</td>'
            "</tr>"
        )
    return (
        f'<table cellspacing="0" cellpadding="0" border="0" style="width:100%">'
        f"{''.join(out)}</table>"
    )
