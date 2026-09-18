#!/usr/bin/env python3
"""Build the bundled offline atlas photographs and their attribution catalog."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / 'ReferenceSources/AtlasMedia/manifest.json'
DEFAULT_MAP_INPUT = ROOT / 'ReferenceSources/wset_region_map_master.json'
DEFAULT_OUTPUT = ROOT / 'WSET/AtlasData/atlas_media.json'
DEFAULT_CATALOG = ROOT / 'WSET/Assets.xcassets/AtlasPhotos'
FIELDS = (
    'regionID', 'assetName', 'filename', 'title', 'altText', 'author',
    'sourceURL', 'license', 'licenseURL', 'changes', 'checkedAt',
)
LICENSES = {
    **{f'CC BY {v}': f'https://creativecommons.org/licenses/by/{v}/' for v in ('2.0', '2.5', '3.0', '4.0')},
    **{f'CC BY-SA {v}': f'https://creativecommons.org/licenses/by-sa/{v}/' for v in ('2.0', '2.5', '3.0', '4.0')},
    'CC0 1.0': 'https://creativecommons.org/publicdomain/zero/1.0/',
    'Public domain': 'https://creativecommons.org/publicdomain/mark/1.0/',
}


class AtlasMediaError(ValueError):
    """Invalid source media or stale generated assets."""


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def read_object(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise AtlasMediaError(f'Cannot read JSON: {path}') from error
    if not isinstance(value, dict):
        raise AtlasMediaError(f'Expected JSON object: {path}')
    return value


def jpeg_dimensions(content: bytes) -> tuple[int, int]:
    """Read JPEG SOF dimensions without an imaging dependency."""
    if not content.startswith(b'\xff\xd8') or not content.endswith(b'\xff\xd9'):
        raise AtlasMediaError('Invalid or truncated JPEG')
    offset = 2
    while offset < len(content) - 1:
        if content[offset] != 0xFF:
            raise AtlasMediaError('Invalid JPEG marker')
        while offset < len(content) and content[offset] == 0xFF:
            offset += 1
        if offset >= len(content):
            break
        marker = content[offset]
        offset += 1
        if marker in (0xD9, 0xDA):
            break
        if marker == 0x01 or 0xD0 <= marker <= 0xD7:
            continue
        if offset + 2 > len(content):
            break
        length = int.from_bytes(content[offset:offset + 2], 'big')
        if length < 2 or offset + length > len(content):
            break
        if marker in (0xC0, 0xC1, 0xC2):
            if length < 8:
                break
            height = int.from_bytes(content[offset + 3:offset + 5], 'big')
            width = int.from_bytes(content[offset + 5:offset + 7], 'big')
            if width > 0 and height > 0:
                return width, height
            break
        offset += length
    raise AtlasMediaError('JPEG has no supported dimensions')


def build_pack(input_path: Path = DEFAULT_INPUT, map_input: Path = DEFAULT_MAP_INPUT):
    manifest = read_object(input_path)
    if manifest.get('schemaVersion') != 1 or not isinstance(manifest.get('photos'), list):
        raise AtlasMediaError('Unsupported atlas manifest schema')
    maps = read_object(map_input).get('maps', [])
    region_ids = {r['id'] for m in maps if m.get('id') == 'france' for r in m.get('regions', [])}
    if not region_ids:
        raise AtlasMediaError('France map has no regions')
    seen = set()
    photos = []
    assets = {}
    for raw in manifest['photos']:
        if not isinstance(raw, dict):
            raise AtlasMediaError('Photo must be an object')
        photo = {}
        for field in FIELDS:
            value = raw.get(field)
            if not isinstance(value, str) or not value.strip():
                raise AtlasMediaError(f'Photo {field} is required')
            photo[field] = value.strip()
        identifier = photo['regionID']
        if identifier not in region_ids or identifier in seen:
            raise AtlasMediaError(f'Unknown or duplicate regionID: {identifier}')
        seen.add(identifier)
        if (re.fullmatch(r'atlas_[a-z0-9_]+', photo['assetName']) is None
                or photo['assetName'] != f'atlas_{identifier}'):
            raise AtlasMediaError('Invalid assetName')
        if photo['assetName'] in assets:
            raise AtlasMediaError('Duplicate assetName')
        filename = photo['filename']
        if re.fullmatch(r'[a-z0-9_]+\.jpg', filename) is None:
            raise AtlasMediaError('Invalid filename: expected a local .jpg basename')
        for field in ('sourceURL', 'licenseURL'):
            url = urlsplit(photo[field])
            if url.scheme != 'https' or not url.hostname or url.username or url.password:
                raise AtlasMediaError(f'{field} must use HTTPS without credentials')
        if LICENSES.get(photo['license']) != photo['licenseURL']:
            raise AtlasMediaError('Unsupported license or mismatched licenseURL')
        try:
            if date.fromisoformat(photo['checkedAt']).isoformat() != photo['checkedAt']:
                raise ValueError
        except ValueError as error:
            raise AtlasMediaError('checkedAt must be YYYY-MM-DD') from error
        image_path = input_path.parent / filename
        if image_path.resolve().parent != input_path.parent.resolve():
            raise AtlasMediaError('filename must stay in the source directory')
        try:
            content = image_path.read_bytes()
        except OSError as error:
            raise AtlasMediaError(f'Missing photograph: {filename}') from error
        width, height = jpeg_dimensions(content)
        if max(width, height) > 1280 or len(content) > 1_500_000:
            raise AtlasMediaError(f'Photograph exceeds offline size budget: {filename}')
        photo.update(width=width, height=height, sha256=hashlib.sha256(content).hexdigest())
        photos.append(photo)
        assets[photo['assetName']] = {
            filename: content,
            'Contents.json': json_bytes({
                'images': [{'filename': filename, 'idiom': 'universal'}],
                'info': {'author': 'xcode', 'version': 1},
            }),
        }
    if seen != region_ids:
        raise AtlasMediaError(f'Every France region needs exactly one photo: missing {sorted(region_ids - seen)}')
    photos.sort(key=lambda item: item['regionID'])
    source_hash = hashlib.sha256(json_bytes(photos)).hexdigest()
    return {'schemaVersion': 1, 'sourceHash': source_hash, 'photos': photos}, assets


def expected_files(pack, assets, output_path, catalog_dir):
    yield output_path, json_bytes(pack)
    yield catalog_dir / 'Contents.json', json_bytes({'info': {'author': 'xcode', 'version': 1}})
    for name, files in assets.items():
        for filename, content in files.items():
            yield catalog_dir / f'{name}.imageset' / filename, content


def write_pack_and_assets(pack, assets, output_path=DEFAULT_OUTPUT, catalog_dir=DEFAULT_CATALOG):
    for path, content in expected_files(pack, assets, output_path, catalog_dir):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def check_existing_pack(input_path=DEFAULT_INPUT, map_input=DEFAULT_MAP_INPUT,
                        output_path=DEFAULT_OUTPUT, catalog_dir=DEFAULT_CATALOG):
    pack, assets = build_pack(input_path, map_input)
    expected = dict(expected_files(pack, assets, output_path, catalog_dir))
    for path, content in expected.items():
        if not path.is_file() or path.read_bytes() != content:
            raise AtlasMediaError(f'Generated atlas media is stale: {path}')
    extras = {p for p in catalog_dir.rglob('*') if p.is_file()} - set(expected)
    if extras:
        raise AtlasMediaError(f'Generated atlas media has stale extra assets: {sorted(map(str, extras))}')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        check_existing_pack()
        print('Verified offline atlas photographs, credits and generated assets')
    else:
        pack, assets = build_pack()
        write_pack_and_assets(pack, assets)
        print(f"Wrote {len(pack['photos'])} offline atlas photographs and credits")


if __name__ == '__main__':
    main()
