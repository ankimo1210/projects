"""DSINC runner: slot accounting, budgets, freeze checks, replay, export and figures."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from hullkit._dsinc_types import BOUNDARY_STATUS, canonical_digest

RUN = Path(__file__).resolve().parents[2] / "research/DSINC/run.py"
PLOT = Path(__file__).resolve().parents[2] / "research/DSINC/plot.py"
BUDGET = {"job_wall_seconds": 180.0, "job_rss_bytes": 2**31, "total_seconds": 600.0}
THREADS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def run():
    return load(RUN, "dsinc_run_tests")


def fixture_job(job_id, **params):
    return {
        "job_id": job_id,
        "method": "fixture",
        "expiry": 0.5,
        "level": None,
        "variant": "fixture",
        "role": "fixture",
        "condition": None,
        "params": params,
    }


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_slots_are_accounted_under_a_fake_clock(run, tmp_path):
    clock = FakeClock()

    def launcher(job, root, timeout):
        clock.now += job["params"]["seconds"]
        if job["params"]["seconds"] > timeout:
            return {"status": "timeout", "reason": f"exceeded {timeout} s"}
        if job["params"].get("fail"):
            return {"status": "error", "reason": "boom"}
        return {
            "status": "ok",
            "prices": {"american": [1.0]},
            "maxrss_bytes": job["params"].get("rss", 10),
        }

    roster = [
        fixture_job("ok", seconds=1.0),
        fixture_job("fails", seconds=1.0, fail=True),
        fixture_job("big", seconds=1.0, rss=3 * 2**30),
        fixture_job("slow", seconds=200.0),
        fixture_job("late", seconds=1.0),
    ]
    records = run.execute_roster(
        roster, tmp_path / "root", BUDGET | {"total_seconds": 183.0}, launcher=launcher, clock=clock
    )
    assert [r["job_id"] for r in records] == ["ok", "fails", "big", "slow", "late"]
    assert [r["status"] for r in records] == [
        "ok",
        "error",
        "memory_exceeded",
        "timeout",
        "not_run_budget",
    ]
    assert records[0]["prices"] == {"american": [1.0]} and all(
        r["prices"] is None for r in records[1:]
    )
    assert records[2]["raw"]["maxrss_bytes"] == 3 * 2**30 and all(r["reason"] for r in records[1:])


def test_real_subprocess_timeout_and_thread_guard(run, tmp_path):
    records = run.execute_roster(
        [fixture_job("sleepy", sleep=3.0), fixture_job("fine", value=1.0)],
        tmp_path / "root",
        BUDGET | {"job_wall_seconds": 1.0, "total_seconds": 30.0},
    )
    assert [r["status"] for r in records] == ["timeout", "ok"] and records[1]["raw"][
        "maxrss_bytes"
    ] > 0
    job = tmp_path / "job.json"
    job.write_text(json.dumps(fixture_job("x", value=1.0)))
    env = os.environ | dict.fromkeys(THREADS, "1") | {"OPENBLAS_NUM_THREADS": "4"}
    proc = subprocess.run(
        [
            sys.executable,
            str(RUN),
            "solve-job",
            "--job",
            str(job),
            "--out",
            str(tmp_path / "out.json"),
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0 and "OPENBLAS_NUM_THREADS" in proc.stderr


def test_conditional_jobs_follow_the_condition_and_the_remaining_budget(run, tmp_path):
    roster = [
        fixture_job("first", value=1.0),
        fixture_job("skip", value=2.0)
        | {"condition": "S0_not_adopted:T0.5", "estimate_seconds": 1.0},
        fixture_job("take", value=3.0) | {"condition": "adopted:S0:T0.5", "estimate_seconds": 1.0},
        fixture_job("too_long", value=4.0)
        | {"condition": "adopted:S0:T0.5", "estimate_seconds": 1e6},
    ]
    seen = []

    def should_run(job, records):
        seen.append([r["job_id"] for r in records])
        return job["condition"] == "adopted:S0:T0.5"

    records = run.execute_roster(roster, tmp_path / "root", BUDGET, should_run=should_run)
    assert [r["status"] for r in records] == ["ok", "not_run_condition", "ok", "not_run_budget"]
    assert seen == [["first"], ["first", "skip"], ["first", "skip", "take"]]


def test_conditions_read_the_level_selection(run):
    selections = {"0.5": {"adopted": "S0"}, "1.0": {"adopted": None}}
    assert run.condition_met("adopted:S0:T0.5", selections)
    assert not run.condition_met("S0_not_adopted:T0.5", selections)
    assert run.condition_met("S0_not_adopted:T1.0", selections)
    assert not run.condition_met("adopted:S1:T1.0", selections)
    with pytest.raises(ValueError):
        run.condition_met("adopted:S3:T0.5", selections)


def test_results_json_never_contains_nan(run, tmp_path):
    records = run.execute_roster([fixture_job("nan", nan=True)], tmp_path / "root", BUDGET)
    assert records[0]["status"] == "nonfinite" and records[0]["prices"] is None
    text = (tmp_path / "root/records.json").read_text()
    assert "NaN" not in text and json.loads(text)
    with pytest.raises(ValueError):
        run.write_json(tmp_path / "x.json", {"a": float("nan")})


def test_output_root_must_be_new(run, tmp_path):
    root = tmp_path / "run"
    root.mkdir()
    (root / "old.json").write_text("{}")
    with pytest.raises(ValueError, match="exists"):
        run.execute_roster([], root, BUDGET)


def test_protocol_and_rosters_are_fixed(run):
    protocol = run.load_protocol()
    assert (
        protocol["thresholds"]["paper_match"] == 6e-6
        and protocol["thresholds"]["independent"] == 2e-5
    )
    assert (
        protocol["budget"]["job_wall_seconds"] == 180 and protocol["budget"]["main_seconds"] == 1800
    )
    pilot = run.build_roster(protocol, "pilot")
    assert (
        len([j for j in pilot if not j.get("optional")]) == 32
        and len([j for j in pilot if j.get("optional")]) == 10
    )
    main = run.build_roster(protocol, "main")
    always, conditional = (
        [j for j in main if not j["condition"]],
        [j for j in main if j["condition"]],
    )
    assert (len(always), len(conditional)) == (50, 38)
    assert all(len({j["job_id"] for j in r}) == len(r) for r in (pilot, main))
    s0 = next(j for j in main if j["job_id"] == "spectral-S0-base-T1.0")
    assert (s0["config"]["n_time"], s0["config"]["n_var"], len(s0["spots"])) == (200, 160, 147)
    run.check_job_in_roster(s0, main)
    with pytest.raises(ValueError, match="roster"):
        run.check_job_in_roster({"job_id": "spectral-S3-base-T0.5"}, main)
    with pytest.raises(ValueError, match="roster"):
        run.check_job_in_roster(s0 | {"config": s0["config"] | {"chi": 0.4}}, main)


def estimates(roster, seconds):
    return [
        {
            "job_id": j["job_id"],
            "condition": j["condition"],
            "status": "estimated",
            "seconds": seconds,
        }
        for j in roster
    ]


def passing_pilot(protocol):
    return {"all_pass": True, "protocol_digest": canonical_digest(protocol)}


def test_freeze_rejects_failed_pilots_and_unmeasured_or_large_estimates(run):
    protocol = run.load_protocol()
    roster = run.build_roster(protocol, "main")
    ok = passing_pilot(protocol)
    run.make_freeze_manifest(protocol, ok, estimates(roster, 1.0))
    with pytest.raises(ValueError, match="pilot"):
        run.make_freeze_manifest(protocol, ok | {"all_pass": False}, estimates(roster, 1.0))
    with pytest.raises(ValueError, match="protocol"):
        run.make_freeze_manifest(
            protocol, ok | {"protocol_digest": "0" * 64}, estimates(roster, 1.0)
        )
    with pytest.raises(ValueError, match="roster"):
        run.make_freeze_manifest(protocol, ok, estimates(roster, 1.0)[1:])
    unmeasured = estimates(roster, 1.0)
    unmeasured[0] |= {"status": "unmeasured", "seconds": None}
    with pytest.raises(ValueError, match="unmeasured"):
        run.make_freeze_manifest(protocol, ok, unmeasured)
    slow = estimates(roster, 1.0)
    slow[-1]["seconds"] = 181.0  # a conditional job: the 180 s rule covers every job
    with pytest.raises(ValueError, match="180"):
        run.make_freeze_manifest(protocol, ok, slow)
    with pytest.raises(ValueError, match="1800"):
        run.make_freeze_manifest(
            protocol, ok, estimates(roster, 37.0)
        )  # 50 always-run jobs x 37 s = 1850 s
    mixed = [e | {"seconds": 170.0 if e["condition"] else 30.0} for e in estimates(roster, 0.0)]
    run.make_freeze_manifest(
        protocol, ok, mixed
    )  # D-5: conditional jobs stay outside the 1800 s gate


def test_main_requires_a_matching_freeze(run, tmp_path, monkeypatch):
    protocol = run.load_protocol()
    roster = run.build_roster(protocol, "main")
    manifest = run.make_freeze_manifest(protocol, passing_pilot(protocol), estimates(roster, 1.0))
    path = tmp_path / "freeze.json"
    run.write_json(path, manifest)
    run.verify_freeze(path)
    run.write_json(path, manifest | {"thresholds": manifest["thresholds"] | {"independent": 3e-5}})
    with pytest.raises(ValueError, match="freeze"):
        run.verify_freeze(path)
    source = tmp_path / "source.py"
    source.write_text("x = 1\n")
    monkeypatch.setattr(run, "SOURCE_FILES", (str(source),))
    run.write_json(
        path, run.make_freeze_manifest(protocol, passing_pilot(protocol), estimates(roster, 1.0))
    )
    source.write_text("x = 2\n")
    with pytest.raises(ValueError, match="source"):
        run.verify_freeze(path)


def test_real_solver_jobs_run_in_subprocesses(run, tmp_path):
    spectral = {
        "job_id": "spectral-tiny",
        "method": "spectral",
        "expiry": 0.5,
        "level": "tiny",
        "variant": "base",
        "role": "ladder",
        "condition": None,
        "spots": [0.9, 1.0, 1.1],
        "config": {
            "n_time": 40,
            "n_var": 24,
            "log_var_bounds": [-5.298317366548036, -1.2039728043259361],
            "chi": 0.5,
            "panels": [0, 2, 5, 10, 20, 40],
            "points_per_panel": 4,
        },
    }
    fd = {
        "job_id": "fd-tiny",
        "method": "fd",
        "expiry": 0.5,
        "level": None,
        "variant": "tiny",
        "role": "reference",
        "condition": None,
        "spots": [0.9, 1.0, 1.1],
        "config": {
            "n_x": 41,
            "n_var": 11,
            "n_time": 10,
            "log_spot_bounds": [-1.2, 1.2],
            "log_var_bounds": [-11.512925464970229, 2.0794415416798357],
            "record_boundary": True,
        },
    }
    records = run.execute_roster([spectral, fd], tmp_path / "root", BUDGET)
    assert [r["status"] for r in records] == ["ok", "ok"]
    for r in records:
        assert (
            np.all(np.isfinite(r["prices"]["american"]))
            and (tmp_path / "root" / r["arrays"]["path"]).exists()
        )
    with np.load(tmp_path / "root" / records[0]["arrays"]["path"]) as arrays:
        assert (
            arrays["log_boundary"].shape == (41, 24) and arrays["boundary_status"].dtype == np.int8
        )


def test_replay_recomputes_the_saved_verdicts(run, tmp_path):
    records = run.execute_roster(
        [fixture_job("a", value=1.0), fixture_job("b", fail=True)], tmp_path / "root", BUDGET
    )
    results = run.write_results(
        tmp_path / "root", "fixture", records, run.load_protocol(), run.load_cases()
    )
    assert run.replay(results)["match"]
    saved = json.loads(results.read_text())
    saved["records"][0]["status"] = "error"
    results.write_text(json.dumps(saved))
    assert not run.replay(results)["match"]


def test_export_respects_the_file_size_limit(run, tmp_path):
    records = run.execute_roster(
        [fixture_job("a", value=1.0, array_bytes=3_000_000)], tmp_path / "root", BUDGET
    )
    results = run.write_results(
        tmp_path / "root", "fixture", records, run.load_protocol(), run.load_cases()
    )
    with pytest.raises(ValueError, match="2000000"):
        run.export(results, tmp_path / "out", 2_000_000)


def test_plot_draws_three_figures_from_saved_results(tmp_path):
    plot = load(PLOT, "dsinc_plot_tests")
    results = plot.synthetic_results(
        tmp_path
    )  # writes a minimal results.json and arrays for the figure contract
    paths = plot.draw(results, tmp_path / "figures")
    assert sorted(p.name for p in paths) == [
        "exercise_boundary.png",
        "price_error_cost.png",
        "refinement_stability.png",
    ]
    assert all(p.stat().st_size > 10_000 for p in paths)


def job_of(roster, method, level, variant, expiry):
    return next(
        j
        for j in roster
        if (j["method"], j["level"], j["variant"], j["expiry"]) == (method, level, variant, expiry)
    )


def record_of(job, status="ok", shift=0.0, diagnostics=None, arrays=None):
    """The record of ``job`` as the runner saves it: prices only when ok, the other fields as the solver left them."""
    prices = (
        {q: [0.05 + shift] * len(job["spots"]) for q in ("european", "american", "eep")}
        if status == "ok"
        else None
    )
    return job | {
        "status": status,
        "reason": None if status == "ok" else status,
        "prices": prices,
        "raw": {},
        "timing": {"setup_seconds": 1.0, "solve_seconds": 1.0},
        "sizes": None,
        "diagnostics": diagnostics,
        "arrays": arrays,
        "wall_seconds": 2.0,
    }


def save_arrays(root, job, **arrays):
    path = root / "arrays" / f"{job['job_id']}.npz"
    path.parent.mkdir(exist_ok=True)
    np.savez_compressed(path, **arrays)
    return {"path": f"arrays/{job['job_id']}.npz"}


def test_boundary_gate_receives_the_recorded_root_residual(run, tmp_path):
    protocol, cases = run.load_protocol(), run.load_cases()
    roster = run.build_roster(protocol, "main")
    spectral, primary, check = (
        job_of(roster, *key, 0.5)
        for key in (
            ("spectral", "S0", "base"),
            ("fd", "boundary", "primary"),
            ("fd", "boundary", "check"),
        )
    )
    spectral_z = np.linspace(*spectral["config"]["log_var_bounds"], spectral["config"]["n_var"])
    fd_z = np.linspace(*primary["config"]["log_var_bounds"], primary["config"]["n_var"])
    dx = 2.4 / (primary["config"]["n_x"] - 1)
    edge = np.full((primary["config"]["n_time"] + 1, fd_z.size), -0.2)
    edge[-1] = np.nan  # no contact at maturity
    star = np.full(
        (spectral["config"]["n_time"] + 1, spectral_z.size), -0.2 + dx / 2
    )  # inside every FD bracket
    fine = record_of(
        primary, arrays=save_arrays(tmp_path, primary, contact_edge=edge, log_variances=fd_z)
    )
    coarse = record_of(
        check, arrays=save_arrays(tmp_path, check, contact_edge=edge[::2], log_variances=fd_z)
    )

    def judged(status, residual, failure=None):
        codes = np.zeros(star.shape, dtype=np.int8)
        if failure:
            codes[40:60, 80] = BOUNDARY_STATUS[failure]  # t/T in the window, v = 0.02
        arrays = save_arrays(
            tmp_path, spectral, log_boundary=star, boundary_status=codes, log_variances=spectral_z
        )
        mine = record_of(
            spectral, status, diagnostics={"max_root_residual": residual}, arrays=arrays
        )
        return run.evaluate("main", [mine, fine, coarse], tmp_path, protocol, cases)["boundary"][
            "0.5"
        ]

    assert judged("ok", 5e-9)["status"] == "pass"
    over = judged("ok", 2e-8)  # only a residual that was passed on can fail this
    assert over["status"] == "fail" and over["reasons"] == ["root_residual_exceeds_limit"]
    failed = judged(
        "pricing_failure", None, failure="maxiter"
    )  # no residual is recorded, the failed roots decide
    assert failed["status"] == "fail" and failed["reasons"] == ["root_failure_in_window"]


def test_selection_builds_the_sensitivity_dict_from_all_protocol_names(run, tmp_path):
    protocol, cases = run.load_protocol(), run.load_cases()
    roster = run.build_roster(protocol, "main")
    names = protocol["spectral"]["sensitivities"]
    wanted = [
        (("spectral", level, "base"), shift)
        for level, shift in (("S0", 0.0), ("S1", 1e-7), ("S2", 2e-7))
    ]
    wanted += [(("spectral", "S0", name), 1e-7 * (i + 1)) for i, name in enumerate(names)]
    wanted += [
        (("fd", "independent", variant), 0.0)
        for variant in (
            "base",
            "x481",
            "x961",
            "x1921",
            "var151",
            "var201",
            "time600",
            "time1200",
            "domain",
        )
    ]
    jobs = [(job_of(roster, *key, 0.5), shift) for key, shift in wanted]

    def selection(**statuses):  # job id -> status, or None for a job without a record
        records = [
            record_of(job, statuses.get(job["job_id"], "ok"), shift)
            for job, shift in jobs
            if statuses.get(job["job_id"], "ok")
        ]
        return run.evaluate("main", records, tmp_path, protocol, cases)["selections"]["0.5"]

    chosen = job_of(roster, "spectral", "S0", "chi_0.75", 0.5)["job_id"]
    complete = selection()
    assert len(names) == 11 and set(complete["checks"]["S0"]["sensitivities"]) == set(names)
    assert complete["adopted"] == "S0" and complete["checks"]["S0"]["passed"]
    for pending in (
        {chosen: "not_run_budget"},
        {chosen: None},
    ):  # one variant not run: the whole level waits
        waiting = selection(**pending)
        assert waiting["adopted"] is None and waiting["status"] == "not_achieved_budget"
        assert (
            waiting["checks"]["S0"]["sensitivities"] is None and waiting["checks"]["S0"]["pending"]
        )
    failed = selection(
        **{chosen: "timeout"}
    )  # a variant that ran and failed is a failed check, not a wait
    assert failed["adopted"] is None and failed["checks"]["S0"]["sensitivities"]["chi_0.75"] is None
    assert not failed["checks"]["S0"]["passed"] and not failed["checks"]["S0"]["pending"]
