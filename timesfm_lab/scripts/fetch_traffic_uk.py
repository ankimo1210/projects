"""Download the 2026 UK motorway sensor counts used as the traffic control."""

from timesfm_lab.traffic_uk import CACHE, fetch, load_series

if __name__ == "__main__":
    df = fetch()
    print(f"\n{len(df)} hourly rows, {df.site.nunique()} sites -> {CACHE}")
    series = load_series()
    print(f"{len(series)} usable segments")
    if series:
        lens = sorted(len(v) for _s, v, _t, _m in series)
        imp = sum(int(m.sum()) for _s, _v, _t, m in series)
        pts = sum(len(v) for _s, v, _t, _m in series)
        print(f"segment length: min {lens[0]} median {lens[len(lens)//2]} max {lens[-1]}")
        print(f"interpolated points: {imp} / {pts} ({100*imp/pts:.2f}%)")
