"""Keep native MathML fences local and its TeX-family font portable."""

import base64
import importlib.util
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("typography_build", ROOT / "build.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class MathTypographyTest(unittest.TestCase):
    def render(self, fragment):
        render = getattr(builder, "group_math_fences", None)
        self.assertTrue(callable(render), "The renderer must isolate matching MathML fences.")
        return render(fragment)

    def test_a_fraction_outside_a_pair_cannot_stretch_that_pair(self):
        source = "<math><mrow><mi>f</mi><mo>(</mo><mi>x</mi><mo>)</mo><mo>=</mo><mfrac><mn>1</mn><mi>y</mi></mfrac></mrow></math>"
        result = ET.fromstring(self.render(source))
        group = result.find("./mrow/mrow")
        self.assertIsNotNone(group)
        self.assertEqual([e.tag for e in group], ["mo", "mi", "mo"])
        self.assertEqual("".join(group.itertext()), "(x)")
        self.assertIsNotNone(result.find("./mrow/mfrac"))
        self.assertIsNone(group.find(".//mfrac"))

    def test_vectors_are_not_stretched_to_a_neighboring_matrix_label(self):
        source = "<math><mrow><mo>(</mo><mtable><mtr><mtd><mi>x</mi></mtd></mtr></mtable><mo>)</mo><mo>=</mo><munder><mi>M</mi><mi>label</mi></munder><mo>(</mo><mi>y</mi><mo>)</mo></mrow></math>"
        row = ET.fromstring(self.render(source))[0]
        self.assertEqual([e.tag for e in row], ["mrow", "mo", "munder", "mrow"])
        self.assertIsNotNone(row[0].find("mtable"))
        self.assertIsNone(row[-1].find(".//munder"))

    def test_nested_pairs_and_inferred_rows_have_local_scopes(self):
        source = "<math><mtd><mo>[</mo><mi>f</mi><mo>(</mo><mi>x</mi><mo>)</mo><mo>]</mo><mo>+</mo><mi>z</mi></mtd></math>"
        cell = ET.fromstring(self.render(source))[0]
        self.assertEqual("".join(cell[0].itertext()), "[f(x)]")
        self.assertEqual("".join(cell[0].find("mrow").itertext()), "(x)")
        self.assertEqual(cell[-1].text, "z")

    def test_existing_scopes_fixed_arity_and_unmatched_intervals_are_preserved(self):
        for source in [
            "<math><msub><mo>(</mo><mo>)</mo></msub></math>",
            "<math><mrow><mi>P</mi><mo>[</mo><mi>a</mi><mo>,</mo><mi>b</mi><mo>)</mo><mo>+</mo><mi>z</mi></mrow></math>",
            "<math><mrow><mo>(</mo><mo>[</mo><mi>x</mi><mo>)</mo><mi>y</mi><mo>]</mo><mo>)</mo><mo>+</mo><mi>z</mi></mrow></math>",
            "<p>(日本語)</p><math><mrow><mi>x</mi><mo>+</mo><mspace width='1em'/><mi>y</mi></mrow></math>",
        ]:
            with self.subTest(source=source):
                self.assertEqual(self.render(source), source)

    def test_grouping_preserves_text_attributes_and_is_idempotent(self):
        source = '<p>前：𝜋</p><math xmlns="http://www.w3.org/1998/Math/MathML"><mrow id="kept"><mi>f</mi><mo fence="true">(</mo><mi>x</mi><mo>&lt;</mo><mn>2</mn><mo>)</mo><mfrac><mn>1</mn><mi>z</mi></mfrac></mrow></math><p>後</p>'
        rendered = self.render(source)
        self.assertTrue(rendered.startswith("<p>前：𝜋</p>"))
        self.assertTrue(rendered.endswith("<p>後</p>"))
        self.assertIn('<mrow id="kept">', rendered)
        self.assertIn('<mo fence="true" stretchy="false">(</mo>', rendered)
        self.assertIn("<mo>&lt;</mo>", rendered)
        self.assertEqual(self.render(rendered), rendered)

    def test_plain_fences_keep_their_intrinsic_glyph_width(self):
        source = "<math><mrow><mo>(</mo><msub><mi>x</mi><mi>n</mi></msub><mo>)</mo></mrow></math>"
        row = ET.fromstring(self.render(source))[0]
        self.assertEqual([child.tag for child in row], ["mo", "msub", "mo"])
        self.assertEqual([row[index].get("stretchy") for index in (0, -1)], ["false", "false"])

    def test_adjacent_pairs_do_not_cross_or_add_fixed_arity_children(self):
        source = (
            "<math><mrow><mo>(</mo><mi>α</mi><mo>)</mo><mo>[</mo><mi>β</mi><mo>]</mo></mrow></math>"
        )
        row = ET.fromstring(self.render(source))[0]
        self.assertEqual([child.tag for child in row], ["mrow", "mrow"])
        self.assertEqual(["".join(child.itertext()) for child in row], ["(α)", "[β]"])
        self.assertEqual(self.render(self.render(source)), self.render(source))

    def test_absolute_values_and_norms_ignore_other_scopes_conditional_bars(self):
        source = "<math><mrow><mo>|</mo><mi>x</mi><mo>|</mo><mo>=</mo><mo>‖</mo><mi>v</mi><mo>‖</mo><mo>+</mo><mi>P</mi><mo>(</mo><mi>A</mi><mo>|</mo><mi>B</mi><mo>)</mo><mi>P</mi><mo>(</mo><mi>C</mi><mo>|</mo><mi>D</mi><mo>)</mo><mfrac><mn>1</mn><mi>z</mi></mfrac></mrow></math>"
        row = ET.fromstring(self.render(source))[0]
        groups = row.findall("mrow")
        self.assertEqual(
            ["".join(group.itertext()) for group in groups], ["|x|", "‖v‖", "(A|B)", "(C|D)"]
        )
        for group in groups[:2]:
            self.assertEqual(
                [group[index].get("stretchy") for index in (0, -1)], ["false", "false"]
            )
        for group in groups[2:]:
            self.assertEqual(group[2].text, "|")
            self.assertEqual(group[2].attrib, {})
        lone = "<math><mrow><mi>a</mi><mo>|</mo><mi>b</mi></mrow></math>"
        self.assertEqual(self.render(lone), lone)

    def test_tall_content_and_explicit_author_stretching_remain_scalable(self):
        for content in [
            "<mfrac><mn>1</mn><mi>x</mi></mfrac>",
            "<mtable><mtr><mtd><mi>x</mi></mtd></mtr></mtable>",
            "<msqrt><mi>x</mi></msqrt>",
            "<munder><mo>∑</mo><mi>n</mi></munder>",
        ]:
            for left, right in [("(", ")"), ("|", "|"), ("‖", "‖")]:
                source = f"<math><mrow><mo>{left}</mo>{content}<mo>{right}</mo></mrow></math>"
                self.assertEqual(self.render(source), source)
        explicit = '<math><mrow><mo stretchy="true">(</mo><mi>x</mi><mo stretchy="true">)</mo></mrow></math>'
        self.assertEqual(self.render(explicit), explicit)

    def test_the_font_is_embedded_without_network_or_local_installation(self):
        font = ROOT / "assets/fonts/latinmodern-math.otf"
        self.assertTrue(font.is_file(), "Bundle the official OpenType math font.")
        with tempfile.TemporaryDirectory() as folder:
            builder.build(Path(folder))
            page = (Path(folder) / "linear-eigenvalues.html").read_text(encoding="utf-8")
        match = re.search(r"data:font/otf;base64,([A-Za-z0-9+/=]+)", page)
        self.assertIsNotNone(match, "Each portable page must carry its own math font.")
        self.assertEqual(base64.b64decode(match[1]), font.read_bytes())
        self.assertIn("GUST Font License", page)
        self.assertTrue("https://ctan.org/pkg/lm-math" in page)
        sample = page.split('id="linear-eigenvalues-directions"', 1)[1]
        math = re.search(r"<math\b[^>]*>.*?</math>", sample, re.S)[0]
        row = ET.fromstring(math)[0]
        groups = row.findall("{http://www.w3.org/1998/Math/MathML}mrow")
        self.assertEqual(
            ["".join(group.itertext()) for group in groups], ["(u,v)", "(1,1)", "(1,−1)"]
        )
        self.assertTrue(
            all(group[index].get("stretchy") == "false" for group in groups for index in (0, -1))
        )
        self.assertIn('font-family:"Latin Modern Math",math', page)


if __name__ == "__main__":
    unittest.main()
