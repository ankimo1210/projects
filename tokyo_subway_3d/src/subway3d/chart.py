"""Digitize rail-surface profiles from the Cabinet Office flood-simulation charts.

Source: 中央防災会議 大規模水害対策に関する専門調査会 (第13回, 2009-01-23)
        資料8「地下鉄等の浸水シミュレーション（縦断図）」pp.3–5, rendered at 300 dpi.
Each page stacks up to four charts; the frame of each is detected from the raster,
and the printed axis values come from the LineSpec.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class Chart:
    """A calibrated raster chart: pixel <-> (chainage in m, elevation in T.P. m)."""

    black: np.ndarray
    frame: dict  # x_left, x_right, y_top, y_bottom (pixels)
    axis: dict  # dist_left, dist_right, elev_top, elev_bottom

    def x_to_dist(self, x: float) -> float:
        f = (x - self.frame["x_left"]) / (self.frame["x_right"] - self.frame["x_left"])
        return self.axis["dist_left"] + f * (self.axis["dist_right"] - self.axis["dist_left"])

    def dist_to_x(self, d: float) -> float:
        f = (d - self.axis["dist_left"]) / (self.axis["dist_right"] - self.axis["dist_left"])
        return self.frame["x_left"] + f * (self.frame["x_right"] - self.frame["x_left"])

    def y_to_elev(self, y: float) -> float:
        f = (y - self.frame["y_top"]) / (self.frame["y_bottom"] - self.frame["y_top"])
        return self.axis["elev_top"] + f * (self.axis["elev_bottom"] - self.axis["elev_top"])


def load_page(png_path: str) -> tuple[np.ndarray, np.ndarray]:
    """Return (black mask, gray mask) of a rendered page."""
    a = np.array(Image.open(png_path).convert("RGB")).astype(int)
    mx, mn = a.max(2), a.min(2)
    # Near-black: the rail-surface curve, the frame, the station markers and the labels.
    # Every other series in the chart is saturated colour, so this isolates them cleanly.
    black = (mx < 110) & ((mx - mn) < 40)
    gray = (mx < 215) & ((mx - mn) < 30)  # gridlines + black
    return black, gray


def detect_frames(black: np.ndarray) -> list[dict]:
    """Find every chart frame on the page, top to bottom.

    A frame edge is a black run spanning most of the page width (top/bottom) or most
    of the frame height (left/right); nothing else on these pages is that long.
    """
    h, w = black.shape
    rows = black.sum(1)
    groups: list[list[int]] = []
    for y in np.where(rows > w * 0.55)[0]:
        if groups and y - groups[-1][-1] <= 2:
            groups[-1].append(int(y))
        else:
            groups.append([int(y)])
    edges = [int(np.mean(g)) for g in groups]
    frames = []
    for top, bottom in zip(edges[0::2], edges[1::2]):
        cols = black[top + 5 : bottom - 5].sum(0)
        xs = np.where(cols > (bottom - top - 10) * 0.9)[0]
        frames.append(dict(x_left=int(xs[0]), x_right=int(xs[-1]), y_top=top, y_bottom=bottom))
    return frames


def chart_at(black: np.ndarray, index: int, axis: dict) -> Chart:
    return Chart(black=black, frame=detect_frames(black)[index], axis=axis)


def rail_profile(chart: Chart, label_chainages=(), half_width: int = 20, tol: float = 3.0
                 ) -> tuple[np.ndarray, np.ndarray]:
    """Return (chainage_m, rail_elevation_TPm).

    The rail-surface curve is the lowest black feature inside the frame: the coloured
    water-head curves are not black and labels normally sit above it. That fails only
    at station labels, which hang below a shallow rail (青山一丁目 on 半蔵門線) or are all
    that is left when a "◯◯線から流入" box covers the curve (永田町 on 有楽町線). So within
    `half_width` px of each label centre (`label_chainages`: detected ▼ markers plus the
    configured station chainages), values that stray more than `tol` from the chord
    through the columns just outside are replaced by that chord. Columns with no black
    pixel at all (curve hidden, label absent) are bridged the same way.
    """
    fr = chart.frame
    # The top 45 px hold the "20:25"-style time labels; the rail never comes that close.
    y0, y1 = fr["y_top"] + 45, fr["y_bottom"] - 2
    xs = np.arange(fr["x_left"] + 3, fr["x_right"] - 2)
    y = np.full(len(xs), np.nan)
    for k, x in enumerate(xs):
        col = np.where(chart.black[y0:y1, x])[0]
        if col.size:
            y[k] = col.max() + y0
    for cx in label_chainages:
        c = int(round(chart.dist_to_x(cx))) - xs[0]
        lo, hi = max(0, c - half_width), min(len(xs) - 1, c + half_width)
        left = [k for k in range(lo - 1, max(-1, lo - 60), -1) if not np.isnan(y[k])]
        right = [k for k in range(hi + 1, min(len(xs), hi + 60)) if not np.isnan(y[k])]
        if not left or not right:
            continue
        a, b = left[0], right[0]
        chord = y[a] + (y[b] - y[a]) * (np.arange(lo, hi + 1) - a) / (b - a)
        dev = np.nanmax(np.abs(y[lo : hi + 1] - chord)) if not np.all(np.isnan(y[lo : hi + 1])) else 0.0
        if dev * _px_per_m(chart) ** -1 > tol:
            y[lo : hi + 1] = np.nan
    ok = ~np.isnan(y)
    d = chart.x_to_dist(xs.astype(float))
    return d, chart.y_to_elev(np.interp(np.arange(len(xs)), np.where(ok)[0], y[ok]))


def _px_per_m(chart: Chart) -> float:
    fr, ax = chart.frame, chart.axis
    return (fr["y_bottom"] - fr["y_top"]) / (ax["elev_top"] - ax["elev_bottom"])


def station_markers(chart: Chart, min_w: int = 18, max_w: int = 34) -> list[float]:
    """Return the chainage of every station marker (a solid black down-triangle)."""
    fr = chart.frame
    hits: list[tuple[int, int]] = []
    for y in range(fr["y_top"] + 3, fr["y_bottom"] - 30):
        row = chart.black[y]
        xs = np.where(row)[0]
        if xs.size == 0:
            continue
        runs, start, prev = [], xs[0], xs[0]
        for x in xs[1:]:
            if x - prev > 1:
                runs.append((start, prev))
                start = x
            prev = x
        runs.append((start, prev))
        for a, b in runs:
            w = b - a + 1
            if not (min_w <= w <= max_w):
                continue
            centre = (a + b) // 2
            below = chart.black[y + 7, max(0, centre - 3) : centre + 4].sum()
            wide_below = chart.black[y + 7, a : b + 1].sum()
            # Apex-down triangle: still filled at the centre, much narrower overall.
            if below >= 5 and wide_below <= w - 6:
                hits.append((centre, y))
    hits.sort()
    groups: list[list[int]] = []
    for cx, _ in hits:
        if groups and cx - groups[-1][-1] <= 12:
            groups[-1].append(cx)
        else:
            groups.append([cx])
    return [chart.x_to_dist(float(np.median(g))) for g in groups if len(g) >= 3]


def snap(chainage: float, markers: list[float], tol: float = 150.0) -> float:
    """Replace an eye-read chainage by the nearest detected marker, if one is close."""
    if not markers:
        return chainage
    m = min(markers, key=lambda v: abs(v - chainage))
    return m if abs(m - chainage) <= tol else chainage


def gridline_errors(gray: np.ndarray, chart: Chart) -> list[float]:
    """How far each printed 5 m gridline decodes from a multiple of 5 m (calibration check)."""
    fr = chart.frame
    band = gray[fr["y_top"] - 6 : fr["y_bottom"] + 6, fr["x_left"] + 40 : fr["x_right"] - 40]
    rows = band.sum(1)
    cand = np.where(rows > band.shape[1] * 0.20)[0]
    groups: list[list[int]] = []
    for y in cand:
        if groups and y - groups[-1][-1] <= 3:
            groups[-1].append(int(y))
        else:
            groups.append([int(y)])
    errs = []
    for g in groups:
        e = chart.y_to_elev(float(np.mean(g)) + fr["y_top"] - 6)
        errs.append(abs(e - round(e / 5) * 5))
    return errs
