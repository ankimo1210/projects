"""In-memory async job queue backed by threading.Thread.

Jobs are cleaned up after 1 hour to prevent memory leaks.
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any


_jobs: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def submit(conversation: list[dict], user_message: str) -> str:
    """Start a Claude agent job in a background thread. Returns job_id."""
    job_id = str(uuid.uuid4())
    with _lock:
        _jobs[job_id] = {
            "status": "running",
            "result": None,
            "error": None,
            "created_at": time.time(),
        }

    def _run():
        try:
            from api.claude_agent import run as agent_run
            result = agent_run(conversation, user_message)
            with _lock:
                _jobs[job_id]["status"] = "done"
                _jobs[job_id]["result"] = result
        except Exception as e:
            with _lock:
                _jobs[job_id]["status"] = "error"
                _jobs[job_id]["error"] = str(e)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    _cleanup_old_jobs()
    return job_id


def get_status(job_id: str) -> dict[str, Any]:
    with _lock:
        job = _jobs.get(job_id)
    if job is None:
        return {"status": "not_found"}
    return {
        "status": job["status"],
        "result": job.get("result"),
        "error": job.get("error"),
    }


def _cleanup_old_jobs():
    cutoff = time.time() - 3600
    with _lock:
        stale = [jid for jid, j in _jobs.items()
                 if j["created_at"] < cutoff and j["status"] != "running"]
        for jid in stale:
            del _jobs[jid]
