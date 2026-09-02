"""Acceptance checks for the nine-line core-Tokyo 3D profile."""
from __future__ import annotations

import json
import pathlib
from collections import defaultdict

import numpy as np
import pytest

from subway3d import alignment as A
from subway3d import chart as C
from subway3d.lines import LINES, PAGES

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODEL = ROOT / "data/out/model.json"
KEYS = list(LINES)

# Stations whose marker is red/blue on the chart and therefore not detected as black.
UNDETECTED = {("marunouchi", "大手町"), ("tozai", "茅場町"), ("yurakucho", "飯田橋"), ("hanzomon", "大手町")}

pytestmark = pytest.mark.skipif(not (ROOT / PAGES[3]).exists(), reason="raw chart pages not rendered")


@pytest.fixture(scope="module")
def pages():
    return {p: C.load_page(str(ROOT / path)) for p, path in PAGES.items()}


@pytest.fixture(scope="module")
def model():
    return json.load(open(MODEL))


def line(model, key):
    return next(ln for ln in model["lines"] if ln["key"] == key)


def test_every_page_has_its_charts(pages):
    assert [len(C.detect_frames(pages[p][0])) for p in (3, 4, 5)] == [4, 4, 4]


@pytest.mark.parametrize("key", KEYS)
def test_y_axis_calibration_matches_printed_gridlines(pages, key):
    """At least six printed 5 m gridlines must decode to a multiple of 5 m within 0.2 m."""
    sp = LINES[key]
    black, gray = pages[sp.page]
    ch = C.chart_at(black, sp.chart, sp.axis)
    errs = sorted(C.gridline_errors(gray, ch))
    assert errs[:6] == pytest.approx([0] * 6, abs=0.2), errs


@pytest.mark.parametrize("key", KEYS)
def test_station_chainages_snap_to_detected_markers(pages, key):
    sp = LINES[key]
    black, _ = pages[sp.page]
    markers = C.station_markers(C.chart_at(black, sp.chart, sp.axis))
    for name, d in sp.stations:
        if (key, name) in UNDETECTED:
            continue
        assert min(abs(m - d) for m in markers) <= 150, (name, d)


@pytest.mark.parametrize("key", KEYS)
def test_rail_profile_has_no_label_spikes(pages, key):
    """A hidden rail curve must be bridged, not replaced by the station label above it."""
    sp = LINES[key]
    black, _ = pages[sp.page]
    ch = C.chart_at(black, sp.chart, sp.axis)
    markers = C.station_markers(ch)
    d, e = C.rail_profile(ch, [*markers, *(C.snap(c, markers) for _, c in sp.stations)])
    # Resample at 25 m: per-column values jitter by a pixel, a label spike is 10-27 m.
    grid = np.arange(sp.stations[0][1], sp.stations[-1][1], 25.0)
    grade = np.abs(np.diff(np.interp(grid, d, e))) / 25.0
    assert grade.max() < 0.08, f"grade {grade.max():.2f} at {grid[grade.argmax()]:.0f} m"


@pytest.mark.parametrize("key", KEYS)
def test_chart_chainage_agrees_with_map_distance(model, key):
    """Chart chainage and OSM alignment length must agree within 7% over the section."""
    st = line(model, key)["stations"]
    chart_len = st[-1]["chart_chainage_m"] - st[0]["chart_chainage_m"]
    map_len = st[-1]["alignment_m"] - st[0]["alignment_m"]
    assert abs(chart_len - map_len) / map_len < 0.07


@pytest.mark.parametrize("key", KEYS)
def test_station_anchors_are_monotonic_and_on_track(model, key):
    ln = line(model, key)
    a = [s["alignment_m"] for s in ln["stations"]]
    assert a == sorted(a) and len(set(a)) == len(a)
    for s in ln["stations"]:
        assert min(A.haversine((p["lon"], p["lat"]), tuple(s["coord"])) for p in ln["track"]) < 20, s["name"]


@pytest.mark.parametrize("key", KEYS)
def test_every_station_is_below_ground(model, key):
    for s in line(model, key)["stations"]:
        assert s["rail_tp_m"] < s["ground_tp_m"], s["name"]


@pytest.mark.parametrize("key", KEYS)
def test_track_is_continuous_and_dense(model, key):
    track = line(model, key)["track"]
    assert len(track) > 100
    steps = [A.haversine((a["lon"], a["lat"]), (b["lon"], b["lat"])) for a, b in zip(track, track[1:])]
    assert max(steps) < 40.0
    grades = [abs(a["rail_tp_m"] - b["rail_tp_m"]) / s for a, b, s in zip(track, track[1:], steps)]
    assert max(grades) < 0.08


def test_kokkaigijidomae_is_the_deepest_chiyoda_station(model):
    depths = {s["name"]: s["depth_m"] for s in line(model, "chiyoda")["stations"]}
    assert max(depths, key=depths.get) == "国会議事堂前"


def test_kokkaigijidomae_depth_matches_published_value(model):
    """Published platform depth is 37.9 m; the pipeline measures to rail level.

    Tolerance is 4 m: pixel tracing contributes ~0.3 m, rail-to-platform ~1.1 m, and
    the published figure's ground reference point is not stated, on terrain that
    varies by several metres within 100 m of the station.
    """
    depth = next(s["depth_m"] for s in line(model, "chiyoda")["stations"] if s["name"] == "国会議事堂前")
    assert depth == pytest.approx(37.9, abs=4.0)


def test_otemachi_stack_order(model):
    """丸ノ内線 is the shallowest and 半蔵門線 the deepest of the five lines under 大手町."""
    rail = {ln["key"]: next(s["rail_tp_m"] for s in ln["stations"] if s["name"] == "大手町")
            for ln in model["lines"] if any(s["name"] == "大手町" for s in ln["stations"])}
    assert set(rail) == {"marunouchi", "tozai", "chiyoda", "hanzomon", "mita"}
    assert max(rail, key=rail.get) == "marunouchi"
    assert min(rail, key=rail.get) == "hanzomon"


def test_shared_stations_see_the_same_ground(model):
    """Ground comes from one DEM, so lines sharing a station must agree on it (nodes ≤ 300 m apart)."""
    ground = defaultdict(list)
    for ln in model["lines"]:
        for s in ln["stations"]:
            ground[s["name"]].append(s["ground_tp_m"])
    spread = {n: max(g) - min(g) for n, g in ground.items() if len(g) > 1}
    assert max(spread.values()) < 6.0, spread
