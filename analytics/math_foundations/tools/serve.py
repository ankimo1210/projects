"""Preview the reader and four generated books without exposing the workspace."""

import argparse
import json
import mimetypes
import os
import shutil
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
BOOK_PATHS = (
    "linear_algebra/book/_build/html",
    "differential_equation/ode-book/book/_build/html",
    "fourier/book/_build/html",
    "statistics/book/_build/html",
)


class ReaderRoutes:
    """Resolve only catalogued reader pages and explicitly mounted book files."""

    def __init__(self, project_root: Path = ROOT):
        project_root = project_root.resolve()
        self.site = project_root / "site"
        catalog = json.loads((project_root / "catalog.json").read_text(encoding="utf-8"))
        self.pages = {"/index.html"} | {
            f"/{chapter['slug']}.html" for chapter in catalog["chapters"]
        }
        self.books = {f"/{book}/": project_root.parent / book for book in BOOK_PATHS}

    def resolve(self, target: str) -> Path | None:
        try:
            path = unquote(target.partition("?")[0], errors="strict")
        except UnicodeError:
            return None
        if (
            not path.startswith("/")
            or "//" in path
            or "\\" in path
            or "\x00" in path
            or any(part in {".", ".."} for part in path.split("/"))
        ):
            return None
        if path == "/":
            path = "/index.html"
        if path in self.pages:
            return self._file(self.site, path[1:])
        for prefix, root in self.books.items():
            if path.startswith(prefix):
                return self._file(root, path[len(prefix) :])
        return None

    @staticmethod
    def _file(root: Path, relative: str) -> Path | None:
        try:
            candidate = (root / relative).resolve(strict=True)
            if candidate.is_relative_to(root) and candidate.is_file():
                return candidate
        except (OSError, RuntimeError, ValueError):
            pass
        return None


def create_server(routes: ReaderRoutes, port: int = 8765) -> ThreadingHTTPServer:
    """Create a loopback-only server; the caller owns its lifetime."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self._serve(head=False)

        def do_HEAD(self):
            self._serve(head=True)

        def _serve(self, *, head: bool):
            # BaseHTTPRequestHandler normalizes a leading // in self.path.
            # Resolve the original target so duplicate slashes stay forbidden.
            path = routes.resolve(self.requestline.split()[1])
            if path is None:
                self.send_error(404)
                return
            try:
                source = path.open("rb")
            except OSError:
                self.send_error(404)
                return
            with source:
                content_type = mimetypes.guess_type(path.name)[0]
                content_type = content_type or "application/octet-stream"
                if content_type.startswith("text/"):
                    content_type += "; charset=utf-8"
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(os.fstat(source.fileno()).st_size))
                self.end_headers()
                if not head:
                    try:
                        shutil.copyfileobj(source, self.wfile)
                    except (BrokenPipeError, ConnectionResetError):
                        pass

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            super().end_headers()

        def log_message(self, message, *args):
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765, help="local port (default: 8765)")
    args = parser.parse_args(argv)
    with create_server(ReaderRoutes(), port=args.port) as server:
        print(f"http://localhost:{server.server_port}/index.html", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
