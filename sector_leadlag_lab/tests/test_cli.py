import json
import subprocess

import numpy as np
import pandas as pd
import pytest
from sector_leadlag import cli
from sector_leadlag.data.store import store_bytes

META = {
    "prereg_commit": "abc",
    "prereg_committed_at": "2026-10-20T10:00:00+09:00",
    "main_a_commit": "def",
}


def write(results, name: str, payload: dict) -> None:
    (results / f"{name}.json").write_text(json.dumps(payload))


def test_every_stage_needs_a_committed_prereg(tmp_path):
    with pytest.raises(cli.StageError, match="PREREG"):
        cli.check_ready("g0", tmp_path, {**META, "prereg_commit": ""})
    assert cli.check_ready("g0", tmp_path, META) == {}


def test_a_failed_replication_stops_every_later_stage(tmp_path):
    with pytest.raises(cli.StageError, match=r"g0\.json"):
        cli.check_ready("g1", tmp_path, META)
    write(tmp_path, "g0", {"pass": False})
    with pytest.raises(cli.StageError, match="replication_failed"):
        cli.check_ready("g1", tmp_path, META)


def test_main_a_needs_a_passed_g1_and_a_prereg_commit_after_it(tmp_path):
    write(tmp_path, "g0", {"pass": True})
    write(tmp_path, "g1", {"pass": False, "meta": {"ran_at": "2026-10-20T00:00:00+00:00"}})
    with pytest.raises(cli.StageError, match="G1 did not pass"):
        cli.check_ready("main-a", tmp_path, META)
    write(tmp_path, "g1", {"pass": True, "meta": {"ran_at": "2026-10-20T02:00:00+00:00"}})
    with pytest.raises(cli.StageError, match="commit it before main A"):
        cli.check_ready("main-a", tmp_path, META)  # PREREG 01:00 UTC, G1 02:00 UTC
    write(tmp_path, "g1", {"pass": True, "meta": {"ran_at": "2026-10-20T00:30:00+00:00"}})
    assert set(cli.check_ready("main-a", tmp_path, META)) == {"g0", "g1"}


def test_main_b_needs_main_a_committed(tmp_path):
    write(tmp_path, "g0", {"pass": True})
    write(tmp_path, "main_a", {"robust": True})
    with pytest.raises(cli.StageError, match=r"commit results/main_a\.json"):
        cli.check_ready("main-b", tmp_path, {**META, "main_a_commit": ""})
    assert set(cli.check_ready("main-b", tmp_path, META)) == {"g0", "main_a"}


def test_main_b_runs_once_without_a_reason(tmp_path):
    assert cli.main_b_target(tmp_path, None) == ("main_b", {})
    cli.take_lock(tmp_path, "abc123")
    with pytest.raises(cli.StageError, match="already ran"):
        cli.main_b_target(tmp_path, None)
    write(tmp_path, "main_b", {"verdict": "etf_only"})
    name, extra = cli.main_b_target(tmp_path, "fixed a data error")
    assert name == "main_b_rerun_1"
    assert extra == {"rerun_reason": "fixed a data error", "verdict_of_record": "etf_only"}


def test_diagnostics_wait_for_the_verdict(tmp_path):
    write(tmp_path, "g0", {"pass": True})
    write(tmp_path, "main_a", {})
    with pytest.raises(cli.StageError, match=r"main_b\.json"):
        cli.check_ready("diagnostics", tmp_path, META)


def test_results_serialise_numpy_values_and_dates(tmp_path):
    result = {
        "a": np.float64(1.5),
        "b": pd.Timestamp("2026-03-18"),
        "c": (1, 2),
        "d": np.bool_(True),
        "e": np.int64(3),
    }
    path = cli.write_result("x", result, tmp_path, {"git_commit": "abc"})
    assert json.loads(path.read_text()) == {
        "meta": {"git_commit": "abc"},
        "a": 1.5,
        "b": "2026-03-18",
        "c": [1, 2],
        "d": True,
        "e": 3,
    }


def test_meta_ignores_result_files_and_dates_the_prereg(tmp_path, monkeypatch):
    lab = tmp_path / "lab"
    (lab / "results").mkdir(parents=True)
    git = ["git", "-C", str(lab), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    subprocess.run(["git", "init", "-q", str(lab)], check=True)
    (lab / "PREREG.md").write_text("x\n")
    subprocess.run([*git, "add", "PREREG.md"], check=True)
    subprocess.run([*git, "-c", "commit.gpgsign=false", "commit", "-qm", "init"], check=True)
    monkeypatch.setattr(cli, "LAB", lab)
    monkeypatch.setattr(cli, "RAW_ROOT", tmp_path / "raw")
    (lab / "results" / "g0.json").write_text("{}")
    first = cli.meta()
    assert first["dirty"] is False and first["prereg_commit"] and first["inputs_count"] == 0
    assert first["prereg_committed_at"][:4].isdigit()
    (lab / "PREREG.md").write_text("y\n")
    assert cli.meta()["dirty"] is True


def test_the_inputs_digest_follows_the_newest_payloads(tmp_path):
    store_bytes(tmp_path, "yf", "XLK", b"old", url="u", filename="XLK.csv")
    first = cli.inputs_digest(tmp_path)
    store_bytes(tmp_path, "yf", "XLK", b"new", url="u", filename="XLK.csv")
    second = cli.inputs_digest(tmp_path)
    assert first[1] == second[1] == 1 and first[0] != second[0]
