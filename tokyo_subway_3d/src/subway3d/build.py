"""Assemble the 3D model: chart profile x OSM alignment x GSI ground elevation.

Chart chainage and map distance disagree by up to a few percent overall and much
more locally (the charts compress some inter-station gaps), so stations are used as
anchors and the chart chainage is rubber-sheeted onto the alignment between them.
"""
from __future__ import annotations

import json
import sys

import numpy as np

from subway3d import alignment as A
from subway3d import chart as C
from subway3d import elevation as E
from subway3d.lines import LINES, PAGES, LineSpec

SOURCES = {
    "depth": "中央防災会議 大規模水害対策に関する専門調査会 第13回 資料8（縦断図, 2009-01-23）",
    "alignment": "OpenStreetMap contributors (ODbL)",
    "ground": "国土地理院 標高API (DEM 1m/5m レーザ)",
}
# OSM `colour` is used when present; 有楽町線 ways carry none.
FALLBACK_COLOUR = {"yurakucho": "#C1A470"}


def rubber_sheet(chart_d: np.ndarray, anchors_chart, anchors_align) -> np.ndarray:
    """Map chart chainage onto alignment distance through the station anchors."""
    return np.interp(chart_d, anchors_chart, anchors_align)


def build_line(spec: LineSpec, page: tuple, ways: list[dict], stops: list[dict],
               cache_path: str, step: float = 25.0, fetch_ground: bool = True) -> dict:
    black, _ = page
    ch = C.chart_at(black, spec.chart, spec.axis)
    markers = C.station_markers(ch)
    chain = [C.snap(d, markers) for _, d in spec.stations]
    cd, ce = C.rail_profile(ch, [*markers, *chain])

    graph = A.Graph(ways, spec.osm_name)
    poly = A.track(graph, stops, [name for name, _ in spec.stations])
    cum = A.cumulative(poly)
    anchors = [A.anchor(poly, stops, graph, name) for name, _ in spec.stations]
    anchors_align = [a[1] for a in anchors]
    if any(b <= a for a, b in zip(anchors_align, anchors_align[1:])):
        raise RuntimeError(f"{spec.key}: station anchors are not monotonic along the track: {anchors_align}")

    # Sample evenly along the alignment, then read the rail elevation for that point.
    s = np.arange(0.0, cum[-1], step)
    s = np.append(s, cum[-1])
    lons = np.interp(s, cum, [p[0] for p in poly])
    lats = np.interp(s, cum, [p[1] for p in poly])
    chart_s = np.interp(s, anchors_align, chain)
    rail = np.interp(chart_s, cd, ce)

    if fetch_ground:
        ground = E.ground_elevations(list(zip(lons, lats)), cache_path)
        g = np.array([np.nan if v is None else v for v in ground], dtype=float)
        if np.isnan(g).any():  # DEM gaps: bridge them rather than drop the vertex
            idx = np.arange(len(g))
            g[np.isnan(g)] = np.interp(idx[np.isnan(g)], idx[~np.isnan(g)], g[~np.isnan(g)])
    else:
        g = np.full(len(s), np.nan)

    colour = next((w["tags"]["colour"] for w in ways
                   if w.get("tags", {}).get("name") == spec.osm_name and "colour" in w["tags"]),
                  FALLBACK_COLOUR.get(spec.key))
    stations = []
    for (name, _), (coord, a), d in zip(spec.stations, anchors, chain):
        j = int(np.argmin(abs(s - a)))
        stations.append({
            "name": name,
            "coord": [round(coord[0], 6), round(coord[1], 6)],
            "chart_chainage_m": float(d),
            "alignment_m": round(float(a), 1),
            "rail_tp_m": round(float(rail[j]), 2),
            "ground_tp_m": None if np.isnan(g[j]) else round(float(g[j]), 1),
            "depth_m": None if np.isnan(g[j]) else round(float(g[j] - rail[j]), 1),
        })
    track = [
        {"lon": round(float(lo), 6), "lat": round(float(la), 6), "rail_tp_m": round(float(r), 2),
         "ground_tp_m": None if np.isnan(gg) else round(float(gg), 1)}
        for lo, la, r, gg in zip(lons, lats, rail, g)
    ]
    return {"key": spec.key, "name": spec.name, "colour": colour,
            "section": f"{spec.stations[0][0]}〜{spec.stations[-1][0]}",
            "length_m": round(float(cum[-1]), 1), "stations": stations, "track": track}


def build_all(root: str = ".", cache_path: str = "data/raw/gsi_cache.json", keys=None,
              fetch_ground: bool = True) -> dict:
    ways = json.load(open(f"{root}/data/raw/osm_ways.json"))["elements"]
    stops = json.load(open(f"{root}/data/raw/osm_stops.json"))["elements"]
    pages = {p: C.load_page(f"{root}/{path}") for p, path in PAGES.items()}
    lines = [build_line(LINES[k], pages[LINES[k].page], ways, stops, f"{root}/{cache_path}",
                        fetch_ground=fetch_ground) for k in (keys or LINES)]
    return {"title": "東京の地下鉄 都心部（実測の軌条面標高）", "sources": SOURCES, "lines": lines}


def to_geojson(model: dict) -> dict:
    feats = []
    for ln in model["lines"]:
        feats.append({
            "type": "Feature",
            "geometry": {"type": "LineString",
                         "coordinates": [[p["lon"], p["lat"], p["rail_tp_m"]] for p in ln["track"]]},
            "properties": {"kind": "rail", "line": ln["name"], "colour": ln["colour"]},
        })
        feats += [{
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [*st["coord"], st["rail_tp_m"]]},
            "properties": {"kind": "station", "line": ln["name"], **st},
        } for st in ln["stations"]]
    return {"type": "FeatureCollection", "features": feats}


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "data/out"
    m = build_all()
    json.dump(m, open(f"{out}/model.json", "w"), ensure_ascii=False, indent=1)
    json.dump(to_geojson(m), open(f"{out}/lines.geojson", "w"), ensure_ascii=False)
    for ln in m["lines"]:
        print(f"\n{ln['name']} {ln['section']} ({ln['length_m']:.0f} m)")
        print(f"{'駅':<8s}{'沿線m':>7s}{'軌条面':>8s}{'地盤高':>8s}{'深さ':>7s}")
        for st in ln["stations"]:
            print(f"{st['name']:<8s}{st['alignment_m']:>7.0f}{st['rail_tp_m']:>8.2f}{st['ground_tp_m']:>8.1f}{st['depth_m']:>7.1f}")
