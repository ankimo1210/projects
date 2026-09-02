"""Ground-surface elevation from the GSI DEM web service, with an on-disk cache."""
from __future__ import annotations

import json
import os
import time
import urllib.request

URL = "https://cyberjapandata2.gsi.go.jp/general/dem/scripts/getelevation.php"


def ground_elevations(points, cache_path: str, pause: float = 0.2) -> list[float]:
    """Return T.P. elevation (m) for each (lon, lat), caching every lookup.

    Points the service cannot resolve come back as "-----"; those become None so the
    caller can interpolate rather than silently treating a gap as sea level.
    """
    cache: dict[str, float | None] = {}
    if os.path.exists(cache_path):
        cache = json.load(open(cache_path))

    out: list[float | None] = []
    fetched = 0
    for lon, lat in points:
        key = f"{lon:.6f},{lat:.6f}"
        if key not in cache:
            with urllib.request.urlopen(f"{URL}?lon={lon}&lat={lat}&outtype=JSON", timeout=30) as r:
                e = json.load(r).get("elevation")
            cache[key] = e if isinstance(e, (int, float)) else None
            fetched += 1
            time.sleep(pause)
        out.append(cache[key])

    if fetched:
        json.dump(cache, open(cache_path, "w"))
    return out
