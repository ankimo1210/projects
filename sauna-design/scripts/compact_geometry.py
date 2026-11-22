"""Dependency-free rectangle sweep independent of the Blender model generator."""

import itertools
import math


def rectangle_metrics(rectangles, width, height):
    if not all(math.isfinite(v) and v > 0 for v in (width, height)):
        raise ValueError("Positive finite floor dimensions required")
    rects = []
    for r in rectangles:
        if len(r) != 4 or not all(math.isfinite(v) for v in r) or r[2] <= 0 or r[3] <= 0:
            raise ValueError("Rectangle requires finite x,y and positive width,height")
        rects.append(tuple(r))
    outside = [
        i
        for i, (x, y, w, h) in enumerate(rects)
        if x < -1e-8 or y < -1e-8 or x + w > width + 1e-8 or y + h > height + 1e-8
    ]
    clipped = [
        (max(0, x), max(0, y), min(width, x + w), min(height, y + h)) for x, y, w, h in rects
    ]
    clipped = [r for r in clipped if r[2] > r[0] and r[3] > r[1]]
    xs = sorted({x for r in clipped for x in (r[0], r[2])})
    union = 0.0
    for x0, x1 in itertools.pairwise(xs):
        mid = (x0 + x1) / 2
        ys = sorted((r[1], r[3]) for r in clipped if r[0] <= mid < r[2])
        covered = 0.0
        if ys:
            start, end = ys[0]
            for low, high in ys[1:]:
                if low > end:
                    covered += end - start
                    start, end = low, high
                else:
                    end = max(end, high)
            covered += end - start
        union += (x1 - x0) * covered
    clipped_sum = sum((r[2] - r[0]) * (r[3] - r[1]) for r in clipped)
    return {
        "floor_area_m2": width * height,
        "summed_area_m2": sum(w * h for _, _, w, h in rects),
        "union_area_m2": union,
        "overlap_area_m2": max(0.0, clipped_sum - union),
        "uncovered_area_m2": max(0.0, width * height - union),
        "out_of_bounds_indices": outside,
        "note": "Outer rectangle geometry only; uncovered space may be deliberately allocated to walls/circulation. Not an occupancy or code determination.",
    }
