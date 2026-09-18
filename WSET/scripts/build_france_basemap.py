#!/usr/bin/env python3
"""Rebuild the offline France SVGs and verify their representative points.

Geometry is pinned in france_geography.json; this command never uses the network.
The equirectangular viewport uses the same transform for paths and region pins.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from xml.sax.saxutils import quoteattr

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'ReferenceSources/RegionMaps/france_geography.json'
MAP_MASTER = ROOT / 'ReferenceSources/wset_region_map_master.json'
OUTPUT = ROOT / 'ReferenceSources/RegionMaps'


def project(longitude, latitude, viewport):
    values = [longitude, latitude, *[viewport[k] for k in ('west', 'east', 'south', 'north')]]
    if not all(math.isfinite(v) for v in values):
        raise ValueError('Coordinates must be finite')
    if viewport['east'] <= viewport['west'] or viewport['north'] <= viewport['south']:
        raise ValueError('Invalid geographic extent')
    return ((longitude - viewport['west']) / (viewport['east'] - viewport['west']),
            (viewport['north'] - latitude) / (viewport['north'] - viewport['south']))


def render_map(data, dark=False):
    v = data['viewport']
    width, height = v['width'], v['height']
    sea, land, france, border, river = (
        ('#182E36', '#283A36', '#3C5144', '#5D7365', '#6A9EAD') if dark else
        ('#DDECF0', '#F1EFE5', '#DCE5D4', '#A5B8A5', '#86B7CA')
    )
    def line(points, close=False):
        coordinates = [project(p[0], p[1], v) for p in points]
        return 'M' + ' L'.join(f'{x * width:.2f} {y * height:.2f}' for x, y in coordinates) + (' Z' if close else '')
    result = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<title>フランスの産地探索地図</title>',
        '<desc>Made with Natural Earth. 国土・河川の概略地図。産地の法的境界を示しません。</desc>',
        f'<rect width="{width}" height="{height}" fill="{sea}"/>',
        f'<defs><clipPath id="extent"><rect width="{width}" height="{height}"/></clipPath></defs>',
        '<g clip-path="url(#extent)" stroke-linejoin="round" stroke-linecap="round">',
    ]
    for country in data['countries']:
        fill = france if country['name'] == 'France' else land
        for polygon in country['polygons']:
            path = ' '.join(line(ring, close=True) for ring in polygon)
            result.append(f'<path data-country={quoteattr(country["name"])} d="{path}" fill="{fill}" fill-rule="evenodd" stroke="{border}" stroke-width="1.25"/>')
    for waterway in data['rivers']:
        for points in waterway['lines']:
            result.append(f'<path data-river={quoteattr(waterway["name"])} d="{line(points)}" fill="none" stroke="{river}" stroke-width="2.0"/>')
    result += ['</g>', '</svg>']
    return ('\n'.join(result) + '\n').encode('utf-8')


def update_master(master, data):
    document = next(m for m in master['maps'] if m['id'] == 'france')
    points = {p['regionID']: p for p in data['representatives']}
    if set(points) != {r['id'] for r in document['regions']}:
        raise ValueError('Representative points do not match France region IDs')
    v = data['viewport']
    document.update(assetFile='france.svg', assetFileDark='france_dark.svg', aspectRatio=v['width'] / v['height'])
    for region in document['regions']:
        p = points[region['id']]
        x, y = project(p['longitude'], p['latitude'], v)
        if not (0 <= x <= 1 and 0 <= y <= 1):
            raise ValueError('Representative point is outside the viewport')
        region['position'] = {'x': round(x, 7), 'y': round(y, 7)}
    old_source = 'wset_app_schematic_france_2026'
    source_id = 'natural_earth_france_2026'
    document['sourceIDs'] = [source_id if value == old_source else value for value in document['sourceIDs']]
    source = next((s for s in master['sources'] if s['id'] in (old_source, source_id)), None)
    if source is None:
        raise ValueError('Missing France basemap source record')
    source.update(
        id=source_id,
        name='Natural Earth — フランスの国土・河川',
        url='https://www.naturalearthdata.com/about/terms-of-use/',
        license='Public domain（パブリックドメイン）',
        checkedAt='2026-09-15',
        note='Made with Natural Earth。1:50mの国土・河川データを配色・範囲調整。ピンは編集上選んだ概略の代表地点で、産地の範囲や法的境界を示しません。',
    )
    return master


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = json.loads(SOURCE.read_text(encoding='utf-8'))
    master = json.loads(MAP_MASTER.read_text(encoding='utf-8'))
    desired = update_master(json.loads(json.dumps(master)), data)
    for filename, dark in [('france.svg', False), ('france_dark.svg', True)]:
        content = render_map(data, dark)
        path = OUTPUT / filename
        if args.check:
            if not path.exists() or path.read_bytes() != content:
                raise ValueError(f'Stale France basemap: {filename}')
        else:
            path.write_bytes(content)
    if args.check:
        if master != desired:
            raise ValueError('France map positions, source or aspect ratio are stale')
        print('Verified France basemaps and geographic pin alignment')
    else:
        MAP_MASTER.write_bytes((json.dumps(desired, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
        print('Wrote light/dark France basemaps and aligned 10 region pins')


if __name__ == '__main__':
    main()
