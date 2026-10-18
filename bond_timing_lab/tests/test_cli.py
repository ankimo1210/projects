import hashlib
import json
import subprocess

import numpy as np
import pandas as pd
import pytest
from bond_timing import cli
from bond_timing.data.store import store_bytes


def write(results, name: str, payload: dict) -> None:
    (results / f"{name}.json").write_text(json.dumps(payload))


def test_stage_order_is_enforced(tmp_path):
    with pytest.raises(cli.StageError, match=r"dev\.json"):
        cli.check_ready("g1", tmp_path, prereg_commit="abc")
    write(tmp_path, "dev", {"p1": "slope"})
    with pytest.raises(cli.StageError, match="PREREG"):
        cli.check_ready("g1", tmp_path, prereg_commit="")
    assert cli.check_ready("g1", tmp_path, prereg_commit="abc")["dev"]["p1"] == "slope"
    assert cli.check_ready("g0", tmp_path, prereg_commit="") == {}


def test_oos_a_requires_prereg_and_a_passed_g1(tmp_path):
    write(tmp_path, "dev", {"p1": "slope"})
    write(tmp_path, "g1", {"pass": False})
    with pytest.raises(cli.StageError, match="G1 did not pass"):
        cli.check_ready("oos-a", tmp_path, prereg_commit="abc")
    write(tmp_path, "g1", {"pass": True})
    assert set(cli.check_ready("oos-a", tmp_path, prereg_commit="abc")) == {"dev", "g1"}


def test_oos_b_runs_once_without_a_reason(tmp_path):
    assert cli.oos_b_target(tmp_path, None) == ("oos_b", {})
    cli.take_lock(tmp_path, "abc123")
    with pytest.raises(cli.StageError, match="already ran"):
        cli.oos_b_target(tmp_path, None)
    write(tmp_path, "oos_b", {"verdict": "no_usable_signal"})
    name, extra = cli.oos_b_target(tmp_path, "fixed a data error")
    assert name == "oos_b_rerun_1"
    assert extra == {"rerun_reason": "fixed a data error", "verdict_of_record": "no_usable_signal"}


def test_results_serialise_numpy_values_and_periods(tmp_path):
    result = {
        "a": np.float64(1.5),
        "b": pd.Period("2000-01", "M"),
        "c": (1, 2),
        "d": np.bool_(True),
    }
    path = cli.write_result("x", result, tmp_path, {"git_commit": "abc"})
    assert json.loads(path.read_text()) == {
        "meta": {"git_commit": "abc"},
        "a": 1.5,
        "b": "2000-01",
        "c": [1, 2],
        "d": True,
    }


def test_meta_ignores_result_files(tmp_path, monkeypatch):
    lab = tmp_path / "lab"
    (lab / "results").mkdir(parents=True)
    git = ["git", "-C", str(lab), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    subprocess.run(["git", "init", "-q", str(lab)], check=True)
    (lab / "code.py").write_text("x = 1\n")
    subprocess.run([*git, "add", "code.py"], check=True)
    subprocess.run([*git, "-c", "commit.gpgsign=false", "commit", "-qm", "init"], check=True)
    monkeypatch.setattr(cli, "LAB", lab)
    monkeypatch.setattr(cli, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(cli, "MACROKIT_RAW", tmp_path / "macrokit")
    (lab / "results" / "g0.json").write_text("{}")
    assert cli.meta()["dirty"] is False
    (lab / "code.py").write_text("x = 2\n")
    assert cli.meta()["dirty"] is True


def test_input_records_name_the_payloads_the_study_reads(tmp_path):
    raw, macrokit = tmp_path / "raw", tmp_path / "macrokit"
    store_bytes(raw, "fred", "DTB3", b"old", url="u", filename="DTB3.csv")
    store_bytes(raw, "fred", "DTB3", b"new", url="u", filename="DTB3.csv")
    store_bytes(raw, "etf", "TLT", b"t", url="u", filename="TLT.csv")
    store_bytes(macrokit, "us_term", "gsw", b"g", url="u", filename="gsw.csv")
    store_bytes(macrokit, "us_term", "wuxia", b"w", url="u", filename="wuxia.xlsx")
    records = cli.input_records(raw, macrokit)
    assert set(records) == {"fred/DTB3", "etf/TLT", "us_term/gsw"}
    assert records["fred/DTB3"]["sha256"] == hashlib.sha256(b"new").hexdigest()
    assert cli.input_records(tmp_path / "none", tmp_path / "none") == {}
