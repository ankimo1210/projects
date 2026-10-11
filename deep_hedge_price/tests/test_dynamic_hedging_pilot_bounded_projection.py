"""Synthetic transport/expense tests; no model generation or financial qualification."""

from __future__ import annotations

import copy
import sys
import weakref
from collections.abc import Mapping, MutableMapping
from pathlib import Path

import numpy as np
import pytest

RESEARCH = Path(__file__).resolve().parents[2] / "johnhull/research/RB-F04/dynamic_hedging"
sys.path.insert(0, str(RESEARCH))

import check_pilot  # noqa: E402
import run_pilot  # noqa: E402


def _events(wall=1.0, cpu=0.25, start=100):
    return {
        "wall_start_ns": start,
        "wall_stop_ns": start + int(wall * 1e9),
        "cpu_start_ns": start,
        "cpu_stop_ns": start + int(cpu * 1e9),
    }


def _expense(identifier, wall=1.0, cpu=0.25, *, inclusive=True):
    return {
        "id": identifier,
        "scope": identifier,
        "parent_id": None,
        "includes_children": inclusive,
        "status": "complete",
        "timing": {"wall_seconds": wall, "cpu_seconds": cpu, "overrun_seconds": 0.0},
    }


class _FreshJobs(Mapping):
    """Each access creates a fresh array, like a noncaching reference-store read."""

    def __init__(self, rows):
        self.rows = copy.deepcopy(rows)
        self.refs = []
        self.alive_before_read = []

    def __iter__(self):
        return iter(self.rows)

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, identifier):
        self.alive_before_read.append(sum(ref() is not None for ref in self.refs))
        row = copy.deepcopy(self.rows[identifier])
        row["raw"]["samples"] = np.asarray(row["raw"]["samples"], dtype=float).copy()
        self.refs.append(weakref.ref(row["raw"]["samples"]))
        return row

    def sequence(self):
        ids = tuple(self)
        return check_pilot.saved_storage.DeferredSequence(len(ids), lambda i: self[ids[i]])


class _FreshChecks(MutableMapping):
    """A saved-check store materializes a full value only during a lookup."""

    def __init__(self):
        self.rows = {}
        self.refs = []

    def __iter__(self):
        return iter(self.rows)

    def __len__(self):
        return len(self.rows)

    def __setitem__(self, identifier, value):
        self.rows[identifier] = copy.deepcopy(value)

    def __delitem__(self, identifier):
        del self.rows[identifier]

    def __getitem__(self, identifier):
        value = copy.deepcopy(self.rows[identifier])
        value["original_samples"] = np.arange(32, dtype=float).reshape(16, 2)
        self.refs.append(weakref.ref(value["original_samples"]))
        return value


def _jobs(count=6):
    return {
        f"job:{i}": {
            "id": f"job:{i}",
            "operation": "precision" if i == count - 1 else "synthetic",
            "original_n": 16,
            "expense": _expense(f"expense:{i}"),
            "timing_events": _events(),
            "raw": {
                "original_n": 16,
                "samples": [[float(j), float(j + i)] for j in range(16)],
                "qualification": "unknown" if i == count - 1 else "qualified",
                "reason": "original last slot remains unknown" if i == count - 1 else None,
            },
        }
        for i in range(count)
    }


def _projection_fixture(monkeypatch):
    """Keep original 121/51 bridge rows; isolate upstream financial computations."""
    candidate = check_pilot.execution.execution_candidate()
    rows = _jobs()
    ids = tuple(rows)
    cases = []
    attempts = []
    case_plans = []
    attempt_plans = []
    specs = {"cases": [], "attempts": [], "selection_policy": {"fixture": "routing only"}}
    for original, plans, results, specifications in (
        (candidate["pilot_cases"], case_plans, cases, specs["cases"]),
        (
            [{"id": identifier} for identifier in candidate["required_pilot_attempt_ids"]],
            attempt_plans,
            attempts,
            specs["attempts"],
        ),
    ):
        for index, descriptor in enumerate(original):
            identifier = descriptor["id"]
            jid = ids[index % len(ids)]
            plan = copy.deepcopy(descriptor) | {
                "original_n": 16,
                "cap": None,
                "expense_id": "alias:" + identifier,
            }
            plans.append(plan)
            results.append(
                {
                    "id": identifier,
                    "original_n": 16,
                    "required_job_ids": [jid],
                    "financial_qualification": "unknown",
                    "cap_evidence": None,
                    "fit_validation": {"scope": "synthetic routing only"},
                }
            )
            specifications.append(
                {
                    "id": identifier,
                    "required_job_ids": [jid],
                    "parent_expense_id": rows[jid]["expense"]["id"],
                    "cap_options": [],
                }
            )
    source = {"protocol_source": {"fixture": "no financial source approval"}}
    plan = {
        "case_plan": case_plans,
        "attempt_plan": attempt_plans,
        "execution_projection": specs,
        "history": [{"id": "unmeasured_external_history", "unknown_cost": None}],
    }
    expenses = [copy.deepcopy(row["expense"]) for row in rows.values()]
    for identifier in candidate["current_pilot_expense_ids"]:
        expenses.append(_expense(identifier, inclusive=False) | {"timing_events": _events()})
    calls = []

    def numerical_adapter(snapshot, *, expected_plan, context, job_store=None, check_store=None):
        # Deliberately recompute every sample on every call; never accept snapshot flags.
        jobs = {row["id"]: row for row in snapshot["jobs"]} if job_store is None else job_store
        checks = {} if check_store is None else check_store
        assert set(jobs) == set(rows)
        calls.append((job_store, check_store))
        for jid in jobs:
            job = jobs[jid]
            np.testing.assert_allclose(job["raw"]["samples"], rows[jid]["raw"]["samples"])
            checks[jid] = {
                "original_n": job["original_n"],
                "worst_mean_loss_se": 0.1,
                "worst_mse_se": 0.2,
                "baseline_mse": 3.0,
                "qualification": job["raw"]["qualification"],
                "reason": job["raw"]["reason"],
                "evidence_sha256": run_pilot.input_identity(job["raw"]),
            }
            del job
        return {
            "closed": True,
            "verification": {"integrity": "pass", "scope": "synthetic arithmetic adapter"},
            "case_results": copy.deepcopy(cases),
            "attempt_results": copy.deepcopy(attempts),
            "raw_checks": checks,
            "costs": {"raw_expenses": copy.deepcopy(expenses)},
        }

    selection = {
        "teacher_selection_status": {"Heston": "unknown", "local": "unknown"},
        "precision_selection": "unknown",
    }
    domains = [{"status": "unknown", "reason": "not financially measured"}]
    monkeypatch.setattr(check_pilot, "check_pilot_records", numerical_adapter)
    monkeypatch.setattr(check_pilot, "derive_execution_selection", lambda *args: selection)
    monkeypatch.setattr(check_pilot, "derive_execution_domains", lambda *args: domains)
    # Only final A-schema validators are isolated; real projection and expense gates run.
    for name in ("_selection", "_domains", "_pilot"):
        monkeypatch.setattr(check_pilot.execution, name, lambda *args: None)
    return rows, plan, source, selection, domains, calls


def test_bounded_projection_matches_eager_and_rechecks_original_samples(monkeypatch):
    rows, plan, source, selection, domains, calls = _projection_fixture(monkeypatch)
    eager_jobs = _FreshJobs(rows)
    eager_snapshot = {"source": source, "jobs": [eager_jobs[jid] for jid in eager_jobs]}
    eager = check_pilot.project_execution_pilot(
        eager_snapshot, expected_plan=plan, context={}, selection=selection, domains=domains
    )
    jobs = _FreshJobs(rows)
    checks = {}
    snapshot = {"source": source, "jobs": jobs.sequence()}
    bounded = check_pilot.project_execution_pilot(
        snapshot,
        expected_plan=plan,
        context={},
        selection=selection,
        domains=domains,
        job_store=jobs,
        check_store=checks,
    )
    assert bounded == eager
    assert calls == [(None, None), (jobs, checks)]
    assert len(bounded["pilot"]["cases"]) == 121
    assert len(bounded["pilot"]["attempts"]) == 51
    assert bounded["pilot"]["financial_qualification"] == "unknown"
    assert bounded["pilot"]["test_precision"][-1]["qualification"] == "unknown"
    assert bounded["pilot"]["history"] == plan["history"]
    assert max(jobs.alive_before_read) <= 2
    assert all(ref() is None for ref in jobs.refs)


def test_bounded_projection_does_not_retain_full_check_arrays(monkeypatch):
    rows, plan, source, selection, domains, calls = _projection_fixture(monkeypatch)
    jobs, checks = _FreshJobs(rows), _FreshChecks()
    snapshot = {"source": source, "jobs": jobs.sequence()}
    result = check_pilot.project_execution_pilot(
        snapshot,
        expected_plan=plan,
        context={},
        selection=selection,
        domains=domains,
        job_store=jobs,
        check_store=checks,
    )
    assert calls == [(jobs, checks)]
    assert len(checks) == len(rows)
    assert result["pilot"]["test_precision"][-1]["qualification"] == "unknown"
    assert checks.refs and all(ref() is None for ref in checks.refs)
    assert all(ref() is None for ref in jobs.refs)


def test_actual_checker_receipt_reuses_one_digest_after_numeric_recheck(monkeypatch):
    rows, plan, source, selection, domains, calls = _projection_fixture(monkeypatch)
    jobs = _FreshJobs(rows)
    snapshot = {"source": source, "jobs": jobs.sequence()}
    adapter = check_pilot.check_pilot_records
    original_digest = check_pilot.saved_storage.payload_digest
    digest_calls = []

    def digest(value):
        if value is snapshot:
            digest_calls.append(value)
        return original_digest(value)

    def with_receipt(*args, **kwargs):
        checked = adapter(*args, **kwargs)
        checked["verification"]["evidence_sha256"] = digest(args[0])
        return checked

    monkeypatch.setattr(check_pilot, "check_pilot_records", with_receipt)
    monkeypatch.setattr(check_pilot.saved_storage, "payload_digest", digest)
    result = check_pilot.project_execution_pilot(
        snapshot,
        expected_plan=plan,
        context={},
        selection=selection,
        domains=domains,
        job_store=jobs,
        check_store={},
    )
    assert len(calls) == 1 and len(digest_calls) == 1
    assert result["pilot"]["raw_snapshot_sha256"] == original_digest(snapshot)


def test_snapshot_digest_is_bound_once_per_verified_projection(monkeypatch):
    rows, plan, source, selection, domains, _ = _projection_fixture(monkeypatch)
    jobs = _FreshJobs(rows)
    snapshot = {"source": source, "jobs": jobs.sequence()}
    original = check_pilot.saved_storage.payload_digest
    expected = original(snapshot)
    snapshot_calls = []

    def digest(value):
        if value is snapshot:
            snapshot_calls.append(value)
        return original(value)

    monkeypatch.setattr(check_pilot.saved_storage, "payload_digest", digest)
    result = check_pilot.project_execution_pilot(
        snapshot, expected_plan=plan, context={}, selection=selection, domains=domains
    )
    assert len(snapshot_calls) == 1
    assert result["pilot"]["raw_snapshot_sha256"] == expected
    assert all(row["verification"]["evidence_sha256"] for row in result["pilot"]["cases"])


def test_last_sample_tamper_cannot_reuse_previously_checked_flags(monkeypatch):
    rows, plan, source, selection, domains, calls = _projection_fixture(monkeypatch)
    jobs = _FreshJobs(rows)
    snapshot = {"source": source, "jobs": jobs.sequence(), "closed": True}
    check_pilot.project_execution_pilot(
        snapshot,
        expected_plan=plan,
        context={},
        selection=selection,
        domains=domains,
        job_store=jobs,
        check_store={},
    )
    last_id = tuple(jobs)[-1]
    jobs.rows[last_id]["raw"]["samples"][-1][-1] += 1.0
    with pytest.raises(AssertionError):
        check_pilot.project_execution_pilot(
            snapshot,
            expected_plan=plan,
            context={},
            selection=selection,
            domains=domains,
            job_store=jobs,
            check_store={},
        )
    assert len(calls) == 2


def test_real_checker_rejects_partial_even_with_external_closed_flags(monkeypatch):
    # No numerical workers: the real checker must enumerate missing original 121/51.
    monkeypatch.setattr(run_pilot, "validate_locked_plan", lambda plan: plan)
    plan = {"jobs": [], "case_plan": [], "attempt_plan": [], "history": []}
    snapshot = {
        "schema": "rb-f04-pilot-raw-v1",
        "locked_plan": plan,
        "jobs": [],
        "source": {},
        "case_bindings": [],
        "attempt_bindings": [],
        "closed": True,
        "verification": {"integrity": "pass"},
    }
    with pytest.raises(ValueError, match="saved original pilot is not closed"):
        check_pilot.project_execution_pilot(
            snapshot,
            expected_plan=plan,
            context={},
            selection={},
            domains=[],
            job_store={},
            check_store={},
        )


@pytest.mark.parametrize("phase", [False, True])
def test_expense_projection_releases_raw_arrays_and_preserves_clock_digests(phase):
    rows = _jobs()
    jobs = _FreshJobs(rows)
    expenses = [copy.deepcopy(row["expense"]) for row in rows.values()]
    if phase:
        parent = _expense("phase", wall=2.0, cpu=0.5) | {
            "timing_events": _events(2.0, 0.5),
            "covered_job_ids": list(rows),
        }
        expenses.append(parent)
        aliases = [
            {"id": "phase-alias", "parent_expense_id": "phase", "required_job_ids": list(rows)}
        ]
    else:
        aliases = [
            {
                "id": "alias:" + jid,
                "parent_expense_id": row["expense"]["id"],
                "required_job_ids": [jid],
            }
            for jid, row in rows.items()
        ]
    expected = check_pilot.project_execution_expense_aliases(expenses, aliases, jobs=rows)
    result = check_pilot.project_execution_expense_aliases(expenses, aliases, jobs=jobs)
    assert result == expected
    assert max(jobs.alive_before_read) <= 2
    assert all(ref() is None for ref in jobs.refs)
    for alias in aliases:
        value = next(row for row in result["raw_records"] if row["id"] == alias["id"])
        parent = next(row for row in expenses if row["id"] == alias["parent_expense_id"])
        assert value["actual_parent_sha256"] == run_pilot.input_identity(parent)
        assert value["covered_job_ids"] == alias["required_job_ids"]


@pytest.mark.parametrize("phase", [False, True])
def test_expense_projection_refuses_last_original_clock_tamper(phase):
    rows = _jobs()
    expenses = [copy.deepcopy(row["expense"]) for row in rows.values()]
    last = tuple(rows)[-1]
    rows[last]["timing_events"]["wall_stop_ns"] += 1_000_000_000
    if phase:
        parent = _expense("phase", wall=2.0, cpu=0.5) | {
            "timing_events": _events(2.0, 0.5),
            "covered_job_ids": list(rows),
        }
        expenses.append(parent)
        aliases = [{"id": "alias", "parent_expense_id": "phase", "required_job_ids": list(rows)}]
    else:
        aliases = [
            {
                "id": "alias",
                "parent_expense_id": rows[last]["expense"]["id"],
                "required_job_ids": [last],
            }
        ]
    with pytest.raises(ValueError, match="actual expense clock duration differs"):
        check_pilot.project_execution_expense_aliases(expenses, aliases, jobs=_FreshJobs(rows))
