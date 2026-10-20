import json
import subprocess
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from click.testing import CliRunner
from sector_leadlag import cli
from sector_leadlag import g0 as g0_module
from sector_leadlag import study as study_module
from sector_leadlag.corrections import KNOWN
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


CHANGE = {
    "rule": "C1",
    "kind": "etf",
    "series": "1629.T",
    "date": "2015-01-05",
    "field": "returns",
    "before": 0.002,
    "after": None,
}
CORRECTED_META = {
    **META,
    "git_commit": "abc",
    "data": "corrected",
    "inputs_digest": "d",
    "prereg_has_section_5": True,
    "record_main_b_committed_at": "2026-10-19T12:00:00+09:00",
}


def test_corrected_data_must_come_from_the_records_snapshot(tmp_path):
    write(tmp_path, "main_b", {"meta": {"inputs_digest": "d"}})
    cli.check_snapshot({"inputs_digest": "d"}, tmp_path)
    with pytest.raises(cli.StageError, match="snapshot of the record"):
        cli.check_snapshot({"inputs_digest": "e"}, tmp_path)


def test_corrected_stages_need_section_5_committed_after_the_record():
    cli.check_prereg_section(CORRECTED_META)
    with pytest.raises(cli.StageError, match="§5"):
        cli.check_prereg_section({**CORRECTED_META, "prereg_has_section_5": False})
    with pytest.raises(cli.StageError, match="after the record"):
        late = {**CORRECTED_META, "record_main_b_committed_at": "2026-10-20T11:00:00+09:00"}
        cli.check_prereg_section(late)


def test_corrected_stages_need_the_corrections_that_the_rules_make(tmp_path):
    with pytest.raises(cli.StageError, match=r"corrections\.json is missing"):
        cli.check_corrections((CHANGE,), tmp_path)
    write(tmp_path, "corrections", {"missing_known": [{"label": "x"}], "changes": [CHANGE]})
    with pytest.raises(cli.StageError, match="known-error check"):
        cli.check_corrections((CHANGE,), tmp_path)
    write(tmp_path, "corrections", {"missing_known": [], "changes": [CHANGE]})
    with pytest.raises(cli.StageError, match="does not match the rules"):
        cli.check_corrections(({**CHANGE, "date": "2015-01-06"},), tmp_path)
    assert len(cli.check_corrections((CHANGE,), tmp_path)) == 64


def _corrected_lab(tmp_path, monkeypatch):
    record = tmp_path / "results"
    corrected = record / "corrected"
    corrected.mkdir(parents=True)
    write(record, "main_b", {"meta": {"inputs_digest": "d"}, "verdict": "usable"})
    monkeypatch.setattr(cli, "RESULTS", record)
    monkeypatch.setattr(cli, "CORRECTED", corrected)

    def load(corrected=False):
        assert corrected, "a corrected run must not load the record's data"
        return SimpleNamespace(corrections=(CHANGE,))

    monkeypatch.setattr(study_module, "load_study", load)
    return record, corrected


def test_the_corrections_command_lists_the_changes_and_stops_on_a_missed_error(
    tmp_path, monkeypatch
):
    _, corrected = _corrected_lab(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "meta", lambda results="results": {**META, "inputs_digest": "d"})
    out = CliRunner().invoke(cli.main, ["corrections"])
    assert out.exit_code == 1 and "no rule changed these known errors" in out.output
    stored = json.loads((corrected / "corrections.json").read_text(encoding="utf-8"))
    assert stored["meta"]["data"] == "corrected" and stored["changes"] == [CHANGE]
    assert stored["counts"]["C1"] == {"etf": 1} and len(stored["missing_known"]) == len(KNOWN) - 1


def test_a_corrected_run_writes_only_under_results_corrected(tmp_path, monkeypatch):
    record, corrected = _corrected_lab(tmp_path, monkeypatch)
    write(corrected, "corrections", {"missing_known": [], "changes": [CHANGE]})
    monkeypatch.setattr(cli, "corrected_meta", lambda: dict(CORRECTED_META))
    monkeypatch.setattr(g0_module, "run_g0", lambda study, prior: {"pass": True})
    before = sorted(path.name for path in record.iterdir())
    out = CliRunner().invoke(cli.main, ["run", "g0", "--data", "corrected"])
    assert out.exit_code == 0, out.output
    written = json.loads((corrected / "g0.json").read_text(encoding="utf-8"))
    assert written["pass"] and written["meta"]["data"] == "corrected"
    assert len(written["meta"]["corrections_sha256"]) == 64
    assert sorted(path.name for path in record.iterdir()) == before


def test_corrected_meta_reads_section_5_from_the_committed_prereg(tmp_path, monkeypatch):
    lab = tmp_path / "lab"
    (lab / "results").mkdir(parents=True)
    git = ["git", "-C", str(lab), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    subprocess.run(["git", "init", "-q", str(lab)], check=True)

    def commit(path: str, text: str) -> None:
        (lab / path).write_text(text)
        subprocess.run([*git, "add", path], check=True)
        subprocess.run([*git, "-c", "commit.gpgsign=false", "commit", "-qm", path], check=True)

    commit("results/main_b.json", "{}")
    commit("PREREG.md", "## 4. x\n")
    monkeypatch.setattr(cli, "LAB", lab)
    monkeypatch.setattr(cli, "RAW_ROOT", tmp_path / "raw")
    first = cli.corrected_meta()
    assert first["data"] == "corrected" and not first["prereg_has_section_5"]
    assert first["record_main_b_commit"] and first["record_main_b_committed_at"][:4].isdigit()
    (lab / "PREREG.md").write_text("## 4. x\n## 5. y\n")
    assert not cli.corrected_meta()["prereg_has_section_5"]  # written, not committed
    commit("PREREG.md", "## 4. x\n## 5. y\n")
    assert cli.corrected_meta()["prereg_has_section_5"]
