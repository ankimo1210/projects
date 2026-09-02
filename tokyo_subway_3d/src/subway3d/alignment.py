"""Build a single continuous 2D centreline for one track of a subway line.

Geometry comes from OpenStreetMap (ODbL); the tunnels there are traced from
基盤地図情報 2500. The two tracks of a line are separate node chains, so a shortest
path through the node graph stays on one track unless a crossover is shorter.
"""
from __future__ import annotations

import heapq
import math
import re

R_EARTH = 6378137.0


def haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance in metres between (lon, lat) pairs."""
    lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * R_EARTH * math.asin(math.sqrt(h))


def norm_name(s: str | None) -> str:
    """Station names as printed on the charts: no 〈丸の内〉 suffix, ケ not ヶ, no 駅."""
    s = re.sub(r"[〈（(].*?[〉）)]", "", s or "")
    return s.replace("ヶ", "ケ").replace("駅", "").strip()


class Graph:
    """Undirected node graph of one line's OSM ways, weighted by metres."""

    def __init__(self, ways: list[dict], osm_name: str):
        self.xy: dict[int, tuple[float, float]] = {}
        self.adj: dict[int, list[tuple[int, float]]] = {}
        for w in ways:
            name = w.get("tags", {}).get("name")
            # Platform tracks are named "<line>;<station>;<n>番線" and a few link ways are
            # unnamed; both are needed to keep the chain continuous through stations.
            if name is not None and osm_name not in name:
                continue
            ids, geom = w["nodes"], w["geometry"]
            for i, (nid, pt) in enumerate(zip(ids, geom)):
                self.xy[nid] = (pt["lon"], pt["lat"])
                if i:
                    a, b = ids[i - 1], nid
                    d = haversine(self.xy[a], self.xy[b])
                    self.adj.setdefault(a, []).append((b, d))
                    self.adj.setdefault(b, []).append((a, d))

    def shortest(self, s: int, targets: set[int]) -> list[int] | None:
        """Dijkstra from `s` to the nearest of `targets`; returns the node path."""
        dist, prev, pq = {s: 0.0}, {}, [(0.0, s)]
        while pq:
            d, u = heapq.heappop(pq)
            if u in targets:
                path = [u]
                while path[-1] != s:
                    path.append(prev[path[-1]])
                return path[::-1]
            if d > dist.get(u, math.inf):
                continue
            for v, w in self.adj.get(u, []):
                nd = d + w
                if nd < dist.get(v, math.inf):
                    dist[v], prev[v] = nd, u
                    heapq.heappush(pq, (nd, v))
        return None


def stop_nodes(stops: list[dict], graph: Graph, name: str) -> list[int]:
    """OSM node ids on this line's ways that carry the station name."""
    return [e["id"] for e in stops if norm_name(e["tags"].get("name")) == norm_name(name) and e["id"] in graph.xy]


def track(graph: Graph, stops: list[dict], first: str, last: str) -> list[tuple[float, float]]:
    """One track's centreline from station `first` to station `last`, as (lon, lat) vertices."""
    starts, goals = stop_nodes(stops, graph, first), set(stop_nodes(stops, graph, last))
    if not starts or not goals:
        raise RuntimeError(f"no stop node on the line for {first!r} or {last!r}")
    best = None
    for s in starts:  # either track may be the shorter one; keep the shortest path
        p = graph.shortest(s, goals)
        if p and (best is None or len(p) < len(best)):
            best = p
    if best is None:
        raise RuntimeError(f"no path from {first!r} to {last!r}")
    return [graph.xy[n] for n in best]


def project(polyline, pt: tuple[float, float]) -> tuple[int, float]:
    """Return (vertex index, cumulative distance) of the polyline vertex nearest `pt`."""
    cum, best, best_i, best_d = 0.0, math.inf, 0, 0.0
    for i, v in enumerate(polyline):
        if i:
            cum += haversine(polyline[i - 1], v)
        d = haversine(v, pt)
        if d < best:
            best, best_i, best_d = d, i, cum
    return best_i, best_d


def anchor(polyline, stops: list[dict], graph: Graph, name: str) -> tuple[tuple[float, float], float]:
    """(coord, chainage along polyline) of the station's stop node on this track.

    Both tracks carry a stop node; the one on our track projects with ~0 m offset.
    """
    cands = [graph.xy[n] for n in stop_nodes(stops, graph, name)]
    if not cands:
        raise RuntimeError(f"no stop node for {name!r}")
    best = min(cands, key=lambda c: min(haversine(c, v) for v in polyline))
    return best, project(polyline, best)[1]


def cumulative(polyline) -> list[float]:
    out, acc = [0.0], 0.0
    for i in range(1, len(polyline)):
        acc += haversine(polyline[i - 1], polyline[i])
        out.append(acc)
    return out
