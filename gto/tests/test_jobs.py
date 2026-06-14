"""In-process job subsystem (gto.api.jobs) — admission control, lifecycle, TTL.

These tests drive the JobManager with fake work functions gated on threading
Events, so they exercise queuing / memory accounting / cancel / TTL without
running the real (heavy) flop solver.
"""

from __future__ import annotations

import threading
import time

from gto.api.jobs import JobManager, JobStatus


def _wait_until(pred, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(0.005)
    return False


def test_single_job_runs_and_returns_result():
    jm = JobManager(budget_gb=12.0)
    jid = jm.submit("flop", est_gb=12.0, fn=lambda: 1 + 1)
    assert _wait_until(lambda: jm.result(jid)[0] == JobStatus.DONE)
    status, result, error = jm.result(jid)
    assert status == JobStatus.DONE
    assert result == 2
    assert error is None


def test_second_flop_job_queues_not_oom():
    """Budget fits exactly one 12 GB job; a second must queue while the first
    runs, then start once the first frees its reservation."""
    jm = JobManager(budget_gb=12.0)
    gate = threading.Event()

    def blocking():
        gate.wait(timeout=2.0)
        return "a"

    a = jm.submit("flop", est_gb=12.0, fn=blocking)
    b = jm.submit("flop", est_gb=12.0, fn=lambda: "b")

    # A is admitted (running), B does not fit (12+12 > 12) so it queues.
    assert _wait_until(lambda: jm.get(a).status == JobStatus.RUNNING)
    assert jm.get(b).status == JobStatus.QUEUED
    assert jm.stats()["running_gb"] == 12.0

    # Release A; B then gets scheduled and completes.
    gate.set()
    assert _wait_until(lambda: jm.result(a)[0] == JobStatus.DONE)
    assert _wait_until(lambda: jm.result(b)[0] == JobStatus.DONE)
    assert jm.result(b)[1] == "b"
    assert jm.stats()["running_gb"] == 0.0


def test_small_job_skips_ahead_of_unfittable_large_job():
    """Skip-and-continue admission: a small job that fits starts ahead of a
    queued large job that does not."""
    jm = JobManager(budget_gb=20.0)
    gate = threading.Event()

    a = jm.submit("flop", est_gb=12.0, fn=lambda: gate.wait(timeout=2.0))
    assert _wait_until(lambda: jm.get(a).status == JobStatus.RUNNING)
    b = jm.submit("flop", est_gb=12.0, fn=lambda: "b")   # 12+12 > 20 -> queues
    c = jm.submit("river", est_gb=5.0, fn=lambda: "c")    # 12+5 <= 20 -> runs

    assert _wait_until(lambda: jm.result(c)[0] == JobStatus.DONE)
    assert jm.get(b).status == JobStatus.QUEUED  # still waiting on A
    gate.set()


def test_cancel_queued_job_is_immediate():
    jm = JobManager(budget_gb=12.0)
    gate = threading.Event()
    a = jm.submit("flop", est_gb=12.0, fn=lambda: gate.wait(timeout=2.0))
    assert _wait_until(lambda: jm.get(a).status == JobStatus.RUNNING)
    b = jm.submit("flop", est_gb=12.0, fn=lambda: "should not run")

    assert jm.cancel(b) is True
    assert jm.get(b).status == JobStatus.CANCELLED
    gate.set()
    # B never ran: its result stays None even after A frees the slot.
    assert _wait_until(lambda: jm.result(a)[0] == JobStatus.DONE)
    time.sleep(0.05)
    assert jm.result(b)[1] is None


def test_error_in_fn_becomes_error_status():
    jm = JobManager(budget_gb=12.0)

    def boom():
        raise RuntimeError("solver exploded")

    jid = jm.submit("flop", est_gb=12.0, fn=boom)
    assert _wait_until(lambda: jm.result(jid)[0] == JobStatus.ERROR)
    status, result, error = jm.result(jid)
    assert status == JobStatus.ERROR
    assert result is None
    assert "solver exploded" in error


def test_base_exception_releases_reservation():
    """A Rust panic surfaces as pyo3 PanicException, which subclasses
    BaseException (not Exception). The worker must still free its memory
    reservation, or the budget leaks and the async flop tier wedges forever."""

    class Panic(BaseException):
        pass

    jm = JobManager(budget_gb=12.0)
    jid = jm.submit("flop", est_gb=12.0, fn=lambda: (_ for _ in ()).throw(Panic("rust panic")))
    assert _wait_until(lambda: jm.result(jid)[0] == JobStatus.ERROR)
    assert jm.stats()["running_gb"] == 0.0
    # The freed reservation lets a subsequent full-budget job be admitted.
    jid2 = jm.submit("flop", est_gb=12.0, fn=lambda: "ok")
    assert _wait_until(lambda: jm.result(jid2)[0] == JobStatus.DONE)
    assert jm.result(jid2)[1] == "ok"


def test_finished_jobs_evicted_after_ttl():
    jm = JobManager(budget_gb=12.0, ttl_s=0.02)
    jid = jm.submit("flop", est_gb=12.0, fn=lambda: 42)
    assert _wait_until(lambda: jm.result(jid)[0] == JobStatus.DONE)
    time.sleep(0.05)
    # Any submit triggers eviction of expired finished jobs.
    jm.submit("flop", est_gb=12.0, fn=lambda: 0)
    assert jm.get(jid) is None


def test_unknown_job_id_returns_none():
    jm = JobManager(budget_gb=12.0)
    assert jm.status("nope") is None
    assert jm.result("nope") is None
    assert jm.cancel("nope") is False
