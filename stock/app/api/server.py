"""Standalone Flask API server for AI chat (port 8051).

Runs in a background daemon thread so it can coexist with the Dash app
on port 8050 without triggering Dash's callback_context middleware.
"""

from __future__ import annotations

import threading

from flask import Flask, jsonify, request

api_app = Flask(__name__)


@api_app.route("/api/chat", methods=["POST"])
def chat():
    from api import job_store
    body = request.get_json(force=True)
    job_id = job_store.submit(
        body.get("conversation", []),
        body.get("message", ""),
    )
    return jsonify({"job_id": job_id})


@api_app.route("/api/status/<job_id>")
def status(job_id: str):
    from api import job_store
    return jsonify(job_store.get_status(job_id))


def start(port: int = 8051) -> None:
    """Start the API server in a daemon thread."""
    t = threading.Thread(
        target=api_app.run,
        kwargs={"host": "127.0.0.1", "port": port, "debug": False},
        daemon=True,
        name="api-server",
    )
    t.start()
