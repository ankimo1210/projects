"""Keep local preview routing inside the reader and generated book roots."""

import http.client
import importlib.util
import json
import tempfile
import threading
import unittest
from pathlib import Path

PREVIEW = Path(__file__).resolve().parents[1] / "tools" / "serve.py"
spec = importlib.util.spec_from_file_location("foundations_serve", PREVIEW)
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)
BOOK_PATHS = (
    "linear_algebra/book/_build/html",
    "differential_equation/ode-book/book/_build/html",
    "fourier/book/_build/html",
    "statistics/book/_build/html",
)


class PreviewFixture(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.analytics = Path(temporary.name) / "analytics"
        self.reader = self.analytics / "math_foundations"
        self.site = self.reader / "site"
        self.site.mkdir(parents=True)
        (self.reader / "catalog.json").write_text(
            json.dumps({"chapters": [{"slug": "observation"}]}), encoding="utf-8"
        )
        (self.site / "index.html").write_text("<h1>Reader</h1>", encoding="utf-8")
        (self.site / "observation.html").write_text("<h1>Chapter</h1>", encoding="utf-8")
        (self.site / "unregistered.html").write_text("private", encoding="utf-8")
        (self.analytics / "private.txt").write_text("private", encoding="utf-8")
        for book in BOOK_PATHS:
            root = self.analytics / book
            (root / "_static").mkdir(parents=True)
            (root / "index.html").write_text("<h1>Book</h1>", encoding="utf-8")
            (root / "_static" / "book.css").write_text("body{}", encoding="utf-8")
        self.preview = preview
        self.routes = preview.ReaderRoutes(self.reader)


class PreviewRoutesTest(PreviewFixture):
    def test_root_and_catalogued_reader_pages_are_served(self):
        expected = {
            "/": self.site / "index.html",
            "/index.html": self.site / "index.html",
            "/observation.html": self.site / "observation.html",
            "/observation.html?theme=dark": self.site / "observation.html",
        }
        for target, path in expected.items():
            with self.subTest(target=target):
                self.assertEqual(self.routes.resolve(target), path)

    def test_unregistered_reader_and_workspace_files_are_not_served(self):
        for target in (
            "/unregistered.html",
            "/catalog.json",
            "/private.txt",
            "/math_foundations/site/index.html",
            "/statistics/book/index.md",
        ):
            with self.subTest(target=target):
                self.assertIsNone(self.routes.resolve(target))

    def test_all_four_legacy_mounts_serve_generated_pages_and_assets(self):
        for book in BOOK_PATHS:
            for filename in ("index.html", "_static/book.css"):
                with self.subTest(book=book, filename=filename):
                    self.assertEqual(
                        self.routes.resolve(f"/{book}/{filename}"),
                        self.analytics / book / filename,
                    )

    def test_missing_built_files_and_unbuilt_books_are_not_served(self):
        for filename in ("index.html", "_static/book.css"):
            (self.analytics / BOOK_PATHS[0] / filename).unlink()
        for target in (
            f"/{BOOK_PATHS[0]}/index.html",
            f"/{BOOK_PATHS[0]}/_static/book.css",
            "/statistics/book/_build/html/missing.html",
            "/missing.html",
        ):
            with self.subTest(target=target):
                self.assertIsNone(self.routes.resolve(target))

    def test_a_missing_book_root_is_not_served(self):
        root = self.analytics / BOOK_PATHS[0]
        root.rename(self.analytics / "not-built")
        self.assertIsNone(self.routes.resolve(f"/{BOOK_PATHS[0]}/index.html"))

    def test_url_decoding_happens_before_rejecting_unsafe_paths(self):
        for target in (
            "/../private.txt",
            "/%2e%2e/private.txt",
            "/statistics/book/_build/html/%2e%2e/index.html",
            "/statistics/book/_build/html/%2e%2e%2findex.html",
            "/statistics/book/_build/html/.%2e/index.html",
            "/statistics/book/_build/html/./index.html",
            "/statistics/book/_build/html/..%5cindex.html",
            "/statistics/book/_build/html/%00index.html",
            "/statistics//book/_build/html/index.html",
            "/statistics/book/_build/html/%2findex.html",
            "//index.html",
            "/index.html%00",
            "/%ff",
            "index.html",
        ):
            with self.subTest(target=target):
                self.assertIsNone(self.routes.resolve(target))
        self.assertEqual(self.routes.resolve("/%6fbservation.html"), self.site / "observation.html")

    def test_symlinks_cannot_escape_an_allowed_root(self):
        (self.site / "observation.html").unlink()
        (self.site / "observation.html").symlink_to(self.analytics / "private.txt")
        book = self.analytics / BOOK_PATHS[3]
        (book / "escape.txt").symlink_to(self.analytics / "private.txt")
        (book / "escape").symlink_to(self.analytics, target_is_directory=True)
        for target in (
            "/observation.html",
            f"/{BOOK_PATHS[3]}/escape.txt",
            f"/{BOOK_PATHS[3]}/escape/private.txt",
        ):
            with self.subTest(target=target):
                self.assertIsNone(self.routes.resolve(target))

    def test_symlinked_roots_cannot_relocate_the_allowed_subtrees(self):
        for index, root in enumerate((self.site, self.analytics / BOOK_PATHS[3])):
            outside = self.analytics / f"outside-{index}"
            root.rename(outside)
            root.symlink_to(outside, target_is_directory=True)
        self.assertIsNone(self.routes.resolve("/index.html"))
        self.assertIsNone(self.routes.resolve(f"/{BOOK_PATHS[3]}/index.html"))

    def test_directories_never_produce_a_listing_or_implicit_index(self):
        for target in (
            f"/{BOOK_PATHS[0]}",
            f"/{BOOK_PATHS[0]}/",
            f"/{BOOK_PATHS[0]}/_static",
            f"/{BOOK_PATHS[0]}/_static/",
        ):
            with self.subTest(target=target):
                self.assertIsNone(self.routes.resolve(target))


class PreviewHTTPTest(PreviewFixture):
    def setUp(self):
        super().setUp()
        self.server = self.preview.create_server(self.routes, port=0)
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            kwargs={"poll_interval": 0.01},
            daemon=True,
        )
        self.thread.start()
        self.addCleanup(self.close_server)

    def close_server(self):
        self.server.shutdown()
        self.thread.join(timeout=3)
        self.server.server_close()

    def request(self, method, target):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        try:
            connection.request(method, target)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_get_returns_the_reader_with_length_and_preview_headers(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        status, headers, body = self.request("GET", "/?theme=dark")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"<h1>Reader</h1>")
        self.assertEqual(headers["Content-Length"], "15")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertNotIn("Content-Security-Policy", headers)

    def test_head_returns_the_get_headers_without_a_body(self):
        status, headers, body = self.request("HEAD", "/observation.html")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"")
        self.assertEqual(headers["Content-Length"], "16")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")

    def test_legacy_pages_and_static_assets_are_reachable_over_http(self):
        status, _, body = self.request("GET", f"/{BOOK_PATHS[3]}/index.html")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"<h1>Book</h1>")
        status, headers, body = self.request("GET", f"/{BOOK_PATHS[3]}/_static/book.css")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"body{}")
        self.assertEqual(headers["Content-Type"], "text/css; charset=utf-8")
        self.assertEqual(headers["Content-Length"], "6")
        self.assertNotIn("Content-Security-Policy", headers)

    def test_missing_and_forbidden_targets_return_404(self):
        for target in (
            "/unregistered.html",
            "/catalog.json",
            "/statistics/book/_build/html/",
            "/statistics/book/_build/html/missing.html",
            "/statistics/book/_build/html/%2e%2e/index.html",
            "/statistics//book/_build/html/index.html",
            "//index.html",
            "/index.html%00",
        ):
            with self.subTest(target=target):
                status, headers, _ = self.request("GET", target)
                self.assertEqual(status, 404)
                self.assertEqual(headers["Cache-Control"], "no-store")
                self.assertEqual(headers["X-Content-Type-Options"], "nosniff")

    def test_missing_head_target_returns_404_without_a_body(self):
        status, headers, body = self.request("HEAD", "/missing.html")
        self.assertEqual(status, 404)
        self.assertEqual(body, b"")
        self.assertGreater(int(headers["Content-Length"]), 0)


if __name__ == "__main__":
    unittest.main()
