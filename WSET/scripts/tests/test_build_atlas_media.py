from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_atlas_media import (
    AtlasMediaError, build_pack, check_existing_pack, write_pack_and_assets,
)

# A real 8x8 JPEG, so validation does not require imaging dependencies in CI.
JPEG = base64.b64decode(
    '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAAIAAgDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDl6KKK5TjP/9k='
)


class AtlasMediaTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.input = self.root / 'manifest.json'
        self.map_input = self.root / 'map.json'
        self.output = self.root / 'bundle/atlas_media.json'
        self.catalog = self.root / 'bundle/AtlasPhotos'
        self.photo = {
            'regionID': 'france_bordeaux', 'assetName': 'atlas_france_bordeaux',
            'filename': 'france_bordeaux.jpg', 'title': 'ボルドーの畑',
            'altText': '列状に並ぶブドウ畑', 'author': 'Test photographer',
            'sourceURL': 'https://commons.wikimedia.org/wiki/File:Vineyard.jpg',
            'license': 'CC BY-SA 4.0',
            'licenseURL': 'https://creativecommons.org/licenses/by-sa/4.0/',
            'changes': '縮小・JPEG再圧縮。表示時にトリミング。', 'checkedAt': '2026-09-15',
        }
        self.map_input.write_text(json.dumps({'maps': [{'id': 'france', 'regions': [{'id': 'france_bordeaux'}]}]}))
        (self.root / self.photo['filename']).write_bytes(JPEG)
        self.save()

    def save(self, photos=None):
        self.input.write_text(json.dumps({'schemaVersion': 1, 'photos': photos if photos is not None else [self.photo]}))

    def test_attribution_dimensions_and_asset_bytes_are_preserved(self):
        pack, assets = build_pack(self.input, self.map_input)
        self.assertEqual(len(pack['photos']), 1)
        photo = pack['photos'][0]
        self.assertEqual(photo['author'], self.photo['author'])
        self.assertEqual((photo['width'], photo['height']), (8, 8))
        self.assertEqual(len(photo['sha256']), 64)
        self.assertEqual(assets['atlas_france_bordeaux']['france_bordeaux.jpg'], JPEG)
        self.assertEqual(build_pack(self.input, self.map_input), (pack, assets))

    def test_missing_attribution_or_noncommercial_license_is_rejected(self):
        for field, value in [('author', ''), ('altText', ' '), ('sourceURL', 'http://example.com/image'),
                             ('license', 'CC BY-NC 4.0'), ('licenseURL', 'https://example.com/rights'),
                             ('checkedAt', '2026-02-30'), ('assetName', 'atlas_wrong_region')]:
            with self.subTest(field=field):
                original = self.photo[field]
                self.photo[field] = value
                self.save()
                with self.assertRaises(AtlasMediaError):
                    build_pack(self.input, self.map_input)
                self.photo[field] = original

    def test_every_region_has_exactly_one_photo(self):
        for photos in [[], [self.photo, self.photo], [{**self.photo, 'regionID': 'france_unknown'}]]:
            with self.subTest(photos=photos):
                self.save(photos)
                with self.assertRaises(AtlasMediaError):
                    build_pack(self.input, self.map_input)

    def test_filename_cannot_escape_the_source_directory(self):
        self.photo['filename'] = '../outside.jpg'
        self.save()
        with self.assertRaisesRegex(AtlasMediaError, 'filename'):
            build_pack(self.input, self.map_input)

    def test_missing_or_corrupt_jpeg_is_rejected(self):
        image = self.root / self.photo['filename']
        image.unlink()
        with self.assertRaises(AtlasMediaError):
            build_pack(self.input, self.map_input)
        image.write_bytes(b'not an image')
        with self.assertRaises(AtlasMediaError):
            build_pack(self.input, self.map_input)

    def test_generated_catalog_drift_is_detected(self):
        pack, assets = build_pack(self.input, self.map_input)
        write_pack_and_assets(pack, assets, self.output, self.catalog)
        check_existing_pack(self.input, self.map_input, self.output, self.catalog)
        # Alter the catalog's bytes without touching its canonical source.
        image = self.catalog / 'atlas_france_bordeaux.imageset/france_bordeaux.jpg'
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(b'tampered')
        with self.assertRaisesRegex(AtlasMediaError, 'stale'):
            check_existing_pack(self.input, self.map_input, self.output, self.catalog)


if __name__ == '__main__':
    unittest.main()
