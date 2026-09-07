"""Short-lived loopback OAuth callback; never logs authorization query strings."""

from __future__ import annotations

import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit

from health.auth import AuthError


def authorize(auth, *, open_browser: bool = True, timeout_s: float = 600) -> None:
    target = urlsplit(auth.redirect_uri)
    if target.scheme != "http" or target.hostname not in {"localhost", "127.0.0.1"}:
        raise AuthError("OAuth callback must use HTTP on loopback")
    if target.path != "/" or not target.port or target.query or target.fragment:
        raise AuthError("OAuth callback must use an explicit port and root path")
    finished = False
    failure: AuthError | None = None
    deadline = time.monotonic() + timeout_s

    class LoopbackServer(HTTPServer):
        def get_request(self):
            connection, address = super().get_request()
            connection.settimeout(max(0.001, min(0.2, deadline - time.monotonic())))
            return connection, address

    class Callback(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            nonlocal finished, failure
            parsed = urlsplit(self.path)
            params = parse_qs(parsed.query, keep_blank_values=True)
            if parsed.path != "/" or not ({"code", "error"} & params.keys()):
                self.send_error(404)
                return
            try:
                if any(len(values) != 1 for values in params.values()):
                    raise AuthError("ambiguous callback parameters")
                auth.complete_auth(
                    params.get("code", [None])[0],
                    params.get("state", [None])[0],
                    params.get("error", [None])[0],
                    params.get("error_description", [None])[0],
                )
                status, message = (
                    200,
                    "Google Health に接続しました。このタブを閉じて端末に戻れます。",
                )
            except AuthError:
                failure = AuthError("Google Health authorization failed; run health auth again")
                status, message = (
                    400,
                    "認可を完了できませんでした。端末から health auth をやり直してください。",
                )
            finished = True
            body = (
                "<!doctype html><meta charset=utf-8><title>Health</title><p>" + message + "</p>"
            ).encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    try:
        server = LoopbackServer(("127.0.0.1", target.port), Callback)
    except OSError as exc:
        raise AuthError(
            f"OAuth callback port {target.port} is unavailable; close its current owner first"
        ) from exc
    server.timeout = min(0.2, max(0.001, timeout_s))
    try:
        url = auth.begin_auth()
        if not open_browser or not webbrowser.open(url):
            print(f"ブラウザで認可してください: {url}", file=sys.stderr)
        while not finished and time.monotonic() < deadline:
            server.handle_request()
        if not finished:
            raise AuthError("Google Health authorization timed out; run health auth again")
        if failure:
            raise failure
    finally:
        server.server_close()
        pending = getattr(auth, "pending_path", None)
        if pending is not None:
            pending.unlink(missing_ok=True)
