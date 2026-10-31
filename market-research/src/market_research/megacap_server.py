"""Loopback-only display server; acquisition requires an explicit POST."""

from __future__ import annotations

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .megacap import collect_snapshot, load_snapshot, save_snapshot

PROJECT = Path(__file__).resolve().parents[2]
TEMPLATE = PROJECT / "web" / "megacap.html"
DEFAULT_DATA = PROJECT.parent / "_data" / "market-research" / "megacap-tracker"


def render_html(snapshot):
    payload = json.dumps(snapshot, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    for original, escaped in (
        ("&", "\\u0026"),
        ("<", "\\u003c"),
        (">", "\\u003e"),
        ("\u2028", "\\u2028"),
        ("\u2029", "\\u2029"),
    ):
        payload = payload.replace(original, escaped)
    return TEMPLATE.read_text(encoding="utf-8").replace("__TRACKER_SNAPSHOT__", payload)


class TrackerServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, snapshot_path):
        if address[0] != "127.0.0.1":
            raise ValueError("tracker must bind to 127.0.0.1")
        self.snapshot_path = Path(snapshot_path)
        self.refresh_lock = threading.Lock()
        super().__init__(address, _Handler)


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass

    def _send(
        self, status, payload, content_type="application/json; charset=utf-8", attachment=False
    ):
        if not isinstance(payload, str):
            payload = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        raw = payload.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        if attachment:
            self.send_header("Content-Disposition", 'attachment; filename="megacap-tracker.html"')
        self.end_headers()
        self.wfile.write(raw)

    def _host_allowed(self):
        return self.headers.get("Host") in {
            f"127.0.0.1:{self.server.server_port}",
            f"localhost:{self.server.server_port}",
        }

    def do_GET(self):
        if not self._host_allowed():
            self._send(403, {"error": "許可されていないホストです"})
            return
        path = urlsplit(self.path).path
        if path not in {"/", "/index.html", "/download.html", "/api/snapshot"}:
            self._send(404, {"error": "ページが見つかりません"})
            return
        try:
            snapshot = load_snapshot(self.server.snapshot_path)
            if path == "/api/snapshot":
                self._send(200, snapshot)
            else:
                self._send(
                    200, render_html(snapshot), "text/html; charset=utf-8", path == "/download.html"
                )
        except (OSError, ValueError):
            self._send(
                500, {"error": "保存データを読み込めません。snapshot.jsonを確認してください"}
            )

    def do_POST(self):
        origin = self.headers.get("Origin")
        allowed_origins = {
            f"http://127.0.0.1:{self.server.server_port}",
            f"http://localhost:{self.server.server_port}",
        }
        if (
            not self._host_allowed()
            or self.headers.get("X-Tracker-Request") != "refresh"
            or (origin is not None and origin not in allowed_origins)
        ):
            self._send(403, {"error": "画面のデータ更新ボタンから実行してください"})
            return
        if urlsplit(self.path).path != "/api/refresh":
            self._send(404, {"error": "ページが見つかりません"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if not 0 <= length <= 1024:
            self._send(413, {"error": "リクエストが大きすぎます"})
            return
        self.rfile.read(length)
        if not self.server.refresh_lock.acquire(blocking=False):
            self._send(409, {"error": "データ更新中です。完了までお待ちください"})
            return
        try:
            previous = load_snapshot(self.server.snapshot_path)
            snapshot = collect_snapshot(previous=previous)
            save_snapshot(snapshot, self.server.snapshot_path)
            self.server.snapshot_path.with_name("index.html").write_text(
                render_html(snapshot), encoding="utf-8"
            )
            self._send(200, snapshot)
        except Exception:
            self._send(503, {"error": "更新処理に失敗しました。保存先と通信環境を確認してください"})
        finally:
            self.server.refresh_lock.release()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Mag7の株価・財務を比較するローカルHTMLトラッカー")
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--refresh", action="store_true", help="Yahoo Financeから明示取得する")
    parser.add_argument("--export", type=Path, help="自己完結HTMLの保存先")
    parser.add_argument("--no-serve", action="store_true", help="HTMLを保存して終了する")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("port must be in 1..65535")
    snapshot_path = args.data_root / "snapshot.json"
    snapshot = load_snapshot(snapshot_path)
    if args.refresh:
        print("Mag7の株価・財務データを取得しています…", flush=True)
        snapshot = collect_snapshot(previous=snapshot)
        save_snapshot(snapshot, snapshot_path)
        ok = sum(c["fetch_status"] == "ok" for c in snapshot["companies"])
        print(f"取得完了: 完全取得 {ok}/7社（欠損・失敗の詳細は画面に表示）", flush=True)
    export = args.export or args.data_root / "index.html"
    export.parent.mkdir(parents=True, exist_ok=True)
    export.write_text(render_html(snapshot), encoding="utf-8")
    print(f"保存HTML: {export}", flush=True)
    if not args.no_serve:
        with TrackerServer(("127.0.0.1", args.port), snapshot_path) as server:
            print(f"http://localhost:{args.port}  終了: Ctrl+C", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
    return 0
