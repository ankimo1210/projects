import json
import unittest
from pathlib import Path
from xml.etree import ElementTree

from scripts.build_france_basemap import project, render_map


class FranceBasemapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[2]
        cls.data = json.loads((root / 'ReferenceSources/RegionMaps/france_geography.json').read_text(encoding='utf-8'))

    def test_projection_has_north_at_top_and_known_corner_coordinates(self):
        v = self.data['viewport']
        self.assertEqual(project(v['west'], v['north'], v), (0, 0))
        self.assertEqual(project(v['east'], v['south'], v), (1, 1))
        x, y = project(-0.58, 44.84, v)
        self.assertAlmostEqual(x, 0.35238095238)
        self.assertAlmostEqual(y, 0.62786885245)

    def test_bordeaux_is_southwest_of_champagne_and_pin_ids_are_unique(self):
        points = {p['regionID']: project(p['longitude'], p['latitude'], self.data['viewport'])
                  for p in self.data['representatives']}
        self.assertEqual(len(points), 10)
        self.assertLess(points['france_bordeaux'][0], points['france_champagne'][0])
        self.assertGreater(points['france_bordeaux'][1], points['france_champagne'][1])
        self.assertTrue(all(0 < x < 1 and 0 < y < 1 for x, y in points.values()))

    def test_both_appearances_use_the_same_real_geometry(self):
        light, dark = render_map(self.data), render_map(self.data, dark=True)
        self.assertIn(b'<svg', light)
        self.assertNotEqual(light, dark)
        roots = [ElementTree.fromstring(value) for value in (light, dark)]
        paths = [[n.attrib['d'] for n in root.iter() if n.tag.endswith('path')] for root in roots]
        self.assertEqual(paths[0], paths[1])
        self.assertGreater(len(paths[0]), 15)
        self.assertEqual(roots[0].attrib['viewBox'], '0 0 760 800')
        self.assertIn(b'Natural Earth', light)


if __name__ == '__main__':
    unittest.main()
