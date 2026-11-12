"""Exercise the generated reader as a portable set of HTML documents."""

import importlib.util
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("foundations_build", ROOT / "build.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.external_assets = []
        self.ids = set()
        self.heading_count = 0
        self.language = None
        self.labs = []
        self.text = []
        self.exercise_summaries = []
        self._exercise = None
        self._summary = None

    def handle_data(self, data):
        self.text.append(data)
        if self._summary is not None:
            self._summary.append(data)

    def handle_endtag(self, tag):
        if tag == "summary" and self._summary is not None:
            self._exercise.append("".join(self._summary).strip())
            self._summary = None
        if tag == "article":
            self._exercise = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "article" and "exercise" in attrs.get("class", "").split():
            self._exercise = []
            self.exercise_summaries.append(self._exercise)
        if tag == "summary" and self._exercise is not None:
            self._summary = []
        if tag == "html":
            self.language = attrs.get("lang")
        if tag == "h1":
            self.heading_count += 1
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if attrs.get("data-lab"):
            self.labs.append(attrs["data-lab"])
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag in {"script", "link", "img"}:
            asset = attrs.get("src") or attrs.get("href")
            if asset:
                self.external_assets.append(asset)


class PortableReaderTest(unittest.TestCase):
    def test_each_chapter_delivers_catalogued_exercises_with_two_hints_and_an_answer(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            builder.build(output)
            for chapter in builder.CHAPTERS:
                slug = chapter["slug"]
                with self.subTest(chapter=slug):
                    expected = chapter.get("exerciseCount", 3)
                    self.assertIs(type(expected), int, "exerciseCount must be a positive integer")
                    self.assertGreater(expected, 0, "exerciseCount must be a positive integer")
                    document = Document()
                    document.feed((output / f"{slug}.html").read_text(encoding="utf-8"))
                    self.assertEqual(len(document.exercise_summaries), expected)
                    for index, summaries in enumerate(document.exercise_summaries, 1):
                        with self.subTest(exercise=index):
                            self.assertEqual(len(summaries), 3)
                            self.assertRegex(summaries[0], r"^ヒント1(?:[：:\s]|$)")
                            self.assertRegex(summaries[1], r"^ヒント2(?:[：:\s]|$)")
                            self.assertEqual(summaries[2], "解答")

    def test_chapter_titles_prioritize_standard_topics_and_optional_subtitles(self):
        chapter = next(c for c in builder.CHAPTERS if c["slug"] == "limits")
        self.assertEqual(chapter["title"], "実数と数列・関数の極限")
        self.assertEqual(chapter.get("subtitle"), "近づくことを、約束にする")
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            builder.build(output)
            page = (output / "limits.html").read_text(encoding="utf-8")
            home = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn("<h1>実数と数列・関数の極限</h1>", page)
            self.assertIn('<p class="chapter-subtitle hero-sub">近づくことを、約束にする</p>', page)
            navigation = page.split('<nav aria-label="章の一覧">', 1)[1].split("</nav>", 1)[0]
            self.assertIn("実数と数列・関数の極限", navigation)
            self.assertNotIn("近づくことを、約束にする", navigation)
            self.assertIn("<strong>実数と数列・関数の極限</strong>", home)

    def test_build_delivers_full_learning_path_without_runtime_assets(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            pages = builder.build(output)
            self.assertEqual(
                {p.name for p in pages},
                {
                    f"{slug}.html"
                    for slug in (
                        "index",
                        "observation",
                        "logic",
                        "sets-maps",
                        "proofs",
                        "induction",
                        "invariants",
                        "inequalities",
                        "numbers",
                        "limits",
                        "continuity",
                        "derivatives",
                        "mean-value",
                        "approximation",
                        "integration",
                        "fundamental-theorem",
                        "integration-methods",
                        "series",
                        "taylor",
                        "elementary-functions",
                        "rotation",
                        "vector-spaces",
                        "dimension",
                        "determinants",
                        "multivariable-limits",
                        "partial-derivatives",
                        "total-derivative",
                        "gradient",
                        "hessian-extrema",
                        "lagrange",
                        "double-integrals",
                        "change-of-variables",
                        "probability-models",
                        "counting-probability",
                        "conditional-probability",
                        "independence",
                        "random-variables",
                        "probability-density",
                        "expectation",
                        "variance",
                        "joint-distributions",
                        "law-of-large-numbers",
                        "discrete-relations",
                        "discrete-orders",
                        "discrete-counting",
                        "inclusion-exclusion",
                        "modular-arithmetic",
                        "recurrence-relations",
                        "discrete-graphs",
                        "discrete-trees",
                        "shortest-paths",
                        "graph-coloring",
                        "complex-plane",
                        "complex-differentiation",
                        "complex-logarithm",
                        "complex-contours",
                        "cauchy-theorem",
                        "cauchy-formula",
                        "complex-taylor",
                        "laurent-singularities",
                        "complex-residues",
                        "complex-real-integrals",
                        "vector-fields",
                        "vector-curves",
                        "vector-line-integrals",
                        "vector-potentials",
                        "vector-green",
                        "vector-div-curl",
                        "vector-surfaces",
                        "vector-flux",
                        "vector-gauss",
                        "vector-stokes",
                        "numerical-errors",
                        "numerical-conditioning",
                        "numerical-bisection",
                        "numerical-newton",
                        "numerical-linear-systems",
                        "numerical-interpolation",
                        "numerical-differentiation",
                        "numerical-quadrature",
                        "numerical-ode",
                        "numerical-reliability",
                        "optimization-problems",
                        "optimization-convexity",
                        "optimization-optimality",
                        "optimization-gradient",
                        "optimization-newton",
                        "optimization-scaling",
                        "optimization-projections",
                        "optimization-lagrange",
                        "optimization-kkt",
                        "optimization-duality",
                        "linear-systems",
                        "linear-elimination",
                        "linear-kernel-image",
                        "linear-basis-change",
                        "linear-orthogonality",
                        "linear-least-squares",
                        "linear-eigenvalues",
                        "linear-diagonalization",
                        "linear-symmetric",
                        "linear-svd",
                    )
                },
            )
            documents = {}
            for page in pages:
                doc = Document()
                doc.feed(page.read_text(encoding="utf-8"))
                self.assertEqual(doc.language, "ja")
                self.assertEqual(doc.heading_count, 1)
                self.assertEqual(doc.external_assets, [], page.name)
                documents[page] = doc
            for page, doc in documents.items():
                for href in doc.links:
                    url = urlsplit(href)
                    if url.scheme or url.netloc:
                        continue
                    target = (page.parent / unquote(url.path)).resolve() if url.path else page
                    self.assertTrue(target.is_file(), (page.name, href))
                    if url.fragment and target in documents:
                        self.assertIn(unquote(url.fragment), documents[target].ids)
            for slug, lab in (
                ("numbers", "numbers"),
                ("continuity", "continuity"),
                ("rotation", "rotation"),
                ("derivatives", "derivatives"),
                ("integration", "integration"),
                ("series", "series"),
                ("determinants", "determinants"),
                ("multivariable-limits", "multivariable-paths"),
                ("total-derivative", "multivariable-linear"),
                ("gradient", "multivariable-compass"),
                ("hessian-extrema", "multivariable-curvature"),
                ("lagrange", "multivariable-constraint"),
                ("double-integrals", "multivariable-double-integral"),
                ("change-of-variables", "multivariable-polar"),
                ("conditional-probability", "probability-bayes"),
                ("independence", "probability-independence"),
                ("random-variables", "probability-binomial"),
                ("probability-density", "probability-density"),
                ("law-of-large-numbers", "probability-lln"),
                ("modular-arithmetic", "discrete-modular"),
                ("recurrence-relations", "discrete-recurrence"),
                ("shortest-paths", "discrete-shortest"),
                ("complex-differentiation", "complex-difference"),
                ("complex-logarithm", "complex-log"),
                ("complex-residues", "complex-residue"),
                ("vector-line-integrals", "vector-work"),
                ("vector-flux", "vector-flux"),
                ("vector-stokes", "vector-stokes"),
                ("numerical-bisection", "numerical-root"),
                ("numerical-differentiation", "numerical-difference"),
                ("numerical-ode", "numerical-ode"),
                ("optimization-gradient", "opt-gradient"),
                ("optimization-projections", "opt-projection"),
                ("optimization-kkt", "opt-kkt"),
                ("linear-elimination", "linear-core-map"),
                ("linear-least-squares", "linear-core-least-squares"),
                ("linear-symmetric", "linear-core-spectral"),
            ):
                self.assertEqual(documents[output / f"{slug}.html"].labs, [lab])

    def test_mathematical_inequalities_remain_visible_text(self):
        markers = {
            "numerical-bisection": "a₀<b₀",
            "numerical-newton": "Cρ<1",
            "numerical-ode": "0<h<2/5",
            "numerical-quadrature": "a<b、N",
        }
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            builder.build(output)
            for slug, marker in markers.items():
                with self.subTest(chapter=slug):
                    document = Document()
                    document.feed((output / f"{slug}.html").read_text(encoding="utf-8"))
                    self.assertIn(marker, "".join(document.text))

    def test_rebuilding_preserves_exact_reader_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            first = {p.name: p.read_bytes() for p in builder.build(output)}
            second = {p.name: p.read_bytes() for p in builder.build(output)}
            self.assertEqual(first, second)

    def test_clean_workspace_explains_unbuilt_optional_books(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder)
            tokens = workspace / "docs/templates/claude-report/tokens.css"
            tokens.parent.mkdir(parents=True)
            tokens.write_text(":root {}", encoding="utf-8")
            output = workspace / "reader"
            with patch.object(builder, "WORKSPACE", workspace):
                pages = builder.build(output)
            home = (output / "index.html").read_text(encoding="utf-8")
            doc = Document()
            doc.feed(home)
            self.assertEqual(len(pages), 102)
            self.assertEqual(home.count("（準備中）"), 4)
            self.assertNotIn("未ビルド", home)
            self.assertFalse(any("_build/html" in link for link in doc.links))

    def test_book_end_continues_to_next_subject(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            builder.build(output)
            for last, following in [
                ("numbers", "limits"),
                ("elementary-functions", "rotation"),
                ("determinants", "linear-systems"),
                ("linear-svd", "multivariable-limits"),
                ("change-of-variables", "probability-models"),
                ("law-of-large-numbers", "discrete-relations"),
                ("graph-coloring", "complex-plane"),
                ("complex-real-integrals", "vector-fields"),
                ("vector-stokes", "numerical-errors"),
                ("numerical-reliability", "optimization-problems"),
            ]:
                doc = Document()
                doc.feed((output / f"{last}.html").read_text(encoding="utf-8"))
                self.assertIn(f"{following}.html", doc.links)

    def test_multivariable_subject_has_its_own_chapter_navigation(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            builder.build(output)
            middle = (output / "partial-derivatives.html").read_text(encoding="utf-8")
            navigation = middle.split('<nav aria-label="章の一覧">', 1)[1].split("</nav>", 1)[0]
            doc = Document()
            doc.feed(navigation)
            self.assertEqual(
                doc.links,
                [
                    "multivariable-limits.html",
                    "partial-derivatives.html",
                    "total-derivative.html",
                    "gradient.html",
                    "hessian-extrema.html",
                    "lagrange.html",
                    "double-integrals.html",
                    "change-of-variables.html",
                ],
            )
            slugs = [link.removesuffix(".html") for link in doc.links]
            for index, slug in enumerate(slugs):
                page = (output / f"{slug}.html").read_text(encoding="utf-8")
                pagination = page.split('aria-label="前後の章">', 1)[1].split("</nav>", 1)[0]
                adjacent = Document()
                adjacent.feed(pagination)
                previous = f"{slugs[index - 1]}.html" if index else "index.html#book-multivariable"
                following = (
                    f"{slugs[index + 1]}.html"
                    if index + 1 < len(slugs)
                    else "probability-models.html"
                )
                self.assertEqual(adjacent.links, [previous, following], slug)

    def test_probability_subject_navigation_and_learning_components(self):
        slugs = [
            "probability-models",
            "counting-probability",
            "conditional-probability",
            "independence",
            "random-variables",
            "probability-density",
            "expectation",
            "variance",
            "joint-distributions",
            "law-of-large-numbers",
        ]
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            builder.build(output)
            for index, slug in enumerate(slugs):
                page = (output / f"{slug}.html").read_text(encoding="utf-8")
                navigation = page.split('<nav aria-label="章の一覧">', 1)[1].split("</nav>", 1)[0]
                doc = Document()
                doc.feed(navigation)
                self.assertEqual(doc.links, [f"{name}.html" for name in slugs])
                pagination = page.split('aria-label="前後の章">', 1)[1].split("</nav>", 1)[0]
                adjacent = Document()
                adjacent.feed(pagination)
                previous = f"{slugs[index - 1]}.html" if index else "index.html#book-probability"
                following = (
                    f"{slugs[index + 1]}.html"
                    if index + 1 < len(slugs)
                    else "discrete-relations.html"
                )
                self.assertEqual(adjacent.links, [previous, following], slug)
                self.assertEqual(page.count('class="column"'), 1, slug)
                self.assertIn(f'id="{slug}-reflection"', page)


if __name__ == "__main__":
    unittest.main()
